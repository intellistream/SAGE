# Safety & Guardrails

**Location**: `sage.libs.safety`\
**Layer**: L3 (Algorithm Library)\
**Dependencies**: Pure Python (regex-based)

## Overview

This module provides lightweight safety checks and content filtering utilities. These are simple,
regex-based filters with no heavy service coupling or ML model dependencies.

## Components

### 1. Content Filtering (`content_filter.py`)

Pattern-based content filtering:

- **ContentFilter**: Regex pattern-based filter
- **Predefined Patterns**: Profanity, personal attacks
- **Filter Methods**: Detection and replacement

**Usage**:

```python
from sage.libs.safety.content_filter import ContentFilter, create_profanity_filter

# Custom filter
filter = ContentFilter([r"\b(banned|word)\b"])
has_violation, matches = filter.contains_violation("This is a banned word")

# Predefined filters
profanity_filter = create_profanity_filter()
clean_text = profanity_filter.filter_text("This is bad shit", replacement="[FILTERED]")
```

### 2. PII Scrubbing (`pii_scrubber.py`)

Simple PII (Personally Identifiable Information) detection and scrubbing:

- **PIIScrubber**: Multi-pattern PII detector
- **Predefined Patterns**: Email, phone, SSN, credit card, IP address
- **Quick Helpers**: `scrub_emails`, `scrub_phone_numbers`

**Usage**:

```python
from sage.libs.safety.pii_scrubber import PIIScrubber, scrub_emails

# Full scrubber
scrubber = PIIScrubber()
pii_detected = scrubber.detect_pii("Contact: john@example.com, 555-1234")
clean_text = scrubber.scrub("Contact: john@example.com")

# Quick helpers
text = "Email me at john@example.com"
scrubbed = scrub_emails(text, replacement="[EMAIL]")
```

### 3. Policy Checking (`policy_check.py`)

Tool call policy validation:

- **PolicyChecker**: Rule-based policy enforcement
- **PolicyDecision**: ALLOW, DENY, WARN
- **Predefined Rules**: Whitelist, argument validation, rate limiting

**Usage**:

```python
from sage.libs.safety.policy_check import (
    PolicyChecker,
    create_tool_whitelist_rule,
    create_rate_limit_rule,
)

# Create checker with rules
checker = PolicyChecker()
checker.add_rule("whitelist", create_tool_whitelist_rule({"search", "calculator"}))
checker.add_rule("rate_limit", create_rate_limit_rule(max_calls=10))

# Check tool call
tool_call = {"name": "search", "args": {"query": "test"}}
result = checker.check(tool_call)

if result.decision == PolicyDecision.DENY:
    raise PermissionError(result.reason)
```

## Design Principles

1. **Lightweight**: Regex-based, no ML models
1. **No Service Coupling**: Standalone utilities
1. **Composable**: Filters and rules can be combined
1. **Fail Fast**: Explicit policy decisions
1. **Extensible**: Easy to add custom patterns/rules

## Used By

- `sage.libs.agentic.agents.runtime` - Tool call validation
- `sage.llm.gateway` - Request filtering
- Custom applications requiring content safety

## Limitations

These are **simple, rule-based utilities** with known limitations:

1. **Content Filtering**: Regex-based, prone to false positives/negatives
1. **PII Scrubbing**: Pattern matching only, no semantic understanding
1. **Policy Checking**: Rule-based, not ML-driven

**For production-grade safety**, consider:

- ML-based content moderation (Azure Content Safety, Perspective API)
- NER-based PII detection (spaCy, AWS Comprehend)
- Context-aware policy engines

## Future Enhancements

- Integration hooks for ML-based safety services
- More sophisticated pattern matching (context-aware)
- Safety scoring (confidence levels)
- Audit logging helpers
- Content classification (hate speech, toxicity levels)

## Migration Notes

This module consolidates safety utilities previously scattered across:

- Adhoc content filters in gateway
- Tool validation logic in agent runtime
- Various regex patterns in different modules

All safety checks now use consistent `PolicyResult` interface.

## Example: Comprehensive Safety Pipeline

```python
from sage.libs.safety import content_filter, pii_scrubber, policy_check

# Content filtering
profanity_filter = content_filter.create_profanity_filter()
has_profanity, _ = profanity_filter.contains_violation(user_input)

# PII scrubbing
scrubber = pii_scrubber.PIIScrubber()
clean_input = scrubber.scrub(user_input)

# Policy checking
checker = policy_check.PolicyChecker()
checker.add_rule("whitelist", policy_check.create_tool_whitelist_rule(allowed_tools))

result = checker.check(tool_call)
if result.decision == policy_check.PolicyDecision.DENY:
    raise PermissionError(f"Tool call denied: {result.reason}")
```
