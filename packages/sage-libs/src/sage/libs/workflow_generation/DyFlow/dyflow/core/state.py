"""
State management for DyFlow workflows.

Provides the central state repository for workflow execution, including:
- Stage tracking and management
- Action tracking (solutions and reviews)
- Execution history and logs
- Incremental state summarization for Designer LLM

Layer: L3 (Core Library)
"""

import json
import re
from typing import Any, Literal, Optional

from sage.common.utils.logging.custom_logger import CustomLogger

from ..model_service.model_service import ModelService

# Initialize logger
logger = CustomLogger(__name__)

# Define simple status literals (can be expanded later)
Status = Literal[
    "pending", "in_progress", "completed", "failed", "error", "needs_review", "accepted", "rejected"
]


class State:
    """
    Represents the single, persistent, and cumulative state of the workflow
    for one specific problem instance. Acts as the central knowledge repository.
    Data from "previous states" is accessed by using the correct path within
    this single state object.
    """

    def __init__(self, original_problem: str, summarize_service: Optional[ModelService] = None):
        """
        Initializes the state with the original problem description.

        Args:
            original_problem: The original problem description
            summarize_service: Optional ModelService for state summarization.
                              If None, defaults to gpt-4o-mini.
        """
        # --- Core Problem & Final Result ---
        self.original_problem: str = original_problem
        self.final_answer: Optional[Any] = None
        self.final_status: Status = "pending"

        # --- Summarization Service ---
        self._summarize_service = summarize_service

        # --- Main Data Structures (Dictionaries keyed by IDs) ---
        self.stages: dict[str, dict[str, Any]] = {}  # Stores stage info (description, status)
        # Merged solutions and reviews into a single actions dictionary
        self.actions: dict[
            str, dict[str, Any]
        ] = {}  # Stores all actions (content, type, status, execution_result, verdict, etc.)

        # --- Flexible Storage & Logs ---
        self.intermediate_data: dict[str, Any] = {}  # For miscellaneous data points
        self.workflow_log: list[dict[str, Any]] = []  # Log of operator executions
        self.stage_history: list[
            dict[str, Any]
        ] = []  # History of designed stages (summary, graph, outcome)
        self.error_log: list[dict[str, Any]] = []  # Log of encountered errors

        # --- Summary Management (for incremental summarization) ---
        self.summarized_stages: list[str] = []  # Stores numbered summaries in presentation order
        self._summarized_stage_ids: list[str] = []  # Tracks which stage_ids have been summarized
        self._stage_summary_counter: int = 0  # Sequential counter for numbered summaries

        # --- Execution Context ---
        self.current_stage_id: Optional[str] = None
        self.current_operator_id: Optional[str] = None

        # --- Simple ID Counters (for this basic implementation) ---
        self._stage_counter: int = 0
        self._action_counter: int = 0  # Combined counter for all actions

    # --- Path-Based Data Access ---

    def get_data_by_path(self, path: str, default: Any = None) -> Any:
        """
        Retrieves data from the state using a dot-separated path string.

        Example Paths:
            - "original_problem"
            - "stages.stage_1.status"
            - "actions.act_0.content"
            - "intermediate_data.extracted_value"
            - "actions.act_1.execution_result.stdout"

        Args:
            path: The dot-separated path string.
            default: The value to return if the path is invalid or data not found.

        Returns:
            The data found at the path, or the default value.
        """
        try:
            keys = path.split(".")
            value = self  # Start traversal from the State object itself
            for key in keys:
                if isinstance(value, dict):
                    value = value[key]
                elif isinstance(value, list) and key.isdigit():
                    idx = int(key)
                    if 0 <= idx < len(value):
                        value = value[idx]
                    else:
                        return default
                elif hasattr(value, key):
                    # Access attributes like 'original_problem' or methods if needed (careful!)
                    value = getattr(value, key)
                else:
                    return default
            return value
        except (KeyError, IndexError, TypeError, AttributeError):
            return default

    def set_data_by_path(self, path: str, value: Any) -> bool:
        """
        Sets data in the state using a dot-separated path string.
        Attempts to create intermediate dictionaries if they are missing in the path.

        Example Paths:
            - "stages.stage_1.status"
            - "actions.act_0.content"
            - "intermediate_data.extracted_value"
            - "actions.act_1.execution_result" (can set a whole dict here)
            - "actions.act_1.execution_result.stdout" (can set nested value)

        Args:
            path: The dot-separated path string where the value should be set.
            value: The data to set at the specified path.

        Returns:
            True if the data was set successfully, False otherwise.
        """
        try:
            keys = path.split(".")
            target: Any = self
            for key in keys[:-1]:
                if isinstance(target, dict):
                    target = target.setdefault(key, {})
                    continue

                if hasattr(target, key):
                    attr = getattr(target, key)
                    if attr is None:
                        attr = {}
                        setattr(target, key, attr)
                    if isinstance(attr, dict):
                        target = attr
                        continue
                    logger.error(f"Attribute '{key}' is not a dict for path '{path}'")
                    return False

                logger.error(f"Cannot traverse path at key '{key}' for path '{path}'")
                return False

            final_key = keys[-1]
            if isinstance(target, dict):
                target[final_key] = value
                return True

            if hasattr(target, final_key):
                current_val = getattr(target, final_key)
                if callable(current_val):
                    logger.error(
                        f"Attempted to overwrite callable attribute '{final_key}' at path '{path}'"
                    )
                    return False
                setattr(target, final_key, value)
                return True

            if isinstance(target, State):
                setattr(target, final_key, value)
                return True

            logger.error(f"Cannot set value on target type {type(target)} for key '{final_key}'")
            return False
        except Exception as exc:
            logger.error(f"Error setting data by path '{path}': {exc}")
            return False

    # --- Helper Methods for Common Operations ---

    def _get_next_id(self, counter_name: str) -> str:
        """Generates simple sequential IDs (e.g., stage_0, stage_1)."""
        if counter_name == "stage":
            idx = self._stage_counter
            self._stage_counter += 1
            return f"stage_{idx}"
        elif counter_name == "action":
            idx = self._action_counter
            self._action_counter += 1
            return f"act_{idx}"
        else:
            raise ValueError(f"Unknown counter name: {counter_name}")

    def add_stage(
        self, description: str, status: Status = "pending", stage_id: Optional[str] = None
    ) -> str:
        """Adds a new stage and returns its generated ID."""
        if stage_id is None:
            stage_id = self._get_next_id("stage")
        self.stages[stage_id] = {
            "description": description,
            "status": status,
            # Add parent_id, child_ids etc. later if needed
        }
        logger.info(f"Added stage '{stage_id}': {description[:50]}...")
        return stage_id

    def add_action(
        self,
        stage_id: str,
        content: Any,
        action_type: str = "solution",
        input_keys: list[str] = None,
        status: Status = "generated",
        verdict: Optional[Status] = None,
    ) -> str:
        """
        Adds a new action (solution or review) and returns its ID.

        Args:
            stage_id: The ID of the stage this action belongs to
            content: The content of the action (solution or review comment)
            action_type: Type of action ('solution' or 'review') - used to determine which fields to add
            input_keys: List of IDs of actions that are inputs to this action
            status: Status of the action
            verdict: Only for reviews - the verdict status (accepted/rejected)

        Returns:
            The generated action ID
        """
        action_id = self._get_next_id("action")
        if stage_id not in self.stages:
            logger.warning(f"Adding action for non-existent stage_id '{stage_id}'")

        action = {
            "stage_id": stage_id,
            "content": content,
            "status": status,
            "input_keys": input_keys or [],
        }

        # Add type-specific fields
        if action_type == "solution":
            action["execution_result"] = None
        elif action_type == "review":
            action["verdict"] = verdict or "pending"

        self.actions[action_id] = action
        logger.info(f"Added {action_type} '{action_id}' for stage '{stage_id}'")
        return action_id

    def log_operator_execution(
        self,
        operator_id: str,
        operator_type: str,
        params: dict,
        status: str,
        details: Optional[dict] = None,
    ):
        """Logs an operator execution attempt."""
        entry = {
            "operator_id": operator_id,
            "operator_type": operator_type,
            "params_summary": {
                k: str(v)[:100] + "..." if isinstance(v, str) and len(v) > 100 else v
                for k, v in params.items()
            },  # Summarize params
            "status": status,
            "details": details or {},
        }
        self.workflow_log.append(entry)

    def add_error(self, source: str, message: str, details: Optional[dict] = None):
        """Logs an error encountered during the workflow."""
        entry = {"source": source, "message": message, "details": details or {}}
        self.error_log.append(entry)
        logger.error(f"Error from {source}: {message}")

    # --- State Summary for Designer ---
    def _build_stage_raw_info(self, stage_id: str) -> str:
        """
        Build raw information for a single stage.

        Args:
            stage_id: The ID of the stage to build info for

        Returns:
            Formatted string containing stage information
        """
        stage = self.stages[stage_id]
        stage_description = stage["description"]
        stage_history = []

        if stage.get("history") is None:
            return f"Stage goal ({stage_id}):\n {stage_description}\nNo actions executed in this stage."

        # Process each item in the stage history
        for item in stage["history"]:
            op_id = item["id"]
            op_description = item["description"]
            instruction_type = item.get("instruction_type", "unknown")

            # Check if the action exists in the actions dictionary
            if op_id in self.actions:
                action = self.actions[op_id]

                # Determine the type of action based on instruction_type
                if instruction_type == "REVIEW_SOLUTION":
                    # This is a review action - show full review content (verdict will be extracted by summarization LLM)
                    input_keys_str = (
                        ", ".join(action["input_keys"])
                        if "input_keys" in action and action["input_keys"]
                        else "None"
                    )
                    item_result = (
                        f"\t##{stage_id}##: Review output key: {op_id}:\n"
                        f" {op_description}\n"
                        f" Instruction type: {instruction_type}\n"
                        f" Reviews actions: {input_keys_str}\n"
                        f" Review content: {action['content']}"
                    )
                elif action.get("execution_result") is not None:
                    # This is a code execution action with execution result
                    item_result = (
                        f"\t##{stage_id}##: Solution output key: {op_id}:\n"
                        f" {op_description}\n"
                        f" Instruction type: {instruction_type}\n"
                        f" Solution content: {action['content']}\n"
                        f" Code execution result: {action['execution_result']}"
                    )
                else:
                    # This is a basic solution action
                    item_result = (
                        f"\t##{stage_id}##: Solution output key: {op_id}:\n"
                        f" {op_description}\n"
                        f" Instruction type: {instruction_type}\n"
                        f" Solution content: {action['content']}"
                    )
            else:
                # Action not found
                item_result = f"Unknown action ({op_id}):\n {op_description}\n Instruction type: {instruction_type}\n Action not found in state"

            stage_history.append(item_result)

        joined_history = "\n".join(stage_history)
        return f"Stage goal ({stage_id}):\n {stage_description}\n{joined_history}"

    def get_state_summary_for_designer(self) -> str:
        """
        Creates an incremental summary of the current state for the Designer LLM.
        Only summarizes new stages that haven't been summarized yet.

        Returns:
            A string containing the complete execution summary
        """
        # Check if there are any stages to process
        if not self.stages:
            return "No previous stages executed yet. This is the first stage."

        sorted_stage_ids = sorted(self.stages.keys())
        len(sorted_stage_ids)
        pending_stage_ids = [
            sid for sid in sorted_stage_ids if sid not in self._summarized_stage_ids
        ]
        len(self._summarized_stage_ids)

        # Only summarize new stages
        if pending_stage_ids:
            # Use LLM to create concise summaries
            # Use the configured summarize service, or fall back to gpt-4o-mini
            if self._summarize_service is None:
                logger.warning("No summarize_service configured, falling back to gpt-4o-mini")
                summarize_service = ModelService(model="gpt-4o-mini")
            else:
                summarize_service = self._summarize_service

            for stage_id in pending_stage_ids:
                # Build raw information for this stage
                stage_raw_info = self._build_stage_raw_info(stage_id)

                # Concise summarization prompt - focus on key information
                prompt = f"""You are summarizing a workflow stage execution. Extract and report ONLY the information that actually exists.

=== INPUT FORMAT ===
The stage information contains actions in this format:
- "##stage_X##: Solution output key: <action_id>:" (for solutions)
- "##stage_X##: Review output key: <action_id>:" (for reviews)

=== YOUR TASK ===
1. Find each "output key: <action_id>" and extract the exact action ID
2. Summarize what each action did based on its instruction type and content
3. For REVIEW_SOLUTION actions: Extract verdict from "Overall Verdict:" (accept/reject/minor_issues/major_issues)
4. For TEST_CODE actions: Extract execution result (Success/Failure)
5. Extract final answer if present

=== OUTPUT FORMAT ===
- Stage goal: <one sentence>
- Actions executed:
  • <action_id> (<instruction_type>): <brief description>
  • <action_id> (<instruction_type>): <brief description>
- Review verdict: <verdict keyword> (only if REVIEW_SOLUTION present)
- Execution result: <Success/Failure details> (only if TEST_CODE present)
- Final Answer: <answer> (only if present)

=== CRITICAL RULES ===
1. One operator = one action = one output key (DO NOT create multiple IDs like act_1, act_2, act_3 from one operator)
2. Copy the EXACT action ID you see after "output key:" (e.g., "output key: act_1" → use "act_1")
3. DO NOT invent, number, or modify action IDs
4. If stage has 1 action, list 1 action; if stage has 2 actions, list 2 actions

=== STAGE INFORMATION ===
{stage_raw_info}"""

                summarized_state = summarize_service.generate(prompt)
                stage_summary = summarized_state["response"].strip()

                # Store this stage's summary with sequential numbering
                self._stage_summary_counter += 1
                numbered_summary = f"Stage {self._stage_summary_counter}:\n{stage_summary}"
                self.summarized_stages.append(numbered_summary)
                self._summarized_stage_ids.append(stage_id)

        # Return concatenated summary of all stages
        return "\n\n".join(self.summarized_stages)

    def _parse_stage_summary(self, raw_summary: str) -> dict[str, Any]:
        """Parse the LLM stage summary JSON response."""

        def _attempt_parse(candidate: str) -> Optional[dict[str, Any]]:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                return None

        cleaned = raw_summary.strip()
        parsed = _attempt_parse(cleaned)
        if parsed is not None:
            return parsed

        # Try to extract the first JSON object
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            parsed = _attempt_parse(match.group(0))
            if parsed is not None:
                return parsed

        logger.warning("Failed to parse stage summary JSON. Falling back to raw text.")
        return {"raw_text": cleaned}

    def _format_stage_summary(self, stage_id: str, summary_data: dict[str, Any]) -> str:
        """Format parsed stage summary data into the canonical text representation."""

        if "raw_text" in summary_data:
            return summary_data["raw_text"]

        stage_goal = summary_data.get("stage_goal", "Unknown stage goal")
        actions = summary_data.get("actions") or []

        lines = [f"Stage {stage_id}:", f"- Stage goal: {stage_goal}"]

        for idx, action in enumerate(actions):
            label = chr(ord("a") + idx) if idx < 26 else f"action_{idx}"
            output_key = action.get("output_key", "unknown_output_key")
            description = action.get("description", "No description provided")
            instruction_type = action.get("instruction_type", "unknown")
            content_summary = action.get("content_summary", "No summary available")
            result = action.get("result") or {}
            result_field = result.get("field")
            result_value = result.get("value")

            lines.append(f"    - Action {label}:")
            lines.append(f"        - Action's output key: {output_key}")
            lines.append(f"        - Description: {description}")
            lines.append(f"        - Instruction type: {instruction_type}")
            lines.append(f"        - Content (brief summary): {content_summary}")
            if result_field and result_value is not None:
                lines.append(f"        - {result_field}: {result_value}")

        return "\n".join(lines)

    def __str__(self) -> str:
        """Provides a basic string representation of the state for debugging."""
        # Avoid dumping excessively large fields like full content or logs
        summary_snapshot = self.get_state_summary_for_designer()
        return json.dumps({"state_summary": summary_snapshot}, ensure_ascii=False, indent=2)
