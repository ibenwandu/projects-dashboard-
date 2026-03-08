# Production Testing Guide - End-of-Day Cleanup Enhancement (Phases 1-4)

## Overview

This guide covers testing the complete end-of-day cleanup enhancement system in production on Render.

**Deployment Status**: ✅ Deployed to Render
**Testing Environment**: Production
**Testing Duration**: 1-2 weeks (minimum 1 full trading week + 1 Friday cleanup)

---

## Testing Timeline

### Week 1: Hourly Sync Checks (Phase 2) + Manual Testing (Phase 3)

**Monday-Friday during trading hours:**
- Hourly sync checks run automatically (Phase 2)
- UI sync status display available (Phase 3)
- Manual sync button available for testing (Phase 3)

### Week 2: End-of-Day Cleanup (Phase 1)

**Friday 21:30 UTC:**
- Comprehensive end-of-day cleanup runs (Phase 1)
- Orphaned order detection (Phase 1)
- Full system verification

---

## What to Monitor

### Phase 1: End-of-Day Cleanup (Friday 21:30 UTC)

**Expected Behavior:**

1. **Friday 21:30 UTC exactly** - Look for these log messages:

```
================================================================================
🧹 END-OF-DAY CLEANUP STARTING: Friday 21:30 UTC - End of trading week
================================================================================

Step 1: Cancelling pending orders in our system...
  ✅ Cancelled pending order: ... (EUR/USD LONG)
  ✅ Cancelled 2 pending order(s) in our system

Step 2: Detecting orphaned orders on OANDA...
  ✅ No orphaned orders detected on OANDA
  (OR if orphaned orders exist:)
  ⚠️ DETECTED 3 ORPHANED ORDER(S) ON OANDA (not in UI system):
    - 12345: EUR_USD 100000 units @ 1.0850 (37.2h old)
    - 12346: GBP_USD 50000 units @ 1.2750 (36.1h old)

Step 3: Attempting to cancel orphaned order(s)...
  ✅ Cancelled orphaned order: 12345
  ✅ Cancelled orphaned order: 12346

Step 4: Closing all open trades...
  ✅ Closed trade: ... (GBP/USD LONG)
  ✅ Closed 1 open trade(s)

Step 5: Persisting clean state...
  ✅ State persisted to file

================================================================================
✅ END-OF-DAY CLEANUP COMPLETED
================================================================================
📊 CLEANUP SUMMARY:
   • Pending orders cancelled: 2
   • Orphaned orders detected: 2
   • Orphaned orders cancelled: 2
   • Open trades closed: 1
================================================================================
```

**Where to Check:**

1. **Render Dashboard** → trade-alerts service → Logs
   - Search for "END-OF-DAY CLEANUP"
   - Look for Friday 21:30 UTC timestamp

2. **Alternative**: Scalp-Engine logs
   - Search for "END-OF-DAY CLEANUP STARTING"
   - Should appear at 21:30 UTC on Friday

**What to Verify:**

- [ ] Cleanup runs at exactly 21:30 UTC on Friday
- [ ] All pending orders are cancelled
- [ ] Orphaned orders are detected (if any exist)
- [ ] Orphaned orders are cancelled
- [ ] All open trades are closed
- [ ] State is persisted
- [ ] Summary shows correct counts

**Expected Outcomes:**

✅ **Best Case**:
```
Pending orders cancelled: 0
Orphaned orders detected: 0
Orphaned orders cancelled: 0
Open trades closed: 0
```
(Everything is clean, no issues)

⚠️ **Alert Case** (if orphaned orders detected):
```
Pending orders cancelled: 0
Orphaned orders detected: 3
Orphaned orders cancelled: 3
Open trades closed: 0
```
(Orphaned orders found and cleaned up)

---

### Phase 2: Hourly Sync Check (Every Hour Mon 01:00 - Fri 21:30 UTC)

**Expected Behavior:**

Every hour at **minute 00-02**, look for:

```
⚠️ SYNC WARNING - Periodic Check: 0 order(s) exist on OANDA but not in UI system!
(OR if no orphaned orders:)
OK: Sync check: No orphaned orders detected (UI and OANDA in sync)
```

**Where to Check:**

1. **Render Dashboard** → scalp_engine service → Logs
   - Search for "SYNC WARNING" or "Sync check"
   - Filter by hour (should appear at :00-:02 of each hour)

