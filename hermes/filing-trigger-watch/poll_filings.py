#!/usr/bin/env python3
"""Filing Trigger Watch poller.

Polls SEC EDGAR for new filings on the watchlist, classifies them with fixed
rules, dedupes by accession number, and sends Telegram alerts for the
interrupt tier. No AI model is called. Digest-tier filings are queued for the
Hermes 21:00 digest job; everything else goes to a silent log.

Usage:
    python poll_filings.py              # normal run (exits quietly outside market window)
    python poll_filings.py --dry-run    # print what would happen, send and save nothing
    python poll_filings.py --force      # ignore the market-hours window
    python poll_filings.py --backtest 90  # classify last 90 days, write CSV, send nothing

Requires Python 3.10+. On Windows also run: pip install tzdata
Telegram bot token is read from the TELEGRAM_BOT_TOKEN environment variable.
"""

import argparse
import csv
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:  # zoneinfo data missing (common on Windows)
    sys.exit("Time zone data missing. Run: pip install tzdata")

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"
INDEX_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{acc}-index.htm"
MIN_REQUEST_GAP = 0.15  # seconds; keeps us under 8 requests/sec to SEC
MAX_QUOTE_WORDS = 40
MAX_MESSAGE_CHARS = 900

INTERRUPT = "interrupt"
DIGEST = "digest"
LOG = "log"

# ---------------------------------------------------------------------------
# Classification rules
# ---------------------------------------------------------------------------

OFFERING_FORMS = {"S-1", "S-3", "S-3ASR", "F-1", "F-3", "424B4", "424B5"}
PERIODIC_FORMS = {"10-Q", "10-K"}
PROXY_PRELIM_FORMS = {"PRE 14A", "PRER14A"}
OWNERSHIP_FORMS = {"SC 13D", "SC 13G", "SCHEDULE 13D", "SCHEDULE 13G"}
DELIST_FORMS = {"25", "25-NSE"}

ATM_RE = re.compile(r"at[- ]the[- ]market|equity distribution agreement|sales agreement", re.I)
FINANCING_RE = re.compile(r"securities purchase agreement|purchase agreement|convertible|warrants?\b", re.I)
# Action wording only; plain mentions ("adjusted for reverse stock splits") are boilerplate
REVERSE_SPLIT_ACTION_RE = re.compile(
    r"(?:effect|effected|effecting|approve|approved|authorize|authorized|implement|implemented)\s+"
    r"(?:a|the)\s+reverse (?:stock )?split|reverse (?:stock )?split (?:ratio|proposal)"
    r"|\b1-for-\d+\b|\bone-for-(?:two|three|four|five|six|seven|eight|nine|ten|\w+teen|twenty|\w+ty)\b",
    re.I,
)
GOING_CONCERN_RE = re.compile(r"going concern", re.I)
OFFERING_LANGUAGE_RE = re.compile(
    r"at[- ]the[- ]market|aggregate offering price|we are offering|equity distribution agreement|sales agreement",
    re.I,
)
AUTHORIZED_INCREASE_RE = re.compile(
    r"increase (?:in )?(?:the )?(?:number of )?(?:our )?authorized (?:shares|capital|common stock)"
    r"|increase the (?:total )?number of authorized",
    re.I,
)
DOLLAR_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:million|billion))?", re.I)
SHARES_RE = re.compile(r"\b\d[\d,]{2,}\s+shares\b", re.I)
PRICE_RE = re.compile(r"(?:offering|purchase|exercise|conversion) price of \$\s?\d[\d,]*(?:\.\d+)?", re.I)


def split_form(form):
    form = (form or "").upper().strip()
    if form.endswith("/A"):
        return form[:-2], True
    return form, False


def parse_items(items):
    return {i.strip() for i in (items or "").split(",") if i.strip()}


