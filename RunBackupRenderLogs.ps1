# Wrapper for scheduled task: loads env vars from a file, then runs BackupRenderLogs.ps1.
# Use this as the task "Program/script" so RENDER_API_KEY and Oanda vars are set when the task runs.
# The task does NOT inherit your interactive session environment.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $scriptDir "BackupRenderLogs.env.ps1"

if (Test-Path $envFile) {
    try {
        . $envFile
    } catch {
        # Log but continue; main script will warn if keys missing
        $logDir = "C:\Users\user\Desktop\Test\Manual logs"
        if (Test-Path $logDir) {
            $errLine = "{0:yyyy-MM-dd HH:mm:ss}: RunBackupRenderLogs - failed to load env file: {1}" -f (Get-Date), $_.Exception.Message
            Add-Content -Path (Join-Path $logDir "error_log.txt") -Value $errLine -Encoding utf8 -ErrorAction SilentlyContinue
        }
    }
} else {
    # Optional: create from example so user knows what to fill in
    $example = Join-Path $scriptDir "BackupRenderLogs.env.ps1.example"
    if (Test-Path $example) {
        $msg = "BackupRenderLogs.env.ps1 not found. Copy BackupRenderLogs.env.ps1.example to BackupRenderLogs.env.ps1 and set your keys so the scheduled task can run Oanda transaction backup."
        Write-Host $msg -ForegroundColor Yellow
    }
}

& (Join-Path $scriptDir "BackupRenderLogs.ps1")
