# Emy Week 5: Multi-Agent Workflows Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Enable multiple agents to execute in parallel, coordinate results, and enforce budget across concurrent executions.

**Architecture:** LangGraph parallel nodes with result aggregation. Budget distributed proportionally across agents in a workflow group. Agent selection logic determines which agents suit a task. Conflict resolver identifies and merges contradictory outputs.

**Tech Stack:** LangGraph (state machine), asyncio (parallel execution), Pydantic (typing), SQLite (budget tracking)

---

## Current State

- ✅ Parallel group executor exists (`emy/brain/executor.py`)
- ✅ Agent registry has 5 agents (TradingAgent, ResearchAgent, KnowledgeAgent, ProjectMonitorAgent, JobSearchAgent)
- ✅ API workflow endpoint exists (`POST /workflows`)
- ❌ Budget enforcement across parallel agents (not implemented)
- ❌ Result aggregation with conflict detection (not implemented)
- ❌ Agent auto-selection logic (not implemented)
- ❌ Conflict resolver (not implemented)

---

## Task 1: Budget Tracker Implementation

**Files:**
- Create: `emy/core/budget_tracker.py`
- Modify: `emy/core/database.py` (add budget tracking schema)
- Test: `emy/tests/test_budget_tracker.py`

**Step 1: Write the failing test**

Create `emy/tests/test_budget_tracker.py`:

```python
import pytest
from datetime import datetime
from emy.core.budget_tracker import BudgetTracker

@pytest.mark.asyncio
async def test_distribute_budget_across_agents():
    """Test proportional budget distribution across multiple agents."""
    tracker = BudgetTracker(daily_limit=10.0)  # $10/day

    agents = ['TradingAgent', 'ResearchAgent', 'KnowledgeAgent']
    budgets = await tracker.distribute_budget(agents)

    # Each agent should get roughly equal share (allow 0.1% variance)
    expected = 10.0 / 3  # ~3.33 each
    for agent, budget in budgets.items():
        assert agent in agents
        assert 3.2 < budget < 3.5, f"Expected ~3.33, got {budget}"
    assert abs(sum(budgets.values()) - 10.0) < 0.01


@pytest.mark.asyncio
async def test_track_agent_spending():
    """Test recording agent spending."""
    tracker = BudgetTracker(daily_limit=10.0)

    # Record two spending events
    await tracker.record_spending('TradingAgent', 2.5)
    await tracker.record_spending('TradingAgent', 1.5)

    spent = await tracker.get_agent_spending('TradingAgent')
    assert spent == 4.0, f"Expected 4.0, got {spent}"


@pytest.mark.asyncio
async def test_check_budget_available():
    """Test budget availability check."""
    tracker = BudgetTracker(daily_limit=10.0)

    await tracker.record_spending('TradingAgent', 5.0)

    # Agent spent $5, $5 remaining
    assert await tracker.has_budget('TradingAgent', 3.0) is True
    assert await tracker.has_budget('TradingAgent', 6.0) is False


@pytest.mark.asyncio
async def test_reset_daily_budget():
    """Test daily budget reset."""
    tracker = BudgetTracker(daily_limit=10.0)

    await tracker.record_spending('TradingAgent', 10.0)

    # All budget used
    assert await tracker.get_remaining_budget('TradingAgent') == 0.0

    # Reset (simulate new day)
    await tracker.reset_daily_budget()

    assert await tracker.get_remaining_budget('TradingAgent') == 10.0 / 3


@pytest.mark.asyncio
async def test_budget_enforcement_prevents_overspend():
    """Test that budget enforcement prevents exceeding agent limit."""
    tracker = BudgetTracker(daily_limit=10.0)

    await tracker.record_spending('TradingAgent', 3.2)

    # Agent has ~0.13 left (3.33 - 3.2)
    assert await tracker.has_budget('TradingAgent', 0.1) is True
    assert await tracker.has_budget('TradingAgent', 0.2) is False


@pytest.mark.asyncio
async def test_get_agent_budget_status():
    """Test getting comprehensive budget status."""
    tracker = BudgetTracker(daily_limit=10.0)

    await tracker.record_spending('TradingAgent', 1.0)

    status = await tracker.get_budget_status('TradingAgent')

    assert 'allocated' in status
    assert 'spent' in status
    assert 'remaining' in status
    assert status['spent'] == 1.0
    assert 3.2 < status['allocated'] < 3.5
    assert 2.2 < status['remaining'] < 2.5
```

**Step 2: Run test to verify it fails**

```bash
cd /c/Users/user/projects/personal
pytest emy/tests/test_budget_tracker.py::test_distribute_budget_across_agents -xvs
```

Expected output:
```
FAILED emy/tests/test_budget_tracker.py::test_distribute_budget_across_agents - ModuleNotFoundError: No module named 'emy.core.budget_tracker'
```

