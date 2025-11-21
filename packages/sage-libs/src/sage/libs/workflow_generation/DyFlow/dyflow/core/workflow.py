import json
import re
import time
from typing import Any, Optional

from ..model_service.model_service import ModelService
from .operator import InstructExecutorOperator, Operator
from .state import State

# Define the design prompt template
DESIGN_STAGE_PROMPT = """
You are the workflow stage designer. Analyze the current execution state and design the next stage dynamically.

Original Problem:
{problem_description}

Current Execution Summary:
{state_summary}

# Available Operators and When to Use

Strategy Selection Guidelines:
- Assess problem complexity in the first stage and choose an appropriate initial strategy
- Adapt strategy based on execution results
- Prefer diverse strategies: if review failed, try DECOMPOSE or ENSEMBLE instead

1. DECOMPOSE_PROBLEM
   Purpose: Break down a complex problem into smaller, manageable sub-goals.
   Output: List of ordered sub-goals.

2. GENERATE_PLAN
   Purpose: Create a strategic solving approach or outline before generating the solution.
   Output: Step-by-step plan.

3. GENERATE_ANSWER
   Purpose: Generate a complete solution with step-by-step reasoning or calculations.
   Output: Full solution text with reasoning or code implementation.

4. REFINE_ANSWER
   Purpose: Improve an existing solution based on review feedback or identified issues.
   Output: Improved solution text.

5. SELF_CONSISTENCY_ENSEMBLE
   Purpose: Generate multiple independent solutions (3-5 solutions) and select the best by majority vote.
   Output: Ensemble of solutions + selected best answer.

6. REVIEW_SOLUTION
   Purpose: Critically evaluate a solution for correctness, soundness, and completeness.
   Output: Review details + "Overall Verdict: accept/minor_issues/major_issues/reject"

7. TEST_CODE
   Purpose: Extract and execute Python code from a code problem solution to verify it runs correctly.
   Output: Execution status (success/failure) and result.

8. ORGANIZE_SOLUTION
   Purpose: Format the final answer and TERMINATE the workflow.
   Output format requirements:
   - For coding problems: ONLY the function implementation in a python block - NO assertions, NO test cases, NO example code

Design Rules

1. Stage Structure:
   - Typical stage: 3-4 operators working together to achieve an intermediate goal
   - Termination stage: If the solution is validated, design a NEW SEPARATE stage containing ONLY ORGANIZE_SOLUTION
   - NEVER mix ORGANIZE_SOLUTION with other operators in the same stage
   - Maximum 7 stages total

2. Naming Conventions:
   - Stage IDs: Increase monotonically (e.g., "stage_1", "stage_2", "stage_3")
   - Operator IDs: Format "op_<stageNum>_<index>" (e.g., "op_3_1", "op_3_2")
   - Output keys: Use ONLY existing action output keys from the execution summary (e.g., "sub_goals", "step_plan")
   - NEVER reference keys that don't exist in the summary (e.g., don't use "act_0", "act_5" unless they appear in the summary)

3. Input Keys:
   - Always reference ONLY existing keys: "original_problem" or action output keys shown in the summary
   - NEVER invent or assume keys that aren't explicitly mentioned in the summary
   - Example: If summary shows "sub_goals" and "step_plan", you can use those as input_keys
   - For any operator that needs the problem statement, use "original_problem" in input_keys
   - On the first solving stage, always pass "original_problem" to the executor so it can see the question

4. Input Usage Field:
   - Explain how to use each input_key's data for this operator

Output Format:
Return valid JSON in this structure:

{{
  "stage_id": "stage_N",
  "stage_description": "One-sentence description of what this stage accomplishes",
  "operators": [
    {{
      "operator_id": "op_N_1",
      "operator_description": "What this specific operator does",
      "params": {{
        "instruction_type": "OPERATOR_NAME",
        "input_keys": ["key1", "key2"],
        "output_key": "act_X",
        "input_usage": "How to use the input_keys data"
      }}
    }},
    ... (add more operators as needed - typically 3-4 per stage)
  ]
}}
"""