2. **Pattern to Look For:**
   - Should appear roughly once per hour
   - Only during trading hours (Mon 01:00 - Fri 21:30 UTC)
   - Not on weekends

**What to Verify:**

- [ ] Sync checks run every hour during trading
- [ ] No sync checks run on weekends
- [ ] Stale orphaned orders are cancelled
- [ ] Recent orders are skipped (not cancelled)
- [ ] Logging is comprehensive

**Expected Log Examples:**

**Clean Sync (No Issues):**
```
INFO: Sync check: No orphaned orders detected (UI and OANDA in sync)
```

**Orphaned Orders Detected:**
```
WARNING: SYNC WARNING - Periodic Check: 2 order(s) exist on OANDA but not in UI system!
  - 12345: EUR_USD 100000 units @ 1.0850 (4.2h old [STALE - will cancel])
  - 12346: GBP_USD 50000 units @ 1.2750 (0.5h old [RECENT])

INFO: Cancelled stale orphaned order: 12345 (EUR_USD, 4.2h old)
INFO: Skipping recent orphaned order (within 1h): 12346

INFO: Cancelled 1 of 2 stale orphaned order(s)
```

---

### Phase 3: UI Sync Status Display

**Expected Behavior:**

1. **Open Scalp-Engine UI**
   - Navigate to "Active Trades Monitor" page
   - Look for new "🔄 System Sync Status" section at the top

2. **Status Display Should Show:**

```
┌─────────────────┬──────────────────┬──────────────────┬─────────────────┐
│  Sync Status    │ Orphaned Orders  │ Last Sync Check  │  Manual Button  │
├─────────────────┼──────────────────┼──────────────────┼─────────────────┤
│ UNKNOWN         │ 0                │ Never            │ 🔄 Manual Sync  │
└─────────────────┴──────────────────┴──────────────────┴─────────────────┘
```

**What to Verify (Week 1):**

- [ ] Sync Status section appears on Active Trades Monitor
- [ ] 4 metrics displayed: Status, Orphaned Count, Last Check, Button
- [ ] Status shows "UNKNOWN" initially
- [ ] Orphaned count shows "0"
- [ ] Last check shows "Never"
- [ ] Manual sync button is clickable

**After First Hourly Sync Check (approximately 1 hour after first load):**

```
┌─────────────────┬──────────────────┬──────────────────┬─────────────────┐
│  Sync Status    │ Orphaned Orders  │ Last Sync Check  │  Manual Button  │
├─────────────────┼──────────────────┼──────────────────┼─────────────────┤
│ CLEAN ✅        │ 0                │ Just now         │ 🔄 Manual Sync  │
└─────────────────┴──────────────────┴──────────────────┴─────────────────┘
```

**What to Verify (After Hourly Check):**

- [ ] Status updates to "CLEAN" (if no orphaned orders)
- [ ] "Last Sync Check" shows "Just now" or "5m ago"
- [ ] Status explanation appears below metrics
- [ ] Green success message displays

---

### Phase 3: Manual Sync Button Testing

**How to Test:**

1. **Click the "🔄 Manual Sync Check" button** on the UI
2. **Observe the following:**

```
INFO message: "Triggering manual sync check..."

(After 5-10 seconds, one of:)

SUCCESS CASE:
✅ Sync Check Results:
   • Orphaned orders detected: 0
   • Orders cancelled: 0
   • Status: OK

OR

WARNING CASE:
⚠️ Sync Check Results:
   • Orphaned orders detected: 3
   • Orders cancelled: 2
   • Status: OK
```

**What to Verify:**

- [ ] Button is clickable without errors
- [ ] Loading state appears ("Triggering manual sync check...")
- [ ] Results appear within 10 seconds
- [ ] Metrics update based on results
- [ ] Status changes accordingly (CLEAN if 0 orphaned, ISSUES if >0)
- [ ] Page updates without full reload

**Test Cases:**

✅ **Test Case 1: Clean System**
- Result: 0 orphaned orders detected
- Expected: ✅ Success message, Status = CLEAN

✅ **Test Case 2: With Orphaned Orders (if they exist)**
- Result: 3+ orphaned orders detected
- Expected: ⚠️ Warning message, Status = ISSUES

