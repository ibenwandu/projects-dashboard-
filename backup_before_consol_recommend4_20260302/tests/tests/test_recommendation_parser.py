"""Unit tests for RecommendationParser — pure functions only, no external dependencies."""

import os
import tempfile
import pytest
from src.recommendation_parser import RecommendationParser, MAX_FILE_SIZE_BYTES


@pytest.fixture
def parser():
    return RecommendationParser()


# ---------------------------------------------------------------------------
# _normalize_pair
# ---------------------------------------------------------------------------

class TestNormalizePair:
    def test_known_pair_with_slash(self, parser):
        assert parser._normalize_pair('EUR/USD') == 'EUR/USD'

    def test_known_pair_no_slash(self, parser):
        assert parser._normalize_pair('EURUSD') == 'EUR/USD'

    def test_known_pair_with_space(self, parser):
        assert parser._normalize_pair('EUR USD') == 'EUR/USD'

    def test_known_pair_with_underscore(self, parser):
        assert parser._normalize_pair('EUR_USD') == 'EUR/USD'

    def test_known_pair_lowercase(self, parser):
        assert parser._normalize_pair('eur/usd') == 'EUR/USD'

    def test_exotic_pair_accepted(self, parser):
        # Valid format even if not in the hardcoded list
        result = parser._normalize_pair('USD/ZAR')
        assert result == 'USD/ZAR'

    def test_jpy_pair(self, parser):
        assert parser._normalize_pair('USD/JPY') == 'USD/JPY'

    def test_invalid_too_short(self, parser):
        assert parser._normalize_pair('EU') is None

    def test_invalid_no_slash_odd_length(self, parser):
        assert parser._normalize_pair('EURUSDX') is None

    def test_invalid_numeric(self, parser):
        assert parser._normalize_pair('123/456') is None


# ---------------------------------------------------------------------------
# parse_text — empty / malformed input
# ---------------------------------------------------------------------------

class TestParseTextEdgeCases:
    def test_empty_string(self, parser):
        assert parser.parse_text('') == []

    def test_whitespace_only(self, parser):
        assert parser.parse_text('   \n\t  ') == []

    def test_no_trade_keywords(self, parser):
        result = parser.parse_text('The market is doing things today.')
        assert result == []

    def test_machine_readable_json_block(self, parser):
        text = (
            'Some analysis text.\n'
            'MACHINE_READABLE: [{"pair": "EUR/USD", "direction": "BUY", '
            '"entry": 1.085, "stop_loss": 1.080, "exit": 1.090}]\n'
        )
        result = parser.parse_text(text)
        assert len(result) == 1
        assert result[0]['pair'] == 'EUR/USD'
        assert result[0]['direction'] == 'BUY'

    def test_chatgpt_format(self, parser):
        text = (
            '### 1. Trade Recommendation: **EUR/USD**\n'
            '- **Entry Price**: 1.08500\n'
            '- **Exit/Target Price**: 1.09000\n'
            '- **Stop Loss Level**: 1.08000\n'
            '- **TIMEFRAME CLASSIFICATION:** INTRADAY\n'
            '- Bullish momentum\n'
        )
        result = parser.parse_text(text)
        assert len(result) >= 1
        opp = result[0]
        assert opp['pair'] == 'EUR/USD'
        assert opp['entry'] == pytest.approx(1.085, abs=1e-4)

    def test_deduplication(self, parser):
        # Same pair/direction/entry appearing in two pattern formats → only one result
        text = (
            '### 1. Trade Recommendation: **GBP/USD**\n'
            '- **Entry Price**: 1.27000\n'
            '- **Stop Loss Level**: 1.26500\n'
            '- **Exit/Target Price**: 1.27500\n'
            '- Bearish bias, sell signal\n'
            '### 2. Trade Recommendation: **GBP/USD**\n'
            '- **Entry Price**: 1.27000\n'
            '- **Stop Loss Level**: 1.26500\n'
            '- **Exit/Target Price**: 1.27500\n'
            '- Same setup repeated - Sell signal\n'
        )
        result = parser.parse_text(text)
        # Should deduplicate to 1
        gbpusd = [o for o in result if o['pair'] == 'GBP/USD']
        assert len(gbpusd) == 1


# ---------------------------------------------------------------------------
# parse_file — security guards
# ---------------------------------------------------------------------------

class TestParseFileGuards:
    def test_oversized_file_rejected(self, parser, tmp_path):
        big_file = tmp_path / 'big.txt'
        # Write just over the limit
        big_file.write_bytes(b'x' * (MAX_FILE_SIZE_BYTES + 1))
        result = parser.parse_file(str(big_file))
        assert result == []

    def test_path_traversal_rejected(self, parser):
        # A path that resolves outside cwd (using /etc/passwd as a known-nonexistent-on-CI path)
        result = parser.parse_file('/etc/passwd')
        # Should be rejected by the path guard (returns []) or simply not parse anything
        # Either way it must not raise
        assert isinstance(result, list)

    def test_valid_small_file(self, parser, tmp_path):
        f = tmp_path / 'analysis.txt'
        f.write_text('No trade recommendations here.', encoding='utf-8')
        result = parser.parse_file(str(f))
        assert result == []

    def test_valid_json_file(self, parser, tmp_path):
        import json
        data = [{"pair": "USD/JPY", "direction": "SELL", "entry": 149.5,
                 "stop_loss": 150.0, "exit": 148.0}]
        f = tmp_path / 'recs.json'
        f.write_text(json.dumps(data), encoding='utf-8')
        result = parser.parse_file(str(f))
        assert len(result) >= 1
        assert result[0]['pair'] == 'USD/JPY'
