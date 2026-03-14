#!/bin/bash
# Helper script to sync agent results from Render to local machine
# Run this after 17:30 EST to pull the latest agent cycle results

cd "$(dirname "$0")" || exit 1

echo "=========================================="
echo "🔄 AGENT SYNC - Pull Results from Render"
echo "=========================================="
echo ""
echo "This script syncs:"
echo "  ✓ Agent database from Render"
echo "  ✓ Logs (UI, Scalp-Engine, OANDA)"
echo "  ✓ Updates agent-coordination.md"
echo ""

# Check if sync script exists
if [ ! -f "sync_render_results.py" ]; then
    echo "❌ Error: sync_render_results.py not found"
    echo "   Expected location: agents/sync_render_results.py"
    exit 1
fi

# Run the sync
python sync_render_results.py

# Check result
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Sync completed!"
    echo ""
    echo "📋 Check the coordination log:"
    echo "   agents/shared-docs/agent-coordination.md"
    echo ""
else
    echo ""
    echo "⚠️  Sync encountered issues."
    echo "   Check the output above for details."
    echo ""
fi
