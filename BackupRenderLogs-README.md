# Render + Oanda Logs Backup

This script backs up **Render service logs** (via CLI/API) and **Oanda** data to the same folder for an end-to-end view: app logs plus Oanda component log and optional Oanda transaction history.

## Oanda backup (new)

- **Oanda app log:** Fetched from Config API (`CONFIG_API_BASE_URL` /logs/oanda), saved as `oanda_YYYY-MM-DD_HHmm.txt`. Same schedule as Render (5 AM / 5 PM).
- **Oanda transactions (optional):** If `OANDA_ACCESS_TOKEN` and `OANDA_ACCOUNT_ID` are set in the task environment, the script also calls the Oanda REST API for the last 24 hours of transactions and saves `oanda_transactions_YYYY-MM-DD_HHmm.json`. Set `OANDA_ENV` to `practice` or `live` (default `practice`). Set `CONFIG_API_BASE_URL` if your Config API is at a different URL (default `https://config-api-8n37.onrender.com`).

## Current status (404 on all log endpoints)

Render’s API returns **404** for every log URL we try (path-based only; query params cause 400). So **the script cannot download real log content via the API** for your account. The script still:

- Runs the Render CLI (several command variants) and the API attempts.
- When everything fails, writes a **placeholder file** per service (e.g. `config-api_2026-02-28_1817.txt`) with a short message, so your backup folder and scheduled task show that the script ran.
- Appends each failure to `error_log.txt`.

The script tries **two CLIs** in order: (1) the **official** Go-based CLI (`render logs`); (2) the Deno-based CLI (`render services tail --id`). Use the official one for reliable log backup.

## Use the official Render CLI (recommended)

There are two different Render CLIs:

