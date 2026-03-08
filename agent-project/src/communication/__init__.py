"""
Communication System

This package handles inter-agent communication and message routing.
"""

from .message_bus import MessageBus
from .protocols import CommunicationProtocol

__all__ = ['MessageBus', 'CommunicationProtocol']














