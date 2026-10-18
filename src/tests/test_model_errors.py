import pytest
from sage.runtime.model_errors import model_request_rejection


@pytest.mark.parametrize(
    "status,body,code",
    [
        (
            400,
            {
                "error": {
                    "message": "No backend can safely fit the estimated 158759-token request context"
                }
            },
            "prompt_capacity",
        ),
        (400, {"error": {"code": "context_length_exceeded"}}, "prompt_capacity"),
        (
            400,
            {"error": {"message": "This model's maximum context length is 32768 tokens"}},
            "prompt_capacity",
        ),
        (413, None, "prompt_capacity"),
        (400, {"error": {"message": "private prompt secret"}}, "model_request_invalid"),
        (422, [], "model_request_invalid"),
        (401, {"error": "secret"}, "model_access_denied"),
        (403, None, "model_access_denied"),
        (400, {"error": {"code": [], "message": {}}}, "model_request_invalid"),
    ],
)
def test_terminal_codes_never_retain_provider_body(status, body, code):
    error = model_request_rejection(status, body)
    assert str(error) == error.code == code
    assert "secret" not in repr(error)


@pytest.mark.parametrize("status", [200, 408, 409, 429, 500, 502, 503, 504])
def test_transient_status_never_becomes_terminal_from_message(status):
    assert model_request_rejection(status, {"error": {"code": "context_length_exceeded"}}) is None
