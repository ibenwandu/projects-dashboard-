# Backup Render service logs and Oanda data to a local folder.
# For scheduled tasks: set RENDER_API_KEY (and optionally OANDA_ACCESS_TOKEN, OANDA_ACCOUNT_ID) in the task's environment.

# --- Configuration ---
if (-not $env:RENDER_API_KEY) {
    Write-Host "RENDER_API_KEY not set in environment - Render log backup may fail with 401. Set it for scheduled task or run: `$env:RENDER_API_KEY = 'your-key'" -ForegroundColor Yellow
}
$apiKey = if ($env:RENDER_API_KEY) { $env:RENDER_API_KEY.Trim() } else { "rnd_kh38hOHbdIrl8jGEovbYNRSsxBtt" }
$backupDir = "C:\Users\user\Desktop\Test\Manual logs"
$archiveDir = "C:\Users\user\Desktop\Test\Manual Logs Archive"
$hygieneExcludeFileName = "Additional quality checks to review using the Logs.txt"
$hygieneDaysToKeep = 7
$errorLogPath = Join-Path $backupDir "error_log.txt"
# Prefer official Render CLI (Go, from https://github.com/render-oss/cli/releases) - has "render logs"
$renderExePathOfficial = "C:\Users\user\render-cli-official\render.exe"
# Fallback: Deno-based CLI (render-oss/render-cli) - has "render services tail --id"
$renderExePath = "C:\Users\user\render-cli\render.exe"
# Max log lines per backup. Render API caps at 1000 (higher returns "invalid limit: too large").
$logsLimit = 1000
$headers = @{
    "Authorization" = "Bearer $apiKey"
    "Accept"        = "application/json"
}

# --- Oanda backup (Config API log + optional Oanda API transactions) ---
# Config API base URL for Oanda/engine/ui logs (same Render app that serves logs to the UI).
$configApiBase = if ($env:CONFIG_API_BASE_URL) { $env:CONFIG_API_BASE_URL.TrimEnd("/") } else { "https://config-api-8n37.onrender.com" }
# Oanda API: set OANDA_ACCESS_TOKEN and OANDA_ACCOUNT_ID to also backup transaction history. OANDA_ENV = "practice" or "live".
# Account ID format: usually XXX-XXX-XXXXXXX-XXX (with dashes). Trimmed to avoid 400 "Invalid value specified for 'accountID'".
$oandaToken = if ($env:OANDA_ACCESS_TOKEN) { $env:OANDA_ACCESS_TOKEN.Trim() } else { $null }
$oandaAccountId = if ($env:OANDA_ACCOUNT_ID) { $env:OANDA_ACCOUNT_ID.Trim() } else { $null }
if ($oandaAccountId -eq "") { $oandaAccountId = $null }
$oandaEnv = if ($env:OANDA_ENV -eq "live") { "live" } else { "practice" }
$oandaApiBase = if ($oandaEnv -eq "live") { "https://api-fxtrade.oanda.com" } else { "https://api-fxpractice.oanda.com" }
# Transaction backup: last N hours (max 365 days per Oanda API).
$oandaTransactionsHoursBack = 24

# Ensure backup directory exists
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
}

# Show what we're using (so you can verify env vars in the same terminal)
$renderKeySource = if ($env:RENDER_API_KEY) { "env (length $($apiKey.Length))" } else { "fallback in script (length $($apiKey.Length)) - may be revoked, set RENDER_API_KEY" }
Write-Host "Render: API key from $renderKeySource" -ForegroundColor Gray
if ($oandaToken -and $oandaAccountId) {
    Write-Host "Oanda: accountID='$oandaAccountId' env=$oandaEnv" -ForegroundColor Gray
} else {
    Write-Host "Oanda: transactions skipped (OANDA_ACCESS_TOKEN or OANDA_ACCOUNT_ID not set)" -ForegroundColor Gray
}

function Write-ErrorLog {
    param([string]$Message)
    $line = "{0:yyyy-MM-dd HH:mm:ss}: {1}" -f (Get-Date), $Message
    Add-Content -Path $errorLogPath -Value $line -Encoding utf8
}

