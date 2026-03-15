"""WebSocket connection management for real-time job updates.

Manages client connections and broadcasts job status updates to all connected clients.
"""
import logging
from typing import Set, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger('EMyBrain.WebSocket')


class JobUpdateManager:
    """Manages WebSocket connections and broadcasts job updates to connected clients."""

    def __init__(self):
        """Initialize the JobUpdateManager with empty connection set."""
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """
        Accept a WebSocket connection and send connection confirmation.

        Args:
            websocket: WebSocket connection to accept
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f'Client connected. Total connections: {len(self.active_connections)}')

        # Send connection confirmation
        await websocket.send_json({"status": "connected"})

    async def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection from active connections.

        Args:
            websocket: WebSocket connection to disconnect
        """
        self.active_connections.discard(websocket)
        logger.info(f'Client disconnected. Total connections: {len(self.active_connections)}')

    async def broadcast_job_update(self, job_id: str, update: Dict[str, Any]):
        """
        Broadcast a job update to all connected clients.

        Removes any disconnected clients from active connections.

        Args:
            job_id: ID of the job being updated
            update: Update data to broadcast (should contain status, message, etc.)
        """
        message = {
            "type": "job_update",
            "job_id": job_id,
            **update
        }

        # Send to all connected clients, remove disconnected ones
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f'Error sending to client: {e}')
                disconnected.append(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            self.active_connections.discard(ws)

    async def broadcast_job_state(self, job_id: str, state: Dict[str, Any]):
        """
        Broadcast complete job state to all connected clients.

        Includes full workflow state (status, results, messages, error).

        Args:
            job_id: ID of the job
            state: Complete state dict with status, results, messages, error fields
        """
        message = {
            "type": "job_state",
            "job_id": job_id,
            **state
        }

        # Send to all connected clients, remove disconnected ones
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f'Error sending state to client: {e}')
                disconnected.append(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            self.active_connections.discard(ws)


# Global instance for use in service
job_update_manager = JobUpdateManager()
