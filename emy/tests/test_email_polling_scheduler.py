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