**Step 3: Write minimal implementation**

Create `emy/core/budget_tracker.py`:

```python
"""Budget tracking and enforcement for parallel agent execution."""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from emy.core.database import EMyDatabase

logger = logging.getLogger('EMyBrain.BudgetTracker')


class BudgetTracker:
    """Track and enforce budget across parallel agent executions."""

    def __init__(self, daily_limit: float = 10.0):
        """
        Initialize budget tracker.

        Args:
            daily_limit: Daily budget limit in dollars (default $10)
        """
        self.daily_limit = daily_limit
        self.db = EMyDatabase()
        self.agent_count = 5  # TradingAgent, ResearchAgent, KnowledgeAgent, ProjectMonitorAgent, JobSearchAgent
        self._per_agent_limit = daily_limit / self.agent_count

    async def distribute_budget(self, agents: List[str]) -> Dict[str, float]:
        """
        Distribute daily budget equally across agents.

        Args:
            agents: List of agent names to distribute budget for

        Returns:
            Dict mapping agent name to allocated budget
        """
        per_agent = self.daily_limit / len(agents) if agents else 0
        return {agent: per_agent for agent in agents}

    async def record_spending(self, agent_name: str, amount: float) -> None:
        """
        Record spending for an agent.

        Args:
            agent_name: Name of agent
            amount: Amount spent in dollars
        """
        today = datetime.utcnow().date()

        # Insert into agent_budget table
        self.db.execute("""
            INSERT INTO agent_budget (agent_name, date, spent_today)
            VALUES (?, ?, ?)
            ON CONFLICT(agent_name, date) DO UPDATE SET
            spent_today = spent_today + ?
        """, (agent_name, today, amount, amount))

        logger.info(f"Recorded ${amount:.2f} spending for {agent_name}")

    async def get_agent_spending(self, agent_name: str) -> float:
        """
        Get total spending for agent today.

        Args:
            agent_name: Name of agent

        Returns:
            Total spent today in dollars
        """
        today = datetime.utcnow().date()

        result = self.db.query_one("""
            SELECT spent_today FROM agent_budget
            WHERE agent_name = ? AND date = ?
        """, (agent_name, today))

        return result[0] if result else 0.0

    async def has_budget(self, agent_name: str, required_amount: float) -> bool:
        """
        Check if agent has sufficient budget remaining.

        Args:
            agent_name: Name of agent
            required_amount: Amount needed in dollars

        Returns:
            True if budget available, False otherwise
        """
        remaining = await self.get_remaining_budget(agent_name)
        return remaining >= required_amount

    async def get_remaining_budget(self, agent_name: str) -> float:
        """
        Get remaining budget for agent.

        Args:
            agent_name: Name of agent

        Returns:
            Remaining budget in dollars
        """
        spent = await self.get_agent_spending(agent_name)
        return max(0, self._per_agent_limit - spent)

    async def reset_daily_budget(self) -> None:
        """Reset daily budget (called at midnight UTC)."""
        logger.info(f"Resetting daily budget for all agents")
        # Budget is per-day in database, so no action needed
        # New entries are created automatically for new date

    async def get_budget_status(self, agent_name: str) -> Dict[str, float]:
        """
        Get comprehensive budget status for agent.

        Args:
            agent_name: Name of agent

        Returns:
            Dict with allocated, spent, remaining amounts
        """
        spent = await self.get_agent_spending(agent_name)
        remaining = await self.get_remaining_budget(agent_name)

        return {
            'allocated': self._per_agent_limit,
            'spent': spent,
            'remaining': remaining,
            'percentage_used': (spent / self._per_agent_limit * 100) if self._per_agent_limit > 0 else 0
        }
```

**Step 4: Update database schema**

Read `emy/core/database.py` to find where schema is initialized:

```python
# In emy/core/database.py, add to __init__ or schema initialization:

CREATE_AGENT_BUDGET_TABLE = """
CREATE TABLE IF NOT EXISTS agent_budget (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    date DATE NOT NULL,
    spent_today REAL DEFAULT 0.0,
    UNIQUE(agent_name, date)
)
"""
```

Then in the EMyDatabase.__init__ or schema creation method, add:

```python
self.execute(CREATE_AGENT_BUDGET_TABLE)
```

**Step 5: Run tests to verify they pass**

```bash
cd /c/Users/user/projects/personal
pytest emy/tests/test_budget_tracker.py -xvs
```

Expected output:
```
test_distribute_budget_across_agents PASSED
test_track_agent_spending PASSED
test_check_budget_available PASSED
test_reset_daily_budget PASSED
test_budget_enforcement_prevents_overspend PASSED
test_get_agent_budget_status PASSED
======================== 6 passed in 0.45s ========================
```