# Strip ANSI escape sequences (terminal color/formatting) so backup files are plain text
function Remove-AnsiSequences {
    param([string]$Text)
    if (-not $Text) { return $Text }
    # CSI sequences: ESC [ ... letter (e.g. [32m for green)
    $Text = [regex]::Replace($Text, "\x1B\[[0-9;]*[a-zA-Z]", "")
    # Other common escapes (cursor, etc.)
    $Text = [regex]::Replace($Text, "\x1B\[[?0-9;]*[a-zA-Z]", "")
    $Text = [regex]::Replace($Text, "\x1B[=0-9;]*[a-zA-Z]", "")
    return $Text
}

# --- Service List ---
$services = @{
    "config-api"        = "srv-d5mo8v56ubrc73ac4r3g"
    "market-state-api"  = "srv-d5hept7pm1nc73d96l60"
    "scalp-engine-ui"   = "srv-d5h6qbkhg0os73fpltlg"
    "scalp-engine"      = "srv-d5h6qbkhg0os73fpltl0"
    "trade-alerts"      = "srv-d56v9tshg0os73auoo3g"
}

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmm"

# Official CLI needs a workspace; get first workspace (owner) ID from API and set it once
$workspaceId = $null
try {
    $ownersResp = Invoke-RestMethod -Uri "https://api.render.com/v1/owners" -Headers $headers -Method Get -ErrorAction Stop
    if ($ownersResp.owner) { $workspaceId = $ownersResp.owner.id }
    elseif ($ownersResp -is [array] -and $ownersResp.Count -gt 0) { $workspaceId = $ownersResp[0].id }
} catch { }
if ($workspaceId -and $renderExePathOfficial -and (Test-Path $renderExePathOfficial)) {
    $env:RENDER_API_KEY = $apiKey
    $env:CI = "true"
    $null = & $renderExePathOfficial workspace set $workspaceId --confirm 2>&1
}

