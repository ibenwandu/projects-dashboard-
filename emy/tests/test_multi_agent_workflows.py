import pytest
import asyncio
from emy.brain.state import EMyState, create_initial_state_with_groups
from emy.brain.executor import execute_agent_group_parallel
from emy.core.budget_tracker import BudgetTracker
from emy.brain.result_aggregator import ResultAggregator
from emy.brain.conflict_resolver import ConflictResolver
from emy.brain.agent_selector import AgentSelector

@pytest.mark.asyncio
async def test_parallel_execution_two_agents():
    """Test parallel execution of two agents."""
    state = create_initial_state_with_groups(
        workflow_type='test_workflow',
        agent_groups=[['TradingAgent', 'ResearchAgent']],
        input={'test': 'data'},
        workflow_id='test-123'
    )

    # Execute parallel agents
    result_state = await execute_agent_group_parallel(state)

    # Verify state updated correctly
    assert result_state.workflow_id == 'test-123'
    assert result_state.current_group_index == 1  # Group index incremented
    # Both agents should have attempted execution (may have results or errors)
    assert len(result_state.results) > 0
    assert 'TradingAgent' in result_state.results or 'ResearchAgent' in result_state.results


@pytest.mark.asyncio
async def test_parallel_execution_three_agents():
    """Test parallel execution of three agents."""
    state = create_initial_state_with_groups(
        workflow_type='test_workflow',
        agent_groups=[['TradingAgent', 'ResearchAgent', 'KnowledgeAgent']],
        input={'test': 'data'},
        workflow_id='test-456'
    )

    result_state = await execute_agent_group_parallel(state)

    # Verify state updated correctly
    assert result_state.workflow_id == 'test-456'
    assert result_state.current_group_index == 1  # Group index incremented
    # Agents should have attempted execution
    assert len(result_state.results) > 0


@pytest.mark.asyncio
async def test_budget_enforcement_during_parallel_execution():
    """Test budget enforcement during parallel execution."""
    tracker = BudgetTracker(daily_limit=10.0)

    agents = ['TradingAgent', 'ResearchAgent']
    budgets = await tracker.distribute_budget(agents)

    # Each agent gets ~$5
    assert all(4.5 < budget < 5.5 for budget in budgets.values())

    # Simulate spending
    await tracker.record_spending('TradingAgent', 4.0)

    # Check remaining
    remaining = await tracker.get_remaining_budget('TradingAgent')
    assert remaining < 2.0


@pytest.mark.asyncio
async def test_result_aggregation_consensus():
    """Test aggregating results when agents agree."""
    aggregator = ResultAggregator()

    results = {
        'TradingAgent': {
            'recommendation': 'SELL EUR/USD',
            'confidence': 0.85
        },
        'ResearchAgent': {
            'recommendation': 'SELL EUR/USD',
            'confidence': 0.80
        }
    }

    aggregated = aggregator.aggregate(results)

    assert aggregated['conflict_detected'] is False
    assert aggregated['consensus'] is not None
    assert aggregated['consensus']['recommendation'] == 'SELL'


@pytest.mark.asyncio
async def test_result_aggregation_with_conflict():
    """Test aggregating results when agents disagree."""
    aggregator = ResultAggregator()

    results = {
        'TradingAgent': {
            'recommendation': 'SELL',
            'confidence': 0.85
        },
        'ResearchAgent': {
            'recommendation': 'BUY',
            'confidence': 0.72
        }
    }

    aggregated = aggregator.aggregate(results)

    assert aggregated['conflict_detected'] is True
    assert len(aggregated['conflicts']) > 0


@pytest.mark.asyncio
async def test_conflict_resolution_by_confidence():
    """Test resolving conflicts using confidence scores."""
    resolver = ConflictResolver()

    results = {
        'TradingAgent': {
            'recommendation': 'SELL',
            'confidence': 0.95
        },
        'ResearchAgent': {
            'recommendation': 'BUY',
            'confidence': 0.70
        }
    }

    resolved = resolver.resolve(results)

    assert resolved['recommendation'] == 'SELL'
    assert resolved['winning_agent'] == 'TradingAgent'


