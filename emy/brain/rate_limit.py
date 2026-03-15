"""Rate limiting for Emy Brain service."""

from collections import defaultdict
from time import time
import os
import logging

logger = logging.getLogger('EMyBrain.RateLimit')


class RateLimiter:
    """Simple token bucket rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests per window (default: 100)
            window_seconds: Time window in seconds (default: 60 = 1 minute)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)  # ip → [timestamps]

    def is_allowed(self, client_ip: str) -> bool:
        """
        Check if request is allowed for client IP.

        Args:
            client_ip: Client IP address

        Returns:
            True if allowed, False if rate limited
        """
        now = time()
        window_start = now - self.window_seconds

        # Clean old requests outside window
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip]
            if ts > window_start
        ]

        # Check limit
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return False

        # Record request timestamp
        self.requests[client_ip].append(now)
        return True

    def reset(self):
        """Clear all stored requests (for testing)."""
        self.requests.clear()


# Global rate limiter instance
_max_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
_window_seconds = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

rate_limiter = RateLimiter(max_requests=_max_requests, window_seconds=_window_seconds)