foreach ($name in $services.Keys) {
    $id = $services[$name]
    $filePath = Join-Path $backupDir "$name`_$timestamp.txt"

    try {
        # 1. Get the latest deploy for the service
        $deployUrl = "https://api.render.com/v1/services/$id/deploys?limit=1"
        $deployList = Invoke-RestMethod -Uri $deployUrl -Headers $headers -Method Get -ErrorAction Stop
        if (-not $deployList -or $deployList.Count -eq 0) {
            Write-ErrorLog "No deploys for $name"
            Write-Host "No deploys for $name" -ForegroundColor Yellow
            continue
        }
        $deployId = $deployList[0].id

        $logContent = $null
        $tailTimeoutSec = 12

        function Test-ValidLogContent {
            param([string]$text)
            if (-not $text -or $text.Length -eq 0) { return $false }
            if ($text -match "Usage:\s*render") { return $false }
            if ($text -match "Missing required option") { return $false }
            if ($text -match "WebSocketStream is not defined") { return $false }
            if ($text -match "unstable-net") { return $false }
            if ($text -match "404 page not found") { return $false }
            if ($text.Trim() -match "^\d+\s+page not found\s*$") { return $false }
            return $true
        }

        # 2. Prefer official Render CLI (Go, render-oss/cli): "render logs <serviceId> -o text"
        $cliCandidates = @()
        if ($renderExePathOfficial -and (Test-Path $renderExePathOfficial)) {
            # Official CLI: -r/--resources required; --limit so each run gets ~12h of logs (5 PM + 5 AM = 24h coverage)
            $cliCandidates += @{ Cmd = $renderExePathOfficial; Args = @(
                @("logs", "-r", $id, "-o", "text", "--confirm", "--limit", [string]$logsLimit),
                @("logs", "--resources", $id, "-o", "text", "--confirm", "--limit", [string]$logsLimit),
                @("logs", "-r", $id, "-o", "text", "--limit", [string]$logsLimit),
                @("logs", "--resources", $id, "-o", "text", "--limit", [string]$logsLimit),
                @("logs", "-r", $id, "--confirm", "--limit", [string]$logsLimit),
                @("logs", "-r", $id, "-o", "text", "--confirm")
            ) }
        }
        if ($renderExePath -and (Test-Path $renderExePath)) {
            $cliCandidates += @{ Cmd = $renderExePath; Args = @(
                @("--unstable-net", "services", "tail", "--id", $id, "--non-interactive", "--raw"),
                @("--unstable-net", "services", "tail", "--id", $id, "--raw"),
                @("services", "tail", "--id", $id, "--non-interactive", "--raw"),
                @("services", "tail", "--id", $id, "--raw")
            ) }
        }
        $renderFromPath = Get-Command "render" -ErrorAction SilentlyContinue
        if ($renderFromPath -and $renderFromPath.Source -and (Test-Path $renderFromPath.Source)) {
            $cliCandidates += @{ Cmd = $renderFromPath.Source; Args = @(@("logs", "-r", $id, "-o", "text", "--confirm", "--limit", [string]$logsLimit), @("logs", "-r", $id, "-o", "text", "--limit", [string]$logsLimit)) }
        }

        foreach ($cli in $cliCandidates) {
            $renderCmd = $cli.Cmd
            $env:RENDER_API_KEY = $apiKey
            $env:CI = "true"
            $env:RENDER_OUTPUT = "text"
            $env:NO_COLOR = "1"
            foreach ($argList in $cli.Args) {
                try {
                    $isTail = ($argList -join " ") -match "tail"
                    if ($isTail) {
                        $job = Start-Job -ScriptBlock {
                            param($key, $cmd, $argList)
                            $env:RENDER_API_KEY = $key
                            $env:CI = "true"
                            & $cmd @argList 2>&1
                        } -ArgumentList $apiKey, $renderCmd, $argList
                        $null = Wait-Job $job -Timeout $tailTimeoutSec
                        $logContent = Receive-Job $job
                        Stop-Job $job -ErrorAction SilentlyContinue
                        Remove-Job $job -Force -ErrorAction SilentlyContinue
                    } else {
                        $logContent = & $renderCmd @argList 2>&1
                    }
                    if ($logContent) {
                        if ($logContent -is [array]) { $logContent = $logContent -join "`n" }
                        $logContent = $logContent.Trim()
                        if (Test-ValidLogContent $logContent) { break }
                    }
                    $logContent = $null
                } catch { $logContent = $null }
            }
            if ($logContent) { break }
        }

        if (-not $logContent) {
            # Fallback: try API log endpoints (Render may use different path/query)
            $lastError = $null
            $lastResponseBody = $null
            # Only path-based URLs: API rejects query params "deployId" and "serviceId" with 400
            $logUrls = @(
                "https://api.render.com/v1/services/$id/deploys/$deployId/logs",
                "https://api.render.com/v1/deploys/$deployId/logs",
                "https://api.render.com/v1/services/$id/logs"
            )
            foreach ($logUrl in $logUrls) {
                try {
                    $response = Invoke-WebRequest -Uri $logUrl -Headers $headers -Method Get -UseBasicParsing -ErrorAction Stop
                    if ($response.StatusCode -eq 200) {
                        $raw = $response.Content
                        if ($raw.TrimStart().StartsWith("{")) {
                            try {
                                $obj = $raw | ConvertFrom-Json
                                if ($obj.logs)        { $logContent = $obj.logs -join "`n"; break }
                                if ($obj.content)     { $logContent = $obj.content; break }
                                if ($obj.message)     { $logContent = $obj.message; break }
                                if ($obj -is [array]) { $logContent = ($obj | ForEach-Object { if ($_.message) { $_.message } else { $_ } }) -join "`n"; break }
                            } catch { }
                        }
                        if ($null -eq $logContent) { $logContent = $raw }
                        break
                    }
                } catch {
                    $lastError = $_.Exception.Message
                    if ($_.ErrorDetails.Message) { $lastResponseBody = $_.ErrorDetails.Message }
                    elseif ($_.Exception.Response) {
                        try {
                            $stream = $_.Exception.Response.GetResponseStream()
                            if ($stream) {
                                $reader = New-Object System.IO.StreamReader($stream)
                                $lastResponseBody = $reader.ReadToEnd()
                                $reader.Close()
                            }
                        } catch { }
                    }
                }
            }
            if ($lastResponseBody) { $lastError = ($lastError + " | API: " + $lastResponseBody.Trim().Substring(0, [Math]::Min(400, $lastResponseBody.Trim().Length))) }
        }

        if ($logContent) {
            $logContent = Remove-AnsiSequences $logContent
            [System.IO.File]::WriteAllText($filePath, $logContent, [System.Text.UTF8Encoding]::new($false))
            Write-Host "Archived logs for $name" -ForegroundColor Green
        } else {
            $errMsg = if ($lastError) { $lastError } else { "No log content returned (CLI and API failed)" }
            if ($errMsg -match "401|Unauthorized") { $errMsg += " [Check RENDER_API_KEY is set and valid.]" }
            Write-ErrorLog "Failed $name - $errMsg"
            Write-Host "Failed to fetch logs for $name - $errMsg" -ForegroundColor Red
            # Placeholder so the backup folder shows something for this run (Render API returns 404 for logs)
            $placeholder = "Render logs could not be fetched for $name at $timestamp.`r`nAPI and CLI attempts failed. See error_log.txt for details."
            [System.IO.File]::WriteAllText($filePath, $placeholder, [System.Text.UTF8Encoding]::new($false))
        }
    } catch {
        $msg = $_.Exception.Message
        if ($_.Exception.Response) {
            try {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $msg += " | " + $reader.ReadToEnd()
                $reader.Close()
            } catch { }
        }
        if ($msg -match "401|Unauthorized") { $msg += " [Check RENDER_API_KEY is set and valid.]" }
        Write-ErrorLog "Failed $name - $msg"
        Write-Host "Failed to fetch logs for $name - $msg" -ForegroundColor Red
    }
}

