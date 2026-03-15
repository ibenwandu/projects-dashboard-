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