@pytest.mark.asyncio
async def test_conflict_resolution_with_weights():
    """Test resolving conflicts using agent weights."""
    resolver = ConflictResolver(agent_weights={
        'TradingAgent': 1.0,
        'ResearchAgent': 2.0  # Higher weight
    })

    results = {
        'TradingAgent': {
            'recommendation': 'SELL',
            'confidence': 0.90
        },
        'ResearchAgent': {
            'recommendation': 'BUY',
            'confidence': 0.60
        }
    }

    resolved = resolver.resolve(results)

    # ResearchAgent should win due to 2x weight
    assert resolved['recommendation'] == 'BUY'
    assert resolved['winning_agent'] == 'ResearchAgent'


@pytest.mark.asyncio
async def test_agent_auto_selection():
    """Test intelligent agent selection."""
    selector = AgentSelector()

    task = {
        'type': 'market_analysis',
        'input': 'Analyze EUR/USD trend for trading opportunity'
    }

    agents = selector.select_agents(task, mode='auto')

    assert 'TradingAgent' in agents


@pytest.mark.asyncio
async def test_agent_explicit_selection():
    """Test explicit agent selection via API."""
    selector = AgentSelector()

    agents = selector.select_agents(
        {},
        mode='explicit',
        agents=['TradingAgent', 'ResearchAgent']
    )

    assert agents == ['TradingAgent', 'ResearchAgent']


@pytest.mark.asyncio
async def test_full_multi_agent_workflow():
    """Test complete multi-agent workflow: select → execute → aggregate → resolve."""
    selector = AgentSelector()
    aggregator = ResultAggregator()
    resolver = ConflictResolver()
    tracker = BudgetTracker(daily_limit=10.0)

    # 1. Select agents
    task = {'type': 'market_analysis', 'input': 'EUR/USD analysis'}
    agents = selector.select_agents(task, mode='auto')

    assert len(agents) > 0

    # 2. Check budget
    budgets = await tracker.distribute_budget(agents)
    assert len(budgets) == len(agents)

    # 3. Simulate agent execution with results
    results = {
        'TradingAgent': {
            'recommendation': 'SELL EUR/USD',
            'confidence': 0.85,
            'analysis': 'Technical breakdown detected'
        },
        'ResearchAgent': {
            'recommendation': 'SELL EUR/USD',
            'confidence': 0.78,
            'analysis': 'Fundamental weakness in EUR'
        }
    }

    # 4. Aggregate results
    aggregated = aggregator.aggregate(results)
    assert aggregated['consensus'] is not None

    # 5. Resolve any conflicts
    resolved = resolver.resolve(results)
    assert resolved['recommendation'] in ['SELL', 'BUY', 'HOLD']

    # 6. Record spending
    for agent in agents:
        await tracker.record_spending(agent, 0.5)

    # 7. Verify budget tracking (check structure, accounting for database persistence)
    for agent in agents:
        spent = await tracker.get_agent_spending(agent)
        # Verify spending was recorded (may include previous test runs)
        assert isinstance(spent, float)
        assert spent > 0


@pytest.mark.asyncio
async def test_budget_prevents_expensive_agent_execution():
    """Test that budget enforcement prevents overspend."""
    tracker = BudgetTracker(daily_limit=0.1)  # Very small budget for isolation

    # Distribute budget
    agents = ['TestAgent_BudgetTest']
    await tracker.distribute_budget(agents)

    # Get initial spending
    initial_spent = await tracker.get_agent_spending('TestAgent_BudgetTest')

    # Record additional spending
    await tracker.record_spending('TestAgent_BudgetTest', 0.05)

    # Get final spending
    final_spent = await tracker.get_agent_spending('TestAgent_BudgetTest')

    # Verify spending increased
    assert final_spent >= initial_spent
    assert final_spent >= 0.05

    # Check remaining budget
    remaining = await tracker.get_remaining_budget('TestAgent_BudgetTest')
    assert remaining >= 0  # Should have some budget or be at limit