def classify(form, items, text, prior_going_concern=None):
    """Return a list of (class_label, tier, regex_or_phrase) matches.

    form: EDGAR form type, e.g. "8-K", "S-3/A".
    items: comma-separated 8-K items string from EDGAR, e.g. "1.01,3.02".
    text: plain text of the primary document ("" if not fetched).
    prior_going_concern: True/False if the previous 10-Q/10-K mentioned going
        concern, None if unknown (then a mention is treated as new).
    """
    root, _amended = split_form(form)
    items = parse_items(items)
    text = text or ""
    hits = []

    def add(label, tier, pattern):
        if not any(h[0] == label for h in hits):
            hits.append((label, tier, pattern))

    # Offerings and shelf registrations
    if root in OFFERING_FORMS:
        if root == "424B5" and ATM_RE.search(text):
            add("DILUTION: ATM", INTERRUPT, ATM_RE)
        else:
            add("DILUTION", INTERRUPT, OFFERING_LANGUAGE_RE)
    if root == "EFFECT":
        add("DILUTION: SHELF EFFECTIVE", INTERRUPT, None)
    if root == "424B3":
        if OFFERING_LANGUAGE_RE.search(text):
            add("DILUTION", INTERRUPT, OFFERING_LANGUAGE_RE)
        else:
            add("PROSPECTUS (424B3)", DIGEST, None)

    if root == "8-K":
        if ATM_RE.search(text):
            add("DILUTION: ATM", INTERRUPT, ATM_RE)
        if "3.02" in items:
            add("DILUTION", INTERRUPT, "Item 3.02")
        if "1.01" in items and FINANCING_RE.search(text):
            add("FINANCING", INTERRUPT, FINANCING_RE)
        if "3.01" in items:
            add("LISTING RISK", INTERRUPT, "Item 3.01")
        if "4.01" in items or "4.02" in items:
            add("ACCOUNTING RISK", INTERRUPT, "Item 4.02" if "4.02" in items else "Item 4.01")
        if "5.03" in items and not REVERSE_SPLIT_ACTION_RE.search(text):
            add("CHARTER/BYLAW CHANGE", DIGEST, "Item 5.03")
        for item, label in (("2.02", "EARNINGS"), ("5.02", "OFFICER CHANGE"),
                            ("7.01", "REG FD"), ("8.01", "OTHER EVENT")):
            if item in items:
                add(label, DIGEST, f"Item {item}")

    # Reverse split: any form, but only when the text actually says it
    if REVERSE_SPLIT_ACTION_RE.search(text):
        add("REVERSE SPLIT", INTERRUPT, REVERSE_SPLIT_ACTION_RE)

    # Preliminary proxy asking to raise authorized shares: early dilution signal
    if root in PROXY_PRELIM_FORMS and AUTHORIZED_INCREASE_RE.search(text):
        add("DILUTION: AUTHORIZED SHARE INCREASE", INTERRUPT, AUTHORIZED_INCREASE_RE)

    # New going-concern language
    if root in PERIODIC_FORMS | {"8-K"} and GOING_CONCERN_RE.search(text) and not prior_going_concern:
        add("GOING CONCERN (new)", INTERRUPT, GOING_CONCERN_RE)

    if root in DELIST_FORMS:
        add("DELISTING (Form 25)", INTERRUPT, None)

    # Digest-only forms
    if root in {"4", "144"}:
        add("INSIDER" if root == "4" else "FORM 144", DIGEST, None)
    if root in OWNERSHIP_FORMS:
        add("OWNERSHIP (13D/13G)", DIGEST, None)
    if root in PERIODIC_FORMS or root == "DEF 14A":
        add("PERIODIC/PROXY - diff vs prior", DIGEST, None)
        if root == "DEF 14A" and AUTHORIZED_INCREASE_RE.search(text):
            add("AUTHORIZED SHARE INCREASE (definitive)", DIGEST, AUTHORIZED_INCREASE_RE)

    return hits


def tier_of(hits):
    tiers = {h[1] for h in hits}
    if INTERRUPT in tiers:
        return INTERRUPT
    if DIGEST in tiers:
        return DIGEST
    return LOG


def needs_text(form, items, is_core):
    """Whether a filing's primary document must be fetched to classify it."""
    root, _ = split_form(form)
    if root in {"EFFECT", "144"} | DELIST_FORMS | OWNERSHIP_FORMS:
        return False
    if root == "4":
        return is_core
    if root in OFFERING_FORMS | {"424B3", "8-K"} | PERIODIC_FORMS | PROXY_PRELIM_FORMS:
        return True
    if root == "DEF 14A":
        return True
    return False


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def html_to_text(raw):
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw).replace("\xa0", " ")
    return re.sub(r"\s+", " ", raw).strip()


def quote_around(text, pattern):
    """Verbatim <=40-word window around the first match. None if no match."""
    if not text or pattern is None:
        return None
    if isinstance(pattern, str):
        m = re.search(re.escape(pattern), text, re.I)
    else:
        m = pattern.search(text)
    if not m:
        return None
    before = text[:m.start()].split()[-15:]
    after = text[m.start():].split()[: MAX_QUOTE_WORDS - len(before)]
    return " ".join(before + after)