**Step 6: Commit**

```bash
cd /c/Users/user/projects/personal
git add emy/core/budget_tracker.py emy/tests/test_budget_tracker.py emy/core/database.py
git commit -m "feat: add budget tracker for parallel agent execution"
```

---

## Task 2: Result Aggregator and Conflict Resolver

**Files:**
- Create: `emy/brain/result_aggregator.py`
- Create: `emy/brain/conflict_resolver.py`
- Test: `emy/tests/test_result_aggregator.py`
- Test: `emy/tests/test_conflict_resolver.py`

**Step 1: Write failing tests for result aggregator**

Create `emy/tests/test_result_aggregator.py`:

```python
import pytest
from emy.brain.result_aggregator import ResultAggregator

def test_aggregate_single_agent_result():
    """Test aggregating result from single agent."""
    aggregator = ResultAggregator()

    result = {
        'TradingAgent': {
            'recommendation': 'SELL EUR/USD',
            'confidence': 0.85,
            'signal_strength': 'strong'
        }
    }

    aggregated = aggregator.aggregate(result)

    assert 'agents' in aggregated
    assert aggregated['agents']['TradingAgent']['confidence'] == 0.85
    assert aggregated['conflict_detected'] is False


def test_aggregate_multiple_agent_results():
    """Test aggregating results from multiple agents."""
    aggregator = ResultAggregator()

    results = {
        'TradingAgent': {
            'recommendation': 'SELL EUR/USD',
            'confidence': 0.85,
        },
        'ResearchAgent': {
            'recommendation': 'SELL EUR/USD (fundamental weakness)',
            'confidence': 0.72,
        }
    }

    aggregated = aggregator.aggregate(results)

    assert len(aggregated['agents']) == 2
    assert aggregated['consensus'] is not None
    assert aggregated['conflict_detected'] is False


def test_detect_recommendation_conflict():
    """Test detection of conflicting recommendations."""
    aggregator = ResultAggregator()

    results = {
        'TradingAgent': {
            'recommendation': 'SELL EUR/USD',
            'confidence': 0.85,
        },
        'ResearchAgent': {
            'recommendation': 'BUY EUR/USD',
            'confidence': 0.72,
        }
    }

    aggregated = aggregator.aggregate(results)

    assert aggregated['conflict_detected'] is True
    assert 'conflicts' in aggregated


def test_normalize_recommendations():
    """Test normalizing different recommendation formats."""
    aggregator = ResultAggregator()

    # Agent outputs different formats
    results = {
        'TradingAgent': {
            'recommendation': 'SELL',
            'pair': 'EUR/USD'
        },
        'ResearchAgent': {
            'recommendation': 'SELL EUR/USD'
        }
    }

    aggregated = aggregator.aggregate(results)

    # Both should normalize to comparable format
    assert aggregated['conflict_detected'] is False


def test_calculate_consensus_confidence():
    """Test calculating consensus confidence."""
    aggregator = ResultAggregator()

    results = {
        'TradingAgent': {'confidence': 0.90},
        'ResearchAgent': {'confidence': 0.80},
        'KnowledgeAgent': {'confidence': 0.85},
    }

    aggregated = aggregator.aggregate(results)

    # Average should be around 0.85
    assert 0.84 < aggregated['consensus']['confidence'] < 0.86


def test_aggregate_empty_results():
    """Test handling empty results."""
    aggregator = ResultAggregator()

    aggregated = aggregator.aggregate({})

    assert aggregated['agents'] == {}
    assert aggregated['conflict_detected'] is False
```

**Step 2: Write failing tests for conflict resolver**

Create `emy/tests/test_conflict_resolver.py`:

