#!/bin/bash
# Script to check config file on Render
# Run this on BOTH scalp-engine and scalp-engine-ui services

echo "================================================================================"
echo "CONFIG FILE DIAGNOSTICS"
echo "================================================================================"
echo ""

# 1. Check file path
CONFIG_FILE="/var/data/auto_trader_config.json"
echo "1. Checking file: $CONFIG_FILE"
echo ""

# 2. Check if file exists
if [ -f "$CONFIG_FILE" ]; then
    echo "✅ File EXISTS"
else
    echo "❌ File DOES NOT EXIST"
    echo ""
    echo "Checking parent directory:"
    ls -la /var/data/ 2>&1 || echo "Cannot access /var/data/"
    exit 1
fi
echo ""

# 3. Show file metadata
echo "2. File Metadata:"
ls -lh "$CONFIG_FILE"
stat "$CONFIG_FILE" 2>/dev/null || echo "stat command not available"
echo ""

# 4. Show file size
FILE_SIZE=$(stat -f%z "$CONFIG_FILE" 2>/dev/null || stat -c%s "$CONFIG_FILE" 2>/dev/null || wc -c < "$CONFIG_FILE")
echo "File size: $FILE_SIZE bytes"
echo ""

# 5. Show file permissions
echo "3. File Permissions:"
ls -l "$CONFIG_FILE"
echo ""

# 6. Show directory permissions
echo "4. Directory Permissions:"
ls -ld /var/data/
echo ""

# 7. List all files in /var/data/
echo "5. Files in /var/data/:"
ls -lah /var/data/ 2>&1 || echo "Cannot list /var/data/"
echo ""

# 8. Show file contents
echo "================================================================================"
echo "6. FILE CONTENTS (Raw):"
echo "================================================================================"
cat "$CONFIG_FILE" || echo "Cannot read file"
echo ""

# 9. Validate JSON
echo "================================================================================"
echo "7. JSON Validation:"
echo "================================================================================"
if command -v python3 &> /dev/null; then
    python3 -m json.tool "$CONFIG_FILE" 2>&1 && echo "✅ Valid JSON" || echo "❌ Invalid JSON"
else
    echo "Python not available for JSON validation"
fi
echo ""

# 10. Show disk mount info
echo "================================================================================"
echo "8. Disk Mount Information:"
echo "================================================================================"
df -h /var/data/ 2>&1 || mount | grep /var/data || echo "Cannot check mount info"
echo ""

echo "================================================================================"
echo "DONE"
echo "================================================================================"