def extract_size(text, pattern):
    """Best-effort dollar amount / share count and price near the match."""
    if not text:
        return "not stated", None
    m = pattern.search(text) if pattern is not None and not isinstance(pattern, str) else (
        re.search(re.escape(pattern), text, re.I) if isinstance(pattern, str) else None)
    start = max(0, (m.start() if m else 0) - 600)
    window = text[start:start + 1800]
    size = None
    for d in DOLLAR_RE.finditer(window):  # skip par values and per-share prices
        amount = d.group(0)
        digits = re.sub(r"[^\d.]", "", re.sub(r"(?i)million|billion", "", amount)).strip(".")
        number = float(digits) if digits.count(".") <= 1 and digits else 0
        if re.search(r"million|billion", amount, re.I) or number >= 100000:
            size = amount
            break
    if size is None:
        shares = SHARES_RE.search(window)
        size = shares.group(0) if shares else "not stated"
    price = PRICE_RE.search(window)
    return size, (price.group(0) if price else None)


def parse_form4(xml_text, min_exercise_usd, min_open_market_usd):
    """Summarize qualifying Form 4 transactions. Returns list of strings."""
    out = []
    for block in re.findall(r"(?s)<nonDerivativeTransaction>.*?</nonDerivativeTransaction>", xml_text):
        code = re.search(r"<transactionCode>\s*(\w)\s*</transactionCode>", block)
        shares = re.search(r"(?s)<transactionShares>.*?<value>\s*([\d.]+)\s*</value>", block)
        price = re.search(r"(?s)<transactionPricePerShare>.*?<value>\s*([\d.]+)\s*</value>", block)
        if not code or not shares:
            continue
        code = code.group(1)
        n = float(shares.group(1))
        p = float(price.group(1)) if price else 0.0
        value = n * p
        if code in ("P", "S") and value >= min_open_market_usd:
            kind = "open-market BUY" if code == "P" else "open-market SELL"
        elif code == "M" and value >= min_exercise_usd:
            kind = "option exercise"
        else:
            continue
        out.append(f"{kind} {n:,.0f} sh @ ${p:,.2f} (${value:,.0f})")
    return out


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

class FetchError(Exception):
    pass


class Sec:
    def __init__(self, user_agent):
        self.user_agent = user_agent
        self._last = 0.0

    def get(self, url, as_json=False):
        for attempt in range(5):
            wait = MIN_REQUEST_GAP - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            req = urllib.request.Request(url, headers={
                "User-Agent": self.user_agent, "Accept-Encoding": "identity"})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    body = r.read().decode("utf-8", errors="replace")
                return json.loads(body) if as_json else body
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                raise
            except urllib.error.URLError:
                if attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                raise


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)


