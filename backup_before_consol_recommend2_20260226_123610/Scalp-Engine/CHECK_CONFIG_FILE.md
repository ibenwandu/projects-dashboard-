# Check Config File on Render - Diagnostic Commands

## Quick Commands to Run

Run these commands in Render Shell for **BOTH** `scalp-engine` and `scalp-engine-ui` services:

### Option 1: Run the Diagnostic Script (if available)

```bash
cd /opt/render/project/Scalp-Engine
bash check_config_file.sh
```

### Option 2: Manual Commands (copy-paste all at once)

```bash
# 1. Check if file exists
CONFIG_FILE="/var/data/auto_trader_config.json"
echo "=== Checking: $CONFIG_FILE ==="
ls -lh "$CONFIG_FILE" 2>&1

# 2. Show file contents
echo ""
echo "=== FILE CONTENTS ==="
cat "$CONFIG_FILE" 2>&1

# 3. Show file metadata
echo ""
echo "=== FILE METADATA ==="
stat "$CONFIG_FILE" 2>&1 || ls -l "$CONFIG_FILE"

# 4. List all files in /var/data/
echo ""
echo "=== FILES IN /var/data/ ==="
ls -lah /var/data/ 2>&1

# 5. Check disk mount
echo ""
echo "=== DISK MOUNT INFO ==="
df -h /var/data/ 2>&1
```

### Option 3: One-Line Check (fastest)

```bash
echo "File exists: $(test -f /var/data/auto_trader_config.json && echo 'YES' || echo 'NO')"; cat /var/data/auto_trader_config.json 2>&1 | head -50; ls -lh /var/data/auto_trader_config.json 2>&1
```

## What to Compare

After running on both services, compare:

1. **File contents**: Are they identical?
2. **File path**: Are both showing `/var/data/auto_trader_config.json`?
3. **File size**: Is the size the same?
4. **Last modified**: Is the timestamp the same?
5. **Files in /var/data/**: Are the same files visible?

## Expected Results

If both services share the same disk:
- ✅ File contents should be **IDENTICAL**
- ✅ File size should be **SAME**
- ✅ Last modified should be **SAME**
- ✅ `/var/data/` should show **SAME FILES**

If they don't match:
- ❌ Services are **NOT sharing the same disk**
- ❌ Need to check disk configuration in Render Dashboard
