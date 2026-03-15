"""LangGraph state graph for Emy Brain."""
from langgraph.graph import StateGraph, END
from emy.brain.state import EMyState
from emy.brain.nodes import router_node, create_agent_node, create_agent_group_node, AGENT_REGISTRY
import logging

logger = logging.getLogger('EMyBrain.Graph')


def build_graph():
    """
    Build LangGraph with support for both single-agent and multi-agent modes.

    Single-agent mode: router → agent → END
    Multi-agent mode: router → agent_group_executor → router (loop) → ... → END
    """
    workflow = StateGraph(EMyState)

    # Add router node
    workflow.add_node("router", router_node)

    # Add agent group executor (for parallel execution)
    workflow.add_node("agent_group_executor", create_agent_group_node())

    # Add individual agent nodes (for backward compatibility)
    for agent_name in AGENT_REGISTRY.keys():
        workflow.add_node(agent_name, create_agent_node(agent_name))

    # Define routing logic after router
    def route_after_router(state: EMyState) -> str:
        if state.agent_groups:
            return "agent_group_executor"
        elif state.current_agent:
            return state.current_agent
        else:
            return END

    workflow.add_conditional_edges("router", route_after_router, {
        "agent_group_executor": "agent_group_executor",
        **{agent_name: agent_name for agent_name in AGENT_REGISTRY.keys()},
        END: END
    })

    # Define routing logic after group execution
    def route_after_group_execution(state: EMyState) -> str:
        if state.agent_groups and state.current_group_index < len(state.agent_groups):
            return "router"  # Execute next group
        else:
            return END  # All groups complete

    workflow.add_conditional_edges("agent_group_executor", route_after_group_execution, {
        "router": "router",
        END: END
    })

    # Individual agents go to END (backward compat)
    for agent_name in AGENT_REGISTRY.keys():
        workflow.add_edge(agent_name, END)

    # Set entry point
    workflow.set_entry_point("router")

    compiled_graph = workflow.compile()
    logger.info(f"LangGraph compiled with {len(AGENT_REGISTRY)} agent nodes and group executor")

    return compiled_graph


async def execute_workflow(state: EMyState) -> EMyState:
    """
    Execute a workflow through the LangGraph.

    Takes an initial state and executes it through the compiled graph,
    returning the final state with all results and messages.

    Args:
        state: Initial EMyState for the workflow

    Returns:
        Final EMyState after workflow completion
    """
    try:
        # Build the graph
        graph = build_graph()

        # Convert state to dict for graph execution
        state_dict = {
            "workflow_id": state.workflow_id,
            "workflow_type": state.workflow_type,
            "agents": state.agents,
            "current_agent": state.current_agent,
            "agent_groups": state.agent_groups,
            "current_group_index": state.current_group_index,
            "agents_executing": state.agents_executing,
            "input": state.input,
            "results": state.results,
            "messages": state.messages,
            "status": state.status,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
            "error": state.error,
            "error_context": state.error_context
        }

        # Execute workflow through graph
        logger.info(f"Executing workflow {state.workflow_id} through LangGraph")
        output = await graph.ainvoke(state_dict)

        # Convert output back to EMyState
        result_state = EMyState(
            workflow_id=output.get("workflow_id"),
            workflow_type=output.get("workflow_type"),
            agents=output.get("agents", []),
            current_agent=output.get("current_agent"),
            agent_groups=output.get("agent_groups", []),
            current_group_index=output.get("current_group_index", 0),
            agents_executing=output.get("agents_executing", []),
            input=output.get("input", {}),
            results=output.get("results", {}),
            messages=output.get("messages", []),
            status=output.get("status", "completed"),
            created_at=output.get("created_at"),
            updated_at=output.get("updated_at"),
            error=output.get("error"),
            error_context=output.get("error_context", {})
        )

        logger.info(f"Workflow {state.workflow_id} completed with status {result_state.status}")
        return result_state

    except Exception as e:
        logger.exception(f"Error executing workflow {state.workflow_id}: {str(e)}")
        state.error = str(e)
        state.status = "failed"
        return state
