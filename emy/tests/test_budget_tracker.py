import pytest
from datetime import datetime, date, timedelta
from emy.core.budget_tracker import BudgetTracker
import tempfile
import os
from unittest.mock import patch


@pytest.fixture(scope="function")
def tracker():
    """Fixture to set up BudgetTracker with isolated test database."""
    # Create a temporary database file for this test
    temp_dir = tempfile.mkdtemp()
    temp_db = os.path.join(temp_dir, "test_budget.db")

    budget_tracker = BudgetTracker(daily_limit=10.0)
    budget_tracker.db.db_path = temp_db
    budget_tracker.db.initialize_schema()

    yield budget_tracker

    # Cleanup
    if os.path.exists(temp_db):
        os.remove(temp_db)
    try:
        os.rmdir(temp_dir)
    except:
        pass


@pytest.mark.asyncio
async def test_distribute_budget_across_agents(tracker):
    """Test proportional budget distribution across multiple agents."""

    agents = ['TradingAgent', 'ResearchAgent', 'KnowledgeAgent']
    budgets = await tracker.distribute_budget(agents)

    # Each agent should get roughly equal share (allow 0.1% variance)
    expected = 10.0 / 3  # ~3.33 each
    for agent, budget in budgets.items():
        assert agent in agents
        assert 3.2 < budget < 3.5, f"Expected ~3.33, got {budget}"
    assert abs(sum(budgets.values()) - 10.0) < 0.01


@pytest.mark.asyncio
async def test_track_agent_spending(tracker):
    """Test recording agent spending."""

    # Record two spending events
    await tracker.record_spending('TradingAgent', 2.5)
    await tracker.record_spending('TradingAgent', 1.5)

    spent = await tracker.get_agent_spending('TradingAgent')
    assert spent == 4.0, f"Expected 4.0, got {spent}"


@pytest.mark.asyncio
async def test_check_budget_available(tracker):
    """Test budget availability check."""

    await tracker.record_spending('TradingAgent', 5.0)

    # Agent spent $5, $5 remaining
    assert await tracker.has_budget('TradingAgent', 3.0) is True
    assert await tracker.has_budget('TradingAgent', 6.0) is False


@pytest.mark.asyncio
async def test_reset_daily_budget(tracker):
    """Test daily budget reset."""

    # Distribute budget to 3 agents
    await tracker.distribute_budget(['TradingAgent', 'ResearchAgent', 'KnowledgeAgent'])

    await tracker.record_spending('TradingAgent', 10.0 / 3)

    # All budget used
    assert await tracker.get_remaining_budget('TradingAgent') == 0.0

    # Reset (simulate new day by mocking the date to tomorrow)
    tomorrow = date.today() + timedelta(days=1)
    with patch('emy.core.budget_tracker.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value.date.return_value = tomorrow
        await tracker.reset_daily_budget()
        # After reset, get_remaining_budget should see a fresh budget for the new date
        assert await tracker.get_remaining_budget('TradingAgent') == 10.0 / 3


@pytest.mark.asyncio
async def test_budget_enforcement_prevents_overspend(tracker):
    """Test that budget enforcement prevents exceeding agent limit."""

    # Distribute budget to 3 agents
    await tracker.distribute_budget(['TradingAgent', 'ResearchAgent', 'KnowledgeAgent'])

    await tracker.record_spending('TradingAgent', 3.2)

    # Agent has ~0.13 left (3.33 - 3.2)
    assert await tracker.has_budget('TradingAgent', 0.1) is True
    assert await tracker.has_budget('TradingAgent', 0.2) is False


@pytest.mark.asyncio
async def test_get_agent_budget_status(tracker):
    """Test getting comprehensive budget status."""

    # Distribute budget to 3 agents
    await tracker.distribute_budget(['TradingAgent', 'ResearchAgent', 'KnowledgeAgent'])

    await tracker.record_spending('TradingAgent', 1.0)

    status = await tracker.get_budget_status('TradingAgent')

    assert 'allocated' in status
    assert 'spent' in status
    assert 'remaining' in status
    assert status['spent'] == 1.0
    assert 3.2 < status['allocated'] < 3.5
    assert 2.2 < status['remaining'] < 2.5
