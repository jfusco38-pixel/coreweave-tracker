# ORACLE Sync routines

Two scheduled-task prompts:

| File | What it does |
|---|---|
| `oracle-sync.md` | Every weekday at 9:45 AM ET, replaces the IBKR "ORACLE" watchlist with the day's StocksToTrade Oracle 2.0 names priced at $0.90 or more, then sends one Telegram message. |
| `oracle-keepalive.md` | Every 4 hours, plus a weekday pre-flight at 8:15 AM ET. Keeps the StocksToTrade and IBKR sessions active, and sends a Telegram message if either one needs you to sign in. |

These must run on your PC in Claude Desktop / Cowork. Step 1 uses your signed-in Chrome, and a cloud session has no browser.

## One-time setup

1. **Create a separate ORACLE bot.** In Telegram, message @BotFather, send `/newbot`, and copy the token.
   - Don't reuse Brovestor_bot.
   - Don't reuse `TELEGRAM_BOT_TOKEN`. Hermes reads that variable, and sharing it would make the two bots collide.
2. **Send the new bot `/start`.** A bot can't message you until you've messaged it first. Without this, sends fail with "chat not found".
3. **Chat ID:** `8207209026`. That's your Telegram user ID, which is also the chat ID for a direct chat with the bot.
4. **Store both as user environment variables.** Don't put them in any file. Paste the token straight into the command below; never paste it into a chat. In PowerShell, run:
   ```powershell
   setx ORACLE_BOT_TOKEN "<token>"
   setx ORACLE_CHAT_ID "8207209026"
   ```
   - Use `setx`, not `$env:ORACLE_BOT_TOKEN = ...`. The `$env:` form lasts only for the current PowerShell window, and the scheduled tasks need values that persist.
   - Restart Claude Desktop so it picks them up.
5. **Test Telegram.** In a new PowerShell window, run:
   ```powershell
   curl.exe -s -X POST "https://api.telegram.org/bot$env:ORACLE_BOT_TOKEN/sendMessage" --data-urlencode "chat_id=$env:ORACLE_CHAT_ID" --data-urlencode "text=ORACLE Sync test"
   ```
   You should get `"ok":true` back and the message on your phone.
6. **Create three scheduled tasks** in Claude Desktop / Cowork:

   | Task | Schedule | Prompt |
   |---|---|---|
   | ORACLE Sync | `CRON_TZ=America/New_York 45 9 * * 1-5` | `oracle-sync.md` |
   | ORACLE Keep-Alive | `CRON_TZ=America/New_York 0 */4 * * *` | `oracle-keepalive.md` |
   | ORACLE Pre-flight | `CRON_TZ=America/New_York 15 8 * * 1-5` | `oracle-keepalive.md` |

   Each task needs:
   - the Chrome browser tool,
   - the IBKR connector, and
   - a shell (PowerShell) for the curl call.
7. **Do one supervised run** of ORACLE Sync by hand before turning the schedule on.

## Notes

- Your PC must be awake, with Chrome open, at the scheduled times. Tasks don't run while the PC is asleep.
- Keep-alive works only if StocksToTrade extends your session each time you visit (sliding expiry). That is inferred, not confirmed. If the site logs you out after a fixed time anyway, the 8:15 AM pre-flight message gives you 90 minutes to sign in before the sync.
- Both routines write a log at `%USERPROFILE%\oracle-sync\oracle-sync.log`.
- If you ever saved the Telegram token anywhere else, revoke it with @BotFather (`/revoke`).
