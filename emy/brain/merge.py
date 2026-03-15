"""Utilities for merging results from parallel agent execution."""

from typing import Dict, Any, List


def merge_agent_results(base: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge agent results into base results.

    Args:
        base: Existing results dict
        new: New results from agents

    Returns:
        Merged results dict with both base and new entries
    """
    merged = base.copy()
    merged.update(new)
    return merged


def aggregate_messages(messages: List[Dict[str, Any]], new_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Aggregate audit messages from all agents.

    Args:
        messages: Existing messages
        new_messages: New messages from agents

    Returns:
        Combined messages list (preserves order)
    """
    return messages + new_messages


def aggregate_agent_outputs(agent_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a summary of all agent outputs for dashboard/API response.

    Args:
        agent_results: Dict keyed by agent name with agent outputs

    Returns:
        Aggregated summary with agent perspectives
    """
    summary = {
        "agent_count": len(agent_results),
        "agents": {},
        "insights": []
    }

    for agent_name, output in agent_results.items():
        summary["agents"][agent_name] = output

        # Extract insight if available, otherwise create entry from output
        if isinstance(output, dict):
            if "insight" in output:
                summary["insights"].append({
                    "agent": agent_name,
                    "insight": output["insight"]
                })
            else:
                # Create insight entry from first available key-value pair
                for key, value in output.items():
                    summary["insights"].append({
                        "agent": agent_name,
                        "insight": value
                    })
                    break

    return summary
