import httpx
import os
from typing import Optional


BASE_URL = "https://api.cursor.com/v0"


class CursorAgentsClient:
    """Wrapper for Cursor Cloud Agents API with async httpx."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CURSOR_AGENTS_API_KEY")
        if not self.api_key:
            raise ValueError("CURSOR_AGENTS_API_KEY environment variable not set")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def launch(
        self,
        task: str,
        repo: Optional[str] = None,
        model: Optional[str] = None
    ) -> dict:
        """Launch a Cursor agent with a coding task.

        Args:
            task: The coding instruction
            repo: GitHub repo in 'owner/name' format (optional)
            model: Model name like 'claude-sonnet', 'gpt-4o', 'gemini-2-pro' (optional)

        Returns:
            dict with agent_id, status, created_at
        """
        payload = {"task": task}
        if repo:
            owner, name = repo.split("/")
            payload["repository"] = {"owner": owner, "repo": name}
        if model:
            payload["model"] = model

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/agents",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def get_status(self, agent_id: str) -> dict:
        """Get status and results of a running or completed agent.

        Args:
            agent_id: Agent ID from launch response

        Returns:
            dict with agent_id, status, result_text, artifacts[], and optional error
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/agents/{agent_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def list(self, limit: int = 10) -> list:
        """List recent agents (running, completed, errored).

        Args:
            limit: Max results to return (default 10)

        Returns:
            list of agent dicts with agent_id, status, task_preview, created_at
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/agents",
                params={"limit": limit},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def send_followup(self, agent_id: str, message: str) -> dict:
        """Send a follow-up instruction to a running or completed agent.

        Args:
            agent_id: Agent ID
            message: Follow-up prompt

        Returns:
            dict with status and response
        """
        payload = {"message": message}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/agents/{agent_id}/followup",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def download_artifact(self, artifact_url: str) -> dict:
        """Fetch generated code or file content from a completed agent.

        Args:
            artifact_url: URL from get_status artifacts list

        Returns:
            dict with content, content_type, and optional filename
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                artifact_url,
                headers=self.headers
            )
            response.raise_for_status()
            return {
                "content": response.text,
                "content_type": response.headers.get("content-type", "text/plain"),
                "filename": artifact_url.split("/")[-1] if "/" in artifact_url else None
            }
