"""
Gemini Agent - AI-powered research, analysis, and code execution

This agent provides Gemini-powered capabilities including:
- General text queries
- Web search and research
- Document analysis
- Image analysis
- Structured data extraction
- Code execution
- Deep research tasks
"""

import json
from typing import Any, Dict, Optional
from datetime import datetime

from loguru import logger

from agents.base_agent import BaseAgent, Task, Message
from utils.gemini_tool import GeminiTool


class GeminiAgent(BaseAgent):
    """
    Agent that provides Gemini LLM capabilities including research,
    analysis, document processing, and code execution.
    """

    def __init__(self, name: str = "Gemini Agent", config: Dict[str, Any] = None):
        """
        Initialize GeminiAgent.

        Args:
            name: Agent name
            config: Configuration dictionary
        """
        super().__init__(name=name, agent_type="gemini", config=config or {})

        # Initialize Gemini tool
        try:
            self.gemini = GeminiTool()
            self.logger.info("GeminiTool initialized successfully")
        except ValueError as e:
            self.logger.error(f"Failed to initialize GeminiTool: {str(e)}")
            self.gemini = None

    async def process_task(self, task: Task) -> Any:
        """
        Process a task using Gemini capabilities.

        Supported task types:
        - query: General LLM queries
        - search: Web search and synthesis
        - document_analysis: Analyze documents
        - image_analysis: Analyze images
        - structured: Generate structured JSON output
        - extract: Extract entities, facts, keywords
        - code_execution: Execute Python code
        - deep_research: Comprehensive research tasks

        Args:
            task: Task to process

        Returns:
            Task result
        """
        if not self.gemini:
            raise RuntimeError("GeminiTool not initialized")

        task_type = task.data.get("task_type", "query")
        self.logger.info(
            f"Processing {task_type} task: {task.name} (ID: {task.id})"
        )

        try:
            if task_type == "query":
                result = await self._handle_query(task)
            elif task_type == "search":
                result = await self._handle_search(task)
            elif task_type == "document_analysis":
                result = await self._handle_document_analysis(task)
            elif task_type == "image_analysis":
                result = await self._handle_image_analysis(task)
            elif task_type == "structured":
                result = await self._handle_structured(task)
            elif task_type == "extract":
                result = await self._handle_extract(task)
            elif task_type == "code_execution":
                result = await self._handle_code_execution(task)
            elif task_type == "deep_research":
                result = await self._handle_deep_research(task)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            return result

        except Exception as e:
            self.logger.error(f"Task {task.id} failed: {str(e)}")
            raise

    async def _handle_query(self, task: Task) -> Dict[str, Any]:
        """Handle general LLM query task."""
        prompt = task.data.get("prompt", "")
        model = task.data.get("model", "flash")
        thinking = task.data.get("thinking", False)

        if not prompt:
            raise ValueError("Query task requires 'prompt' field")

        response = self.gemini.query(prompt=prompt, model=model, thinking=thinking)

        return {"task_type": "query", "response": response, "timestamp": datetime.now()}

    async def _handle_search(self, task: Task) -> Dict[str, Any]:
        """Handle web search task."""
        query = task.data.get("query", "")

        if not query:
            raise ValueError("Search task requires 'query' field")

        response = self.gemini.search(query=query)

        return {
            "task_type": "search",
            "query": query,
            "response": response,
            "timestamp": datetime.now(),
        }

    async def _handle_document_analysis(self, task: Task) -> Dict[str, Any]:
        """Handle document analysis task."""
        file_path = task.data.get("file_path", "")
        question = task.data.get("question", "Analyze this document comprehensively")

        if not file_path:
            raise ValueError("Document analysis task requires 'file_path' field")

        response = self.gemini.analyze_document(file_path=file_path, question=question)

        return {
            "task_type": "document_analysis",
            "file_path": file_path,
            "response": response,
            "timestamp": datetime.now(),
        }

    async def _handle_image_analysis(self, task: Task) -> Dict[str, Any]:
        """Handle image analysis task."""
        image_path = task.data.get("image_path", "")
        question = task.data.get(
            "question", "Analyze this image in detail and detect objects"
        )

        if not image_path:
            raise ValueError("Image analysis task requires 'image_path' field")

        response = self.gemini.analyze_image(image_path=image_path, question=question)

        return {
            "task_type": "image_analysis",
            "image_path": image_path,
            "response": response,
            "timestamp": datetime.now(),
        }

    async def _handle_structured(self, task: Task) -> Dict[str, Any]:
        """Handle structured JSON generation task."""
        prompt = task.data.get("prompt", "")
        schema = task.data.get("schema", {})

        if not prompt:
            raise ValueError("Structured task requires 'prompt' field")

        if not schema:
            raise ValueError("Structured task requires 'schema' field")

        response = self.gemini.structured(prompt=prompt, schema=schema)

        return {
            "task_type": "structured",
            "response": response,
            "timestamp": datetime.now(),
        }

    async def _handle_extract(self, task: Task) -> Dict[str, Any]:
        """Handle data extraction task."""
        text = task.data.get("text", "")
        extract_type = task.data.get("extract_type", "entities")
        custom_fields = task.data.get("custom_fields", None)

        if not text:
            raise ValueError("Extract task requires 'text' field")

        response = self.gemini.extract(
            text=text, extract_type=extract_type, custom_fields=custom_fields
        )

        return {
            "task_type": "extract",
            "extract_type": extract_type,
            "response": response,
            "timestamp": datetime.now(),
        }

    async def _handle_code_execution(self, task: Task) -> Dict[str, Any]:
        """Handle code execution task."""
        prompt = task.data.get("prompt", "")
        data = task.data.get("data", None)

        if not prompt:
            raise ValueError("Code execution task requires 'prompt' field")

        response = self.gemini.run_code(prompt=prompt, data=data)

        return {
            "task_type": "code_execution",
            "response": response,
            "timestamp": datetime.now(),
        }

    async def _handle_deep_research(self, task: Task) -> Dict[str, Any]:
        """Handle deep research task."""
        query = task.data.get("query", "")

        if not query:
            raise ValueError("Deep research task requires 'query' field")

        response = self.gemini.deep_research(query=query)

        return {
            "task_type": "deep_research",
            "query": query,
            "response": response,
            "timestamp": datetime.now(),
        }

    async def handle_message(self, message: Message) -> Any:
        """
        Handle incoming inter-agent messages.

        Args:
            message: Message from another agent

        Returns:
            Response or acknowledgment
        """
        self.logger.info(
            f"Received message from {message.sender}: {message.message_type}"
        )

        # Update metrics
        self.metrics["messages_received"] += 1

        # Simple message handling for inter-agent communication
        # Can be extended based on message_type
        if message.message_type == "query_gemini":
            # Another agent is asking us to perform a Gemini task
            task_data = message.content or {}
            try:
                # Create a task from the message
                task = Task(
                    name=f"Gemini task from {message.sender}",
                    description="Inter-agent request",
                    data=task_data,
                )

                # Process the task
                result = await self.process_task(task)

                # Return result as response
                response_message = Message(
                    sender=self.name,
                    recipient=message.sender,
                    message_type="gemini_result",
                    content=result,
                )

                self.metrics["messages_sent"] += 1
                return response_message

            except Exception as e:
                self.logger.error(f"Failed to process inter-agent request: {str(e)}")
                return Message(
                    sender=self.name,
                    recipient=message.sender,
                    message_type="error",
                    content={"error": str(e)},
                )
        else:
            # For unknown message types, acknowledge receipt
            return {
                "status": "acknowledged",
                "sender": self.name,
                "message_id": message.id,
            }
