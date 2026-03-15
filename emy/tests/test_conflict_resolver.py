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