class WorkflowExecutor:
    """
    Executes a workflow by dynamically generating and running stages.

    This class coordinates the overall workflow execution by:
    1. Using a Designer LLM to dynamically design stages
    2. Executing each stage's operators in sequence
    3. Terminating when an InstructExecutorOperator with 'TERMINATE' instruction signals completion
    """

    def __init__(
        self,
        problem_description: str,
        designer_service: ModelService,
        executor_service: ModelService,
        save_design_history: bool = False,
    ):
        """
        Initialize the workflow executor.

        Args:
            problem_description: The original problem to solve
            designer_model: Model name for the designer LLM
            executor_model: Model name for the executor LLM
            save_design_history: If True, design_history will be returned via get_design_history() instead of saved to JSONL
        """
        # Initialize state with the designer service for summarization
        self.state = State(original_problem=problem_description, summarize_service=designer_service)

        # Initialize LLM clients
        self.designer_llm = designer_service
        self.executor_llm = executor_service

        # Create operator instances
        self.operator_instances = {}
        self.stage_counter = 0
        self.design_history = []
        self.save_design_history = save_design_history
        self.design_output_path = None

    def _extract_json_from_string(self, text: str) -> dict[str, Any]:
        """
        Extract JSON from text using multiple strategies for robust parsing.

        Args:
            text: The text containing JSON to extract

        Returns:
            Extracted JSON as a dictionary

        Raises:
            ValueError: If no valid JSON could be extracted
        """
        # Strategy 1: Look for ```json and ``` markers
        json_block_pattern = r"```json\s*([\s\S]*?)\s*```"
        json_matches = re.findall(json_block_pattern, text)

        # If standard JSON blocks are found
        if json_matches:
            for json_str in json_matches:
                try:
                    return json.loads(json_str)
                except:
                    continue

        # Strategy 2: Look for content between <stage_design> and </stage_design> tags
        stage_design_pattern = r"<stage_design>\s*([\s\S]*?)\s*</stage_design>"
        stage_matches = re.findall(stage_design_pattern, text)

        if stage_matches:
            for stage_content in stage_matches:
                # Try to find JSON blocks within the stage_design content
                json_block_pattern = r"```json\s*([\s\S]*?)\s*```"
                json_matches = re.findall(json_block_pattern, stage_content)

                if json_matches:
                    for json_str in json_matches:
                        try:
                            return json.loads(json_str)
                        except:
                            continue

                # Try to directly parse JSON from stage_content
                try:
                    # Find the first { and last }
                    json_start = stage_content.find("{")
                    json_end = stage_content.rfind("}") + 1

                    if json_start != -1 and json_end != -1 and json_start < json_end:
                        json_str = stage_content[json_start:json_end]
                        return json.loads(json_str)
                except:
                    pass

        # Strategy 3: Try balanced bracket method to extract the outermost JSON object
        json_obj = self._find_balanced_json(text)
        if json_obj:
            return json_obj

        # Strategy 4: Last resort, try handling special characters
        try:
            # Find the most likely JSON start and end positions
            json_start = text.find("{")
            json_end = text.rfind("}") + 1

            if json_start != -1 and json_end != -1 and json_start < json_end:
                json_str = text[json_start:json_end]
                # Handle common issues
                sanitized = json_str.replace("\\", "\\\\")
                sanitized = re.sub(r'(?<!\\)"(?=(,|\s*}|]|:))', '\\"', sanitized)
                sanitized = re.sub(r'(?<![\\{[,:\s])"', '\\"', sanitized)
                try:
                    return json.loads(sanitized)
                except:
                    # Final attempt, remove comments
                    sanitized = re.sub(r"//.*?(\n|$)", "", sanitized)
                    return json.loads(sanitized)
        except:
            raise ValueError("Could not extract valid JSON from response")

        raise ValueError("Could not extract valid JSON from response")

    def _find_balanced_json(self, text: str) -> Optional[dict[str, Any]]:
        """
        Find balanced JSON objects using bracket matching.

        Args:
            text: Text to search for balanced JSON

        Returns:
            JSON object if found, None otherwise
        """
        stack = []
        start_idx = None
        for i, char in enumerate(text):
            if char == "{":
                if not stack:  # If this is the first opening bracket
                    start_idx = i
                stack.append("{")
            elif char == "}":
                if stack and stack[-1] == "{":
                    stack.pop()
                    if not stack:  # If brackets are balanced
                        json_str = text[start_idx : i + 1]
                        try:
                            json_obj = json.loads(json_str)
                            return json_obj
                        except:
                            pass  # Continue searching for the next possible JSON object
        return None

    def _get_stage_id(self) -> str:
        """Generate a unique stage ID."""
        stage_id = f"stage_{self.stage_counter}"
        self.stage_counter += 1
        return stage_id

    def _create_operator_instance(self, operator_id: str, operator_description: str) -> Operator:
        """
        Create an instance of an operator.

        Args:
            operator_id: Unique identifier for this operator

        Returns:
            An instance of the requested operator
        """
        return InstructExecutorOperator(
            operator_id=operator_id,
            operator_description=operator_description,
            llm_client=self.executor_llm,
        )

    def _get_operator_instance(self, operator_id: str, operator_description: str) -> Operator:
        """
        Get or create an operator instance.

        Args:
            operator_id: Unique identifier for this operator
            operator_description: Description of the operator's task
        Returns:
            An instance of the requested operator
        """
        if operator_id not in self.operator_instances:
            self.operator_instances[operator_id] = self._create_operator_instance(
                operator_id, operator_description
            )
        return self.operator_instances[operator_id]

    def _design_next_stage(self) -> dict[str, Any]:
        """
        Use the designer LLM to design the next stage.

        Returns:
            A dictionary describing the stage
        """
        # Get the current state summary to provide to the designer
        state_summary = self.state.get_state_summary_for_designer()

        # Add stage count constraint notice if approaching iteration limit
        stage_count_notice = ""
        current_stage_count = len(self.state.stages)
        if current_stage_count >= 4:
            stage_count_notice = f"\n\nConstraint: This will be stage {current_stage_count + 1}. The workflow has a maximum iteration limit of 6-7 stages. To ensure successful termination, include ORGANIZE_SOLUTION in this stage."
        if current_stage_count >= 6:
            stage_count_notice = f"\n\nTermination Required: This is stage {current_stage_count + 1}. The workflow must terminate at this iteration to avoid exceeding the maximum allowed stages. Include ORGANIZE_SOLUTION in this stage. If no solution has been accepted, use SELF_CONSISTENCY_ENSEMBLE followed by ORGANIZE_SOLUTION to output the best available result."

        # Create the design prompt
        prompt = (
            DESIGN_STAGE_PROMPT.format(
                problem_description=self.state.original_problem, state_summary=state_summary
            )
            + stage_count_notice
        )

        # Call the designer LLM
        response = self.designer_llm.generate(prompt=prompt, temperature=0.1)
        design_output = response["response"]
        try:
            # Extract and parse JSON from the LLM response
            try:
                stage_design = self._extract_json_from_string(design_output)
            except Exception as e:
                raise ValueError(f"Failed to parse designer LLM response JSON: {str(e)}")

            # Validate the stage design with more detailed feedback
            required_keys = ["stage_id", "stage_description", "operators"]
            missing_keys = [key for key in required_keys if key not in stage_design]
            if missing_keys:
                raise ValueError(
                    f"Missing required fields in stage design: {', '.join(missing_keys)}"
                )

            # Override the stage_id with our own to ensure uniqueness
            # stage_design["stage_id"] = self._get_stage_id()
            self.state.add_stage(
                stage_design["stage_description"], stage_id=stage_design["stage_id"]
            )

            # Store the input and output
            self.design_history.append({"input": prompt, "output": design_output})

            return stage_design

        except Exception as e:
            raise RuntimeError(f"Failed to parse designer LLM response: {str(e)}")

    def _execute_stage(self, stage: dict[str, Any]) -> tuple[bool, Optional[str], Optional[Any]]:
        """
        Execute a single stage of the workflow.

        Args:
            stage: A dictionary describing the stage to execute

        Returns:
            A tuple of (should_continue, termination_reason, final_answer)
        """
        stage_id = stage["stage_id"]
        stage_description = stage["stage_description"]
        operators = stage["operators"]

        # Update state with current stage
        self.state.current_stage_id = stage_id

        # Log stage start
        stage_log = {
            "stage_id": stage_id,
            "description": stage_description,
            "operators": [op["operator_id"] for op in operators],
            "outcome": "started",
        }

        # Execute each operator in sequence
        final_answer = None
        for op_data in operators:
            operator_id = op_data["operator_id"]
            operator_description = op_data["operator_description"]
            params = op_data["params"]
            params["target_stage_id"] = stage_id

            # Update state with current operator
            self.state.current_operator_id = operator_id
            self.state.current_operator_description = operator_description

            # Get or create the operator instance
            operator = self._get_operator_instance(operator_id, operator_description)

            # TERMINATE instruction is now deprecated - ORGANIZE_SOLUTION handles termination
            # Keep this for backward compatibility but log a warning
            if params.get("instruction_type") == "TERMINATE":
                print(
                    "WARNING: TERMINATE instruction is deprecated. Use ORGANIZE_SOLUTION instead."
                )
                if "final_answer_key" in params:
                    final_answer_key = params["final_answer_key"]
                    if final_answer_key.startswith("<<"):
                        final_answer_key = final_answer_key[2:-2]
                    # Ensure final_answer_key has the correct format
                    if not final_answer_key.startswith("actions.") and "." not in final_answer_key:
                        # This is likely a bare action ID, construct the full path
                        full_final_answer_key = f"actions.{final_answer_key}.content"
                    else:
                        full_final_answer_key = final_answer_key

                    final_answer = self.state.get_data_by_path(full_final_answer_key)

                    # Extract the action ID from the key
                    action_id = (
                        final_answer_key.split(".")[-3]
                        if final_answer_key.startswith("actions.")
                        and final_answer_key.endswith(".content")
                        else final_answer_key
                    )

                    # Check if this is an action with execution result
                    if action_id in self.state.actions:
                        action = self.state.actions[action_id]
                        if action.get("execution_result") is not None:
                            if isinstance(final_answer, str):
                                final_answer = f"{final_answer}\n\nexecution result: {json.dumps(action['execution_result'], ensure_ascii=False)}"
                            else:
                                final_answer = f"{str(final_answer)}"

                    params["final_answer"] = final_answer
                else:
                    final_answer = None

            # Execute the operator
            signal = operator.execute(self.state, params)

            # Handle the execution signal
            if signal == "terminate":
                termination_reason = params.get("reason", "Workflow terminated by operator")
                # Ensure we propagate the final answer returned by the operator
                if params.get("final_answer") is not None:
                    final_answer = params.get("final_answer")
                stage_log["outcome"] = f"terminated: {termination_reason}"
                self.state.stage_history.append(stage_log)
                print(f"\n=== Received TERMINATE signal from operator {operator_id} ===")
                print(f"Termination reason: {termination_reason}")
                print(f"Final answer: {params.get('final_answer', 'None')}")
                print("=== Workflow will terminate now ===")
                return False, termination_reason, final_answer

            elif signal == "error":
                # Log the error but continue to the next operator
                print(f"Error in operator {operator_id}, continuing with next operator")

            elif signal == "end_stage":
                # Skip remaining operators in this stage
                stage_log["outcome"] = "ended_early"
                self.state.stage_history.append(stage_log)
                return True, None, None

        # Stage completed successfully
        stage_log["outcome"] = "completed"
        self.state.stage_history.append(stage_log)
        return True, None, None

    def execute(self) -> Any:
        """
        Execute the workflow until completion.

        Returns:
            The final answer directly, not wrapped in a dictionary
        """
        print("\n=== Starting Workflow Execution ===")
        print(f"Problem: {self.state.original_problem}")

        should_continue = True
        termination_reason = None
        final_answer = None
        iteration_count = 0  # Track the number of iterations
        max_iterations = 8
        pattern_history: list[tuple] = []

        while should_continue and iteration_count < max_iterations:
            try:
                # Increment iteration counter
                iteration_count += 1
                print(f"\n=== Iteration {iteration_count}/{max_iterations} ===")

                # Design the next stage
                stage = self._design_next_stage()
                print(f"========== Stage {stage['stage_id']} ==========")
                print(f"Stage Description: {stage['stage_description']}")
                print(f"Operators: {stage['operators']}")
                print("========================================================")

                # Track operator patterns to detect loops (e.g., repeated review cycles)
                current_pattern = tuple(
                    op.get("params", {}).get("instruction_type")
                    for op in stage.get("operators", [])
                )
                pattern_history.append(current_pattern)

                if len(pattern_history) >= 3:
                    recent_patterns = pattern_history[-3:]
                    loop_detected = all(
                        pattern and "REVIEW_SOLUTION" in pattern for pattern in recent_patterns
                    )
                    warning_text = "LOOP DETECTED: Last 3 stages each ran REVIEW_SOLUTION. Switch strategy (e.g., SELF_CONSISTENCY_ENSEMBLE or DECOMPOSE_PROBLEM)."
                    if loop_detected:
                        if getattr(self.state, "loop_warning", None) != warning_text:
                            print(f"WARNING: {warning_text}")
                        self.state.loop_warning = warning_text
                    else:
                        if getattr(self.state, "loop_warning", None):
                            print("Loop pattern cleared. Removing warning.")
                        self.state.loop_warning = None

                # Execute the stage
                should_continue, termination_reason, stage_final_answer = self._execute_stage(stage)

                # If we got a final answer from this stage, store it
                if stage_final_answer is not None:
                    final_answer = stage_final_answer

                # Handle termination immediately
                if not should_continue:
                    print("\n=== Workflow received termination signal, stopping execution ===")
                    break

            except Exception as e:
                # Log the error but try to continue with next stage
                print(f"Error in workflow execution: {str(e)}")
                self.state.add_error(
                    source="WorkflowExecutor",
                    message=str(e),
                    details={"stage_id": self.state.current_stage_id},
                )

        # Check if we've reached the maximum iterations
        if iteration_count >= max_iterations and should_continue:
            termination_reason = f"Maximum number of iterations ({max_iterations}) reached"
            print(f"\n=== Workflow terminated: {termination_reason} ===")
            return None

        # Workflow completed
        if termination_reason and "Workflow terminated by operator" in termination_reason:
            print("\n=== Workflow Terminated by TERMINATE Instruction ===")
            print(f"Termination reason: {termination_reason}")
            print(f"Final answer: {final_answer}")
        else:
            print("\n=== Workflow Execution Completed ===")
            print(f"Termination reason: {termination_reason}")

        # Update final status
        self.state.final_status = "completed"

        # Return the final answer directly
        if final_answer is not None:
            # Only save to JSONL if NOT using save_design_history mode
            if not self.save_design_history:
                # Store the design history
                final_record = {
                    "problem": self.state.original_problem,
                    "final_answer": final_answer,
                    "design_history": self.design_history,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                # Append to JSONL file (one record per line)
                try:
                    with open(self.design_output_path, "a") as f:
                        f.write(json.dumps(final_record, ensure_ascii=False) + "\n")
                except Exception as e:
                    print(f"Failed to save design history: {str(e)}")

            return final_answer
        else:
            return None

    def get_design_history(self) -> list[dict]:
        """Return the design history for this workflow execution."""
        return self.design_history
