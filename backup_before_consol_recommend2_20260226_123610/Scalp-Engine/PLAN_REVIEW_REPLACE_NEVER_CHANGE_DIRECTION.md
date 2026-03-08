# Plan: Review-and-Replace Must Never Change Direction

**Goal:** The system may review and replace a user-set-up trade **only in the same direction** (e.g. better entry price for the same LONG or SHORT). The system must **never** change the direction of a trade that the user has already set up.

**Current behavior:** `_review_and_replace_pending_trades` considers **all** opportunities for a pair (any direction) and explicitly treats a **direction change** as "better," so a pending SELL can be replaced by a LONG (and vice versa) when the market state has the opposite recommendation.

**Desired behavior:** Replace only when (1) **same pair and same direction** and (2) better entry price (or position size change). Never replace with an opportunity that has the opposite direction.

---

## 1. Codebase review: where direction can change

### 1.1 Single location: `_review_and_replace_pending_trades` (scalp_engine.py)

**File:** `scalp_engine.py`  
**Function:** `_review_and_replace_pending_trades(self, opportunities, market_state)`  
**Called from:** `_check_new_opportunities` (once per main loop, before processing new opportunities).

**Current logic (simplified):**
1. For each **pending** trade (pair, direction, entry_price):
2. Find **matching_opps** = all opportunities for **same pair** (any direction).
3. Pick **best_opp** by iterating over matching_opps:
   - "Better" = better entry for that direction (LONG: lower entry; SHORT: higher entry).
   - **If direction changed (opposite direction), set `is_better = True`** → so opposite direction always wins.
4. If should_replace (better entry ≥1 pip, or position size change): cancel old order, place new order using **best_opp** (which may have opposite direction).

**No other path changes direction.** New trades are opened from the opportunity list with their own direction; the only place that can "flip" a user’s pending trade to the opposite direction is this function.

---

## 2. Required code changes

### 2.1 Restrict "matching" to same direction only

**Location:** `scalp_engine.py`, `_review_and_replace_pending_trades`, where `matching_opps` is built (around lines 2242–2248).

**Current:**
```python
# Find matching opportunities for the same pair (regardless of direction)
# STRICT RULE: Only one order per pair, so we check for ANY opportunity on this pair
matching_opps = [
    opp for opp in opportunities
    if opp.get('pair', '').upper() == pair.upper()
]
```

**Change to:** Only consider opportunities with the **same direction** as the pending trade. Normalize both trade direction and opp direction (LONG/BUY → LONG, SHORT/SELL → SHORT) and require equality.

**New logic:**
- Normalize `direction` for the pending trade to LONG or SHORT (if it’s BUY/SELL, map to LONG/SHORT).
- Build `matching_opps` = opportunities where `pair` matches **and** normalized direction matches the pending trade’s direction.
- Do **not** include opportunities with the opposite direction.

**Exact change:** Extend the list comprehension to filter by direction: e.g. for each `opp`, compute normalized `opp_direction` (BUY/LONG → LONG, SELL/SHORT → SHORT) and keep only those where `opp_direction == trade_direction_normalized`. Use a small helper or inline normalization so LONG/BUY and SHORT/SELL are compared consistently.

---

### 2.2 Remove "direction change = always replace"

**Location:** `scalp_engine.py`, inside the `for opp in matching_opps` loop (around lines 2278–2282).

**Current:**
```python
# If direction changed, always replace (new opportunity for same pair)
if opp_dir_normalized != direction:
    is_better = True
```

**Change:** Delete this block. After 2.1, `matching_opps` only contains same-direction opportunities, so `opp_dir_normalized` will always equal the pending trade’s direction. Removing this block prevents any future code path from using direction change as a reason to replace.

---

### 2.3 Use pending trade’s direction when building replacement (safety)

**Location:** `scalp_engine.py`, when building the replacement order (around lines 2341–2357).

**Current:** Replacement uses `opp_direction` from the chosen `best_opp` (and in the position-size-only path uses `opp_direction` which was set in the loop).

**Change (defensive):** When building the dict for the new order, **always use the pending trade’s direction** (`direction`) for the `direction` field, not `opp_direction`. This guarantees that even if `matching_opps` or `best_opp` were ever wrong, we never send a different direction to `open_trade`.

- When `best_opp` is set: build `opp` from `best_opp` but set `opp['direction'] = direction` (trade’s direction).
- When `best_opp` is None (position-size-only replace): build `opp` with `'direction': direction`.

So: replace every use of `opp_direction` in the replacement-order construction with `direction`.

---

### 2.4 Docstring and comments

**Location:** Same function, docstring and inline comments.

**Updates:**
- Docstring: Change "1. A better entry price available in the new opportunities (same pair, any direction)" to "1. A better entry price available in the new opportunities (same pair, **same direction only**). Direction is never changed."
- Remove or reword the comment "Find the best opportunity for this pair (may be different direction)" to "Find the best opportunity for this pair (same direction only; never change direction)."
- Optionally add a one-line comment when building `matching_opps`: "Same direction only: never replace user’s trade with opposite direction."

---

## 3. Optional: logging when opposite-direction opportunity is skipped

**Location:** After building `matching_opps`, or in a single pass over `opportunities` for this pair.

**Idea:** If there exists at least one opportunity for this pair with the **opposite** direction, log at DEBUG (e.g. "Skipping opposite-direction opportunity for {pair}: user has pending {direction}, market state has {opposite}; never change direction"). This helps confirm in logs that the new rule is in effect and that opposite-direction opportunities are intentionally ignored.

**Implementation:** Optional. If done, keep it DEBUG to avoid log noise.

---

## 4. Behaviour after the fix

| Scenario | Before | After |
|----------|--------|--------|
| Pending EUR/JPY SELL @ 181.5; market state has EUR/JPY LONG @ 181.7 | Replace with LONG @ 181.7 | **Do not replace**; keep SELL @ 181.5 (opposite direction ignored). |
| Pending EUR/JPY SELL @ 181.5; market state has EUR/JPY SELL @ 181.3 | Replace with SELL @ 181.3 (better entry for short) | **Same:** replace with SELL @ 181.3. |
| Pending EUR/JPY LONG @ 181.7; market state has EUR/JPY LONG @ 181.5 | Replace with LONG @ 181.5 (better entry for long) | **Same:** replace with LONG @ 181.5. |
| Pending EUR/JPY SELL; only change is position size (config) | Replace keeping direction | **Same:** replace with same direction and new size. |

So: **replace only for same-direction better entry (or position size); never change direction.**

---

## 5. Implementation checklist

- [ ] **2.1** In `_review_and_replace_pending_trades`, restrict `matching_opps` to same pair **and** same (normalized) direction as the pending trade.
- [ ] **2.2** Remove the block that sets `is_better = True` when `opp_dir_normalized != direction`.
- [ ] **2.3** When building the replacement order (both when `best_opp` is set and when it is None), set `direction` from the pending **trade’s** `direction`, not from `opp_direction`.
- [ ] **2.4** Update docstring and comments to state "same direction only; never change direction."
- [ ] **Optional** Add DEBUG log when an opposite-direction opportunity for the pair exists and is skipped.
- [ ] Run any existing tests; add a test that a pending SELL is **not** replaced by a LONG for the same pair (and vice versa).

---

## 6. Files to touch

| File | Change |
|------|--------|
| `scalp_engine.py` | `_review_and_replace_pending_trades`: filter matching_opps by direction; remove direction-change block; use trade’s direction in replacement; update docstring/comments. |

No config or UI changes required. The rule is: **user’s chosen direction is fixed; review-and-replace only improves entry/size in that same direction.**
