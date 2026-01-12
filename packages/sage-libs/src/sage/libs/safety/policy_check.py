"""Policy checking for tool calls and actions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class PolicyDecision(Enum):
    """Policy decision result."""

    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"


@dataclass
class PolicyResult:
    """Result of policy check."""

    decision: PolicyDecision
    reason: str | None = None
    metadata: dict[str, Any] | None = None


class PolicyChecker:
    """Policy checker for tool calls and actions."""

    def __init__(self):
        self.rules: list[tuple[str, Callable[[dict], PolicyResult]]] = []

    def add_rule(self, name: str, rule_fn: Callable[[dict], PolicyResult]) -> None:
        """Add a policy rule.

        Args:
            name: Rule name
            rule_fn: Function that takes tool_call dict and returns PolicyResult
        """
        self.rules.append((name, rule_fn))

    def check(self, tool_call: dict[str, Any]) -> PolicyResult:
        """Check tool call against all rules.

        Args:
            tool_call: Tool call dictionary with 'name', 'args', etc.

        Returns:
            PolicyResult (DENY if any rule denies, WARN if any warns, ALLOW otherwise)
        """
        warnings = []

        for rule_name, rule_fn in self.rules:
            result = rule_fn(tool_call)

            if result.decision == PolicyDecision.DENY:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Denied by rule '{rule_name}': {result.reason}",
                    metadata=result.metadata,
                )
            elif result.decision == PolicyDecision.WARN:
                warnings.append(f"Warning from rule '{rule_name}': {result.reason}")

        if warnings:
            return PolicyResult(
                decision=PolicyDecision.WARN,
                reason="; ".join(warnings),
            )

        return PolicyResult(decision=PolicyDecision.ALLOW)


# Predefined policy rules


def create_tool_whitelist_rule(allowed_tools: set[str]) -> Callable[[dict], PolicyResult]:
    """Create a rule that only allows specific tools.

    Args:
        allowed_tools: Set of allowed tool names

    Returns:
        Rule function
    """

    def rule(tool_call: dict) -> PolicyResult:
        tool_name = tool_call.get("name", "")
        if tool_name not in allowed_tools:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Tool '{tool_name}' not in whitelist",
            )
        return PolicyResult(decision=PolicyDecision.ALLOW)

    return rule


def create_arg_validator_rule(
    validators: dict[str, Callable[[Any], bool]],
) -> Callable[[dict], PolicyResult]:
    """Create a rule that validates tool arguments.

    Args:
        validators: Dictionary mapping arg names to validator functions

    Returns:
        Rule function
    """

    def rule(tool_call: dict) -> PolicyResult:
        args = tool_call.get("args", {})

        for arg_name, validator in validators.items():
            if arg_name in args:
                if not validator(args[arg_name]):
                    return PolicyResult(
                        decision=PolicyDecision.DENY,
                        reason=f"Argument '{arg_name}' failed validation",
                    )

        return PolicyResult(decision=PolicyDecision.ALLOW)

    return rule


def create_rate_limit_rule(max_calls: int) -> Callable[[dict], PolicyResult]:
    """Create a rule that limits number of tool calls.

    Args:
        max_calls: Maximum number of calls allowed

    Returns:
        Rule function
    """
    call_count = {"count": 0}

    def rule(tool_call: dict) -> PolicyResult:
        call_count["count"] += 1
        if call_count["count"] > max_calls:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Rate limit exceeded ({max_calls} calls)",
            )
        elif call_count["count"] == max_calls:
            return PolicyResult(
                decision=PolicyDecision.WARN,
                reason=f"Approaching rate limit ({max_calls} calls)",
            )
        return PolicyResult(decision=PolicyDecision.ALLOW)

    return rule


__all__ = [
    "PolicyDecision",
    "PolicyResult",
    "PolicyChecker",
    "create_tool_whitelist_rule",
    "create_arg_validator_rule",
    "create_rate_limit_rule",
]