def send_telegram(token, chat_id, text):
    data = urllib.parse.urlencode({
        "chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("ok", False)
    except Exception as e:  # network error or bad token; keep the alert pending
        print(f"Telegram send failed: {e}", file=sys.stderr)
        return False


def load_config():
    if not CONFIG_PATH.exists():
        sys.exit(f"Missing {CONFIG_PATH}. Copy config.example.json to config.json and fill it in.")
    cfg = load_json(CONFIG_PATH, {})
    ua = cfg.get("sec_user_agent", "")
    if not ua or "<<<" in ua or "@" not in ua:
        sys.exit("Set sec_user_agent in config.json to your real name and email (SEC requires it).")
    core = [t.upper() for t in cfg.get("watchlist_core", []) if "<<<" not in t]
    rot = [t.upper() for t in cfg.get("watchlist_rotators", []) if "<<<" not in t]
    if not core and not rot:
        sys.exit("Watchlist is empty. Fill watchlist_core / watchlist_rotators in config.json.")
    cfg["watchlist_core"], cfg["watchlist_rotators"] = core, rot
    cfg["state_dir"] = Path(os.path.expanduser(cfg.get("state_dir", "~/.hermes/state")))
    cfg["log_dir"] = Path(os.path.expanduser(cfg.get("log_dir", "~/.hermes/logs")))
    return cfg


def in_window(cfg, now_et):
    w = cfg.get("market_window_et", {})
    if w.get("weekdays_only", True) and now_et.weekday() >= 5:
        return False
    start = datetime.strptime(w.get("start", "04:00"), "%H:%M").time()
    end = datetime.strptime(w.get("end", "20:00"), "%H:%M").time()
    return start <= now_et.time() <= end


def cik_map(sec, state_dir):
    cache = state_dir / "company_tickers.json"
    if not cache.exists() or time.time() - cache.stat().st_mtime > 7 * 86400:
        data = sec.get(TICKERS_URL, as_json=True)
        save_json(cache, data)
    else:
        data = load_json(cache, {})
    return {row["ticker"].upper(): int(row["cik_str"]) for row in data.values()}


def recent_filings(submissions):
    r = submissions.get("filings", {}).get("recent", {})
    keys = ["accessionNumber", "form", "filingDate", "acceptanceDateTime", "primaryDocument", "items"]
    n = len(r.get("accessionNumber", []))
    return [{k: (r.get(k) or [""] * n)[i] for k in keys} for i in range(n)]  # newest first


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

class Processor:
    def __init__(self, cfg, sec, dry_run=False):
        self.cfg = cfg
        self.sec = sec
        self.dry_run = dry_run
        self._text_cache = {}

    def doc_url(self, cik, f):
        return ARCHIVE_URL.format(cik=cik, acc_nodash=f["accessionNumber"].replace("-", ""),
                                  doc=f["primaryDocument"])

    def index_url(self, cik, f):
        return INDEX_URL.format(cik=cik, acc_nodash=f["accessionNumber"].replace("-", ""),
                                acc=f["accessionNumber"])

    def fetch_text(self, cik, f, raw_xml=False):
        acc = f["accessionNumber"]
        if acc in self._text_cache:
            return self._text_cache[acc]
        doc = f["primaryDocument"]
        if raw_xml:  # Form 4: drop the "xslF345X05/" rendering prefix to get raw XML
            doc = doc.split("/")[-1]
        try:
            body = self.sec.get(ARCHIVE_URL.format(cik=cik, acc_nodash=acc.replace("-", ""), doc=doc))
        except Exception as e:  # don't classify blind; caller retries next run
            raise FetchError(f"could not fetch {acc}: {e}") from e
        text = body if raw_xml else html_to_text(body)
        self._text_cache[acc] = text
        return text

    def prior_going_concern(self, cik, filings, idx):
        for f in filings[idx + 1:]:
            root, amended = split_form(f["form"])
            if root in PERIODIC_FORMS and not amended:
                return bool(GOING_CONCERN_RE.search(self.fetch_text(cik, f)))
        return None

    def evaluate(self, ticker, cik, filings, idx, is_core):
        """Classify one filing. Returns dict with tier, classes, quote, etc."""
        f = filings[idx]
        root, _ = split_form(f["form"])
        text = ""
        extra = []
        if needs_text(f["form"], f["items"], is_core):
            if root == "4":
                xml = self.fetch_text(cik, f, raw_xml=True)
                extra = parse_form4(xml, self.cfg.get("form4_min_option_exercise_usd", 50000),
                                    self.cfg.get("form4_min_open_market_usd", 25000))
            else:
                text = self.fetch_text(cik, f)
        prior_gc = None
        if root in PERIODIC_FORMS | {"8-K"} and GOING_CONCERN_RE.search(text):
            prior_gc = self.prior_going_concern(cik, filings, idx)
        hits = classify(f["form"], f["items"], text, prior_gc)
        if root == "4" and not extra:
            hits = [h for h in hits if h[0] != "INSIDER"]  # nothing above the size floors
        if not is_core:  # rotators: interrupt tier only
            hits = [h for h in hits if h[1] == INTERRUPT]
        tier = tier_of(hits)
        lead = next((h for h in hits if h[1] == tier), None)
        quote = None
        for h in hits:  # first matched pattern that yields a quote, interrupt first
            if h[1] == tier:
                quote = quote_around(text, h[2])
                if quote:
                    lead = h
                    break
        size, price = "", None
        if lead and lead[0].startswith(("DILUTION", "FINANCING")):
            size, price = extract_size(text, lead[2])
        return {
            "ticker": ticker, "accession": f["accessionNumber"], "form": f["form"],
            "items": f["items"], "filed": f["filingDate"], "accepted": f["acceptanceDateTime"],
            "classes": [h[0] for h in hits if h[1] == tier] if tier != LOG else [],
            "tier": tier, "quote": quote, "size": size, "price": price,
            "form4": extra, "url": self.index_url(cik, f),
            "prior5": "; ".join(f"{p['form']} {p['filingDate']}" for p in filings[idx + 1: idx + 6]),
        }


def format_alert(ev):
    accepted = ev["accepted"]
    try:
        t = datetime.fromisoformat(accepted.replace("Z", "+00:00")).astimezone(ET)
        when = t.strftime("%Y-%m-%d %H:%M ET")
    except Exception:
        when = ev["filed"]
    items = f" Item {ev['items']}" if ev["items"] else ""
    section = f"Item {ev['items']}" if ev["items"] else "primary document"
    quote = f'"{ev["quote"]}"' if ev["quote"] else "Not found in filing."
    size_line = f"Size: {ev['size'] or 'not stated'}"
    if ev["price"]:
        size_line += f" | Price/discount: {ev['price']}"
    lines = [
        f"\U0001F6A8 {ev['ticker']} | {' + '.join(ev['classes'])} | {ev['form']}{items} | {when}",
        f"[{ev['form']}, {ev['filed']}, {section}]: {quote}",
        size_line,
        f"Link: {ev['url']}",
        f"Prior 5 filings: {ev['prior5'] or 'none'}",
    ]
    msg = "\n".join(lines)
    if len(msg) > MAX_MESSAGE_CHARS:  # trim the quote, keep everything else
        over = len(msg) - MAX_MESSAGE_CHARS + 4
        lines[1] = lines[1][: max(40, len(lines[1]) - over)] + '..."'
        msg = "\n".join(lines)[:MAX_MESSAGE_CHARS]
    return msg


def log_line(cfg, ev, dry_run):
    line = f"{datetime.now(ET):%Y-%m-%d %H:%M} {ev['ticker']} {ev['form']} {ev['items']} {ev['accession']} {ev['url']}\n"
    if dry_run:
        print("LOG   ", line.strip())
        return
    cfg["log_dir"].mkdir(parents=True, exist_ok=True)
    with open(cfg["log_dir"] / "filings.log", "a", encoding="utf-8") as f:
        f.write(line)


def run(cfg, sec, dry_run):
    state_path = cfg["state_dir"] / "filings_seen.json"
    digest_path = cfg["state_dir"] / "digest_queue.json"
    state = load_json(state_path, None)
    first_run = state is None
    if first_run:
        state = {"seen": {}, "alerts_by_day": {}}
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = str(cfg.get("telegram_chat_id", ""))
    can_send = bool(token and chat_id and "<<<" not in chat_id)
    if not can_send and not dry_run:
        print("TELEGRAM_BOT_TOKEN or telegram_chat_id not set; interrupt alerts stay pending.", file=sys.stderr)

    today = datetime.now(ET).strftime("%Y-%m-%d")
    day = state["alerts_by_day"].setdefault(today, {"count": 0, "classes": {}, "warned": False})
    digest = load_json(digest_path, [])
    proc = Processor(cfg, sec, dry_run)
    ciks = cik_map(sec, cfg["state_dir"])
    core = set(cfg["watchlist_core"])

    def deliver(acc_state, ev_msg):
        if dry_run:
            print("ALERT ->\n" + ev_msg + "\n")
            return
        if can_send and send_telegram(token, chat_id, ev_msg):
            acc_state["status"] = "sent"
            acc_state.pop("msg", None)

    # Resend anything still pending from earlier runs
    for ticker, seen in state["seen"].items():
        for acc, s in seen.items():
            if isinstance(s, dict) and s.get("status") == "pending":
                deliver(s, s["msg"])

    for ticker in cfg["watchlist_core"] + cfg["watchlist_rotators"]:
        cik = ciks.get(ticker)
        if not cik:
            print(f"{ticker}: no CIK found on SEC ticker list, skipped", file=sys.stderr)
            continue
        try:
            filings = recent_filings(sec.get(SUBMISSIONS_URL.format(cik=cik), as_json=True))
        except Exception as e:
            print(f"{ticker}: submissions fetch failed: {e}", file=sys.stderr)
            continue
        seen = state["seen"].get(ticker)
        if seen is None:  # first run, or a ticker newly added: seed silently
            state["seen"][ticker] = {f["accessionNumber"]: {"status": "seeded"} for f in filings}
            print(f"{ticker}: seeded {len(filings)} existing filings (no alerts)")
            continue
        for idx in reversed(range(len(filings))):  # oldest new filing first
            f = filings[idx]
            if f["accessionNumber"] in seen:
                continue
            try:
                ev = proc.evaluate(ticker, cik, filings, idx, ticker in core)
            except FetchError as e:  # leave unseen so the next run retries it
                print(f"{ticker}: {e}", file=sys.stderr)
                continue
            if ev["tier"] == INTERRUPT:
                msg = format_alert(ev)
                acc_state = {"status": "pending", "msg": msg, "classes": ev["classes"]}
                seen[f["accessionNumber"]] = acc_state  # written before send
                if not dry_run:
                    save_json(state_path, state)
                deliver(acc_state, msg)
                day["count"] += 1
                for c in ev["classes"]:
                    day["classes"][c] = day["classes"].get(c, 0) + 1
            elif ev["tier"] == DIGEST:
                seen[f["accessionNumber"]] = {"status": "digest"}
                digest.append({k: ev[k] for k in ("ticker", "form", "items", "filed", "accession",
                                                   "classes", "quote", "form4", "url")})
                if dry_run:
                    print("DIGEST", ev["ticker"], ev["form"], ev["classes"], ev["form4"] or "")
            else:
                seen[f["accessionNumber"]] = {"status": "log"}
                log_line(cfg, ev, dry_run)

    limit = cfg.get("max_interrupts_per_day_before_warning", 5)
    if day["count"] > limit and not day["warned"]:
        top = max(day["classes"].items(), key=lambda kv: kv[1])[0] if day["classes"] else "n/a"
        warn = f"⚠️ Filter likely mis-tuned: {day['count']} interrupt alerts today. Top class: {top}."
        if dry_run:
            print(warn)
        elif can_send and send_telegram(token, chat_id, warn):
            day["warned"] = True

    # Keep 14 days of daily counters
    cutoff = (datetime.now(ET) - timedelta(days=14)).strftime("%Y-%m-%d")
    state["alerts_by_day"] = {d: v for d, v in state["alerts_by_day"].items() if d >= cutoff}

    if not dry_run:
        save_json(state_path, state)
        save_json(digest_path, digest)
    if first_run:
        print("First run complete: existing filings recorded, no alerts sent.")


def backtest(cfg, sec, days):
    since = (date.today() - timedelta(days=days)).isoformat()
    proc = Processor(cfg, sec, dry_run=True)
    ciks = cik_map(sec, cfg["state_dir"])
    core = set(cfg["watchlist_core"])
    out_path = cfg["log_dir"] / "backtest_alerts.csv"
    cfg["log_dir"].mkdir(parents=True, exist_ok=True)
    rows = 0
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["ticker", "filed", "accepted", "form", "items", "classes", "quote", "size", "url"])
        for ticker in cfg["watchlist_core"] + cfg["watchlist_rotators"]:
            cik = ciks.get(ticker)
            if not cik:
                print(f"{ticker}: no CIK found, skipped", file=sys.stderr)
                continue
            filings = recent_filings(sec.get(SUBMISSIONS_URL.format(cik=cik), as_json=True))
            for idx, f in enumerate(filings):
                if f["filingDate"] < since:
                    break
                try:
                    ev = proc.evaluate(ticker, cik, filings, idx, ticker in core)
                except FetchError as e:
                    print(f"{ticker}: {e} (skipped)", file=sys.stderr)
                    continue
                if ev["tier"] == INTERRUPT:
                    w.writerow([ticker, ev["filed"], ev["accepted"], ev["form"], ev["items"],
                                " + ".join(ev["classes"]), ev["quote"] or "Not found in filing.",
                                ev["size"], ev["url"]])
                    rows += 1
    print(f"Backtest: {rows} would-be interrupt alerts since {since} -> {out_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print actions; send and save nothing")
    ap.add_argument("--force", action="store_true", help="ignore the market-hours window")
    ap.add_argument("--backtest", type=int, metavar="DAYS", help="classify last DAYS of filings to CSV")
    args = ap.parse_args()

    cfg = load_config()
    sec = Sec(cfg["sec_user_agent"])
    if args.backtest:
        backtest(cfg, sec, args.backtest)
        return
    if not (args.force or args.dry_run) and not in_window(cfg, datetime.now(ET)):
        return
    run(cfg, sec, args.dry_run)


if __name__ == "__main__":
    main()
