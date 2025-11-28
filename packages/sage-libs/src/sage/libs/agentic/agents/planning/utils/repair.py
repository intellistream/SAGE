"""
Utility Functions for Plan Repair

Handles JSON parsing, repair, and error recovery for plan generation.
"""

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


def strip_code_fences(text: str) -> str:
    """
    Remove markdown code fences from text.

    Args:
        text: Text potentially containing code fences

    Returns:
        Text with code fences removed
    """
    text = text.strip()

    # Remove leading ```json or ```
    if text.startswith("```"):
        text = text[3:]
        # Remove language identifier
        if "\n" in text:
            first_line, rest = text.split("\n", 1)
            if first_line.strip().lower() in ["json", "python", ""]:
                text = rest
            else:
                text = text
        # Remove trailing ```
        if text.endswith("```"):
            text = text[:-3]

    return text.strip()


def extract_json_array(text: str) -> Optional[list[Any]]:
    """
    Extract JSON array from text using multiple strategies.

    Strategies:
    1. Direct parsing
    2. Find first [...] block
    3. Regex extraction

    Args:
        text: Text potentially containing JSON

    Returns:
        Parsed JSON array or None if extraction failed
    """
    text = strip_code_fences(text)

    # Strategy 1: Direct parsing
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        # If it's a dict with a "steps" or "plan" key
        if isinstance(data, dict):
            if "steps" in data and isinstance(data["steps"], list):
                return data["steps"]
            if "plan" in data and isinstance(data["plan"], list):
                return data["plan"]
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract first [...] block
    try:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            snippet = text[start : end + 1]
            data = json.loads(snippet)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 3: Regex extraction (nested arrays)
    try:
        # Match balanced brackets
        pattern = r"\[(?:[^\[\]]|\[[^\]]*\])*\]"
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, list) and len(data) > 0:
                    return data
            except json.JSONDecodeError:
                continue
    except Exception as e:
        logger.debug(f"Regex extraction failed: {e}")

    return None


def repair_json(text: str) -> Optional[str]:
    """
    Attempt to repair malformed JSON.

    Common fixes:
    - Add missing closing brackets
    - Fix trailing commas
    - Escape unescaped quotes
    - Fix common typos

    Args:
        text: Potentially malformed JSON text

    Returns:
        Repaired JSON string or None if repair failed
    """
    text = strip_code_fences(text)

    # Count brackets to detect missing closures
    open_count = text.count("[")
    close_count = text.count("]")
    if open_count > close_count:
        text = text + "]" * (open_count - close_count)
        logger.info(f"Added {open_count - close_count} closing brackets")

    # Remove trailing commas before closing brackets/braces
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # Try to parse
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError as e:
        logger.debug(f"JSON repair unsuccessful: {e}")
        return None


def validate_plan_structure(data: list[dict[str, Any]]) -> bool:
    """
    Validate that plan data has correct structure.

    Args:
        data: List of plan step dictionaries

    Returns:
        True if structure is valid, False otherwise
    """
    if not isinstance(data, list):
        return False

    if len(data) == 0:
        return False

    for item in data:
        if not isinstance(item, dict):
            return False

        # Check for required fields (flexible)
        has_action = "action" in item or "type" in item or "name" in item
        if not has_action:
            return False

    return True


def normalize_plan_steps(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Normalize plan steps to standard format.

    Converts various formats to consistent structure:
    {
        "id": int,
        "action": str,
        "tool_id": str,
        "inputs": dict,
        "depends_on": list,
        "expected_outputs": list,
        "description": str
    }

    Args:
        data: List of raw plan step dictionaries

    Returns:
        List of normalized step dictionaries
    """
    normalized = []

    for idx, step in enumerate(data):
        normalized_step = {
            "id": step.get("id", idx + 1),
            "action": step.get("action", step.get("type", step.get("name", f"step_{idx + 1}"))),
            "tool_id": step.get("tool_id", step.get("tool", step.get("name"))),
            "inputs": step.get("inputs", step.get("arguments", step.get("params", {}))),
            "depends_on": step.get("depends_on", step.get("dependencies", [])),
            "expected_outputs": step.get("expected_outputs", step.get("outputs", [])),
            "description": step.get("description", step.get("text", "")),
        }

        # Ensure depends_on is a list
        if not isinstance(normalized_step["depends_on"], list):
            if isinstance(normalized_step["depends_on"], (int, str)):
                normalized_step["depends_on"] = [normalized_step["depends_on"]]
            else:
                normalized_step["depends_on"] = []

        # Ensure expected_outputs is a list
        if not isinstance(normalized_step["expected_outputs"], list):
            if isinstance(normalized_step["expected_outputs"], str):
                normalized_step["expected_outputs"] = [normalized_step["expected_outputs"]]
            else:
                normalized_step["expected_outputs"] = []

        # Ensure inputs is a dict
        if not isinstance(normalized_step["inputs"], dict):
            normalized_step["inputs"] = {}

        normalized.append(normalized_step)

    return normalized


def extract_and_repair_plan(text: str) -> Optional[list[dict[str, Any]]]:
    """
    Main function to extract and repair plan from LLM output.

    Combines all repair strategies:
    1. Extract JSON array
    2. Repair malformed JSON
    3. Validate structure
    4. Normalize format

    Args:
        text: Raw LLM output

    Returns:
        List of normalized plan step dictionaries or None if failed
    """
    # Try direct extraction first
    data = extract_json_array(text)

    if data is None:
        # Try repairing the JSON first
        repaired = repair_json(text)
        if repaired:
            data = extract_json_array(repaired)

    if data is None:
        logger.warning("Failed to extract plan from text")
        return None

    # Validate structure
    if not validate_plan_structure(data):
        logger.warning("Extracted data does not have valid plan structure")
        return None

    # Normalize format
    normalized = normalize_plan_steps(data)

    return normalized


def create_fallback_plan(goal: str, num_steps: int = 5) -> list[dict[str, Any]]:
    """
    Create a minimal fallback plan when extraction fails.

    Args:
        goal: The original goal
        num_steps: Number of fallback steps to create

    Returns:
        List of minimal plan step dictionaries
    """
    steps = []
    for i in range(num_steps):
        steps.append(
            {
                "id": i + 1,
                "action": f"step_{i + 1}_for_{goal[:30]}",
                "tool_id": None,
                "inputs": {},
                "depends_on": [i] if i > 0 else [],
                "expected_outputs": [],
                "description": f"Step {i + 1} towards: {goal}",
            }
        )

    return steps
