"""
Message Bus System

This module provides a centralized message bus for inter-agent communication.
"""

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
from dataclasses import asdict

from loguru import logger

from agents.base_agent import Message, TaskPriority


class MessageBus:
    """
    Centralized message bus for inter-agent communication.
    
    This class manages message routing, delivery, and subscription handling.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the message bus.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.subscribers: Dict[str, Set[Callable]] = {}
        self.message_history: List[Message] = []
        self.max_history = self.config.get('max_history', 1000)
        self.delivery_timeout = self.config.get('delivery_timeout', 30)
        self.logger = logger.bind(component="MessageBus")
        
        # Performance metrics
        self.metrics = {
            'messages_sent': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'active_subscribers': 0
        }
        
        self.logger.info("Message bus initialized")
    
    async def subscribe(self, topic: str, callback: Callable) -> None:
        """
        Subscribe to a message topic.
        
        Args:
            topic: Topic to subscribe to
            callback: Callback function to handle messages
        """
        if topic not in self.subscribers:
            self.subscribers[topic] = set()
        
        self.subscribers[topic].add(callback)
        self.metrics['active_subscribers'] = sum(len(subs) for subs in self.subscribers.values())
        
        self.logger.debug(f"Subscriber added to topic: {topic}")
    
    async def unsubscribe(self, topic: str, callback: Callable) -> None:
        """
        Unsubscribe from a message topic.
        
        Args:
            topic: Topic to unsubscribe from
            callback: Callback function to remove
        """
        if topic in self.subscribers:
            self.subscribers[topic].discard(callback)
            if not self.subscribers[topic]:
                del self.subscribers[topic]
            
            self.metrics['active_subscribers'] = sum(len(subs) for subs in self.subscribers.values())
            self.logger.debug(f"Subscriber removed from topic: {topic}")
    
    async def publish(self, message: Message) -> bool:
        """
        Publish a message to all subscribers of the topic.
        
        Args:
            message: Message to publish
            
        Returns:
            True if message was delivered successfully
        """
        try:
            self.metrics['messages_sent'] += 1
            
            # Add to history
            self.message_history.append(message)
            if len(self.message_history) > self.max_history:
                self.message_history.pop(0)
            
            # Get topic from message type
            topic = message.message_type
            
            if topic in self.subscribers:
                delivery_tasks = []
                
                # Create delivery tasks for all subscribers
                for callback in self.subscribers[topic]:
                    task = asyncio.create_task(self._deliver_message(callback, message))
                    delivery_tasks.append(task)
                
                # Wait for all deliveries to complete
                if delivery_tasks:
                    results = await asyncio.wait_for(
                        asyncio.gather(*delivery_tasks, return_exceptions=True),
                        timeout=self.delivery_timeout
                    )
                    
                    # Count successful deliveries
                    successful_deliveries = sum(1 for result in results if not isinstance(result, Exception))
                    self.metrics['messages_delivered'] += successful_deliveries
                    self.metrics['messages_failed'] += len(results) - successful_deliveries
                    
                    self.logger.debug(f"Message delivered to {successful_deliveries}/{len(results)} subscribers")
                    return successful_deliveries > 0
                else:
                    self.logger.warning(f"No subscribers for topic: {topic}")
                    return False
            else:
                self.logger.warning(f"No subscribers for topic: {topic}")
                return False
                
        except Exception as e:
            self.metrics['messages_failed'] += 1
            self.logger.error(f"Failed to publish message: {str(e)}")
            return False
    
    async def _deliver_message(self, callback: Callable, message: Message) -> Any:
        """
        Deliver a message to a specific callback.
        
        Args:
            callback: Callback function
            message: Message to deliver
            
        Returns:
            Result from callback
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                return await callback(message)
            else:
                return callback(message)
        except Exception as e:
            self.logger.error(f"Error in message callback: {str(e)}")
            raise
    
    async def send_direct(self, recipient: str, message: Message) -> bool:
        """
        Send a message directly to a specific recipient.
        
        Args:
            recipient: Recipient agent name
            message: Message to send
            
        Returns:
            True if message was sent successfully
        """
        try:
            # Create a direct message topic
            topic = f"direct:{recipient}"
            
            if topic in self.subscribers:
                delivery_tasks = []
                for callback in self.subscribers[topic]:
                    task = asyncio.create_task(self._deliver_message(callback, message))
                    delivery_tasks.append(task)
                
                if delivery_tasks:
                    results = await asyncio.wait_for(
                        asyncio.gather(*delivery_tasks, return_exceptions=True),
                        timeout=self.delivery_timeout
                    )
                    
                    successful_deliveries = sum(1 for result in results if not isinstance(result, Exception))
                    self.metrics['messages_delivered'] += successful_deliveries
                    
                    self.logger.debug(f"Direct message delivered to {recipient}")
                    return successful_deliveries > 0
                else:
                    self.logger.warning(f"No subscribers for direct message to: {recipient}")
                    return False
            else:
                self.logger.warning(f"No subscribers for direct message to: {recipient}")
                return False
                
        except Exception as e:
            self.metrics['messages_failed'] += 1
            self.logger.error(f"Failed to send direct message: {str(e)}")
            return False
    
    def get_message_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent message history.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of message dictionaries
        """
        recent_messages = self.message_history[-limit:]
        return [asdict(msg) for msg in recent_messages]
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get message bus metrics.
        
        Returns:
            Metrics dictionary
        """
        return {
            'metrics': self.metrics.copy(),
            'topics': list(self.subscribers.keys()),
            'total_subscribers': self.metrics['active_subscribers'],
            'message_history_size': len(self.message_history)
        }
    
    async def broadcast(self, message: Message) -> int:
        """
        Broadcast a message to all subscribers of all topics.
        
        Args:
            message: Message to broadcast
            
        Returns:
            Number of successful deliveries
        """
        all_subscribers = set()
        for subscribers in self.subscribers.values():
            all_subscribers.update(subscribers)
        
        if not all_subscribers:
            return 0
        
        delivery_tasks = []
        for callback in all_subscribers:
            task = asyncio.create_task(self._deliver_message(callback, message))
            delivery_tasks.append(task)
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*delivery_tasks, return_exceptions=True),
                timeout=self.delivery_timeout
            )
            
            successful_deliveries = sum(1 for result in results if not isinstance(result, Exception))
            self.metrics['messages_delivered'] += successful_deliveries
            
            self.logger.info(f"Broadcast delivered to {successful_deliveries}/{len(results)} subscribers")
            return successful_deliveries
            
        except Exception as e:
            self.logger.error(f"Broadcast failed: {str(e)}")
            return 0
    
    async def shutdown(self) -> None:
        """Shutdown the message bus gracefully."""
        self.logger.info("Message bus shutting down")
        
        # Clear all subscribers
        self.subscribers.clear()
        self.metrics['active_subscribers'] = 0
        
        # Clear message history
        self.message_history.clear()
        
        self.logger.info("Message bus shutdown complete")
