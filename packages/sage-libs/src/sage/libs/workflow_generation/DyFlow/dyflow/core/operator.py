import json
import re
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Literal, Optional

from .state import State

# Define Base classes here for standalone testing
ExecuteSignal = Literal["next", "end_stage", "terminate", "error", "branch"]


class Operator:
    def __init__(self, operator_id: str, operator_description: str):
        self.operator_id = operator_id
        self.operator_description = operator_description

    def execute(self, state: State, params: dict[str, Any]) -> ExecuteSignal:
        raise NotImplementedError

    def _log_execution(
        self,
        state: State,
        params: dict[str, Any],
        status: ExecuteSignal,
        error_message: Optional[str] = None,
        **kwargs,
    ):
        # Helper to log execution details to state.workflow_log (NO TIME)
        log_entry = {
            # "timestamp": Removed,
            "operator_type": self.__class__.__name__,
            "operator_id": self.operator_id,
            "params_summary": {
                k: str(v)[:100] + "..." if isinstance(v, str) and len(v) > 100 else v
                for k, v in params.items()
            },
            "status": status,
            # "duration": Removed,
            "error": error_message,
            **kwargs,
        }
        # Assume state has this method implemented or append directly
        if hasattr(state, "log_operator_execution"):
            state.workflow_log.append(log_entry)
        else:
            state.workflow_log.append(log_entry)


PROMPT_TEMPLATES = {
    "GENERATE_ANSWER": """You are an expert problem solver. Think step by step to solve the problem using the context and guidance.

Context:
{context}

Guidance:
{guidance}

Instructions:
- For reasoning problems: provide step-by-step reasoning and final answer
- For coding problems: include Python code in ```python blocks
- Show complete reasoning or code logic

Output Format:
<your_solution_with_reasoning_and_or_code>""",
    "REVIEW_SOLUTION": """You are a careful reviewer trained to detect logical and mathematical errors. Your job is to critically evaluate the solution for correctness, soundness, and completeness — not just surface structure.

Context:
{context}

Guidance:
{guidance}

Instructions:
- You should try to find mistakes at every step of the given answer.
- You should bring the given answer into the original question to check if there is anything that does not meet the question setting.


Output Format:
Review Details: <step-by-step review>
Overall Verdict: <accept/minor_issues/major_issues/reject>
""",
    "DECOMPOSE_PROBLEM": """You are an expert in decomposing problems. Break down the original problem into clearly defined, structured sub-tasks.

Context:
{context}

Guidance:
{guidance}

Instructions:
- Clearly outline each distinct sub-task.
- Do not attempt to solve any sub-task.
- Maintain logical completeness.
- Decompose the problem into 2-4 steps at most.

Output:
<your_decomposed_problem>""",
    "GENERATE_PLAN": """You are an expert in generating step-by-step executable plans. Generate a step-by-step executable plan to approach the given problem.

Context:
{context}

Guidance:
{guidance}

Instructions:
- Clearly number each step.
- Ensure each step is actionable and logically sequenced.
- Do not solve the problem here, only provide the plan.
- Give 2-4 steps at most.

Output Format:
Solution Plan:
<step_id>: <description>
<step_id>: <description>""",
    "REFINE_ANSWER": """You are an expert in refining answers. Refine the existing answer based on context and guidance.

Context:
{context}

Guidance:
{guidance}

Output Format:
Answer: <your refined answer>""",
    "ORGANIZE_SOLUTION": """You are an expert in organizing solutions. Clearly organize the final solution for presentation based on the provided context and guidance.

Context:
{context}

Guidance:
{guidance}

Instructions:
- Extract the key action steps from the solution
- Present them in a structured workflow format with nodes and edges
- Use this EXACT format:

Node:
1: [first action step description]
2: [second action step description]
3: [third action step description]
...
Edge: (START,1) (1,2) (2,3) ... (n,END)

Requirements:
- Each node should be a clear, concise action step (one sentence)
- Nodes should be numbered sequentially starting from 1
- Edges must start with (START,1) and end with (n,END)
- Edges should show the sequential flow: (1,2), (2,3), etc.
- Extract 2-5 key action steps from the solution
- This is the FINAL output - the workflow will terminate after this

Output Format (MUST follow exactly):
Node:
1: <first action>
2: <second action>
...
Edge: (START,1) (1,2) ... (n,END)""",
    "SELF_CONSISTENCY_ENSEMBLE": """You are an expert problem solver. Generate ONE complete solution using a DISTINCT reasoning approach.

Context:
{context}

Guidance:
{guidance}

IMPORTANT Instructions:
- Use a unique logical approach (this is one member of an ensemble run in parallel).
- Think step-by-step and show the full chain of reasoning.
- Provide the final answer in the exact format the task requires.

Output:
<your_solution_with_final_answer>""",
    "DEFAULT": """You are an expert in executing actions strictly according to the given context and guidance.

Context:
{context}

Guidance:
{guidance}

Instructions:
- Follow every detail of the instructions carefully.
- Ensure output exactly matches the requested format.

Output:
<your_output>""",
}


