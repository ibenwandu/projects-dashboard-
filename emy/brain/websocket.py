"""WebSocket connection management for real-time job updates.

Manages client connections and broadcasts job status updates to all connected clients.
"""
import asyncio
import logging
from typing import List, Dict, Any
from fastapi import WebSocket

from emy.brain.config import MAX_WS_CONNECTIONS

logger = logging.getLogger('EMyBrain.WebSocket')


class JobUpdateManager:
    """Manages WebSocket connections and broadcasts job updates to connected clients."""

    def __init__(self):
        """Initialize the JobUpdateManager with empty connection list and lock."""
        self.active_connections: List[WebSocket] = []
        self.connections_lock = asyncio.Lock()
        self.sequence_id = 0

    async def connect(self, websocket: WebSocket):
        """
        Accept a WebSocket connection and send connection confirmation.

        Args:
            websocket: WebSocket connection to accept

        Raises:
            ConnectionError: If connection limit is reached or acceptance fails
        """
        # Check connection limit before accepting
        async with self.connections_lock:
            if len(self.active_connections) >= MAX_WS_CONNECTIONS:
                await websocket.close(code=1008, reason="Connection limit reached")
                raise ConnectionError(f"WebSocket connection limit ({MAX_WS_CONNECTIONS}) reached")

        # Try to accept the connection
        try:
            await websocket.accept()
        except RuntimeError as e:
            logger.warning(f"Failed to accept WebSocket: {e}")
            raise

        # Add to active connections (thread-safe)
        async with self.connections_lock:
            self.active_connections.append(websocket)
        logger.info(f'Client connected. Total connections: {len(self.active_connections)}')

        # Send connection confirmation
        await websocket.send_json({"status": "connected"})

    async def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection from active connections (thread-safe).

        Args:
            websocket: WebSocket connection to disconnect
        """
        async with self.connections_lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f'Client disconnected. Total connections: {len(self.active_connections)}')

    async def broadcast_job_update(self, job_id: str, update: Dict[str, Any]):
        """
        Broadcast a job update to all connected clients (thread-safe).

        Removes any disconnected clients from active connections.

        Args:
            job_id: ID of the job being updated
            update: Update data to broadcast (should contain status, message, etc.)
        """
        message = {
            "type": "job_update",
            "job_id": job_id,
            "sequence_id": self.sequence_id,
            **update
        }
        self.sequence_id += 1

        # Create snapshot of connections (avoid iteration during modification)
        async with self.connections_lock:
            connections_copy = self.active_connections.copy()

        # Send to all connected clients, collect disconnected ones
        disconnected = []
        for websocket in connections_copy:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f'Error sending to client: {e}')
                disconnected.append(websocket)

        # Clean up disconnected clients (thread-safe)
        if disconnected:
            async with self.connections_lock:
                for ws in disconnected:
                    if ws in self.active_connections:
                        self.active_connections.remove(ws)

    async def broadcast_job_state(self, job_id: str, state: Dict[str, Any]):
        """
        Broadcast complete job state to all connected clients (thread-safe).

        Includes full workflow state (status, results, messages, error).

        Args:
            job_id: ID of the job
            state: Complete state dict with status, results, messages, error fields
        """
        message = {
            "type": "job_state",
            "job_id": job_id,
            "sequence_id": self.sequence_id,
            **state
        }
        self.sequence_id += 1

        # Create snapshot of connections (avoid iteration during modification)
        async with self.connections_lock:
            connections_copy = self.active_connections.copy()

        # Send to all connected clients, collect disconnected ones
        disconnected = []
        for websocket in connections_copy:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f'Error sending state to client: {e}')
                disconnected.append(websocket)

        # Clean up disconnected clients (thread-safe)
        if disconnected:
            async with self.connections_lock:
                for ws in disconnected:
                    if ws in self.active_connections:
                        self.active_connections.remove(ws)


# Global instance for use in service
job_update_manager = JobUpdateManager()
