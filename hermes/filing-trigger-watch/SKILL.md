---
name: filing-trigger-watch
description: Watch SEC EDGAR filings on the watchlist. A plain script (poll_filings.py) polls, classifies, dedupes and sends interrupt alerts with no model calls. This skill runs the low-frequency jobs - 21:00 digest, 08:30 ORACLE brief, Sunday review, one-time backtest - and merges sentiment only as a delta.
---

# Filing Trigger Watch

## What runs where
- **poll_filings.py (no AI, every 10 min via Windows Task Scheduler):** polls EDGAR,
  classifies with the table below, dedupes by accession number, sends INTERRUPT
  alerts to Telegram, queues DIGEST items to `~/.hermes/state/digest_queue.json`,
  logs everything else to `~/.hermes/logs/filings.log`.
- **This skill (Hermes, scheduled):** the digest (21:00 ET), the ORACLE brief
  (08:30 ET), the weekly review (Sunday 18:00 ET), and the one-time backtest.
- Never re-implement polling inside a Hermes job. If the script looks broken, say so
  and stop. Do not fall back to polling with the model.

## Config
All settings live in `config.json` next to this file (copy from `config.example.json`).
The Telegram bot token is in the `TELEGRAM_BOT_TOKEN` environment variable, never in a file.
Files:
- `~/.hermes/state/filings_seen.json`: owned by the script. Read only, never write it.
- `~/.hermes/state/digest_queue.json`: written by the script, emptied by the digest job.
- `~/.hermes/state/sentiment_baseline.json`: owned by this skill.
- `~/.hermes/state/oracle.txt`: the current ORACLE list, one ticker per line. <<<fill in>>>

## Hard rules
- Evidence from filings only. Every claim gets:
  [Form, filing date, item/section]: "exact quote" -> classification.
  No quote found = "Not found in filing."
- Never place, modify, or cancel orders. IBKR is read-only (prices and positions only).
- Max 8 requests/sec to SEC. Always send the User-Agent from config.json.
- Never alert on an accession number the script already marked `sent` in filings_seen.json.
- Do not send "no new filings" messages. Silence means nothing happened.

## Classification table (the script implements this; keep the two in sync)
Amended forms (`/A`) are treated the same as the original form.

INTERRUPT (Telegram immediately, one message per filing listing every class it hit):
- S-1, S-3, S-3ASR, F-1, F-3, 424B4, 424B5 -> DILUTION (offering / shelf)
- 424B5 or 8-K mentioning "at-the-market", "equity distribution agreement",
  "sales agreement" -> DILUTION: ATM
- 424B3 -> DILUTION only if it has offering language ("aggregate offering price",
  "we are offering", ATM terms). Otherwise DIGEST (usually resale or merger prospectus).
- EFFECT -> DILUTION: SHELF EFFECTIVE (a registration can now be used to sell stock)
- 8-K Item 3.02 (unregistered sales of equity) -> DILUTION
- 8-K Item 1.01 with "purchase agreement", "convertible", "warrant" -> FINANCING
- 8-K Item 3.01 (listing deficiency / delisting notice) -> LISTING RISK
- Any form with reverse-split action wording ("effect a reverse stock split",
  "1-for-20", "reverse split ratio") -> REVERSE SPLIT.
  A bare mention ("adjusted for reverse stock splits") does not count.
- PRE 14A / PRER14A proposing an increase in authorized shares
  -> DILUTION: AUTHORIZED SHARE INCREASE (early warning, weeks before the DEF 14A)
- 8-K Item 4.01/4.02 (auditor change / non-reliance) -> ACCOUNTING RISK
- 10-Q, 10-K or 8-K containing "going concern" when the prior 10-Q/10-K did not
  -> GOING CONCERN (new)
- Form 25 / 25-NSE -> DELISTING
- Trading halts are not SEC filings and are not covered. Not found in EDGAR.

DIGEST (core tickers only, batched for 21:00 ET):
- Form 4: open-market buys/sells at or above `form4_min_open_market_usd`, option
  exercises at or above `form4_min_option_exercise_usd`. Smaller ones are logged only.
