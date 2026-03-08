#!/bin/bash
# Script to check if two services are on the SAME physical disk
# Run this on BOTH scalp-engine and scalp-engine-ui Shells

echo "================================================================================"
echo "DISK IDENTITY CHECK"
echo "================================================================================"
echo ""

CONFIG_FILE="/var/data/auto_trader_config.json"

# 1. Check mount info
echo "1. MOUNT INFORMATION:"
echo "--------------------"
df -h /var/data/ 2>&1
echo ""

# 2. Check device ID (if available)
echo "2. DEVICE/BLOCK INFORMATION:"
echo "----------------------------"
stat -f "%i" /var/data 2>&1 || stat -c "%i" /var/data 2>&1 || echo "stat command not available"
lsblk 2>&1 | grep -A 5 "/var/data" || df -i /var/data/ 2>&1
echo ""

# 3. Check file contents (for comparison)
echo "3. CONFIG FILE DETAILS:"
echo "----------------------"
if [ -f "$CONFIG_FILE" ]; then
    echo "File exists: YES"
    ls -lh "$CONFIG_FILE" 2>&1
    echo ""
    echo "File size: $(stat -f%z "$CONFIG_FILE" 2>&1 || stat -c%s "$CONFIG_FILE" 2>&1 || wc -c < "$CONFIG_FILE") bytes"
    echo "File mtime: $(stat -f%Sm "$CONFIG_FILE" 2>&1 || stat -c%y "$CONFIG_FILE" 2>&1 || echo 'mtime unavailable')"
    echo ""
    echo "First 5 lines of file:"
    head -5 "$CONFIG_FILE" 2>&1
else
    echo "File exists: NO"
fi
echo ""

# 4. List all files in /var/data (for comparison)
echo "4. FILES IN /var/data/:"
echo "----------------------"
ls -lah /var/data/ 2>&1
echo ""

echo "================================================================================"
echo "COMPARISON INSTRUCTIONS:"
echo "================================================================================"
echo "1. Run this script in scalp-engine-ui Shell"
echo "2. Run this script in scalp-engine Shell"
echo "3. Compare the results:"
echo "   - If 'Device' or mount info is DIFFERENT → They are on different disks"
echo "   - If file sizes/mtimes are DIFFERENT → They are on different disks"
echo "   - If file contents are DIFFERENT → They are on different disks"
echo ""
echo "If different, attach scalp-engine to the same disk as scalp-engine-ui"
echo "================================================================================"
