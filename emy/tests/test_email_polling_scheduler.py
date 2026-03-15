import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from emy.tasks.email_polling_task import check_inbox_periodically

@patch('emy.tasks.email_polling_task.log_polling_event', new_callable=AsyncMock)
@patch('emy.tasks.email_polling_task.EmailParser')
def test_polling_task_checks_inbox(mock_parser_class, mock_log_event):
    """Test that polling task calls email parser check_inbox()"""
    mock_parser = AsyncMock()
    mock_parser_class.return_value = mock_parser
    mock_parser.check_inbox.return_value = []

    with patch('emy.tasks.email_polling_task.asyncio.run') as mock_run:
        mock_run.return_value = []
        result = check_inbox_periodically()

        assert result['status'] == 'success'
        assert result['processed'] == 0

@patch('emy.tasks.email_polling_task.log_polling_event', new_callable=AsyncMock)
@patch('emy.tasks.email_polling_task.EmailParser')
def test_polling_task_logs_event(mock_parser_class, mock_log_event):
    """Test that polling task logs event to database"""
    mock_parser = AsyncMock()
    mock_parser_class.return_value = mock_parser
    mock_parser.check_inbox.return_value = []

    with patch('emy.tasks.email_polling_task.asyncio.run') as mock_run:
        mock_run.return_value = []
        result = check_inbox_periodically()

        assert result['status'] == 'success'
        assert result['processed'] == 0

@patch('emy.tasks.email_polling_task.log_polling_event', new_callable=AsyncMock)
@patch('emy.tasks.email_polling_task.redis_client')
@patch('emy.tasks.email_polling_task.EmailParser')
def test_polling_task_rate_limiting(mock_parser_class, mock_redis, mock_log_event):
    """Test that polling task respects rate limiting"""
    # Setup redis mock to indicate rate limit exceeded
    mock_redis.incr.return_value = 11  # Exceeds limit (11 > 10)

    with patch('emy.tasks.email_polling_task.asyncio.run') as mock_run:
        mock_run.return_value = []
        result = check_inbox_periodically()

        # Should return rate_limited status
        assert result['status'] == 'rate_limited'
        assert result['processed'] == 0


@pytest.mark.asyncio
async def test_polling_task_production_environment():
    """Test polling task configuration for production (Render)"""
    from emy.config.celery_config import celery_app

    # Verify Celery config has correct schedule
    schedule = celery_app.conf.beat_schedule
    assert 'check-inbox-every-10-minutes' in schedule

    # Verify 10-minute interval
    task_config = schedule['check-inbox-every-10-minutes']
    assert task_config['schedule'] == 10.0 * 60  # 600 seconds

    # Verify rate limiting configured
    rate_limits = celery_app.conf.task_rate_limit
    assert 'emy.tasks.email_polling_task.check_inbox_periodically' in rate_limits


@pytest.mark.asyncio
async def test_polling_status_endpoint():
    """Test /emails/polling-status endpoint"""
    from fastapi.testclient import TestClient
    from emy.gateway.api import app

    client = TestClient(app)
    response = client.get('/emails/polling-status')

    assert response.status_code == 200
    data = response.json()
    assert 'status' in data
    assert 'last_check' in data or data['status'] == 'no_data'
    assert 'email_count' in data