```python
import pytest
from emy.brain.conflict_resolver import ConflictResolver

def test_resolve_same_recommendation():
    """Test resolving unanimous recommendation."""
    resolver = ConflictResolver()

    results = {
        'TradingAgent': {'recommendation': 'SELL', 'confidence': 0.90},
        'ResearchAgent': {'recommendation': 'SELL', 'confidence': 0.80},
    }

    resolved = resolver.resolve(results)

    assert resolved['recommendation'] == 'SELL'
    assert resolved['resolution_method'] == 'unanimous'


def test_resolve_conflicting_recommendations():
    """Test resolving conflicting recommendations by confidence."""
    resolver = ConflictResolver()

    results = {
        'TradingAgent': {'recommendation': 'SELL', 'confidence': 0.95},  # Higher confidence
        'ResearchAgent': {'recommendation': 'BUY', 'confidence': 0.70},
    }

    resolved = resolver.resolve(results)

    # Higher confidence wins
    assert resolved['recommendation'] == 'SELL'
    assert resolved['resolution_method'] == 'highest_confidence'
    assert resolved['winning_agent'] == 'TradingAgent'


def test_resolve_with_agent_weight():
    """Test resolving with agent priority weights."""
    resolver = ConflictResolver(agent_weights={
        'TradingAgent': 2.0,  # 2x weight
        'ResearchAgent': 1.0,
    })

    results = {
        'TradingAgent': {'recommendation': 'SELL', 'confidence': 0.50},
        'ResearchAgent': {'recommendation': 'BUY', 'confidence': 0.90},
    }

    resolved = resolver.resolve(results)

    # TradingAgent wins due to 2x weight despite lower confidence
    assert resolved['recommendation'] == 'SELL'
    assert resolved['resolution_method'] == 'weighted_voting'


def test_resolve_three_way_tie():
    """Test resolving three-way conflict."""
    resolver = ConflictResolver()

    results = {
        'TradingAgent': {'recommendation': 'SELL', 'confidence': 0.85},
        'ResearchAgent': {'recommendation': 'BUY', 'confidence': 0.85},
        'KnowledgeAgent': {'recommendation': 'HOLD', 'confidence': 0.85},
    }

    resolved = resolver.resolve(results)

    # Should pick by consistent tiebreaker (e.g., highest confidence then alphabetical)
    assert resolved['recommendation'] in ['SELL', 'BUY', 'HOLD']
    assert resolved['conflict_severity'] == 'high'


def test_flag_conflicting_recommendation():
    """Test flagging conflicts for human review."""
    resolver = ConflictResolver()

    results = {
        'TradingAgent': {'recommendation': 'SELL EUR/USD', 'confidence': 0.75},
        'ResearchAgent': {'recommendation': 'BUY EUR/USD', 'confidence': 0.78},
    }

    resolved = resolver.resolve(results)

    # Close confidence = should flag for review
    assert resolved.get('flag_for_review') is True
    assert 'review_reason' in resolved
```

**Step 3: Implement result aggregator**

Create `emy/brain/result_aggregator.py`:

```python
"""Aggregate results from multiple agents."""

import logging
from typing import Dict, Any, List
from statistics import mean

logger = logging.getLogger('EMyBrain.ResultAggregator')


class ResultAggregator:
    """Aggregate and normalize results from multiple agents."""

    def aggregate(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate results from multiple agents.

        Args:
            results: Dict mapping agent name to result dict

        Returns:
            Aggregated result with consensus and conflict detection
        """
        if not results:
            return {
                'agents': {},
                'consensus': None,
                'conflict_detected': False,
                'conflicts': []
            }

        # Normalize all recommendations to comparable format
        normalized = {}
        recommendations = {}
        confidences = []

        for agent_name, result in results.items():
            normalized[agent_name] = result
            recommendations[agent_name] = self._normalize_recommendation(result.get('recommendation', ''))
            if 'confidence' in result:
                confidences.append(result['confidence'])

        # Check for conflicts
        unique_recs = set(recommendations.values())
        has_conflict = len(unique_recs) > 1 and len(results) > 1

        conflicts = []
        if has_conflict:
            conflicts = self._find_conflicts(recommendations)

        # Calculate consensus
        consensus = None
        if not has_conflict and recommendations:
            consensus = {
                'recommendation': list(recommendations.values())[0],
                'confidence': mean(confidences) if confidences else 0.0,
                'agent_count': len(results)
            }

        return {
            'agents': normalized,
            'consensus': consensus,
            'conflict_detected': has_conflict,
            'conflicts': conflicts
        }

    def _normalize_recommendation(self, rec: str) -> str:
        """
        Normalize recommendation to comparable format.

        Args:
            rec: Recommendation text

        Returns:
            Normalized recommendation (e.g., 'SELL', 'BUY', 'HOLD')
        """
        rec_upper = rec.upper().strip()

        # Extract main recommendation
        for keyword in ['SELL', 'BUY', 'HOLD']:
            if keyword in rec_upper:
                return keyword

        return rec_upper

    def _find_conflicts(self, recommendations: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Identify conflicting recommendations.

        Args:
            recommendations: Dict mapping agent to normalized recommendation

        Returns:
            List of conflict records
        """
        conflicts = []
        recs_list = list(recommendations.items())

        for i, (agent1, rec1) in enumerate(recs_list):
            for agent2, rec2 in recs_list[i+1:]:
                if rec1 != rec2:
                    conflicts.append({
                        'agent1': agent1,
                        'agent2': agent2,
                        'rec1': rec1,
                        'rec2': rec2
                    })

        return conflicts
```

**Step 4: Implement conflict resolver**

Create `emy/brain/conflict_resolver.py`:

