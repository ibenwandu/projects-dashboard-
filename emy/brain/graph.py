"""LangGraph state graph for Emy Brain."""
from langgraph.graph import StateGraph, END
from emy.brain.state import EMyState
from emy.brain.nodes import router_node, create_agent_node, AGENT_REGISTRY
import logging

logger = logging.getLogger('EMyBrain.Graph')


def route_to_agent(state: EMyState) -> str:
    """
    Determine which agent to route to based on current_agent in state.

    Args:
        state: Current EMyState

    Returns:
        Agent name or END
    """
    if state.current_agent and state.current_agent in AGENT_REGISTRY:
        return state.current_agent
    return END


def build_graph():
    """
    Build the LangGraph state graph.

    Creates a graph with:
    - Router node that directs workflow to appropriate agent
    - Agent nodes for each registered agent
    - Conditional edges based on agent selection

    Returns:
        Compiled LangGraph StateGraph
    """
    graph = StateGraph(EMyState)

    # Add router node
    graph.add_node("router", router_node)

    # Add agent nodes for each registered agent
    for agent_name in AGENT_REGISTRY.keys():
        agent_node = create_agent_node(agent_name)
        graph.add_node(agent_name, agent_node)

    # Set entry point to router
    graph.set_entry_point("router")

    # Add conditional edge from router to agents based on current_agent
    graph.add_conditional_edges("router", route_to_agent)

    # Set finish point (any agent → END)
    for agent_name in AGENT_REGISTRY.keys():
        graph.add_edge(agent_name, END)

    # Compile the graph
    compiled_graph = graph.compile()
    logger.info(f"LangGraph compiled with {len(AGENT_REGISTRY)} agent nodes")

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
