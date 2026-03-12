"""MemoryStore - Workflow context persistence wrapper.

Provides a clean interface for LangGraph nodes to save and load workflow context
without needing to know about database details. Uses SQLite via EMyDatabase.

Architecture:
- Composition pattern: wraps EMyDatabase (no subclassing)
- Called from LangGraph nodes to persist context between steps
- Enables workflow resumption after interruptions
"""

import logging
from typing import Optional, Any

logger = logging.getLogger("MemoryStore")


class MemoryStore:
    """Workflow context persistence store.

    Wraps EMyDatabase to provide a simple interface for saving and loading
    workflow execution context. Used by LangGraph nodes to enable resumption.

    Example:
        ```python
        memory = MemoryStore(db)
        memory.save_step("wf_123", "RouterAgent", 1, context_dict)
        recovered = memory.load_latest("wf_123")
        ```
    """

    def __init__(self, db: Any):
        """Initialize MemoryStore with database instance.

        Args:
            db: EMyDatabase instance for persistence
        """
        self.db = db
        self.logger = logging.getLogger("MemoryStore")
        self.logger.debug("MemoryStore initialized")

    def save_step(
        self,
        workflow_id: str,
        agent_name: str,
        step: int,
        context: dict,
        checkpoint: Optional[dict] = None,
    ) -> None:
        """Save workflow step context.

        Args:
            workflow_id: Unique workflow identifier
            agent_name: Name of agent executing this step
            step: Step number
            context: Context accumulated so far
            checkpoint: Optional checkpoint data for resumption
        """
        try:
            self.logger.debug(
                f"Saving context for {workflow_id} step {step} (agent={agent_name})"
            )
            self.db.save_workflow_context(
                workflow_id=workflow_id,
                agent_name=agent_name,
                step_number=step,
                context_dict=context,
                checkpoint_dict=checkpoint,
            )
            self.logger.info(f"Context saved for {workflow_id} step {step}")

        except Exception as e:
            self.logger.error(f"Failed to save context for {workflow_id}: {e}")

    def load_latest(self, workflow_id: str) -> Optional[dict]:
        """Load latest context for workflow.

        Returns:
            Dict with context, checkpoint, step_number, agent_name or None if not found
        """
        try:
            self.logger.debug(f"Loading latest context for {workflow_id}")
            result = self.db.load_workflow_context(workflow_id)

            if result:
                self.logger.info(
                    f"Loaded context for {workflow_id} step {result['step_number']} "
                    f"(agent={result['agent_name']})"
                )
            else:
                self.logger.debug(f"No context found for {workflow_id}")

            return result

        except Exception as e:
            self.logger.error(f"Failed to load context for {workflow_id}: {e}")
            return None

    def clear_workflow(self, workflow_id: str) -> None:
        """Clear all saved context for a workflow.

        Args:
            workflow_id: Unique workflow identifier
        """
        try:
            self.logger.debug(f"Clearing context for {workflow_id}")
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM workflow_contexts WHERE workflow_id = ?",
                    (workflow_id,),
                )
            self.logger.info(f"Context cleared for {workflow_id}")

        except Exception as e:
            self.logger.error(f"Failed to clear context for {workflow_id}: {e}")