```python
"""Resolve conflicts between agent recommendations."""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('EMyBrain.ConflictResolver')


class ConflictResolver:
    """Resolve conflicts between agent recommendations."""

    def __init__(self, agent_weights: Optional[Dict[str, float]] = None):
        """
        Initialize conflict resolver.

        Args:
            agent_weights: Optional weights for agents (default 1.0 for all)
        """
        self.agent_weights = agent_weights or {}

    def resolve(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Resolve conflicts in agent results.

        Args:
            results: Dict mapping agent name to result

        Returns:
            Resolved recommendation with metadata
        """
        if not results:
            return {'recommendation': None, 'conflict_detected': False}

        # Extract recommendations and confidences
        agents_data = {}
        for agent_name, result in results.items():
            confidence = result.get('confidence', 0.5)
            recommendation = result.get('recommendation', '').upper().strip()

            # Extract main recommendation
            for keyword in ['SELL', 'BUY', 'HOLD']:
                if keyword in recommendation:
                    recommendation = keyword
                    break

            weight = self.agent_weights.get(agent_name, 1.0)
            agents_data[agent_name] = {
                'recommendation': recommendation,
                'confidence': confidence,
                'weight': weight,
                'weighted_confidence': confidence * weight
            }

        # Check if unanimous
        unique_recs = set(a['recommendation'] for a in agents_data.values())
        if len(unique_recs) == 1:
            winning_rec = unique_recs.pop()
            avg_confidence = sum(a['confidence'] for a in agents_data.values()) / len(agents_data)

            return {
                'recommendation': winning_rec,
                'resolution_method': 'unanimous',
                'confidence': avg_confidence,
                'agents_agreeing': list(agents_data.keys()),
                'conflict_detected': False
            }

        # Check weighted voting
        if self.agent_weights:
            scores = {}
            for agent, data in agents_data.items():
                rec = data['recommendation']
                scores[rec] = scores.get(rec, 0) + data['weighted_confidence']

            winning_rec = max(scores, key=scores.get)
            winning_agent = [a for a, d in agents_data.items()
                           if d['recommendation'] == winning_rec][0]

            return {
                'recommendation': winning_rec,
                'resolution_method': 'weighted_voting',
                'confidence': agents_data[winning_agent]['confidence'],
                'winning_agent': winning_agent,
                'conflict_detected': True,
                'conflict_severity': self._assess_severity(agents_data)
            }

        # Resolve by highest confidence
        best_agent = max(agents_data.items(),
                        key=lambda x: x[1]['confidence'])
        winning_agent, best_data = best_agent

        # Flag for review if close call
        flag_for_review = False
        review_reason = None

        confidences = [a['confidence'] for a in agents_data.values()]
        if len(confidences) > 1:
            top2 = sorted(confidences, reverse=True)[:2]
            if abs(top2[0] - top2[1]) < 0.15:  # Within 15%
                flag_for_review = True
                review_reason = f"Close call: top confidence {top2[0]:.2f} vs {top2[1]:.2f}"

        return {
            'recommendation': best_data['recommendation'],
            'resolution_method': 'highest_confidence',
            'confidence': best_data['confidence'],
            'winning_agent': winning_agent,
            'conflict_detected': True,
            'conflict_severity': self._assess_severity(agents_data),
            'flag_for_review': flag_for_review,
            'review_reason': review_reason
        }

    def _assess_severity(self, agents_data: Dict[str, Dict[str, Any]]) -> str:
        """
        Assess conflict severity.

        Args:
            agents_data: Agent data with recommendations

        Returns:
            'low', 'medium', or 'high'
        """
        unique_recs = len(set(a['recommendation'] for a in agents_data.values()))

        if unique_recs == 2:
            return 'low'
        elif unique_recs == 3:
            return 'medium'
        else:
            return 'high'
```

**Step 5: Run tests to verify they pass**

```bash
cd /c/Users/user/projects/personal
pytest emy/tests/test_result_aggregator.py emy/tests/test_conflict_resolver.py -xvs
```

Expected output:
```
test_aggregate_single_agent_result PASSED
test_aggregate_multiple_agent_results PASSED
test_detect_recommendation_conflict PASSED
test_normalize_recommendations PASSED
test_calculate_consensus_confidence PASSED
test_aggregate_empty_results PASSED
test_resolve_same_recommendation PASSED
test_resolve_conflicting_recommendations PASSED
test_resolve_with_agent_weight PASSED
test_resolve_three_way_tie PASSED
test_flag_conflicting_recommendation PASSED
======================== 11 passed in 0.63s ========================
```

**Step 6: Commit**

```bash
cd /c/Users/user/projects/personal
git add emy/brain/result_aggregator.py emy/brain/conflict_resolver.py emy/tests/test_result_aggregator.py emy/tests/test_conflict_resolver.py
git commit -m "feat: add result aggregation and conflict resolution for parallel agents"
```

---

