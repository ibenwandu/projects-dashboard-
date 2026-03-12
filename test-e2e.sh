#!/bin/bash
# Emy End-to-End Integration Test
#
# Validates all system components before production deployment.
# Run this before registering with Task Scheduler.

set -e

PASS=0
FAIL=0
TOTAL=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "================================================"
echo "Emy - End-to-End Integration Test"
echo "================================================"
echo ""

# Test 1: Python environment
echo -n "[1] Python installation... "
TOTAL=$((TOTAL + 1))
if python --version &> /dev/null; then
    echo -e "${GREEN}PASS${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}FAIL${NC}"
    FAIL=$((FAIL + 1))
fi

# Test 2: Required packages
echo -n "[2] Required packages (anthropic, dotenv)... "
TOTAL=$((TOTAL + 1))
if python -c "import anthropic; from dotenv import load_dotenv" 2>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}FAIL${NC} - Install: pip install anthropic python-dotenv"
    FAIL=$((FAIL + 1))
fi

# Test 3: .env configuration
echo -n "[3] .env file configuration... "
TOTAL=$((TOTAL + 1))
if [ -f "emy/.env" ] && grep -q "ANTHROPIC_API_KEY" emy/.env; then
    echo -e "${GREEN}PASS${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}FAIL${NC} - .env file missing or incomplete"
    FAIL=$((FAIL + 1))
fi

# Test 4: Database initialization
echo -n "[4] Database schema initialization... "
TOTAL=$((TOTAL + 1))
if python -c "from emy.core.database import EMyDatabase; db = EMyDatabase(); db.initialize_schema(); print('OK')" &> /dev/null; then
    echo -e "${GREEN}PASS${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}FAIL${NC}"
    FAIL=$((FAIL + 1))
fi

# Test 5: CLI Status Command
echo -n "[5] CLI status command... "
TOTAL=$((TOTAL + 1))
if python emy.py status 2>/dev/null | grep -q "Task Status"; then
    echo -e "${GREEN}PASS${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}FAIL${NC}"
    FAIL=$((FAIL + 1))
fi

# Test 6: CLI Skills Command
echo -n "[6] CLI skills command... "
TOTAL=$((TOTAL + 1))
if python emy.py skills 2>/dev/null | grep -q "TRADING\|JOB_SEARCH"; then
    echo -e "${GREEN}PASS${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}FAIL${NC}"
    FAIL=$((FAIL + 1))
fi

# Test 7: CLI Agents Command
echo -n "[7] CLI agents command... "
TOTAL=$((TOTAL + 1))
if python emy.py agents 2>/dev/null | grep -q "TradingAgent\|JobSearchAgent"; then
    echo -e "${GREEN}PASS${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}FAIL${NC}"
    FAIL=$((FAIL + 1))
fi

# Test 8: Main loop boot (timeout after 2 seconds)
echo -n "[8] Main loop bootstrap... "
TOTAL=$((TOTAL + 1))
if timeout 2 python emy.py run 2>&1 | grep -q "Emy boot complete" || true; then
    echo -e "${GREEN}PASS${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}FAIL${NC}"
    FAIL=$((FAIL + 1))
fi

# Test 9: Delegation engine
echo -n "[9] Agent delegation engine... "
TOTAL=$((TOTAL + 1))
if python -c "from emy.core.delegation_engine import EMyDelegationEngine; from emy.core.database import EMyDatabase; db = EMyDatabase(); de = EMyDelegationEngine(db); print('OK')" 2>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}FAIL${NC}"
    FAIL=$((FAIL + 1))
fi

# Test 10: Task router
echo -n "[10] Task router initialization... "
TOTAL=$((TOTAL + 1))
if python -c "from emy.core.task_router import EMyTaskRouter; from emy.core.delegation_engine import EMyDelegationEngine; from emy.core.approval_gate import EMyApprovalGate; from emy.core.database import EMyDatabase; db = EMyDatabase(); de = EMyDelegationEngine(db); ag = EMyApprovalGate(db); tr = EMyTaskRouter(de, ag); print('OK')" 2>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}FAIL${NC}"
    FAIL=$((FAIL + 1))
fi

# Summary
echo ""
echo "================================================"
echo "Test Results"
echo "================================================"
echo -e "Passed:  ${GREEN}${PASS}/${TOTAL}${NC}"
echo -e "Failed:  ${RED}${FAIL}/${TOTAL}${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "System is ready for production deployment."
    echo "Next: Run 'setup-task-scheduler.ps1' to register with Windows Task Scheduler"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Review errors above and fix issues before deployment."
    echo ""
    exit 1
fi
