"""RouterAgent - Claude-based request classifier for LangGraph.

Classifies incoming user requests into workflow types (job_search, trading, etc.)
and determines which domain agent should handle the request.

This is a LangGraph node that returns state updates only (not a full state object).
"""

import json
import logging
from anthropic import Anthropic, APIError, AuthenticationError, APIConnectionError

logger = logging.getLogger("RouterAgent")

ROUTE_PROMPT = """You are Emy's routing agent. Classify this request into exactly one workflow type.

Request: {request}

Respond ONLY with valid JSON (no markdown, no code blocks, just raw JSON):
{{"workflow_type": "<type>", "confidence": <0.0-1.0>, "rationale": "<brief>"}}

Valid types: job_search, trading, knowledge_query, project_monitor, research, unknown

Examples:
- "Find jobs in Toronto" → {{"workflow_type": "job_search", "confidence": 0.95, "rationale": "Job search request with location"}}
- "What's my portfolio performance?" → {{"workflow_type": "trading", "confidence": 0.9, "rationale": "Trading portfolio query"}}
- "What is LangGraph?" → {{"workflow_type": "knowledge_query", "confidence": 0.8, "rationale": "General knowledge question"}}
"""

DOMAIN_MAP = {
    "job_search": "JobSearchAgent",
    "trading": "TradingAgent",
    "knowledge_query": "KnowledgeAgent",
    "project_monitor": "ProjectMonitorAgent",
    "research": "ResearchAgent",
    "unknown": "UnknownHandlerAgent",
}


class RouterAgent:
    """Claude-powered request router for workflow orchestration.

    Routes incoming requests to appropriate domain agents by:
    1. Sending request to Claude for classification
    2. Parsing Claude's response for workflow type and confidence
    3. Mapping workflow type to agent name
    4. Returning state updates for LangGraph to use

    Attributes:
        model: Claude model to use (default: claude-haiku-4-5-20251001)
    """

    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        """Initialize RouterAgent with specified model.

        Args:
            model: Claude model ID (default: Haiku for fast routing)
        """
        self.model = model
        self.logger = logging.getLogger("RouterAgent")
        self.logger.debug(f"RouterAgent initialized with model={model}")

    def route(self, state: dict) -> dict:
        """LangGraph node: classify request and return state updates only.

        This method is called as a node in the LangGraph graph. It:
        1. Extracts user_request from state
        2. Calls Claude to classify
        3. Returns ONLY the state fields being updated

        Args:
            state: Current workflow state dict (contains user_request at minimum)

        Returns:
            Dict with state updates: workflow_type, current_agent, step_count
            If error: {status: "error", error: "..."}
        """
        try:
            # Extract request
            user_request = state.get("user_request", {})
            request_str = str(user_request) if isinstance(user_request, dict) else user_request

            self.logger.debug(f"Routing request: {request_str[:100]}")

            # Call Claude
            client = Anthropic()
            msg = client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[
                    {
                        "role": "user",
                        "content": ROUTE_PROMPT.format(request=request_str),
                    }
                ],
            )

            # Parse response
            response_text = msg.content[0].text
            self.logger.debug(f"Claude response: {response_text}")

            parsed = json.loads(response_text)
            workflow_type = parsed.get("workflow_type", "unknown")
            confidence = parsed.get("confidence", 0.0)

            self.logger.info(
                f"Classified as {workflow_type} (confidence={confidence:.2f})"
            )

            # Map to agent
            agent_name = DOMAIN_MAP.get(workflow_type, "UnknownHandlerAgent")

            # Return state updates ONLY
            return {
                "workflow_type": workflow_type,
                "current_agent": agent_name,
                "step_count": state.get("step_count", 0) + 1,
            }

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Claude response as JSON: {e}")
            return {
                "status": "error",
                "error": f"router_json_decode_failed: {e}",
                "workflow_type": "unknown",
                "current_agent": "ErrorHandlerAgent",
            }

        except (APIError, AuthenticationError, APIConnectionError) as e:
            self.logger.error(f"Claude API error in RouterAgent: {type(e).__name__}: {e}")
            return {
                "status": "error",
                "error": f"router_api_failed: {type(e).__name__}",
                "workflow_type": "unknown",
                "current_agent": "ErrorHandlerAgent",
            }

        except Exception as e:
            self.logger.critical(
                f"Unexpected RouterAgent error: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return {
                "status": "error",
                "error": f"router_unexpected: {type(e).__name__}",
                "workflow_type": "unknown",
                "current_agent": "ErrorHandlerAgent",
            }