✅ **Test Case 3: Repeated Clicks**
- Click button multiple times in succession
- Expected: Each click triggers new check, results update

---

### Phase 4: API Endpoint Testing

**Manual Testing (Advanced):**

```bash
# Test the API endpoint directly
curl -X POST https://config-api-8n37.onrender.com/sync-check

# Expected response:
{
  "status": "ok",
  "orphaned_detected": 0,
  "orphaned_cancelled": 0,
  "message": "Manual sync check requested"
}
```

**What to Verify:**

- [ ] Endpoint responds with 200 status
- [ ] Response JSON is valid
- [ ] Fields match expected schema
- [ ] No timeout errors

---

## Testing Checklist

### Week 1: Hourly Checks (Mon-Fri)

**Daily Monitoring:**
- [ ] Check Scalp-Engine logs for hourly sync checks
- [ ] Verify checks run at :00-:02 of each hour
- [ ] Verify no checks run on weekends (Sat/Sun)
- [ ] Open UI and verify Sync Status section displays
- [ ] Test manual sync button at least once per day
- [ ] Verify status updates after manual sync

**Expected Logs per Day:**
- Approximately 16-17 hourly sync checks (Mon 01:00 - Fri 21:30 UTC)
- Each check logs either "No orphaned orders" or details of found orders

**UI Testing:**
- [ ] Sync Status metric visible on every page load
- [ ] Manual button works every time clicked
- [ ] Results display correctly
- [ ] Status text matches actual state

### Week 2: End-of-Day Cleanup (Friday 21:30 UTC)

**Friday Testing:**
- [ ] Set reminder for Friday 21:30 UTC
- [ ] 5 minutes before: Check OANDA for any pending orders or open trades
- [ ] At 21:30 UTC: Monitor logs for cleanup start
- [ ] During cleanup (5-10 minutes): Watch for each step completion
- [ ] After cleanup: Verify all pending orders cancelled
- [ ] After cleanup: Verify all open trades closed
- [ ] After cleanup: Check OANDA to confirm no orders remain

**Critical Checks:**
- [ ] Cleanup starts at exactly 21:30 UTC (within 30 seconds)
- [ ] No errors in log during cleanup
- [ ] All 5 steps complete successfully
- [ ] Summary shows expected counts
- [ ] Market state file updated

**Weekend Verification:**
- [ ] Saturday: Confirm no trading occurs
- [ ] Sunday: Confirm no trading occurs
- [ ] Saturday/Sunday: Confirm no cleanup attempts

---

## Expected Results by Phase

### Phase 1 Results (Friday 21:30 UTC)

**Ideal Scenario:**
```
Pending orders cancelled: 0
Orphaned orders detected: 0
Orphaned orders cancelled: 0
Open trades closed: 0

Status: ✅ CLEAN - System was already clean
```

**Improved Scenario:**
```
Pending orders cancelled: 2
Orphaned orders detected: 0
Orphaned orders cancelled: 0
Open trades closed: 1

Status: ✅ CLEANED - System had pending orders, now clean
```

**Alert Scenario:**
```
Pending orders cancelled: 0
Orphaned orders detected: 3
Orphaned orders cancelled: 3
Open trades closed: 0

Status: ⚠️ ORPHANS FOUND AND CLEANED - Critical: UI/OANDA sync issue resolved
```

### Phase 2 Results (Hourly)

**Expected:**
- 95%+ of checks: "No orphaned orders detected"
- 5% or less: Finds stale orders, cancels them
- 0 false positives (recent orders never cancelled)

### Phase 3 Results (UI)

**Expected:**
- Sync Status visible within 1 second of page load
- Manual button response within 10 seconds
- Accurate status (CLEAN/ISSUES/UNKNOWN)
- Correct orphaned count

### Phase 4 Results (API)

**Expected:**
- Endpoint responds in < 1 second
- 200 status code always returned
- JSON response always valid

---

## Troubleshooting Guide

### Issue: No sync checks appear in logs

**Possible Causes:**
1. Service not running
2. Logs are buffered/delayed
3. Wrong log search term

**Solutions:**
1. Check Render Dashboard - Service status should be "Running"
2. Wait 30 seconds and refresh logs
3. Search for "Sync" or "periodic" instead
4. Check scalp_engine logs specifically (not trade-alerts)

### Issue: Manual sync button not responsive

