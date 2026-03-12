"""EMyBrain orchestration engine using LangGraph.

Main entry point for Phase 2. Builds a LangGraph state machine that routes requests
through specialized agents and manages workflow execution. No async/await here;
async is handled at the gateway level.

Architecture:
- Entry point: router node (uses RouterAgent to classify requests)
- Exit: END node (returns final_result)
- State: Dict-based (LangGraph standard, not WorkflowState class)
- Composition: Does NOT import from gateway.api
"""

import logging
from typing import Any, Dict, Optional
from langgraph.graph import StateGraph, END

logger = logging.getLogger("EMyBrain")


class EMyBrain:
    """Main orchestration engine for Emy workflows.

    Manages LangGraph workflow execution, routes requests to appropriate agents,
    and persists execution state via optional MemoryStore.

    Example:
        ```python
        brain = EMyBrain()
        result = await brain.execute_workflow(
            workflow_id="wf_abc123",
            request={"query": "find jobs in Toronto"}
        )
        ```
    """

    def __init__(self, db: Optional[Any] = None, memory_store: Optional[Any] = None):
        """Initialize the Brain.

        Args:
            db: Optional EMyDatabase instance for workflow persistence
            memory_store: Optional MemoryStore for context persistence
        """
        self.db = db
        self.memory_store = memory_store
        self._graph = self._build_graph()
        logger.info("EMyBrain initialized")

    def _build_graph(self):
        """Build the LangGraph state machine.

        Returns:
            Compiled LangGraph for workflow execution
        """
        # State is a plain dict (LangGraph standard)
        graph = StateGraph(dict)

        # Define nodes
        graph.add_node("router", self._router_node)

        # Set entry point
        graph.set_entry_point("router")

        # Route from router to END (scaffold — Tasks 2-4 add more nodes)
        graph.add_edge("router", END)

        # Compile
        return graph.compile()

    def _router_node(self, state: dict) -> dict:
        """Placeholder router node.

        Tasks 2-4 will integrate RouterAgent, BrowserController, MemoryStore here.

        Args:
            state: Current workflow state dict

        Returns:
            State updates (only return the fields you're modifying)
        """
        # Scaffold: just increment step count
        return {"step_count": state.get("step_count", 0) + 1}

    async def execute_workflow(self, workflow_id: str, request: dict) -> dict:
        """Execute a workflow end-to-end.

        This is the main entry point called by gateway/api.py via BackgroundTasks.

        Args:
            workflow_id: Unique workflow identifier (for logging and resumption)
            request: User request dict (must include at minimum user input)

        Returns:
            Result dict with status, workflow_type, output, etc.
        """
        try:
            # Initialize state
            state = {
                "user_request": request,
                "workflow_id": workflow_id,
                "status": "running",
                "step_count": 0,
                "workflow_type": "",
                "current_agent": "",
                "context": {},
                "execution_history": [],
                "final_result": {},
                "error": None,
            }

            # Execute graph (synchronous execution of graph, wrapped in async)
            result = self._graph.invoke(state)

            # Return result
            return {
                "workflow_id": workflow_id,
                "status": result.get("status", "complete"),
                "workflow_type": result.get("workflow_type", "unknown"),
                "output": result.get("final_result", {}),
                "steps": result.get("step_count", 0),
            }

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}", exc_info=True)
            return {
                "workflow_id": workflow_id,
                "status": "error",
                "workflow_type": "",
                "output": None,
                "error": str(e),
            }
