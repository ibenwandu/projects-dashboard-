#!/usr/bin/env python
"""
Verify RL System Logs Script
Analyzes daily_learning.py and OutcomeEvaluator logs to confirm system is working

Usage:
  Local: python verify_rl_logs.py
  Render: curl https://your-render-url/verify-logs (via web service)

Output:
  - Checks for daily learning runs
  - Verifies recommendations were evaluated
  - Confirms LLM weights were updated
  - Reports any errors
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

def get_log_files():
    """Get most recent log files"""
    logs_dir = Path('logs')
    if not logs_dir.exists():
        return []

    # Look for trade_alerts_*.log files
    log_files = sorted(logs_dir.glob('trade_alerts_*.log'), key=lambda x: x.stat().st_mtime, reverse=True)
    return log_files[:5]  # Last 5 log files

def analyze_daily_learning_logs(log_files):
    """Analyze logs for daily learning activity"""
    findings = {
        'daily_learning_runs': 0,
        'components_initialized': 0,
        'pending_recommendations': [],
        'evaluated_recommendations': [],
        'weight_updates': [],
        'errors': [],
        'last_run': None
    }

    for log_file in log_files:
        try:
            with open(log_file, 'r') as f:
                content = f.read()

                # Check for daily learning cycle start
                if 'DAILY LEARNING CYCLE' in content:
                    findings['daily_learning_runs'] += 1
                    # Extract timestamp
                    for line in content.split('\n'):
                        if 'DAILY LEARNING CYCLE' in line:
                            findings['last_run'] = line
                            break

                # Check for component initialization
                if 'COMPONENTS INITIALIZED' in content:
                    findings['components_initialized'] += 1

                # Check for pending recommendations
                if 'Found' in content and 'recommendations ready for evaluation' in content:
                    for line in content.split('\n'):
                        if 'recommendations ready for evaluation' in line:
                            findings['pending_recommendations'].append(line.strip())

                # Check for evaluated recommendations
                if 'Evaluating' in content or '[OutcomeEvaluator]' in content:
                    count = content.count('[OutcomeEvaluator]')
                    if count > 0:
                        findings['evaluated_recommendations'].append(f"{log_file.name}: {count} evaluations")

                # Check for weight updates
                if 'Updated LLM Weights' in content or 'LLM weights will be' in content:
                    findings['weight_updates'].append(log_file.name)

                # Check for errors
                for line in content.split('\n'):
                    if 'ERROR' in line or 'CRITICAL' in line:
                        if 'DAILY LEARNING' not in line:  # Skip header lines
                            findings['errors'].append(line.strip())

        except Exception as e:
            findings['errors'].append(f"Error reading {log_file}: {e}")

    return findings

def print_verification_report(findings):
    """Print verification report"""
    print("\n" + "="*80)
    print("RL SYSTEM LOG VERIFICATION REPORT")
    print("="*80)
    print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    # Summary
    print("SUMMARY:")
    print(f"  Daily Learning Runs Found: {findings['daily_learning_runs']}")
    print(f"  Components Initialized: {findings['components_initialized']}")
    print(f"  Recommendations Evaluated: {len(findings['evaluated_recommendations'])}")
    print(f"  Weight Updates Found: {len(findings['weight_updates'])}")
    print(f"  Errors Found: {len(findings['errors'])}")
    print()

    # Last run
    if findings['last_run']:
        print("LAST RUN:")
        print(f"  {findings['last_run']}")
        print()

    # Pending recommendations
    if findings['pending_recommendations']:
        print("PENDING RECOMMENDATIONS:")
        for rec in findings['pending_recommendations'][-3:]:  # Last 3
            print(f"  {rec}")
        print()

    # Evaluated recommendations
    if findings['evaluated_recommendations']:
        print("EVALUATION ACTIVITY:")
        for eval_info in findings['evaluated_recommendations']:
            print(f"  {eval_info}")
        print()

    # Weight updates
    if findings['weight_updates']:
        print("WEIGHT UPDATES:")
        for weight_file in findings['weight_updates'][-3:]:  # Last 3
            print(f"  {weight_file}")
        print()

    # Errors
    if findings['errors']:
        print("ERRORS:")
        for error in findings['errors'][-5:]:  # Last 5
            print(f"  {error}")
        print()

    # Status
    print("STATUS:")
    if findings['daily_learning_runs'] > 0 and len(findings['evaluated_recommendations']) > 0:
        print("  ✅ RL System appears to be working")
        print(f"     - Daily learning running (last: {findings['last_run'][:50]}...)")
        print(f"     - Recommendations being evaluated ({len(findings['evaluated_recommendations'])} instances)")
        if findings['weight_updates']:
            print(f"     - Weights being updated (found in {len(findings['weight_updates'])} log files)")
    else:
        print("  ⚠️ RL System may not be running")
        if findings['daily_learning_runs'] == 0:
            print("     - No daily learning runs found in logs")
        if len(findings['evaluated_recommendations']) == 0:
            print("     - No recommendation evaluations found in logs")

    if findings['errors']:
        print(f"\n  ❌ Errors detected ({len(findings['errors'])} total)")

    print("\n" + "="*80)

def main():
    # Get log files
    log_files = get_log_files()

    if not log_files:
        print("No log files found in logs/ directory")
        print("Expected: logs/trade_alerts_*.log")
        print("\nMake sure main.py has run at least once")
        return 1

    print(f"Analyzing {len(log_files)} log files...")
    print(f"Most recent: {log_files[0].name}")

    # Analyze
    findings = analyze_daily_learning_logs(log_files)

    # Report
    print_verification_report(findings)

    # Exit status
    if findings['daily_learning_runs'] > 0 and len(findings['evaluated_recommendations']) > 0:
        return 0  # Success
    else:
        return 1  # Not running

if __name__ == '__main__':
    sys.exit(main())
