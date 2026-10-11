# Filing Trigger Watch: Windows setup

Two parts:
- `poll_filings.py` checks SEC EDGAR every 10 minutes and sends urgent alerts to Telegram.
  It never calls an AI model, so it doesn't use any of your Claude plan.
- `SKILL.md` is the Hermes skill for the jobs that need the model: the 21:00 digest,
  the 08:30 ORACLE brief, the Sunday review, and the one-time backtest.

## 1. Install Python and copy the files
1. Install Python 3.10 or newer from python.org (tick "Add Python to PATH").
2. In PowerShell: `pip install tzdata` (Windows needs it for Eastern time).
3. Copy this whole folder to your Hermes skills folder, usually:
   `C:\Users\<you>\.hermes\skills\filing-trigger-watch\`

## 2. Fill in config.json
Copy `config.example.json` to `config.json` in the same folder and replace every `<<<...>>>`:
- `watchlist_core`: names that get every alert type plus the digest.
- `watchlist_rotators`: names that only get urgent (interrupt) alerts.
- `sec_user_agent`: your real name and email, e.g. `"Jane Doe jane@example.com"`. SEC blocks requests without it.
- `telegram_chat_id`: see step 3.

## 3. Telegram
1. If Hermes already sends you Telegram messages, reuse that bot token. Otherwise
   create a bot with @BotFather in Telegram and copy the token.
2. Send your bot any message, then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser.
   The number after `"chat":{"id":` is your chat ID. Put it in config.json.
3. Save the token as an environment variable (not in any file):
   ```powershell
   setx TELEGRAM_BOT_TOKEN "123456:ABC..."
   ```
   Close and reopen PowerShell afterwards. Sign out and back in so Task Scheduler picks it up too.

## 4. First run (silent) and a test
```powershell
cd $HOME\.hermes\skills\filing-trigger-watch
python poll_filings.py --dry-run     # shows what it would do; sends and saves nothing
python poll_filings.py --force       # first real run: records existing filings, sends NO alerts
```
After the first real run, only filings that appear later will alert.
Adding a ticker later works the same way: its existing filings are recorded silently.

## 5. Schedule it every 10 minutes
The script exits by itself outside Mon-Fri 04:00-20:00 Eastern, so it's safe to run all day:
```powershell
$py = (Get-Command pythonw).Source
$script = "$HOME\.hermes\skills\filing-trigger-watch\poll_filings.py"
schtasks /Create /TN "FilingTriggerWatch" /SC MINUTE /MO 10 /TR "`"$py`" `"$script`"" /F
```
The computer has to be on and you have to be signed in for it to run.
To remove it later: `schtasks /Delete /TN "FilingTriggerWatch" /F`

## 6. Schedule the Hermes jobs
In a Hermes chat, ask in plain English, for example:
- "Using the filing-trigger-watch skill, run the digest job every weekday at 21:00 Eastern."
- "Run the filing-trigger-watch ORACLE brief every weekday at 08:30 Eastern."
- "Run the filing-trigger-watch weekly review every Sunday at 18:00 Eastern."
- Once: "Run the filing-trigger-watch one-time backtest."

Also fill in `~/.hermes/state/oracle.txt` (one ticker per line) before the first brief.

## Files it creates (in `C:\Users\<you>\.hermes\`)
| File | What it is |
|---|---|
| `state\filings_seen.json` | Every filing already handled (`seeded`, `pending`, `sent`, `digest`, `log`) |
| `state\digest_queue.json` | Items waiting for the 21:00 digest |
| `state\company_tickers.json` | SEC ticker-to-CIK list, refreshed weekly |
| `logs\filings.log` | Filings that didn't need a message |
| `logs\backtest_alerts.csv` | Output of `--backtest` |

## Good to know
- If a Telegram send fails, the alert stays `pending` and is retried on the next run. You won't get duplicates.
- Quotes are copied word for word from the filing, with extra spaces and line breaks removed.
- "Size" is a best guess: the first dollar amount of $100k or more, or the first share count, near the matched text.
  Always check the link.
- Trading halts aren't SEC filings, so they aren't covered.
