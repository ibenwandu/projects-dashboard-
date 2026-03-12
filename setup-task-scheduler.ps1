# Emy - Windows Task Scheduler Setup
# This script registers Emy with Windows Task Scheduler for automatic startup

param(
    [switch]$Uninstall
)

$TaskName = "Emy Chief of Staff"
$TaskDescription = "Autonomous AI agent managing trading, job search, and knowledge management"
$ScriptPath = "C:\Users\user\projects\personal\.worktrees\emy"
$PythonExe = "python"
$MainScript = "emy.py"

# Function to create the scheduled task
function Create-Task {
    Write-Host "Creating Task Scheduler entry for Emy..." -ForegroundColor Cyan

    # Create action: run python emy.py run
    $action = New-ScheduledTaskAction `
        -Execute $PythonExe `
        -Argument "emy.py run" `
        -WorkingDirectory $ScriptPath

    # Create trigger: at system startup
    $trigger = New-ScheduledTaskTrigger -AtStartup

    # Create settings
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable `
        -MultipleInstances IgnoreNew

    # Register task
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description $TaskDescription `
        -RunLevel Highest `
        -Force

    Write-Host "[OK] Task created successfully" -ForegroundColor Green
    Write-Host "  Name: $TaskName"
    Write-Host "  Trigger: At system startup"
    Write-Host "  Working Directory: $ScriptPath"
    Write-Host ""
}

# Function to remove the scheduled task
function Remove-Task {
    Write-Host "Removing Task Scheduler entry for Emy..." -ForegroundColor Cyan

    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Host "[OK] Task removed successfully" -ForegroundColor Green
    } catch {
        Write-Host "[ERR] Failed to remove task: $_" -ForegroundColor Red
    }
}

# Function to check task status
function Show-TaskStatus {
    Write-Host "Emy Task Scheduler Status:" -ForegroundColor Cyan
    Write-Host ""

    try {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        Write-Host "Status: REGISTERED" -ForegroundColor Green
        Write-Host "  Name: $($task.TaskName)"
        Write-Host "  State: $($task.State)"
        Write-Host "  Enabled: $($task.Settings.Enabled)"
        Write-Host ""

        $lastRun = Get-ScheduledTaskInfo -TaskName $TaskName
        if ($lastRun.LastRunTime) {
            Write-Host "Last Run: $($lastRun.LastRunTime)"
            Write-Host "Last Result: $($lastRun.LastTaskResult)"
        }
    } catch {
        Write-Host "Status: NOT REGISTERED" -ForegroundColor Yellow
        Write-Host "  Run this script to register the task"
    }
}

# Main
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Emy - Windows Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "[ERR] This script must run as Administrator" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run PowerShell as Administrator and try again."
    exit 1
}

if ($Uninstall) {
    Remove-Task
} else {
    Create-Task
}

Write-Host "Showing current status..." -ForegroundColor Cyan
Write-Host ""
Show-TaskStatus

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Setup Complete" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