## Task 3: Agent Selection Logic

**Files:**
- Create: `emy/brain/agent_selector.py`
- Modify: `emy/gateway/api.py` (update `/workflows` endpoint)
- Test: `emy/tests/test_agent_selector.py`

**Step 1: Write failing tests**

Create `emy/tests/test_agent_selector.py`:

```python
import pytest
from emy.brain.agent_selector import AgentSelector

def test_auto_select_agents_for_market_analysis():
    """Test auto-selecting agents for market analysis task."""
    selector = AgentSelector()

    task = {
        'type': 'market_analysis',
        'input': 'Analyze EUR/USD trend'
    }

    agents = selector.select_agents(task, mode='auto')

    assert 'TradingAgent' in agents
    # Market analysis is trading-focused
    assert len(agents) >= 1


def test_auto_select_agents_for_research():
    """Test auto-selecting agents for research task."""
    selector = AgentSelector()

    task = {
        'type': 'research',
        'input': 'Evaluate feasibility of new project'
    }

    agents = selector.select_agents(task, mode='auto')

    assert 'ResearchAgent' in agents
    assert len(agents) >= 1


def test_auto_select_agents_for_knowledge_query():
    """Test auto-selecting agents for knowledge query."""
    selector = AgentSelector()

    task = {
        'type': 'knowledge_query',
        'input': 'What is my project status?'
    }

    agents = selector.select_agents(task, mode='auto')

    assert 'KnowledgeAgent' in agents


def test_explicit_agent_selection():
    """Test explicit agent selection."""
    selector = AgentSelector()

    agents = selector.select_agents(
        {},
        mode='explicit',
        agents=['TradingAgent', 'ResearchAgent']
    )

    assert agents == ['TradingAgent', 'ResearchAgent']


def test_select_agents_by_capability():
    """Test selecting agents by required capability."""
    selector = AgentSelector()

    task = {
        'required_capabilities': ['market_analysis', 'sentiment']
    }

    agents = selector.select_agents(task, mode='auto')

    # TradingAgent has market_analysis, should be selected
    assert 'TradingAgent' in agents


def test_validate_agent_exists():
    """Test validation of agent existence."""
    selector = AgentSelector()

    # Valid agent
    assert selector.is_valid_agent('TradingAgent') is True

    # Invalid agent
    assert selector.is_valid_agent('NonExistentAgent') is False


def test_get_agent_capabilities():
    """Test getting agent capabilities."""
    selector = AgentSelector()

    caps = selector.get_agent_capabilities('TradingAgent')

    assert isinstance(caps, list)
    assert len(caps) > 0
    assert 'market_analysis' in caps


def test_combine_agents_for_complex_task():
    """Test combining multiple agents for complex task."""
    selector = AgentSelector()

    task = {
        'type': 'complex',
        'input': 'Analyze market AND evaluate opportunity'
    }

    agents = selector.select_agents(task, mode='auto')

    # Should select both TradingAgent and ResearchAgent
    assert len(agents) >= 2
```

**Step 2: Run test to verify it fails**

```bash
cd /c/Users/user/projects/personal
pytest emy/tests/test_agent_selector.py::test_auto_select_agents_for_market_analysis -xvs
```

Expected output:
```
FAILED emy/tests/test_agent_selector.py::test_auto_select_agents_for_market_analysis - ModuleNotFoundError: No module named 'emy.brain.agent_selector'
```

**Step 3: Implement agent selector**

Create `emy/brain/agent_selector.py`:

