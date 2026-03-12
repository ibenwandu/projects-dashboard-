"""
Gradio Chat Interface for Emy Phase 1a.

Provides a web-based chat UI for triggering Emy workflows with:
- Natural language command parsing (Research, Analyze, Generate)
- Real-time workflow status monitoring (polling every 5s)
- Chat history management (in-memory)
- System status display
- Mobile-friendly design
"""

import logging
import json
import re
import requests
import gradio as gr
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class WorkflowType(str, Enum):
    """Supported workflow types."""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    GENERATION = "generation"


@dataclass
class ChatMessage:
    """Represents a single chat message."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    workflow_id: Optional[str] = None
    status: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return asdict(self)


@dataclass
class CommandParseResult:
    """Result of parsing a command."""

    workflow_type: WorkflowType
    topic: str
    duration_minutes: int
    agents: List[str]
    original_command: str


# ============================================================================
# Command Parser
# ============================================================================

class CommandParser:
    """Parse natural language commands into structured workflows."""

    PATTERNS = {
        "research": r"(?:research|explore|investigate)\s+(.+?)(?:\s+for\s+(.+?))?$",
        "analysis": r"(?:analyze|analyse|examine)\s+(.+?)(?:\s+for\s+(.+?))?$",
        "generation": r"(?:generate|create|write)\s+(.+?)(?:\s+for\s+(.+?))?$",
    }

    AGENT_MAP = {
        WorkflowType.RESEARCH: ["research"],
        WorkflowType.ANALYSIS: ["analysis"],
        WorkflowType.GENERATION: ["generation"],
    }

    @staticmethod
    def _parse_duration(duration_str: Optional[str]) -> int:
        """
        Parse duration string to minutes.

        Supports: "2 hours", "30 minutes", "1 hour", etc.
        Defaults to 30 minutes if not specified.
        """
        if not duration_str:
            return 30

        duration_str = duration_str.lower().strip()

        # Extract numbers
        match = re.search(r'(\d+(?:\.\d+)?)', duration_str)
        if not match:
            return 30

        value = float(match.group(1))

        # Convert to minutes
        if "hour" in duration_str:
            return int(value * 60)
        elif "minute" in duration_str:
            return int(value)
        elif "second" in duration_str:
            return int(max(1, value / 60))
        else:
            # Default to minutes
            return int(value)

    def parse(self, command: str) -> Optional[Dict[str, Any]]:
        """
        Parse a natural language command.

        Args:
            command: User's text command

        Returns:
            Dict with parsed workflow details, or None if invalid
        """
        command_lower = command.lower().strip()

        # Try each pattern
        for workflow_type_str, pattern in self.PATTERNS.items():
            match = re.match(pattern, command_lower, re.IGNORECASE)
            if match:
                topic = match.group(1).strip()
                duration_str = match.group(2) if len(match.groups()) > 1 else None

                workflow_type = WorkflowType(workflow_type_str)
                duration_minutes = self._parse_duration(duration_str)
                agents = self.AGENT_MAP[workflow_type]

                return {
                    "workflow_type": workflow_type_str,
                    "topic": topic,
                    "duration_minutes": duration_minutes,
                    "agents": agents,
                    "original_command": command
                }

        # Invalid command
        return None


# ============================================================================
# API Client
# ============================================================================

class APIClient:
    """HTTP client for communicating with Emy gateway API."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 10):
        """
        Initialize API client.

        Args:
            base_url: Gateway API base URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def execute_workflow(
        self,
        workflow_type: str,
        agents: List[str],
        input: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a workflow via the gateway API.

        Args:
            workflow_type: Type of workflow
            agents: List of agent names
            input: Input data for workflow

        Returns:
            Workflow response dict, or None on error
        """
        try:
            url = f"{self.base_url}/workflows/execute"
            payload = {
                "workflow_type": workflow_type,
                "agents": agents,
                "input": input
            }

            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    f"[API] Workflow execution failed: {response.status_code} - {response.text}"
                )
                return None

        except requests.RequestException as e:
            logger.error(f"[API] Request failed: {e}")
            return None

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a workflow.

        Args:
            workflow_id: Workflow ID to check

        Returns:
            Workflow details dict, or None on error
        """
        try:
            url = f"{self.base_url}/workflows/{workflow_id}"
            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    f"[API] Failed to get workflow: {response.status_code}"
                )
                return None

        except requests.RequestException as e:
            logger.error(f"[API] Request failed: {e}")
            return None

    def health_check(self) -> Optional[Dict[str, Any]]:
        """
        Check API health.

        Returns:
            Health check response, or None on error
        """
        try:
            url = f"{self.base_url}/health"
            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"[API] Health check failed: {response.status_code}")
                return None

        except requests.RequestException as e:
            logger.error(f"[API] Health check failed: {e}")
            return None


# ============================================================================
# Chat Interface
# ============================================================================

class ChatInterface:
    """Gradio chat interface for Emy workflows."""

    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """
        Initialize chat interface.

        Args:
            api_base_url: Gateway API base URL
        """
        self.api_client = APIClient(base_url=api_base_url)
        self.parser = CommandParser()
        self.chat_history: List[ChatMessage] = []
        self.active_workflows: Dict[str, Dict[str, Any]] = {}

    def add_message(self, message: ChatMessage) -> None:
        """Add a message to chat history."""
        self.chat_history.append(message)

    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Get chat history as list of dicts."""
        return [msg.to_dict() for msg in self.chat_history]

    def process_message(self, user_input: str) -> Dict[str, Any]:
        """
        Process a user message.

        Args:
            user_input: User's text input

        Returns:
            Response dict with workflow info or error
        """
        # Add user message to history
        user_msg = ChatMessage(role="user", content=user_input)
        self.add_message(user_msg)

        # Parse command
        parsed = self.parser.parse(user_input)

        if not parsed:
            error_msg = (
                "Invalid command format. Please use one of:\n"
                "- Research {topic} for {duration}\n"
                "- Analyze {topic} for {duration}\n"
                "- Generate {topic} for {duration}\n\n"
                "Duration is optional and defaults to 30 minutes."
            )
            assistant_msg = ChatMessage(
                role="assistant",
                content=error_msg
            )
            self.add_message(assistant_msg)
            return {"error": "Invalid command", "message": error_msg}

        # Execute workflow
        workflow_input = {
            "topic": parsed["topic"],
            "duration_minutes": parsed["duration_minutes"]
        }

        result = self.api_client.execute_workflow(
            workflow_type=parsed["workflow_type"],
            agents=parsed["agents"],
            input=workflow_input
        )

        if not result:
            error_msg = (
                "Failed to execute workflow. "
                "Please check that the API server is running."
            )
            assistant_msg = ChatMessage(
                role="assistant",
                content=error_msg
            )
            self.add_message(assistant_msg)
            return {"error": "API error", "message": error_msg}

        # Store active workflow
        workflow_id = result.get("workflow_id")
        self.active_workflows[workflow_id] = result

        # Create response
        response_text = (
            f"Starting {parsed['workflow_type']} workflow...\n"
            f"Workflow ID: {workflow_id}\n"
            f"Topic: {parsed['topic']}\n"
            f"Duration: {parsed['duration_minutes']} minutes\n"
            f"Status: {result.get('status', 'unknown')}"
        )

        assistant_msg = ChatMessage(
            role="assistant",
            content=response_text,
            workflow_id=workflow_id,
            status=result.get("status")
        )
        self.add_message(assistant_msg)

        return {
            "success": True,
            "workflow_id": workflow_id,
            "status": result.get("status"),
            "message": response_text
        }

    def get_command_suggestions(self) -> List[str]:
        """Get list of command suggestions for autocomplete."""
        return [
            "Research {topic} for {duration}",
            "Research {topic}",
            "Analyze {topic} for {duration}",
            "Analyze {topic}",
            "Generate {topic} for {duration}",
            "Generate {topic}",
        ]

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status."""
        health = self.api_client.health_check()

        if health:
            return {
                "api_status": "Connected",
                "database_status": health.get("database", "unknown"),
                "last_updated": datetime.now().isoformat()
            }
        else:
            return {
                "api_status": "Disconnected",
                "database_status": "unknown",
                "last_updated": datetime.now().isoformat()
            }

    def format_chat_for_gradio(self) -> List[Tuple[str, str]]:
        """
        Format chat history for Gradio's chatbot component.

        Returns Gradio-compatible format: [(user_msg, assistant_msg), ...]
        """
        pairs = []
        current_user = None

        for msg in self.chat_history:
            if msg.role == "user":
                current_user = msg.content
            elif msg.role == "assistant" and current_user:
                pairs.append((current_user, msg.content))
                current_user = None

        return pairs


# ============================================================================
# Gradio UI Builder
# ============================================================================

def create_gradio_interface(api_base_url: str = "http://localhost:8000") -> gr.Blocks:
    """
    Create Gradio interface for Emy chat.

    Args:
        api_base_url: Gateway API base URL

    Returns:
        Gradio Blocks interface
    """
    interface = ChatInterface(api_base_url=api_base_url)

    with gr.Blocks(
        title="Emy AI Assistant",
        theme=gr.themes.Soft(),
        css="""
        #chat-container {
            max-width: 900px;
            margin: 0 auto;
        }
        .status-badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-healthy {
            background-color: #10b981;
            color: white;
        }
        .status-error {
            background-color: #ef4444;
            color: white;
        }
        """
    ) as ui:
        gr.Markdown("# Emy AI Assistant")
        gr.Markdown("Execute AI workflows with natural language commands")

        with gr.Row():
            with gr.Column(scale=3):
                # Chat interface
                chat_history = gr.Chatbot(
                    label="Chat History",
                    show_label=True,
                    height=500
                )

            with gr.Column(scale=1):
                # Sidebar: System status
                with gr.Group(label="System Status"):
                    status_text = gr.Textbox(
                        label="API Status",
                        value="Checking...",
                        interactive=False
                    )

                # Workflow suggestions
                with gr.Group(label="Command Examples"):
                    suggestions = gr.Textbox(
                        label="Suggested Commands",
                        value=(
                            "• Research [topic] for [duration]\n"
                            "• Analyze [topic] for [duration]\n"
                            "• Generate [topic] for [duration]\n\n"
                            "Duration defaults to 30 minutes"
                        ),
                        interactive=False,
                        lines=6
                    )

                # Active workflows info
                workflows_text = gr.Textbox(
                    label="Active Workflows",
                    value="None",
                    interactive=False,
                    lines=6
                )

        # Input row
        with gr.Row():
            with gr.Column(scale=4):
                user_input = gr.Textbox(
                    label="Your Command",
                    placeholder="e.g., Research AI trends for 2 hours",
                    lines=2
                )

            with gr.Column(scale=1):
                submit_btn = gr.Button("Send", variant="primary", scale=1)

        # Status updates
        last_update = gr.Textbox(
            label="Last Updated",
            value=datetime.now().isoformat(),
            interactive=False,
            visible=False
        )

        # ====================================================================
        # Event Handlers
        # ====================================================================

        def update_status():
            """Update system status."""
            status = interface.get_system_status()
            api_status = status["api_status"]
            db_status = status.get("database_status", "unknown")

            status_display = f"API: {api_status}\nDB: {db_status}"
            return status_display

        def send_message(user_text):
            """Handle user message submission."""
            if not user_text.strip():
                return interface.format_chat_for_gradio(), ""

            # Process message
            result = interface.process_message(user_text)

            # Return updated chat and clear input
            return interface.format_chat_for_gradio(), ""

        def update_workflows():
            """Update active workflows display."""
            if not interface.active_workflows:
                return "None"

            workflows_list = []
            for wf_id, wf_info in interface.active_workflows.items():
                workflows_list.append(
                    f"• {wf_id}: {wf_info.get('status', 'unknown')}"
                )

            return "\n".join(workflows_list)

        # Connect button to handler
        submit_btn.click(
            send_message,
            inputs=[user_input],
            outputs=[chat_history, user_input]
        )

        # Allow Enter key to submit
        user_input.submit(
            send_message,
            inputs=[user_input],
            outputs=[chat_history, user_input]
        )

        # Load and update status on page load
        ui.load(
            update_status,
            outputs=[status_text]
        )

        # Periodically refresh status (every 5 seconds)
        ui.load(
            update_workflows,
            outputs=[workflows_text],
            every=5
        )

    return ui


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Emy Gradio Chat Interface")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to bind to (default: 7860)"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Gateway API URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Share the interface publicly"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger.info(
        f"[CHAT] Starting Emy Chat Interface on {args.host}:{args.port}"
    )
    logger.info(f"[CHAT] Gateway API: {args.api_url}")

    # Create and launch interface
    ui = create_gradio_interface(api_base_url=args.api_url)
    ui.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        show_error=True
    )
