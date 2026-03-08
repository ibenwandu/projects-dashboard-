"""
Communication Protocols

This module defines communication protocols for inter-agent communication.
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class MessageType(Enum):
    """Message types for inter-agent communication."""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    RESEARCH_REQUEST = "research_request"
    ANALYSIS_REQUEST = "analysis_request"
    WRITING_REQUEST = "writing_request"
    QUALITY_CHECK_REQUEST = "quality_check_request"
    VALIDATION_REQUEST = "validation_request"
    WORKFLOW_UPDATE = "workflow_update"
    ERROR_NOTIFICATION = "error_notification"
    HEARTBEAT = "heartbeat"


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProtocolMessage:
    """Base protocol message structure."""
    message_id: str
    message_type: MessageType
    sender: str
    recipient: str
    timestamp: datetime
    payload: Dict[str, Any]
    priority: int = 1
    retry_count: int = 0
    max_retries: int = 3


class CommunicationProtocol:
    """
    Base class for communication protocols.
    """
    
    def __init__(self, name: str, version: str = "1.0"):
        """
        Initialize the communication protocol.
        
        Args:
            name: Protocol name
            version: Protocol version
        """
        self.name = name
        self.version = version
        self.supported_message_types = []
    
    def encode_message(self, message: ProtocolMessage) -> bytes:
        """
        Encode a protocol message.
        
        Args:
            message: Protocol message to encode
            
        Returns:
            Encoded message as bytes
        """
        raise NotImplementedError("Subclasses must implement encode_message")
    
    def decode_message(self, data: bytes) -> ProtocolMessage:
        """
        Decode a protocol message.
        
        Args:
            data: Raw message data
            
        Returns:
            Decoded protocol message
        """
        raise NotImplementedError("Subclasses must implement decode_message")
    
    def validate_message(self, message: ProtocolMessage) -> bool:
        """
        Validate a protocol message.
        
        Args:
            message: Protocol message to validate
            
        Returns:
            True if valid, False otherwise
        """
        raise NotImplementedError("Subclasses must implement validate_message")


class JSONProtocol(CommunicationProtocol):
    """
    JSON-based communication protocol.
    """
    
    def __init__(self):
        """Initialize JSON protocol."""
        super().__init__("JSON", "1.0")
        self.supported_message_types = [msg_type.value for msg_type in MessageType]
    
    def encode_message(self, message: ProtocolMessage) -> bytes:
        """
        Encode a protocol message to JSON.
        
        Args:
            message: Protocol message to encode
            
        Returns:
            JSON-encoded message as bytes
        """
        import json
        
        message_dict = {
            'message_id': message.message_id,
            'message_type': message.message_type.value,
            'sender': message.sender,
            'recipient': message.recipient,
            'timestamp': message.timestamp.isoformat(),
            'payload': message.payload,
            'priority': message.priority,
            'retry_count': message.retry_count,
            'max_retries': message.max_retries
        }
        
        return json.dumps(message_dict).encode('utf-8')
    
    def decode_message(self, data: bytes) -> ProtocolMessage:
        """
        Decode a JSON protocol message.
        
        Args:
            data: JSON-encoded message data
            
        Returns:
            Decoded protocol message
        """
        import json
        
        message_dict = json.loads(data.decode('utf-8'))
        
        return ProtocolMessage(
            message_id=message_dict['message_id'],
            message_type=MessageType(message_dict['message_type']),
            sender=message_dict['sender'],
            recipient=message_dict['recipient'],
            timestamp=datetime.fromisoformat(message_dict['timestamp']),
            payload=message_dict['payload'],
            priority=message_dict.get('priority', 1),
            retry_count=message_dict.get('retry_count', 0),
            max_retries=message_dict.get('max_retries', 3)
        )
    
    def validate_message(self, message: ProtocolMessage) -> bool:
        """
        Validate a JSON protocol message.
        
        Args:
            message: Protocol message to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        if not message.message_id or not message.sender or not message.recipient:
            return False
        
        # Check message type
        if message.message_type.value not in self.supported_message_types:
            return False
        
        # Check timestamp
        if not isinstance(message.timestamp, datetime):
            return False
        
        # Check payload
        if not isinstance(message.payload, dict):
            return False
        
        return True


class ProtocolFactory:
    """
    Factory for creating communication protocols.
    """
    
    _protocols = {
        'json': JSONProtocol
    }
    
    @classmethod
    def create_protocol(cls, protocol_type: str) -> CommunicationProtocol:
        """
        Create a communication protocol instance.
        
        Args:
            protocol_type: Type of protocol to create
            
        Returns:
            Protocol instance
        """
        if protocol_type not in cls._protocols:
            raise ValueError(f"Unsupported protocol type: {protocol_type}")
        
        return cls._protocols[protocol_type]()
    
    @classmethod
    def register_protocol(cls, protocol_type: str, protocol_class: type) -> None:
        """
        Register a new protocol type.
        
        Args:
            protocol_type: Protocol type name
            protocol_class: Protocol class
        """
        cls._protocols[protocol_type] = protocol_class
    
    @classmethod
    def get_supported_protocols(cls) -> List[str]:
        """
        Get list of supported protocol types.
        
        Returns:
            List of supported protocol types
        """
        return list(cls._protocols.keys())














