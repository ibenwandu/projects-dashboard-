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
from emy.brain.router_agent import RouterAgent

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
        self.router_agent = RouterAgent()
        self._graph = self._build_graph()
        logger.info("EMyBrain initialized")

    def _build_graph(self):
        """Build the LangGraph state machine.

        Returns:
            Compiled LangGraph for workflow execution
        """
        from emy.brain.nodes import (
            KnowledgeBrainNode,
            TradingBrainNode,
            ResearchBrainNode,
            ProjectMonitorBrainNode,
            JobSearchBrainNode,
            CompleteBrainNode,
            UnknownBrainNode,
        )

        # State is a plain dict (LangGraph standard)
        graph = StateGraph(dict)

        # Register all nodes - use callables to defer instantiation
        graph.add_node("router", self._router_node)
        graph.add_node("knowledge_node", lambda state: KnowledgeBrainNode().execute(state))
        graph.add_node("trading_node", lambda state: TradingBrainNode().execute(state))
        graph.add_node("research_node", lambda state: ResearchBrainNode().execute(state))
        graph.add_node("project_monitor_node", lambda state: ProjectMonitorBrainNode().execute(state))
        graph.add_node("job_search_node", lambda state: JobSearchBrainNode().execute(state))
        graph.add_node("complete_node", lambda state: CompleteBrainNode().execute(state))
        graph.add_node("unknown_node", lambda state: UnknownBrainNode().execute(state))

        # Conditional routing function
        def route_by_type(state: dict) -> str:
            """Route request to appropriate node based on workflow_type."""
            routing_map = {
                "knowledge_query": "knowledge_node",
                "trading": "trading_node",
                "research": "research_node",
                "project_monitor": "project_monitor_node",
                "job_search": "job_search_node",
            }
            return routing_map.get(state.get("workflow_type", "unknown"), "unknown_node")

        # Add conditional edges from router
        graph.add_conditional_edges("router", route_by_type)

        # All domain nodes route to complete_node
        for node in [
            "knowledge_node",
            "trading_node",
            "research_node",
            "project_monitor_node",
            "job_search_node",
            "unknown_node",
        ]:
            graph.add_edge(node, "complete_node")

        # complete_node → END
        graph.add_edge("complete_node", END)

        # Set entry point
        graph.set_entry_point("router")

        # Compile
        return graph.compile()

    def _router_node(self, state: dict) -> dict:
        """Route request to appropriate agent based on classification.

        Uses RouterAgent to classify the request and determine which domain agent
        should handle it. Returns only the fields being updated.

        Args:
            state: Current workflow state dict

        Returns:
            State updates with workflow_type, current_agent, step_count
        """
        return self.router_agent.route(state)

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
