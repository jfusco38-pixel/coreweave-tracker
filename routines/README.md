# ORACLE Sync routines

Two scheduled-task prompts:

| File | What it does |
|---|---|
| `oracle-sync.md` | Every weekday at 9:45 AM ET, replaces the IBKR "ORACLE" watchlist with the day's StocksToTrade Oracle 2.0 names priced at $0.90 or more, then sends one Telegram message. |
| `oracle-keepalive.md` | Every 4 hours, plus a weekday pre-flight at 8:15 AM ET. Keeps the StocksToTrade and IBKR sessions active, and sends a Telegram message if either one needs you to sign in. |

These must run on your PC in Claude Desktop / Cowork. Step 1 uses your signed-in Chrome, and a cloud session has no browser.

## One-time setup

1. **Create the bot.** In Telegram, message @BotFather, send `/newbot`, and copy the token.
2. **Get your chat ID.**
   - Send your new bot any message.
   - Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy `"chat":{"id": ...}`.
3. **Store both as user environment variables.** Don't put them in any file. In PowerShell, run:
   ```powershell
   setx TELEGRAM_BOT_TOKEN "<token>"
   setx TELEGRAM_CHAT_ID "<chat id>"
   ```
   Restart Claude Desktop so it picks them up.
4. **Test Telegram.** In a new PowerShell window, run:
   ```powershell
   curl.exe -s -X POST "https://api.telegram.org/bot$env:TELEGRAM_BOT_TOKEN/sendMessage" --data-urlencode "chat_id=$env:TELEGRAM_CHAT_ID" --data-urlencode "text=ORACLE Sync test"
   ```
   You should get `"ok":true` back and the message on your phone.
5. **Create three scheduled tasks** in Claude Desktop / Cowork:

   | Task | Schedule | Prompt |
   |---|---|---|
   | ORACLE Sync | `CRON_TZ=America/New_York 45 9 * * 1-5` | `oracle-sync.md` |
   | ORACLE Keep-Alive | `CRON_TZ=America/New_York 0 */4 * * *` | `oracle-keepalive.md` |
   | ORACLE Pre-flight | `CRON_TZ=America/New_York 15 8 * * 1-5` | `oracle-keepalive.md` |

   Each task needs:
   - the Chrome browser tool,
   - the IBKR connector, and
   - a shell (PowerShell) for the curl call.
6. **Do one supervised run** of ORACLE Sync by hand before turning the schedule on.

## Notes

- Your PC must be awake, with Chrome open, at the scheduled times. Tasks don't run while the PC is asleep.
- Keep-alive works only if StocksToTrade extends your session each time you visit (sliding expiry). That is inferred, not confirmed. If the site logs you out after a fixed time anyway, the 8:15 AM pre-flight message gives you 90 minutes to sign in before the sync.
- Both routines write a log at `%USERPROFILE%\oracle-sync\oracle-sync.log`.
- If you ever saved the Telegram token anywhere else, revoke it with @BotFather (`/revoke`).