# --- Oanda: Config API log (app log from Scalp-Engine Oanda component) ---
$oandaLogPath = Join-Path $backupDir "oanda_$timestamp.txt"
try {
    $oandaLogUrl = "$configApiBase/logs/oanda"
    $response = Invoke-WebRequest -Uri $oandaLogUrl -Method Get -UseBasicParsing -TimeoutSec 15 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        $content = if ($response.Content) { Remove-AnsiSequences $response.Content.Trim() } else { "" }
        if (-not $content) { $content = "(Oanda app log empty - Config API returned 200 with no content. No Oanda client activity in this period, or log not yet pushed.)" }
        [System.IO.File]::WriteAllText($oandaLogPath, $content, [System.Text.UTF8Encoding]::new($false))
        Write-Host "Archived Oanda log (Config API)" -ForegroundColor Green
    } else {
        $placeholder = "Oanda log could not be fetched at $timestamp (Config API returned $($response.StatusCode))."
        [System.IO.File]::WriteAllText($oandaLogPath, $placeholder, [System.Text.UTF8Encoding]::new($false))
        Write-ErrorLog "Oanda log: Config API returned $($response.StatusCode)"
    }
} catch {
    $errMsg = $_.Exception.Message
    if ($_.Exception.Response) {
        try {
            $stream = $_.Exception.Response.GetResponseStream()
            if ($stream) {
                $reader = New-Object System.IO.StreamReader($stream)
                $errMsg += " | " + $reader.ReadToEnd()
                $reader.Close()
            }
        } catch { }
    }
    Write-ErrorLog "Oanda log failed - $errMsg"
    Write-Host "Oanda log: $errMsg" -ForegroundColor Yellow
    $placeholder = "Oanda log could not be fetched at $timestamp. Config API error: $errMsg"
    [System.IO.File]::WriteAllText($oandaLogPath, $placeholder, [System.Text.UTF8Encoding]::new($false))
}