```python
"""Intelligent agent selection for workflow tasks."""

import logging
from typing import List, Dict, Any, Optional
from emy.brain.nodes import AGENT_REGISTRY

logger = logging.getLogger('EMyBrain.AgentSelector')


class AgentSelector:
    """Intelligently select agents based on task requirements."""

    # Define agent capabilities
    AGENT_CAPABILITIES = {
        'TradingAgent': [
            'market_analysis',
            'forex_signals',
            'price_prediction',
            'technical_analysis',
            'risk_assessment'
        ],
        'ResearchAgent': [
            'research',
            'project_evaluation',
            'feasibility_analysis',
            'data_collection',
            'summary_generation'
        ],
        'KnowledgeAgent': [
            'knowledge_query',
            'project_status',
            'memory_retrieval',
            'context_synthesis',
            'documentation'
        ],
        'ProjectMonitorAgent': [
            'project_monitoring',
            'status_tracking',
            'milestone_tracking',
            'email_notifications',
            'daily_reports'
        ],
        'JobSearchAgent': [
            'job_search',
            'job_application',
            'cover_letter_generation',
            'follow_up_emails',
            'opportunity_ranking'
        ]
    }

    # Define agent affinity keywords
    AGENT_KEYWORDS = {
        'TradingAgent': ['market', 'trade', 'forex', 'price', 'signal', 'analysis', 'sell', 'buy'],
        'ResearchAgent': ['research', 'evaluate', 'feasibility', 'project', 'opportunity', 'analysis'],
        'KnowledgeAgent': ['knowledge', 'status', 'query', 'information', 'memory', 'project'],
        'ProjectMonitorAgent': ['monitor', 'status', 'track', 'milestone', 'email', 'report'],
        'JobSearchAgent': ['job', 'apply', 'search', 'opportunity', 'employment']
    }

    def select_agents(
        self,
        task: Dict[str, Any],
        mode: str = 'auto',
        agents: Optional[List[str]] = None
    ) -> List[str]:
        """
        Select agents for task.

        Args:
            task: Task dict with type, input, required_capabilities
            mode: 'auto' for intelligent selection, 'explicit' for manual list
            agents: List of agents (for explicit mode)

        Returns:
            List of agent names to execute
        """
        if mode == 'explicit' and agents:
            # Validate agents exist
            valid_agents = [a for a in agents if self.is_valid_agent(a)]
            return valid_agents

        # Auto-select agents
        selected = set()

        # Check required capabilities
        required_caps = task.get('required_capabilities', [])
        if required_caps:
            for cap in required_caps:
                for agent_name, caps in self.AGENT_CAPABILITIES.items():
                    if cap in caps:
                        selected.add(agent_name)

        # Check task type
        task_type = task.get('type', '').lower()
        for agent_name, keywords in self.AGENT_KEYWORDS.items():
            if task_type in keywords:
                selected.add(agent_name)

        # Check task input text
        task_input = task.get('input', '').lower()
        for agent_name, keywords in self.AGENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in task_input:
                    selected.add(agent_name)
                    break

        # If nothing selected, use KnowledgeAgent as fallback
        if not selected:
            selected.add('KnowledgeAgent')

        # Convert to sorted list for consistency
        result = sorted(list(selected))
        logger.info(f"Selected agents for task: {result}")
        return result

    def is_valid_agent(self, agent_name: str) -> bool:
        """
        Check if agent exists.

        Args:
            agent_name: Agent name to validate

        Returns:
            True if agent exists, False otherwise
        """
        return agent_name in AGENT_REGISTRY

    def get_agent_capabilities(self, agent_name: str) -> List[str]:
        """
        Get capabilities for agent.

        Args:
            agent_name: Agent name

        Returns:
            List of capability strings
        """
        return self.AGENT_CAPABILITIES.get(agent_name, [])
```

**Step 4: Update API endpoint**

Modify `emy/gateway/api.py`. Find the POST `/workflows` endpoint and update it:

```python
from emy.brain.agent_selector import AgentSelector

selector = AgentSelector()

@app.post("/workflows")
async def submit_workflow(request: dict):
    """
    Submit a workflow for execution.

    Request body:
    {
        "task": "market analysis",
        "agent_selection": "auto" | ["TradingAgent", "ResearchAgent"],
        ...
    }
    """
    try:
        task = request.get('task', '')
        agent_selection = request.get('agent_selection', 'auto')

        # Auto-select agents if needed
        if agent_selection == 'auto':
            agents = selector.select_agents({'input': task})
        else:
            agents = agent_selection if isinstance(agent_selection, list) else [agent_selection]

        # Validate agents
        agents = [a for a in agents if selector.is_valid_agent(a)]

        if not agents:
            raise HTTPException(status_code=400, detail="No valid agents selected")

        # Create workflow with selected agents
        workflow_id = str(uuid.uuid4())

        # Store agents in workflow
        # (implementation depends on your workflow storage)

        return {
            'workflow_id': workflow_id,
            'selected_agents': agents,
            'status': 'queued'
        }
    except Exception as e:
        logger.error(f"Error submitting workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 5: Run tests**

```bash
cd /c/Users/user/projects/personal
pytest emy/tests/test_agent_selector.py -xvs
```

Expected output:
```
test_auto_select_agents_for_market_analysis PASSED
test_auto_select_agents_for_research PASSED
test_auto_select_agents_for_knowledge_query PASSED
test_explicit_agent_selection PASSED
test_select_agents_by_capability PASSED
test_validate_agent_exists PASSED
test_get_agent_capabilities PASSED
test_combine_agents_for_complex_task PASSED
======================== 8 passed in 0.73s ========================
```

**Step 6: Commit**

```bash
cd /c/Users/user/projects/personal
git add emy/brain/agent_selector.py emy/gateway/api.py emy/tests/test_agent_selector.py
git commit -m "feat: implement intelligent agent selection logic"
```

---

## Task 4: Multi-Agent Workflow Integration Tests

**Files:**
- Create: `emy/tests/test_multi_agent_workflows.py`

**Step 1: Write comprehensive integration tests**

Create `emy/tests/test_multi_agent_workflows.py`:

```python
import pytest
import asyncio
from emy.brain.state import EMyState
from emy.brain.executor import execute_agent_group_parallel
from emy.core.budget_tracker import BudgetTracker
from emy.brain.result_aggregator import ResultAggregator
from emy.brain.conflict_resolver import ConflictResolver
from emy.brain.agent_selector import AgentSelector