def extract_final_answer(solution: str, task_type: str = "general") -> str:
    """Heuristically pull the final answer segment from a solution string."""
    if not solution:
        return ""

    # Generic patterns that appear across reasoning tasks
    patterns = [
        r"Final\s*Answer\s*[:\-]\s*(.+)",
        r"Answer\s*[:\-]\s*(.+)",
        r"Conclusion\s*[:\-]\s*(.+)",
        r"Result\s*[:\-]\s*(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, solution, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

    lines = [line.strip() for line in solution.strip().splitlines() if line.strip()]
    return lines[-1] if lines else solution.strip()


class InstructExecutorOperator(Operator):
    """
    Executes a specific instruction using the configured Executor LLM.

    It fetches context data from the State based on 'input_keys',
    constructs a prompt using a template determined by 'instruction_type'
    The LLM's response is then stored back into the State at the location
    specified by 'output_key'.

    Instruction types include:
    - Regular instructions: 'GENERATE_ANSWER', 'TEST_CODE', 'REVIEW_SOLUTION', etc.
    - 'TERMINATE': Ends the workflow and returns the final answer.
    """

    def __init__(self, operator_id: str, operator_description: str, llm_client: Any):
        """
        Initializes the operator.

        Args:
            operator_id: A unique identifier for this operator instance.
            llm_client: An instance of a client class (e.g., ExecutorLLMClient)
                        that has a `generate(prompt: str) -> Dict` method.
        """
        super().__init__(operator_id, operator_description)
        if not hasattr(llm_client, "generate"):
            raise TypeError("llm_client must have a 'generate' method.")
        self.llm_client = llm_client

    def _build_input_usage_string(self, input_usage: str) -> str:
        """Build input usage string for the prompt."""
        if input_usage:
            return f"Input Usage:\n{input_usage}\n"
        return ""

    def _build_context_string(self, context: dict[str, Any]) -> str:
        context_str = ""
        for key, value in context.items():
            context_str += f"{key}'s Context:\n{value}\n"
        return context_str

    def _get_prompt_template(self, template_key: str) -> Optional[str]:
        return PROMPT_TEMPLATES.get(template_key, PROMPT_TEMPLATES["DEFAULT"])

    def _process_output(self, llm_output: str, instruction_type: str) -> dict[str, str]:
        """
        Process the LLM output based on the instruction type and extract relevant information.

        Args:
            llm_output: Raw output from the LLM
            instruction_type: Type of instruction that was executed

        Returns:
            Dictionary containing processed output with different fields based on instruction type:
            - For REVIEW_SOLUTION: {'content': str, 'verdict': str}
            - For others: {'content': str}
        """
        if instruction_type == "REVIEW_SOLUTION":
            # Return full review content without extracting verdict
            # Let the summarization LLM handle verdict extraction
            return {"content": llm_output}

        elif instruction_type == "GENERATE_PLAN":
            # Extract the solution plan steps
            try:
                plan_start = llm_output.find("Solution Plan:") + len("Solution Plan:")
                if plan_start == -1:
                    return {"content": llm_output}
                return {"content": llm_output[plan_start:].strip()}
            except Exception:
                return {"content": llm_output}

        else:  # DEFAULT or unknown types
            return {"content": llm_output}

    def _execute_code(self, code: str) -> tuple[str, str, Optional[dict[str, Any]]]:
        """
        Execute code in a sandbox environment.

        Args:
            code: Python code to execute

        Returns:
            Tuple of (status, result/error_message, execution_details)
            - status: 'Success' or 'Error'
            - result: execution result or error message
            - execution_details: Optional dict containing execution metadata
        """
        try:
            # Create a new global namespace
            global_namespace = {}

            disallowed_imports = [
                "os",
                "sys",
                "subprocess",
                "multiprocessing",
                "matplotlib",
                "seaborn",
                "plotly",
                "bokeh",
                "ggplot",
                "pylab",
                "tkinter",
                "PyQt5",
                "wx",
                "pyglet",
            ]

            # Check for prohibited imports
            for lib in disallowed_imports:
                if f"import {lib}" in code or f"from {lib}" in code:
                    return "Error", f"Prohibited import: {lib} and graphing functionalities", None

            # Use exec to execute the code
            exec(code, global_namespace)

            # Prepare execution details
            execution_details = {
                "variables": {k: v for k, v in global_namespace.items() if not k.startswith("__")},
                "function_names": [name for name, obj in global_namespace.items() if callable(obj)],
                "imports": [
                    name for name, obj in global_namespace.items() if isinstance(obj, type)
                ],
            }

            # Check if solve function exists and call it if present
            if "solve" in global_namespace and callable(global_namespace["solve"]):
                result = global_namespace["solve"]()
                return "Success", str(result), execution_details
            else:
                # Code executed successfully without solve function (e.g., assertions passed)
                return (
                    "Success",
                    "Code executed successfully (no solve function, assertions passed)",
                    execution_details,
                )

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_str = traceback.format_exception(exc_type, exc_value, exc_traceback)
            full_traceback = "".join(tb_str)
            error_details = {
                "error_type": str(exc_type.__name__) if exc_type else "Unknown",
                "error_message": str(e) if str(e) else f"{exc_type.__name__} (no message)",
                "traceback": full_traceback,
            }
            # Include full traceback in the result message for visibility
            error_msg = f"{exc_type.__name__}: {str(e) if str(e) else '(no message)'}\n\nTraceback:\n{full_traceback}"
            return "Error", error_msg, error_details

    def execute(self, state: State, params: dict[str, Any]) -> ExecuteSignal:
        """
        Executes the LLM instruction task.

        Required params:
            - instruction_type: str (e.g., 'GENERATE_ANSWER', 'TEST_CODE', 'REVIEW_SOLUTION', 'TERMINATE'. Used for prompt selection).
            - input_keys: List[str] (Paths in State to fetch context data).
            - output_key: str (Path in State to store the LLM's raw text output).
        Optional params:
            - guidance: Dict[str, Any] (Specific details to guide the LLM, used to fill prompt placeholders).
            - prompt_template_key: str (Overrides instruction_type for template lookup if provided).
            - final_answer_key: str (Required when instruction_type is 'TERMINATE')
            - final_answer: str (Optional direct final answer when instruction_type is 'TERMINATE')

        Returns:
            'next' on successful execution.
            'terminate' when instruction_type is 'TERMINATE'.
            'error' if any step fails (fetching data, building prompt, LLM call, storing output).
        """
        status: ExecuteSignal = "next"  # Optimistic default
        error_message: Optional[str] = None
        llm_output: Optional[str] = None

        print(f"\n--- Executing Operator: {self.operator_id} ({self.__class__.__name__}) ---")
        print(f"Params: {json.dumps(params, indent=2)}")

        try:
            # --- 1. Parameter Validation ---
            instruction_type = params.get("instruction_type")
            input_keys = params.get("input_keys")
            output_key = params.get("output_key")

            # Special case for TERMINATE instruction
            if instruction_type == "TERMINATE":
                final_answer = None

                # Get final answer from key if provided
                if "final_answer_key" in params:
                    final_answer_key = params["final_answer_key"]

                    # Ensure final_answer_key has the correct format
                    if not final_answer_key.startswith("actions.") and "." not in final_answer_key:
                        # This is likely a bare action ID, construct the full path
                        full_final_answer_key = f"actions.{final_answer_key}.content"
                    else:
                        full_final_answer_key = final_answer_key

                    final_answer = state.get_data_by_path(full_final_answer_key)

                    # Extract the action ID from the key
                    action_id = (
                        final_answer_key.split(".")[-3]
                        if final_answer_key.startswith("actions.")
                        and final_answer_key.endswith(".content")
                        else final_answer_key
                    )

                    # Check if this is an action with execution result
                    if action_id in state.actions:
                        action = state.actions[action_id]
                        if action.get("execution_result") is not None:
                            if isinstance(final_answer, str):
                                final_answer = f"{final_answer}\n\nexecution result: {json.dumps(action['execution_result'], ensure_ascii=False)}"
                            else:
                                final_answer = f"{str(final_answer)}"

                    params["final_answer"] = final_answer
                elif "final_answer" not in params:
                    params["final_answer"] = "No final answer generated"

                # Log termination
                self._log_execution(
                    state, params, "terminate", final_answer=params.get("final_answer")
                )

                print(f"--- Operator {self.operator_id} Finished with 'terminate' signal ---")
                return "terminate"

            if not instruction_type or not isinstance(input_keys, list) or not output_key:
                missing = [
                    p
                    for p, v in [
                        ("instruction_type", instruction_type),
                        ("input_keys", input_keys),
                        ("output_key", output_key),
                    ]
                    if not v or (p == "input_keys" and not isinstance(v, list))
                ]
                raise ValueError(f"Missing or invalid required parameters: {', '.join(missing)}")

            # Special case for TEST_CODE instruction - execute code directly without LLM
            if instruction_type == "TEST_CODE":
                print("TEST_CODE: Extracting and executing code directly (no LLM call)")

                # Fetch the input (solution with code)
                input_key = input_keys[0] if input_keys else None
                if not input_key:
                    raise ValueError("TEST_CODE requires at least one input_key")

                # Resolve full path
                if input_key == "original_problem":
                    full_key_path = input_key
                elif input_key.startswith("<<") and input_key.endswith(">>"):
                    full_key_path = f"actions.{input_key[2:-2]}.content"
                elif not input_key.startswith("actions.") and "." not in input_key:
                    full_key_path = f"actions.{input_key}.content"
                else:
                    full_key_path = input_key

                solution_text = state.get_data_by_path(full_key_path)
                if solution_text is None:
                    raise ValueError(f"Input data not found at path: '{full_key_path}'")

                print(f"  Fetched solution from: {full_key_path}")

                # Extract all Python code blocks (support multiple formats)
                # Try multiple patterns in order of preference
                patterns = [
                    r"```python\s*(.*?)\s*```",  # ```python ... ```
                    r"```py\s*(.*?)\s*```",  # ```py ... ```
                    r"```Python\s*(.*?)\s*```",  # ```Python ... ```
                    r"```\s*(def\s+.*?)\s*```",  # ``` def ... ``` (starts with def)
                    r"```\s*(.*?)\s*```",  # ``` ... ``` (any code block)
                ]

                matches = []
                for pattern in patterns:
                    matches = re.findall(pattern, solution_text, re.DOTALL)
                    if matches:
                        print(f"  Extracted {len(matches)} code block(s) using pattern: {pattern}")
                        break

                if matches:
                    code = "\n\n".join(matches)
                else:
                    # No code blocks found - try to extract raw code if it looks like Python
                    # Check if the solution contains function definitions
                    if re.search(r"^\s*def\s+\w+", solution_text, re.MULTILINE):
                        print(
                            "  No code blocks found, but solution contains function definitions - using entire text as code"
                        )
                        code = solution_text
                    else:
                        # Really no code found - store error and return
                        llm_output = "No Python code blocks found in the solution."
                        processed_output = {
                            "content": llm_output,
                            "execution_result": {
                                "status": "Error",
                                "result": "No code to execute",
                                "details": None,
                            },
                        }
                        # Store and return
                        full_output_key = (
                            f"actions.{output_key}.content"
                            if not output_key.startswith("actions.") and "." not in output_key
                            else output_key
                        )
                        state.set_data_by_path(full_output_key, llm_output)

                        action_id = (
                            output_key.split(".")[-3]
                            if output_key.startswith("actions.") and output_key.endswith(".content")
                            else output_key
                        )
                        if action_id in state.actions:
                            action = state.actions[action_id]
                            action["content"] = llm_output
                            action["execution_result"] = processed_output["execution_result"]
                            if "input_keys" in params:
                                action["input_keys"] = [
                                    k.split(".")[1] if k.startswith("actions.") else k
                                    for k in params["input_keys"]
                                ]
                            if state.stages[params["target_stage_id"]].get("history") is None:
                                state.stages[params["target_stage_id"]]["history"] = [
                                    {
                                        "id": action_id,
                                        "description": self.operator_description,
                                        "instruction_type": instruction_type,
                                    }
                                ]
                            else:
                                state.stages[params["target_stage_id"]]["history"].append(
                                    {
                                        "id": action_id,
                                        "description": self.operator_description,
                                        "instruction_type": instruction_type,
                                    }
                                )

                        self._log_execution(
                            state, params, "next", llm_output_preview=llm_output[:100]
                        )
                        print(f"--- Operator {self.operator_id} Finished ---")
                        return "next"

                # Execute the code
                print(f"  Code to execute:\n{code}\n")
                exec_status, exec_result, exec_details = self._execute_code(code)
                print(f"  Execution status: {exec_status}")
                if exec_status == "Error":
                    print(f"  Execution error:\n{exec_result}")
                else:
                    print(
                        f"  Execution result: {exec_result[:100]}..."
                        if len(exec_result) > 100
                        else f"  Execution result: {exec_result}"
                    )

                # Format output with clear error formatting
                if exec_status == "Error":
                    llm_output = f"Extracted Code:\n```python\n{code}\n```\n\n**Execution Failed**\n\nError Details:\n{exec_result}"
                else:
                    llm_output = f"Extracted Code:\n```python\n{code}\n```\n\nExecution Status: Success\nResult: {exec_result}"

                processed_output = {
                    "content": llm_output,
                    "code": code,
                    "execution_result": {
                        "status": exec_status,
                        "result": exec_result,
                        "details": exec_details,
                    },
                }

                # Store output
                full_output_key = (
                    f"actions.{output_key}.content"
                    if not output_key.startswith("actions.") and "." not in output_key
                    else output_key
                )
                success = state.set_data_by_path(full_output_key, llm_output)
                if not success:
                    raise RuntimeError(f"Failed to store output to state path: '{full_output_key}'")

                # Update action
                action_id = (
                    output_key.split(".")[-3]
                    if output_key.startswith("actions.") and output_key.endswith(".content")
                    else output_key
                )
                if action_id in state.actions:
                    action = state.actions[action_id]
                    action["content"] = llm_output
                    action["execution_result"] = processed_output["execution_result"]
                    action["code"] = code

                    if "input_keys" in params:
                        processed_input_keys = []
                        for key in params["input_keys"]:
                            if key.startswith("actions.") and "." in key:
                                processed_key = key.split(".")[1]
                            else:
                                processed_key = key
                            processed_input_keys.append(processed_key)
                        action["input_keys"] = processed_input_keys

                    if state.stages[params["target_stage_id"]].get("history") is None:
                        state.stages[params["target_stage_id"]]["history"] = [
                            {
                                "id": action_id,
                                "description": self.operator_description,
                                "instruction_type": instruction_type,
                            }
                        ]
                    else:
                        state.stages[params["target_stage_id"]]["history"].append(
                            {
                                "id": action_id,
                                "description": self.operator_description,
                                "instruction_type": instruction_type,
                            }
                        )

                # Log execution
                self._log_execution(
                    state,
                    params,
                    "next",
                    llm_output_preview=llm_output[:200] + "..."
                    if len(llm_output) > 200
                    else llm_output,
                )

                print(f"--- Operator {self.operator_id} Finished ---")
                return "next"

            input_usage = params.get("input_usage", "")

            # --- 2. Fetch Context Data ---
            print("Fetching context data from state...")
            context = {}
            for key_path in input_keys:
                # Ensure we're using the full path for actions
                if key_path == "original_problem":
                    full_key_path = key_path
                elif key_path.startswith("<<") and key_path.endswith(">>"):
                    full_key_path = f"actions.{key_path[2:-2]}.content"
                elif not key_path.startswith("actions.") and "." not in key_path:
                    # This is likely a bare action ID, construct the full path
                    full_key_path = f"actions.{key_path}.content"
                else:
                    full_key_path = key_path

                context_value = state.get_data_by_path(full_key_path)
                try:
                    if full_key_path.endswith(".content"):
                        execution_result = state.get_data_by_path(
                            full_key_path.replace(".content", ".execution_result")
                        )
                        if execution_result is not None:
                            context_value = f"{context_value}\n\nExecution Result: {json.dumps(execution_result, ensure_ascii=False)}"
                except Exception:
                    pass
                if context_value is None:
                    # Input data missing - this is usually critical
                    raise ValueError(f"Input data not found in state at path: '{full_key_path}'")

                # Use the last part of the path as the context key name for the prompt
                context_key = key_path.split(".")[-1] if "." in key_path else key_path
                context[context_key] = context_value
                print(
                    f"  - Fetched '{full_key_path}' as '{context_key}': {str(context_value)[:80]}..."
                )  # Log fetched data preview

            # --- 3. Select Prompt Template ---
            template_key = params.get("prompt_template_key", instruction_type)
            print(f"Selecting prompt template for key: '{template_key}'")
            prompt_template = self._get_prompt_template(template_key)
            if prompt_template is None:
                raise ValueError(f"No prompt template found for key: '{template_key}'")

            # --- 4. Construct Final Prompt ---
            # Prepare keyword arguments for formatting
            prompt_kwargs = {
                "context": self._build_context_string(context),
                "guidance": self._build_input_usage_string(input_usage),
            }

            # Attempt to format the prompt, catching key errors
            try:
                final_prompt = prompt_template.format(**prompt_kwargs)
            except KeyError as e:
                raise ValueError(
                    f"Missing key in prompt template '{template_key}' or context/guidance: {e}"
                ) from e

            # --- 5. Call Executor LLM ---
            print(f"Calling Executor LLM (Client: {self.llm_client.__class__.__name__})...")

            if instruction_type == "SELF_CONSISTENCY_ENSEMBLE":
                num_samples = max(1, int(params.get("num_samples", 5)))
                ensemble_temperature = params.get("ensemble_temperature", 0.7)
                ensemble_max_tokens = params.get("max_tokens", 2048)

                print(f"  Generating {num_samples} ensemble solutions in parallel...")

                # Define a function to generate a single solution
                def generate_single_solution(idx: int) -> tuple[int, str]:
                    response = self.llm_client.generate(
                        prompt=final_prompt,
                        temperature=ensemble_temperature,
                        max_tokens=ensemble_max_tokens,
                    )
                    sol = response["response"]
                    print(f"  Generated ensemble solution {idx + 1}/{num_samples}")
                    return idx, sol

                # Use ThreadPoolExecutor to generate solutions concurrently
                solutions: list[str] = [None] * num_samples
                with ThreadPoolExecutor(max_workers=num_samples) as executor:
                    futures = {
                        executor.submit(generate_single_solution, idx): idx
                        for idx in range(num_samples)
                    }
                    for future in as_completed(futures):
                        idx, sol = future.result()
                        solutions[idx] = sol

                context_block = prompt_kwargs["context"]
                guidance_block = prompt_kwargs["guidance"]
                solutions_formatted = "\n\n".join(
                    [f"Solution {i + 1}:\n{solutions[i].strip()}" for i in range(len(solutions))]
                )

                selector_prompt = (
                    "You are an impartial adjudicator comparing multiple candidate solutions to the same task.\n"
                    "First, identify which solutions reach the same conclusion (majority consensus).\n"
                    "Then select one solution from the majority group - choose the one with the clearest reasoning.\n"
                    "If there is no clear majority, select the single solution that is most likely correct and logically sound.\n\n"
                    "Problem Context:\n"
                    f"{context_block}\n\n"
                    "Guidance for the task:\n"
                    f"{guidance_block}\n\n"
                    "Candidate solutions:\n"
                    f"{solutions_formatted}\n\n"
                    "Respond strictly in JSON with keys 'selected_index' (1-based integer), 'justification', and optional 'confidence' (0-1)."
                )

                selector_raw = ""
                selector_data: Optional[dict[str, Any]] = None
                selection_method = "llm_majority_selection"
                selection_confidence: Optional[float] = None
                selected_index = 0

                if solutions:
                    selector_response = self.llm_client.generate(
                        prompt=selector_prompt,
                        temperature=0.0,
                        max_tokens=min(ensemble_max_tokens, 1024),
                    )
                    selector_raw = selector_response["response"]
                    try:
                        json_match = re.search(r"\{[\s\S]*\}", selector_raw)
                        if not json_match:
                            raise ValueError("Selector output missing JSON block")
                        selector_data = json.loads(json_match.group())
                        selected_index = int(selector_data.get("selected_index", 1)) - 1
                        raw_confidence = selector_data.get("confidence")
                        try:
                            selection_confidence = (
                                float(raw_confidence) if raw_confidence is not None else None
                            )
                        except (ValueError, TypeError):
                            selection_confidence = None
                        print(
                            f"  Selector chose solution {selected_index + 1} (majority consensus)"
                        )
                    except Exception as parse_error:
                        print(
                            f"  Selector parsing failed ({parse_error}). Falling back to first solution."
                        )
                        selector_data = None
                        selection_method = "fallback_first"
                        selected_index = 0
                        selection_confidence = 0.0
                else:
                    selection_method = "fallback_first"
                    selected_index = 0

                # Boundary check for selected_index
                if not (0 <= selected_index < len(solutions)):
                    selected_index = max(0, min(selected_index, len(solutions) - 1))

                llm_output = solutions[selected_index] if solutions else ""
                processed_output = self._process_output(llm_output, instruction_type)
                processed_output["ensemble_info"] = {
                    "all_solutions": solutions,
                    "num_samples": num_samples,
                    "selected_index": selected_index,
                    "selection_method": selection_method,
                    "selector_justification": selector_data.get("justification")
                    if selector_data
                    else None,
                    "confidence": selection_confidence,
                }
                print(
                    f"  Ensemble finalized: solution {selected_index + 1}/{num_samples} via {selection_method}"
                )

            else:
                temperature = params.get("temperature", 0.1)
                response = self.llm_client.generate(prompt=final_prompt, temperature=temperature)
                llm_output = response["response"]
                processed_output = self._process_output(llm_output, instruction_type)
            # --- 6. Store Raw Output ---
            print(f"Storing LLM output to state path: '{output_key}'")

            # Ensure output_key has the correct format
            if not output_key.startswith("actions.") and "." not in output_key:
                # This is likely a bare action ID, construct the full path
                full_output_key = f"actions.{output_key}.content"
            elif output_key.startswith("<<") and output_key.endswith(">>"):
                full_output_key = f"actions.{output_key[2:-2]}.content"
            else:
                full_output_key = output_key

            # Store the output at the specified path
            success = state.set_data_by_path(full_output_key, llm_output)
            if not success:
                # This is a critical failure, the result is lost
                raise RuntimeError(f"Failed to store LLM output to state path: '{full_output_key}'")

            # --- 7. Update action based on output ---
            # Get actual action ID (remove path prefix if present)
            action_id = (
                output_key.split(".")[-3]
                if output_key.startswith("actions.") and output_key.endswith(".content")
                else output_key
            )

            # Update the action in the actions dictionary directly
            if action_id in state.actions:
                action = state.actions[action_id]
                action["content"] = processed_output["content"]

                # If input_keys present in params, make sure we update them in the action
                if "input_keys" in params:
                    # Process the input_keys (convert paths to action IDs if needed)
                    processed_input_keys = []
                    for key in params["input_keys"]:
                        if key.startswith("actions.") and "." in key:
                            # Extract action ID from path
                            processed_key = key.split(".")[
                                1
                            ]  # Get "act_X" from "actions.act_X.content"
                        else:
                            processed_key = key
                        processed_input_keys.append(processed_key)

                    # Update the input_keys in the action
                    action["input_keys"] = processed_input_keys

                # Store ensemble info if present
                if (
                    instruction_type == "SELF_CONSISTENCY_ENSEMBLE"
                    and "ensemble_info" in processed_output
                ):
                    action["ensemble_info"] = processed_output["ensemble_info"]

                # Add the action to stage history
                if state.stages[params["target_stage_id"]].get("history") is None:
                    state.stages[params["target_stage_id"]]["history"] = [
                        {
                            "id": action_id,
                            "description": self.operator_description,
                            "instruction_type": instruction_type,
                        }
                    ]
                else:
                    state.stages[params["target_stage_id"]]["history"].append(
                        {
                            "id": action_id,
                            "description": self.operator_description,
                            "instruction_type": instruction_type,
                        }
                    )

                # If this is ORGANIZE_SOLUTION, automatically trigger termination
                if instruction_type == "ORGANIZE_SOLUTION":
                    # Store the organized solution as final answer in both state and params
                    final_answer_content = processed_output["content"]
                    state.final_answer = final_answer_content
                    state.final_status = "completed"
                    params["final_answer"] = (
                        final_answer_content  # Also store in params for workflow return
                    )

                    # Log termination
                    self._log_execution(
                        state, params, "terminate", final_answer=final_answer_content
                    )
                    print("--- ORGANIZE_SOLUTION completed, triggering automatic termination ---")
                    print(f"Final answer stored: {final_answer_content[:200]}...")
                    return "terminate"

        except Exception as e:
            status = "error"
            error_message = (
                f"Error in {self.__class__.__name__} ({self.operator_id}): {type(e).__name__} - {e}"
            )
            print(f"\nERROR ENCOUNTERED: {error_message}\n")  # Ensure error is visible
            # Log the error persistently in the state
            if hasattr(state, "add_error"):
                state.add_error(
                    source=f"{self.__class__.__name__}-{self.operator_id}",
                    message=str(e),
                    details={"params": params},
                )  # Pass params for context

        finally:
            # --- 8. Log Execution Attempt ---
            # Skip logging for TERMINATE and ORGANIZE_SOLUTION (already logged in try block)
            if instruction_type not in ["TERMINATE", "ORGANIZE_SOLUTION"]:
                print(f"Logging execution for {self.operator_id}. Final Status: {status}")
                self._log_execution(
                    state,
                    params,
                    status,
                    error_message,
                    llm_output_preview=llm_output[:100] + "..." if llm_output else None,
                )
                print(f"--- Operator {self.operator_id} Finished ---")
                return status
            else:
                # TERMINATE or ORGANIZE_SOLUTION: ensure terminate signal is returned
                return "terminate"