- Form 144
- SC 13D / 13G and SCHEDULE 13D / 13G, plus amendments
- 8-K Item 2.02 (earnings), 5.02 (officer change), 7.01, 8.01, and 5.03 without reverse-split wording
- 10-Q, 10-K, DEF 14A: flagged for diff (see digest job)
- 424B3 without offering language

ROTATOR tickers: INTERRUPT classes only. Everything else is logged silently.

SILENT LOG: everything else, appended to `~/.hermes/logs/filings.log`.

## Interrupt alert format (sent by the script)
```
🚨 {TICKER} | {CLASS + CLASS} | {Form} {Item} | {accepted time ET}
[{Form}, {date}, {section}]: "{exact quote, <=40 words}"
Size: {$ amount or share count if stated, else "not stated"} | Price/discount: {if stated}
Link: {EDGAR index URL}
Prior 5 filings: {forms + dates}
```
Under 900 characters. No commentary. Quotes are copied verbatim from the document
text, with whitespace collapsed.

## Job: 21:00 ET digest
1. Read `digest_queue.json`. If empty, send nothing and stop.
2. Group by ticker. One line per item: form, items, date, class, link.
   Form 4 lines include the transaction summaries already in the queue entry.
3. For each 10-Q, 10-K or DEF 14A: open it and the prior filing of the same form.
   Report only changes in share count, authorized shares, cash and burn, debt terms,
   and new risk factors, each with a quote from both filings. Nothing changed = say so in one line.
4. Add the sentiment deltas (below) at the end.
5. Send as one Telegram message (split only if over 4,000 characters).
6. Move the processed entries to `~/.hermes/state/digest_archive.json` and empty the queue.

## Sentiment / news merge (delta only)
- Source: Stocktwits message volume and sentiment. <<<confirm this is the source you want>>>
- Keep a 20-session rolling baseline per ticker in `sentiment_baseline.json`.
- Report ONLY if volume > 3x baseline OR sentiment moves > 2 standard deviations from baseline.
- Label it:
  - Coincides with a filing (filings_seen.json / digest queue) or dated news in the last
    24h -> "CATALYST-BACKED"
  - No filing, no news -> "UNEXPLAINED SPIKE - pump risk"
- Sentiment never triggers an interrupt. Plain bullish/bearish readings with no delta are never sent.

## Job: 08:30 ET ORACLE crossover brief
Surface only names that meet ALL of:
1. In `oracle.txt`
2. No DILUTION / FINANCING / REVERSE SPLIT / GOING CONCERN alert in the last 30 days
   (check `classes` on `sent`/`pending` entries in filings_seen.json, and the EDGAR filing list)
3. A dated catalyst within the next 14 days (earnings, offering close, FDA or contract
   date, lease start, conference), with a quote and source for the date
Format per name: TICKER | float if known | last filing + date | catalyst + date.
Then list, separately, ORACLE names that FAIL rule 2, with the filing that
disqualified them. That second list is the one that saves money.

## Alert discipline (script handles the first two)
- Dedupe by accession number. Never repeat.
- More than 5 interrupts in one day -> one "Filter likely mis-tuned" warning naming
  the top class.
- In the weekly review, suggest which rule caused the most noise.

## Job: weekly self-review (Sunday 18:00 ET)
For each interrupt alert in the last 7 days (entries with status `sent` in
filings_seen.json, matched to their accepted time), get the stock's % move at +1, +2
and +3 sessions from IBKR (read-only price history). Report hit count by class,
average move by class, false positives, and one suggested filter change.
Save to `~/.hermes/logs/review.md`.

## Job: one-time backtest (run once after install)
1. Run `python poll_filings.py --backtest 90`. It writes
   `~/.hermes/logs/backtest_alerts.csv` and sends nothing.
2. For each row, get the +1/+2/+3 session move from IBKR (read-only).
3. Output a table: ticker, date, class, move +1/+2/+3, plus averages by class.
   No Telegram messages during the backtest.
