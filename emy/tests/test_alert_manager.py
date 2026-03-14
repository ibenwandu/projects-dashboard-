"""Test-Driven Development: AlertManager - Centralized Alert System

Tests written FIRST, implementation follows.
RED → GREEN → REFACTOR cycle.
"""

import pytest
import time
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from emy.core.alert_manager import AlertManager
from emy.core.database import EMyDatabase
from emy.tools.notification_tool import PushoverNotifier


class TestAlertManagerThrottling:
    """Test throttling behavior per alert_type"""

    @pytest.fixture
    def manager(self):
        """Create AlertManager with mocked notifier and database"""
        mock_notifier = Mock(spec=PushoverNotifier)
        mock_db = Mock(spec=EMyDatabase)
        return AlertManager(notifier=mock_notifier, db=mock_db)

    def test_send_returns_true_on_first_send(self, manager):
        """First send always succeeds and notifier is called"""
        manager.notifier.send_alert.return_value = True

        result = manager.send(
            alert_type='trade_opened',
            title='Trade Opened',
            message='EUR/USD opened',
            priority=0,
            throttle_seconds=60
        )

        assert result is True
        manager.notifier.send_alert.assert_called_once()
        manager.db.log_alert.assert_called_once()

    def test_send_throttled_within_window(self, manager):
        """Second send within throttle window returns False, notifier not called"""
        manager.notifier.send_alert.return_value = True

        # First send
        manager.send(
            alert_type='trade_opened',
            title='Trade Opened',
            message='EUR/USD opened',
            throttle_seconds=60
        )

        # Second send immediately after (within throttle window)
        result = manager.send(
            alert_type='trade_opened',
            title='Trade Opened',
            message='GBP/USD opened',
            throttle_seconds=60
        )

        assert result is False
        manager.notifier.send_alert.assert_called_once()  # Still only 1 call
        manager.db.log_alert.assert_called_once()  # Still only 1 log

    def test_send_allowed_after_throttle_expires(self, manager):
        """Send allowed after throttle window expires"""
        manager.notifier.send_alert.return_value = True

        # First send
        manager.send(
            alert_type='trade_opened',
            title='Trade Opened',
            message='EUR/USD opened',
            throttle_seconds=1  # 1 second throttle
        )

        # Wait for throttle to expire
        time.sleep(1.1)

        # Second send after throttle expires
        result = manager.send(
            alert_type='trade_opened',
            title='Trade Opened',
            message='GBP/USD opened',
            throttle_seconds=1
        )

        assert result is True
        assert manager.notifier.send_alert.call_count == 2
        assert manager.db.log_alert.call_count == 2

    def test_different_alert_types_have_separate_throttles(self, manager):
        """Different alert types maintain separate throttle timers"""
        manager.notifier.send_alert.return_value = True

        # Send first alert type
        manager.send(
            alert_type='trade_opened',
            title='Trade Opened',
            message='EUR/USD opened',
            throttle_seconds=60
        )

        # Send different alert type immediately (should succeed)
        result = manager.send(
            alert_type='trade_closed',
            title='Trade Closed',
            message='EUR/USD closed',
            throttle_seconds=60
        )

        assert result is True
        assert manager.notifier.send_alert.call_count == 2
        assert manager.db.log_alert.call_count == 2


class TestAlertManagerBadges:
    """Test unread alert badge tracking"""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create AlertManager with real database for badge testing"""
        db_path = tmp_path / "test_emy.db"
        mock_notifier = Mock(spec=PushoverNotifier)
        mock_notifier.send_alert.return_value = True
        db = EMyDatabase(str(db_path))
        db.initialize_schema()
        return AlertManager(notifier=mock_notifier, db=db)

    def test_unread_count_zero_initially(self, manager):
        """Unread count starts at zero"""
        count = manager.get_unread_count()
        assert count == 0

    def test_unread_count_increments_on_send(self, manager):
        """Unread count increments when alert is sent"""
        manager.send(
            alert_type='trade_opened',
            title='Trade Opened',
            message='EUR/USD opened'
        )

        count = manager.get_unread_count()
        assert count == 1

        # Send another alert
        manager.send(
            alert_type='trade_closed',
            title='Trade Closed',
            message='EUR/USD closed'
        )

        count = manager.get_unread_count()
        assert count == 2

    def test_mark_read_clears_all_badges(self, manager):
        """mark_read() with no args clears all unread alerts"""
        # Send multiple alerts (use different types to avoid throttling)
        manager.send(
            alert_type='trade_opened',
            title='Trade Opened 1',
            message='EUR/USD opened'
        )
        manager.send(
            alert_type='trade_opened_high',
            title='Trade Opened 2',
            message='GBP/USD opened'
        )
        manager.send(
            alert_type='trade_closed',
            title='Trade Closed',
            message='AUD/USD closed'
        )

        assert manager.get_unread_count() == 3

        # Mark all as read
        updated = manager.mark_read()

        assert updated == 3
        assert manager.get_unread_count() == 0

    def test_mark_read_by_type_clears_only_that_type(self, manager):
        """mark_read(alert_type) clears only specified type"""
        # Send multiple alert types (use different types to avoid throttling)
        manager.send(
            alert_type='trade_opened',
            title='Trade Opened 1',
            message='EUR/USD opened'
        )
        manager.send(
            alert_type='trade_opened_high',
            title='Trade Opened 2',
            message='GBP/USD opened'
        )
        manager.send(
            alert_type='trade_closed',
            title='Trade Closed',
            message='AUD/USD closed'
        )

        assert manager.get_unread_count() == 3

        # Mark only 'trade_opened' as read
        updated = manager.mark_read(alert_type='trade_opened')

        assert updated == 1  # Only 1 'trade_opened' alert
        assert manager.get_unread_count() == 2  # 'trade_opened_high' + 'trade_closed' remain

        # Unread should only be 'trade_opened_high' and 'trade_closed'
        remaining_closed = manager.db.get_unread_alerts(alert_type='trade_closed')
        assert len(remaining_closed) == 1
        remaining_high = manager.db.get_unread_alerts(alert_type='trade_opened_high')
        assert len(remaining_high) == 1


class TestAlertManagerPushover:
    """Test Pushover integration"""

    @pytest.fixture
    def manager(self):
        """Create AlertManager with mocked notifier"""
        mock_notifier = Mock(spec=PushoverNotifier)
        mock_db = Mock(spec=EMyDatabase)
        return AlertManager(notifier=mock_notifier, db=mock_db)

    def test_notifier_called_when_not_throttled(self, manager):
        """Notifier is called when send is not throttled"""
        manager.notifier.send_alert.return_value = True

        manager.send(
            alert_type='test_alert',
            title='Test',
            message='Test message',
            priority=1
        )

        manager.notifier.send_alert.assert_called_once_with(
            title='Test',
            message='Test message',
            priority=1
        )

    def test_notifier_not_called_when_throttled(self, manager):
        """Notifier is NOT called when send is throttled"""
        manager.notifier.send_alert.return_value = True

        # First send
        manager.send(
            alert_type='test_alert',
            title='Test',
            message='Test message',
            throttle_seconds=60
        )

        # Second send (throttled)
        manager.send(
            alert_type='test_alert',
            title='Test',
            message='Different message',
            throttle_seconds=60
        )

        manager.notifier.send_alert.assert_called_once()

    def test_notifier_not_called_when_send_fails(self, manager):
        """Database log not created when notifier fails"""
        manager.notifier.send_alert.return_value = False

        result = manager.send(
            alert_type='test_alert',
            title='Test',
            message='Test message'
        )

        assert result is False
        manager.db.log_alert.assert_not_called()