# --- Oanda: Transaction history from Oanda API (optional; requires OANDA_ACCESS_TOKEN and OANDA_ACCOUNT_ID) ---
if ($oandaToken -and $oandaAccountId) {
    $oandaTxPath = Join-Path $backupDir "oanda_transactions_$timestamp.json"
    try {
        $toDt = [DateTime]::UtcNow
        $fromDt = $toDt.AddHours(-$oandaTransactionsHoursBack)
        $fromStr = $fromDt.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $toStr = $toDt.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $fromEnc = [uri]::EscapeDataString($fromStr)
        $toEnc = [uri]::EscapeDataString($toStr)
        $listUrl = "$oandaApiBase/v3/accounts/$oandaAccountId/transactions?from=$fromEnc&to=$toEnc&pageSize=1000"
        $authHeaders = @{
            "Authorization" = "Bearer $oandaToken"
            "Accept-Datetime-Format" = "RFC3339"
            "Content-Type" = "application/json"
        }
        $listResp = Invoke-RestMethod -Uri $listUrl -Headers $authHeaders -Method Get -ErrorAction Stop
        $allTransactions = @()
        if ($listResp.pages -and $listResp.pages.Count -gt 0) {
            foreach ($pageUrl in $listResp.pages) {
                try {
                    $pageResp = Invoke-RestMethod -Uri $pageUrl -Headers $authHeaders -Method Get -ErrorAction Stop
                    if ($pageResp.transactions) { $allTransactions += $pageResp.transactions }
                } catch { Write-ErrorLog "Oanda transactions page failed - $($_.Exception.Message)" }
            }
        }
        $payload = @{
            from = $fromStr
            to = $toStr
            count = $listResp.count
            lastTransactionID = $listResp.lastTransactionID
            transactions = $allTransactions
        } | ConvertTo-Json -Depth 20
        [System.IO.File]::WriteAllText($oandaTxPath, $payload, [System.Text.UTF8Encoding]::new($false))
        Write-Host "Archived Oanda transactions ($($allTransactions.Count) in range)" -ForegroundColor Green
    } catch {
        $errMsg = $_.Exception.Message
        if ($_.ErrorDetails.Message) { $errMsg += " | " + $_.ErrorDetails.Message }
        if ($errMsg -match "accountID|Invalid value") { $errMsg += " [Check OANDA_ACCOUNT_ID format: usually XXX-XXX-XXXXXXX-XXX from Oanda account dashboard.]" }
        if ($errMsg -match "403|Forbidden") { $errMsg += " [Oanda token may lack account access or be for wrong env (practice vs live). Create a new token at Oanda Developer with Account scope.]" }
        Write-ErrorLog "Oanda transactions failed - $errMsg"
        Write-Host "Oanda transactions: $errMsg" -ForegroundColor Red
        $placeholder = "{ `"error`": `"Oanda API failed at $timestamp`", `"message`": `"$($errMsg -replace '"','\"')`" }"
        [System.IO.File]::WriteAllText($oandaTxPath, $placeholder, [System.Text.UTF8Encoding]::new($false))
    }
} else {
    Write-Host "Oanda API credentials not set (OANDA_ACCESS_TOKEN, OANDA_ACCOUNT_ID) - skipping transaction backup." -ForegroundColor Gray
}

# --- Hygiene: move files older than N days to Manual Logs Archive (exclude specific file) ---
try {
    if (-not (Test-Path $backupDir)) { return }
    $cutoff = (Get-Date).AddDays(-$hygieneDaysToKeep)
    $toArchive = @(Get-ChildItem -Path $backupDir -File -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $cutoff -and $_.Name -ne $hygieneExcludeFileName })
    if ($toArchive.Count -eq 0) {
        Write-Host "Hygiene: no files older than $hygieneDaysToKeep days to archive." -ForegroundColor Gray
    } else {
        if (-not (Test-Path $archiveDir)) {
            New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
        }
        $moved = 0
        foreach ($f in $toArchive) {
            try {
                Move-Item -LiteralPath $f.FullName -Destination (Join-Path $archiveDir $f.Name) -Force -ErrorAction Stop
                $moved++
            } catch {
                Write-ErrorLog "Hygiene: failed to move $($f.Name) - $($_.Exception.Message)"
            }
        }
        Write-Host "Hygiene: moved $moved file(s) older than $hygieneDaysToKeep days to Manual Logs Archive." -ForegroundColor Green
    }
} catch {
    Write-ErrorLog "Hygiene failed - $($_.Exception.Message)"
    Write-Host "Hygiene: $($_.Exception.Message)" -ForegroundColor Yellow
}