| Source | Type | Logs command | Notes |
|--------|------|--------------|------|
| **[render-oss/cli](https://github.com/render-oss/cli)** | Go (official) | `render logs <serviceId> -o text` | In Render docs; no WebSocket/Deno issues. |
| render-oss/render-cli | Deno | `render services tail --id <serviceId>` | Can need `--unstable-net`; may hit WebSocketStream errors. |

**Install the official CLI on Windows**

1. Open **[github.com/render-oss/cli/releases](https://github.com/render-oss/cli/releases)** and download the latest Windows zip (e.g. `cli_1.x.x_windows_amd64.zip`).
2. Unzip it into a folder, e.g. `C:\Users\user\render-cli-official`.
3. Ensure the folder contains `render.exe` (or the single executable from the zip).
4. In `BackupRenderLogs.ps1` the config already has:
   - `$renderExePathOfficial = "C:\Users\user\render-cli-official\render.exe"`
   Change that path if you used a different folder.
5. Set `RENDER_API_KEY` and run the script; it will try the official CLI first, then the Deno one.

You can keep or remove the old Deno CLI; the script uses the official one when the path exists.

## Why backups weren’t appearing

1. **404 on logs API** – `error_log.txt` showed `(404) Not Found` for the logs URL. Render’s public API may not expose deploy logs at the paths we tried, or the path has changed. The script now tries several possible endpoints and logs failures.
2. **Backup folder** – The script now creates `Manual logs` if it doesn’t exist.
3. **Scheduled task** – Tasks often run with a different working directory and without your profile; the script no longer depends on the current directory and logs errors to `error_log.txt`.

## What was changed in the script

- **Backup directory** – Creates `C:\Users\user\Desktop\Test\Manual logs` if missing.
- **Multiple log URLs** – Tries four possible Render API paths for logs; if one works, logs are saved.
- **Error logging** – All failures (and 404 response bodies) are appended to `Manual logs\error_log.txt` with a timestamp.
- **Response handling** – If the API returns JSON (e.g. `logs`, `content`, `message`), the script extracts the log text before writing the file.
- **Render CLI fallback** – If the API never returns logs and `render` is in your PATH (with `RENDER_API_KEY` set or after `render login`), the script will try `render logs <serviceId> --output text` and save that output.
- **API key** – Prefers `RENDER_API_KEY` environment variable; falls back to the key in the script. **You should revoke the key that was in the script** (Dashboard → Account Settings → API Keys) and create a new one, then set it only in the scheduled task or in your environment.

## Backup timeframe (5 PM & 5 AM EST)

Your task runs **at 5:00 AM and 5:00 PM EST** (every 12 hours).

- The script requests up to **1,000 log lines** per service per run (`$logsLimit = 1000`). **Render’s API rejects higher values** (“invalid limit: too large”), so 1000 is the maximum. The CLI default is 100.
- **5 PM run** → file with the most recent 1000 lines (e.g. `service_2026-02-28_1700.txt`).
- **5 AM run** → same; the next snapshot.
- How much wall-clock time 1000 lines covers depends on how chatty each service is. Two runs per day give you two snapshots; together they cover more of the day than a single run.

You cannot increase `$logsLimit` beyond 1000 without the API returning an error.

**Strange characters in backup files:** If you see garbled prefixes (e.g. `=fôè`, `「\1`, `TÜán Å`) or odd symbols, they are usually **ANSI terminal color/format codes** from the CLI or your app’s logs. The script now (1) sets `NO_COLOR=1` when calling the CLI to reduce color output, and (2) **strips ANSI escape sequences** from the log text before writing. New backups should be cleaner. Any remaining odd characters may be from the app’s log format (e.g. Unicode symbols) or encoding; open the file in an editor that uses UTF-8 if needed. For longer history you’d need to use `--start` / `--end` if the CLI/API supports a time range (and the script doesn’t currently pass those).

## Scheduled task (5:00 AM / 5:00 PM EST)

1. **Set the API key in the task**  
   So the script doesn’t need a key in the file:
   - Open Task Scheduler → your task → Properties → General.
   - Option A: “Run whether user is logged on or not” and “Run with highest privileges” if needed; then in the Action, start the program with env set (e.g. a wrapper script that sets `$env:RENDER_API_KEY` and runs the script).
   - Option B: Use “Run only when user is logged on” and in a profile script set `[Environment]::SetEnvironmentVariable('RENDER_API_KEY', 'rnd_...', 'User')`, then log out and back in so the task runs with that user env.

2. **Start the script correctly**  
   - **For Oanda transaction backup (recommended):** Run the **wrapper** so the task has env vars:
     - Program: `powershell.exe`
     - Arguments: `-NoProfile -ExecutionPolicy Bypass -File "C:\Users\user\projects\personal\RunBackupRenderLogs.ps1"`
     - Start in: `C:\Users\user\projects\personal`
     - Create `BackupRenderLogs.env.ps1` (copy from `BackupRenderLogs.env.ps1.example`) and set `RENDER_API_KEY`, `OANDA_ACCESS_TOKEN`, `OANDA_ACCOUNT_ID`, `OANDA_ENV` there. Do not commit the `.env.ps1` file.
   - **Without Oanda env file:** If you run `BackupRenderLogs.ps1` directly, the task has no access to your session env, so `oanda_transactions_*.json` will not be created (only Render logs and `oanda_*.txt` from Config API).

3. **Redirect output to a log (optional)**  
   In the Action, you can log stdout/stderr to a file, e.g.  
   `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\user\projects\personal\BackupRenderLogs.ps1" >> "C:\Users\user\Desktop\Test\Manual logs\run_log.txt" 2>&1`

## 404 "page not found"

If you see **404 Not Found**: the script tries the CLI with both service ID and deploy ID, and several API paths. Your CLI uses `deploys` and `services` (no top-level `logs`). Use `.\render.exe -h`, then `.\render.exe deploys -h` and `.\render.exe services -h` to see subcommands (this CLI has no `help` command). Ensure the API key is for the same Render account that owns the services.

**400 "invalid path deployId"**: the script no longer uses the `?deployId=` query parameter; that was causing 400. If you still see 400, the API may not accept `?serviceId=` either—check `error_log.txt` for the exact API message.

## If the API never returns logs

Render’s REST API may not offer a “get deploy logs” endpoint that works with your key/plan. In that case:

1. **Use the Render CLI**  
   Install the CLI, run `render login` (or set `RENDER_API_KEY`), then from a command prompt run:
   ```powershell
   render logs <service-id> --output text
   ```
   You can wire this into the script (CLI fallback is already there if `render` is in PATH) or run it manually and redirect output to a file.

2. **Check Render docs**  
   Look at [List logs](https://api-docs.render.com/reference/list-logs) and any “log stream” or “events” APIs for your plan; the script’s URLs are based on common patterns and may need to match the latest docs.

## Quick test

Run the script manually from PowerShell. Set the API key in a **separate command** (or the same line with a semicolon), then run the script:

```powershell
cd C:\Users\user\projects\personal
$env:RENDER_API_KEY = "your-api-key"
.\BackupRenderLogs.ps1
```

Or one line:

```powershell
$env:RENDER_API_KEY = "your-api-key"; & "C:\Users\user\projects\personal\BackupRenderLogs.ps1"
```

Do not use `>>` before the API key; that redirects output to a file.

Then check:

- `C:\Users\user\Desktop\Test\Manual logs\` for new `*_yyyy-MM-dd_HHmm.txt` files.
- `C:\Users\user\Desktop\Test\Manual logs\error_log.txt` for any failure messages.

If you still see 404 for all services, the remaining option is to rely on the Render CLI (and ensure it’s on PATH when the scheduled task runs).
