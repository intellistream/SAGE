"""Transport-independent classification of deterministic model request failures."""

import re


class ModelRequestRejected(RuntimeError):
    """Safe terminal code; never persist provider bodies, prompts or credentials."""

    def __init__(self, code):
        if code not in {"prompt_capacity", "model_request_invalid", "model_access_denied"}:
            raise ValueError("invalid_model_rejection_code")
        self.code = code
        super().__init__(code)


def model_request_rejection(status, body):
    """Return a typed terminal error, or None for retryable/unknown transport errors."""
    if status not in {400, 401, 403, 413, 422}:
        return None
    error = body.get("error", {}) if isinstance(body, dict) else {}
    code = error.get("code") if isinstance(error, dict) else None
    message = error.get("message", "") if isinstance(error, dict) else ""
    capacity = status == 413 or (
        isinstance(code, str) and code in {"context_length_exceeded", "max_context_length_exceeded"}
    )
    if isinstance(message, str):
        capacity = capacity or bool(
            re.search(
                r"maximum context length|context length (?:exceeded|is too long)|"
                r"No backend can safely fit the estimated \d+-token request context",
                message,
                re.I,
            )
        )
    if capacity and status in {400, 413, 422}:
        return ModelRequestRejected("prompt_capacity")
    return ModelRequestRejected(
        "model_access_denied" if status in {401, 403} else "model_request_invalid"
    )