**Possible Causes:**
1. API endpoint not deployed
2. Network timeout
3. API server down

**Solutions:**
1. Test API directly: `curl -X POST https://config-api.../sync-check`
2. Check config-api service status on Render
3. Refresh UI page and try again
4. Check browser console for errors (F12)

### Issue: Cleanup doesn't run Friday 21:30 UTC

**Possible Causes:**
1. Service restarted near 21:30 UTC
2. Logs showing wrong timezone
3. Cleanup happened but logs not visible

**Solutions:**
1. Check for any recent deployments at that time
2. Verify time is UTC (not local timezone)
3. Search logs for "CLEANUP" on Friday (any time)
4. Check if trades were actually closed in OANDA

### Issue: Orphaned orders not being cancelled

**Possible Causes:**
1. Orders are < 1 hour old (intentional - they're recent)
2. API call to OANDA failed
3. Permission issue on OANDA account

**Solutions:**
1. Check order creation time in logs - if < 1h, that's expected
2. Look for error messages in logs
3. Try manual sync button to test
4. Check OANDA API token in Render environment variables

### Issue: UI shows "ISSUES" but logs show no orphaned orders

**Possible Causes:**
1. Orphaned orders were detected but already cancelled
2. Session state out of sync
3. Manual sync button result cached

**Solutions:**
1. Click manual sync button again
2. Refresh page (F5)
3. Wait 1 minute and refresh
4. Check logs to see actual current state

---

## Success Criteria

### Phase 1 Success
✅ Cleanup runs Friday 21:30 UTC
✅ All log steps complete successfully
✅ No errors in output
✅ Summary shows expected counts
✅ OANDA is clean after completion

### Phase 2 Success
✅ Checks run hourly Mon 01:00 - Fri 21:30 UTC
✅ No false positives (recent orders preserved)
✅ Stale orders cancelled automatically
✅ Comprehensive logging appears
✅ No checks on weekends

### Phase 3 Success
✅ UI section displays on every page
✅ Metrics show correct values
✅ Manual button works consistently
✅ Status updates accurately
✅ Explanations are clear

### Phase 4 Success
✅ API endpoint responds reliably
✅ Response format is correct
✅ No timeout errors
✅ Status codes are appropriate

---

## Reporting Issues

If you find any issues during testing:

1. **Collect Evidence:**
   - Screenshot of UI showing issue
   - Log excerpt showing error
   - Timestamp of incident (UTC)
   - Steps to reproduce

2. **Check Logs First:**
   - Search for ERROR, WARN, FAILED, EXCEPTION
   - Look for stack traces
   - Note exact error messages

3. **Document Details:**
   - Exact time issue occurred
   - What was expected vs actual
   - Reproducible? (always/sometimes/once)
   - Which phase affected (1/2/3/4)

4. **Test Manually:**
   - Click manual sync button
   - Check OANDA directly
   - Verify trades on file match OANDA

---

## Testing Timeline

| Date | Phase | Action | Expected |
|------|-------|--------|----------|
| Mon Day 1 | 2 & 3 | Deploy code, monitor hourly checks | Hourly checks appear in logs |
| Tue-Thu | 2 & 3 | Daily UI testing, manual sync tests | Status displays, button works |
| Fri 21:30 | 1 | End-of-day cleanup | Cleanup logs appear, system clean |
| Mon Day 8 | 2 & 3 | Repeat cycle with confidence | Everything works smoothly |
| Fri 21:30 | 1 | Second end-of-day cleanup | Consistent performance |

---

## Sign-Off Criteria

Testing is complete when:

✅ All Phase 1-4 features have been observed working in production
✅ No ERROR or CRITICAL log messages related to cleanup
✅ UI sync status displays correctly and updates accurately
✅ Manual sync button works reliably
✅ End-of-day cleanup completes without errors (Friday 21:30 UTC)
✅ System remains stable throughout testing period
✅ OANDA remains perfectly in sync with UI

---

## Notes

- All times are in UTC
- Render is in UTC timezone by default
- Check both trade-alerts and scalp_engine service logs
- UI may take up to 1 minute to update after sync check
- Manual sync button is non-blocking (doesn't interrupt trading)
- Cleanup runs regardless of number of trades/orders

---

**Testing Ready**: ✅ All code deployed to Render
**Start Date**: Upon approval
**Expected Duration**: 1-2 weeks