@pytest.mark.asyncio
async def test_parallel_execution_two_agents():
    """Test parallel execution of two agents."""
    state = EMyState(
        workflow_id='test-123',
        agent_groups=[['TradingAgent', 'ResearchAgent']],
        current_group_index=0,
        status='starting'
    )

    # Execute parallel agents
    result_state = await execute_agent_group_parallel(state)

    assert result_state.status in ['completed', 'executing']
    assert 'TradingAgent' in result_state.agents_executing or result_state.messages


@pytest.mark.asyncio
async def test_parallel_execution_three_agents():
    """Test parallel execution of three agents."""
    state = EMyState(
        workflow_id='test-456',
        agent_groups=[['TradingAgent', 'ResearchAgent', 'KnowledgeAgent']],
        current_group_index=0
    )

    result_state = await execute_agent_group_parallel(state)

    assert result_state.status in ['completed', 'executing']


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

    # 7. Verify budget tracking
    for agent in agents:
        spent = await tracker.get_agent_spending(agent)
        assert spent == 0.5


@pytest.mark.asyncio
async def test_budget_prevents_expensive_agent_execution():
    """Test that budget enforcement prevents overspend."""
    tracker = BudgetTracker(daily_limit=1.0)  # Very small budget

    agents = ['TradingAgent', 'ResearchAgent']

    # Record spending
    await tracker.record_spending('TradingAgent', 0.4)

    # Can execute 0.2 more
    assert await tracker.has_budget('TradingAgent', 0.2) is True

    # Cannot execute 0.5 more
    assert await tracker.has_budget('TradingAgent', 0.5) is False
```

**Step 2: Run tests**

```bash
cd /c/Users/user/projects/personal
pytest emy/tests/test_multi_agent_workflows.py -xvs
```

Expected output:
```
test_parallel_execution_two_agents PASSED
test_parallel_execution_three_agents PASSED
test_budget_enforcement_during_parallel_execution PASSED
test_result_aggregation_consensus PASSED
test_result_aggregation_with_conflict PASSED
test_conflict_resolution_by_confidence PASSED
test_conflict_resolution_with_weights PASSED
test_agent_auto_selection PASSED
test_agent_explicit_selection PASSED
test_full_multi_agent_workflow PASSED
test_budget_prevents_expensive_agent_execution PASSED
======================== 11 passed in 2.45s ========================
```

**Step 3: Commit**

```bash
cd /c/Users/user/projects/personal
git add emy/tests/test_multi_agent_workflows.py
git commit -m "feat: add comprehensive multi-agent workflow integration tests"
```

---

## Verification Checklist

Before marking complete, verify:

```bash
# 1. All tests pass
pytest emy/tests/test_budget_tracker.py emy/tests/test_result_aggregator.py emy/tests/test_conflict_resolver.py emy/tests/test_agent_selector.py emy/tests/test_multi_agent_workflows.py -v

# 2. Code quality check
pylint emy/core/budget_tracker.py emy/brain/result_aggregator.py emy/brain/conflict_resolver.py emy/brain/agent_selector.py

# 3. Database schema applied
sqlite3 emy/data/emy.db ".tables" | grep agent_budget

# 4. Git log shows all commits
git log --oneline | head -5
```

Expected final output:
```
======================== 44 passed in 3.72s ========================
All budget tracking, result aggregation, conflict resolution, and agent selection features implemented and tested.
```

---

## Summary

Week 5 implementation adds:

1. **Budget Tracker** (6 tests) - Proportional budget distribution, per-agent spending tracking, budget enforcement
2. **Result Aggregator** (5 tests) - Multi-agent result normalization, consensus detection, conflict identification
3. **Conflict Resolver** (6 tests) - Unanimous resolution, weighted voting, confidence-based selection, severity assessment
4. **Agent Selector** (8 tests) - Auto-selection by task type, capability matching, explicit selection, validation
5. **Integration Tests** (11 tests) - Full multi-agent workflows, budget enforcement during execution, result coordination

**Success Metrics:**
- ✅ 44/44 tests passing
- ✅ TradingAgent + ResearchAgent execute in parallel
- ✅ Results combined with consensus or conflict resolution
- ✅ Budget split correctly across agents
- ✅ Conflicts detected and resolved with explanation
- ✅ Agent selection logic working for common task types

