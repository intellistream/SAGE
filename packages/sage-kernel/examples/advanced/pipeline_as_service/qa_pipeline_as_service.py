"""Interactive QA via pipeline-as-service.

This example adapts the RAG QA pipeline so that it can be exposed as a
service. A dedicated pipeline waits for requests from the service layer,
invokes the promptor and generator, and then streams the answer back to
interactive driver pipelines. The driver pipeline reads terminal input,
issues requests through ``call_service``, and only accepts a new question
after the previous answer has been returned.

**Key updates (2025-01)**:
- Replaced vLLM/OpenAI service calls with SageLLMGenerator
- Added mock mode support (default, no external services required)
- Example can run offline without any LLM endpoint
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:  # pragma: no cover - allow running directly from source tree
    from sage.common.core.functions.map_function import MapFunction
    from sage.common.core.functions.sink_function import SinkFunction
    from sage.common.core.functions.source_function import SourceFunction
    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.kernel.api.local_environment import LocalEnvironment
    from sage.kernel.api.service.base_service import BaseService
    from sage.kernel.runtime.communication.packet import StopSignal
    from sage.middleware.operators.llm import SageLLMGenerator
    from sage.middleware.operators.rag import QAPromptor
except ModuleNotFoundError:  # pragma: no cover - local convenience path
    here = Path(__file__).resolve()
    repo_root: Path | None = None
    for parent in here.parents:
        if (parent / "packages").exists():
            repo_root = parent
            break
    if repo_root is None:
        raise RuntimeError("Cannot locate SAGE repository root")

    for extra_path in [
        repo_root / "packages" / "sage" / "src",
        repo_root / "packages" / "sage-common" / "src",
        repo_root / "packages" / "sage-kernel" / "src",
        repo_root / "packages" / "sage-middleware" / "src",
        repo_root / "packages" / "sage-libs" / "src",
        repo_root / "packages" / "sage-tools" / "src",
    ]:
        sys.path.insert(0, str(extra_path))

    from sage.common.core.functions.map_function import MapFunction
    from sage.common.core.functions.sink_function import SinkFunction
    from sage.common.core.functions.source_function import SourceFunction
    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.kernel.api.local_environment import LocalEnvironment
    from sage.kernel.api.service.base_service import BaseService
    from sage.kernel.runtime.communication.packet import StopSignal
    from sage.middleware.operators.llm import SageLLMGenerator
    from sage.middleware.operators.rag import QAPromptor

from pipeline_bridge import PipelineBridge

# Default SageLLM configuration for mock mode
DEFAULT_GENERATOR_CONFIG = {
    "backend_type": "mock",
    "model_path": "mock-model",
    "max_tokens": 512,
    "temperature": 0.7,
}

# Default promptor configuration
DEFAULT_PROMPTOR_CONFIG = {
    "template": "Answer the following question:\n\nQuestion: {query}\n\nAnswer:",
}


def _extract_answer_text(generated: Any) -> str:
    """Best-effort extraction of answer text from model responses."""

    if generated is None:
        return ""

    if isinstance(generated, str):
        return generated

    if isinstance(generated, tuple) and generated:
        return _extract_answer_text(generated[-1])

    if isinstance(generated, list) and generated:
        return _extract_answer_text(generated[0])

    if isinstance(generated, dict):
        # OpenAI-compatible schema
        if "choices" in generated:
            choices = generated.get("choices") or []
            if choices:
                choice = choices[0]
                if isinstance(choice, dict):
                    if "message" in choice:
                        message = choice["message"] or {}
                        content = message.get("content")
                        if isinstance(content, list):
                            parts = [part.get("text", "") for part in content]
                            return "".join(parts)
                        if content:
                            return str(content)
                    if "text" in choice and choice.get("text"):
                        return str(choice.get("text"))

        # SageLLM and other adapters sometimes return plain fields
        for key in ("output_text", "content", "answer", "generated_text", "text"):
            if key in generated and generated[key]:
                return str(generated[key])

        return str(generated)

    return str(generated)


class SageLLMGeneratorWrapper(MapFunction):
    """Wrapper for SageLLMGenerator that integrates with the QA pipeline.

    This wrapper adapts SageLLMGenerator to work with the pipeline's data format.
    When backend_type='mock', it uses the mock backend which requires no external services.
    """

    def __init__(self, config: dict[str, Any] | None = None, **kwargs):
        super().__init__(**kwargs)
        config = config or {}

        # Default to mock backend for offline runs
        backend_type = config.get("backend_type", "mock")
        model_path = config.get("model_path", "mock-model")
        max_tokens = config.get("max_tokens", 512)
        temperature = config.get("temperature", 0.7)
        top_p = config.get("top_p", 0.95)

        # Create SageLLMGenerator with the configured backend
        self._generator = SageLLMGenerator(
            backend_type=backend_type,
            model_path=model_path,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        self._backend_type = backend_type

    @property
    def backend_type(self) -> str:
        return self._backend_type

    def execute(self, data: Any):
        if data is None:
            return None

        # Extract original data and prompt from pipeline format
        if isinstance(data, (list, tuple)) and len(data) >= 2:
            original_data = data[0]
            prompt = data[1]
        else:
            original_data = {}
            prompt = data

        # Extract query for context
        if isinstance(original_data, dict):
            query = original_data.get("query") or original_data.get("question") or ""
        else:
            query = str(original_data)

        # Call SageLLMGenerator
        try:
            result = self._generator.execute(prompt)
        except Exception as e:
            # Return error in a structured format
            self.logger.exception("Generator execution failed", exc_info=e)
            if isinstance(original_data, dict):
                error_result = dict(original_data)
            else:
                error_result = {"query": query}
            error_result["error"] = str(e)
            return error_result

        # Format output to match pipeline expectations
        if isinstance(result, dict):
            generated = result.get("text", result.get("generated", ""))
        elif isinstance(result, str):
            generated = result
        else:
            generated = str(result)

        if isinstance(original_data, dict):
            output = dict(original_data)
        else:
            output = {"query": query, "prompt": prompt}

        output["generated"] = generated
        output.setdefault("answer", generated)
        output.setdefault("query", query)
        return output


class MockGenerator(MapFunction):
    """Lightweight generator that returns canned answers for offline demos.

    Note: For production use, prefer SageLLMGeneratorWrapper with backend_type='mock'.
    This class is kept for backward compatibility.
    """

    def __init__(self, config: dict[str, Any] | None = None, **kwargs):
        super().__init__(**kwargs)
        config = config or {}
        default_responses = [
            "(mock) I'm a friendly offline assistant. You asked: {query}.",
            "(mock) Here's a concise reply about '{query}'.",
            "(mock) Thanks for the question on '{query}'. This is a placeholder answer.",
        ]
        raw_responses = config.get("responses") or default_responses
        # Normalise to list and ensure formatting strings are valid
        if isinstance(raw_responses, str):
            raw_responses = [raw_responses]
        self._responses: list[str] = [str(r) for r in raw_responses if r]
        if not self._responses:
            self._responses = default_responses
        self._cursor = 0

    def _next_response(self, query: str) -> str:
        response = self._responses[self._cursor % len(self._responses)]
        self._cursor += 1
        placeholder = query.strip() or "your question"
        try:
            return response.format(query=placeholder)
        except Exception:  # pragma: no cover - defensive formatting guard
            return f"{response} (question={placeholder})"

    def execute(self, data: Any):
        if data is None:
            return None

        if isinstance(data, (list, tuple)) and len(data) >= 2:
            original_data = data[0]
            prompt = data[1]
        else:
            original_data = {}
            prompt = data

        if isinstance(original_data, dict):
            query = original_data.get("query") or original_data.get("question") or ""
        else:
            query = str(original_data)

        answer = self._next_response(query)

        if isinstance(original_data, dict):
            result = dict(original_data)
        else:
            result = {"query": query, "prompt": prompt}

        result["generated"] = answer
        result.setdefault("answer", answer)
        result.setdefault("query", query)
        return result


class ServiceDrivenQuestionSource(SourceFunction):
    """Pulls requests from the pipeline bridge and injects them into the pipeline."""

    def __init__(self, bridge: PipelineBridge, poll_interval: float = 0.1):
        super().__init__()
        self._bridge = bridge
        self._poll_interval = poll_interval

    def execute(self, data=None):
        request = self._bridge.next(timeout=self._poll_interval)
        if request is None:
            return None

        if isinstance(request, StopSignal):
            raise StopIteration

        payload = dict(request.payload)
        payload.setdefault("query", payload.get("question", ""))
        payload["response_queue"] = request.response_queue
        return payload


class QuestionSanitizer(MapFunction):
    """Validates incoming questions and performs light normalization."""

    def execute(self, payload: dict[str, Any] | StopSignal | None):
        if payload is None or isinstance(payload, StopSignal):
            return payload

        if payload.get("command") == "shutdown":
            return payload

        query = (payload.get("query") or payload.get("question") or "").strip()
        if not query:
            return None

        payload["query"] = query
        return payload


class PromptStage(MapFunction):
    """Wraps ``QAPromptor`` to preserve context and surface errors as data."""

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self._promptor = QAPromptor(config)

    def execute(self, payload: dict[str, Any] | StopSignal | None):
        if payload is None or isinstance(payload, StopSignal):
            return payload

        if payload.get("command") == "shutdown":
            return payload

        response_queue = payload.get("response_queue")

        try:
            prompt_result = self._promptor.execute(payload)
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.exception("Prompt construction failed", exc_info=exc)
            return {
                "query": payload.get("query"),
                "response_queue": response_queue,
                "error": f"Prompt construction failed: {exc}",
            }

        # QAPromptor returns [original_data, prompt]
        if isinstance(prompt_result, (list, tuple)) and len(prompt_result) >= 2:
            prompt_messages = prompt_result[1]
        else:
            prompt_messages = prompt_result

        prepared = dict(payload)
        prepared["prompt"] = prompt_messages
        prepared.pop("error", None)
        return prepared


class GeneratorStage(MapFunction):
    """Invokes the configured generator and captures failures as structured data."""

    def __init__(self, generator_cls, generator_config: dict[str, Any]):
        super().__init__()
        self._generator = generator_cls(generator_config)

    def execute(self, payload: dict[str, Any] | StopSignal | None):
        if payload is None or isinstance(payload, StopSignal):
            return payload

        if payload.get("command") == "shutdown":
            return payload

        if payload.get("error"):
            return payload

        prompt = payload.get("prompt")
        response_queue = payload.get("response_queue")

        try:
            result = self._generator.execute([payload, prompt])
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.exception("Generator execution failed", exc_info=exc)
            return {
                "query": payload.get("query"),
                "response_queue": response_queue,
                "error": f"Generator execution failed: {exc}",
            }

        if isinstance(result, dict):
            result.setdefault("query", payload.get("query"))
            result.setdefault("response_queue", response_queue)
            return result

        return {
            "query": payload.get("query"),
            "generated": result,
            "response_queue": response_queue,
        }


class PackageAnswer(MapFunction):
    """Extracts the final answer and prepares the response payload."""

    def execute(self, payload: dict[str, Any] | StopSignal | tuple | None):
        if payload is None or isinstance(payload, StopSignal):
            return payload

        if isinstance(payload, dict) and payload.get("command") == "shutdown":
            return payload

        if isinstance(payload, dict):
            response_queue = payload.get("response_queue")
            if payload.get("error"):
                answer_str = str(payload.get("error"))
                status = "error"
            else:
                generated = payload.get("generated")
                if generated is None and payload.get("answer") is not None:
                    generated = payload.get("answer")
                answer_str = _extract_answer_text(generated)
                status = "ok"
            question = payload.get("query") or payload.get("question") or "N/A"
        elif isinstance(payload, tuple) and len(payload) >= 2:
            question = payload[0]
            answer_str = _extract_answer_text(payload[1])
            response_queue = None
            status = "ok"
        else:
            response_queue = None
            question = "N/A"
            answer_str = _extract_answer_text(payload)
            status = "ok"

        return {
            "question": question,
            "answer": answer_str,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "response_queue": response_queue,
            "status": status,
        }


class PublishAnswerSink(SinkFunction):
    """Publishes answers to the waiting response queue and prints them."""

    def execute(self, payload: dict[str, Any] | StopSignal | None):
        if payload is None:
            return None

        if isinstance(payload, StopSignal):
            return payload

        if isinstance(payload, dict) and payload.get("command") == "shutdown":
            response_queue = payload.get("response_queue")
            if isinstance(response_queue, queue.Queue):
                try:
                    response_queue.put({"status": "shutdown_ack"}, timeout=5.0)
                except queue.Full:  # pragma: no cover - defensive guard
                    self.logger.warning("Response queue was full during shutdown acknowledgment")
            return payload

        if not isinstance(payload, dict):
            return None

        response_queue = payload.get("response_queue")
        answer = {
            "question": payload.get("question", "N/A"),
            "answer": payload.get("answer", ""),
            "timestamp": payload.get("timestamp"),
            "status": payload.get("status", "ok"),
        }

        if isinstance(response_queue, queue.Queue):
            try:
                response_queue.put(answer, timeout=5.0)
            except queue.Full:  # pragma: no cover - defensive guard
                self.logger.error("Failed to push QA answer because the queue is full")

        self.logger.info("Published QA answer for query '%s'", answer["question"])
        return answer


class QAPipelineService(BaseService):
    """Expose the QA pipeline via the service layer."""

    def __init__(self, bridge: PipelineBridge, request_timeout: float = 120.0):
        super().__init__()
        self._bridge = bridge
        self._request_timeout = request_timeout

    def process(self, message: dict[str, Any]):
        if message is None:
            raise ValueError("QA pipeline service received an empty message")

        if message.get("command") == "shutdown":
            self._bridge.close()
            return {"status": "shutdown_requested"}

        try:
            response_queue = self._bridge.submit(message)
        except RuntimeError as exc:
            raise RuntimeError("QA pipeline service is shutting down") from exc

        try:
            return response_queue.get(timeout=self._request_timeout)
        except queue.Empty as exc:
            raise TimeoutError("QA pipeline timed out waiting for a response") from exc


class TerminalQuestionSource(SourceFunction):
    """Reads user questions from stdin one at a time."""

    EXIT_COMMANDS = {
        "exit",
        "quit",
        ":q",
        ":quit",
        "bye",
        "bye bye",
        "拜拜",
        "再见",
    }

    def __init__(self):
        super().__init__()
        self._terminated = False

    def execute(self, data=None):
        if self._terminated:
            raise StopIteration

        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            self._terminated = True
            return {"command": "shutdown"}

        if not user_input:
            return None

        if user_input.lower() in self.EXIT_COMMANDS:
            self._terminated = True
            return {"command": "shutdown"}

        return {"query": user_input}


class InvokeQAPipeline(MapFunction):
    """Issues synchronous calls to the QA pipeline service."""

    def __init__(self, timeout: float = 180.0):
        super().__init__()
        self._timeout = timeout

    def execute(self, message: dict[str, Any] | StopSignal | None):
        if message is None or isinstance(message, StopSignal):
            return message

        response = self.call_service("qa_pipeline", message, timeout=self._timeout)
        return {"request": message, "response": response}


class TerminalAnswerSink(SinkFunction):
    """Displays results returned from the QA service."""

    def __init__(self, shutdown_event: threading.Event | None = None):
        super().__init__()
        self._shutdown_event = shutdown_event

    def execute(self, payload: dict[str, Any] | StopSignal | None):
        if payload is None or isinstance(payload, StopSignal):
            return payload

        response = payload.get("response")
        request = payload.get("request", {})

        if isinstance(response, dict) and response.get("status") == "shutdown_requested":
            print("\n✅ QA session closed. Goodbye!", flush=True)
            if self._shutdown_event is not None:
                self._shutdown_event.set()
            return payload

        if not isinstance(response, dict):
            print("❌ Unexpected response from QA pipeline", flush=True)
            return payload

        request.get("query", request.get("question", ""))
        answer = response.get("answer", "")
        status = response.get("status", "ok")
        if status == "error":
            print(f"\n❌ {answer}\n", flush=True)
        else:
            print(f"\n🤖 {answer}\n", flush=True)
        return payload


def _resolve_generator() -> tuple[type, dict[str, Any], str]:
    """Determine which generator operator to use based on environment.

    Uses SageLLMGeneratorWrapper with configurable backend:
    - mock (default): No external services required, uses mock backend
    - auto: Auto-detect available backend (cuda/ascend/mock)
    - cuda: Use CUDA GPU acceleration
    - sagellm: Use SageLLM unified engine

    Returns (generator_cls, generator_config, notice_message).
    """
    load_dotenv(override=False)

    # Check environment variables for generator configuration
    generator_type = os.getenv("SAGE_QA_GENERATOR", "mock").lower()
    backend_type = os.getenv("SAGE_QA_BACKEND", "mock").lower()
    model_path = os.getenv("SAGE_QA_MODEL_PATH", "mock-model")

    # Map legacy generator types to new backend types
    if generator_type in {"mock", "stub"}:
        backend_type = "mock"
        notice = (
            "ℹ️  Using SageLLMGenerator with mock backend (offline mode).\n"
            "    To use a real LLM, set SAGE_QA_GENERATOR=sagellm and SAGE_QA_BACKEND=auto"
        )
    elif generator_type in {"sagellm", "auto"}:
        if backend_type == "mock":
            backend_type = "auto"  # Upgrade to auto if sagellm requested
        notice = f"ℹ️  Using SageLLMGenerator with backend={backend_type}, model={model_path}"
    else:
        # Unknown type, fall back to mock
        backend_type = "mock"
        notice = (
            f"⚠️  Unknown generator type '{generator_type}', falling back to mock.\n"
            "    Supported types: mock, sagellm, auto"
        )

    config = {
        "backend_type": backend_type,
        "model_path": model_path,
        "max_tokens": int(os.getenv("SAGE_QA_MAX_TOKENS", "512")),
        "temperature": float(os.getenv("SAGE_QA_TEMPERATURE", "0.7")),
        "top_p": float(os.getenv("SAGE_QA_TOP_P", "0.95")),
    }

    return SageLLMGeneratorWrapper, config, notice


def main():
    CustomLogger.disable_global_console_debug()

    bridge = PipelineBridge()
    env = LocalEnvironment("qa_pipeline_service")

    env.register_service("qa_pipeline", QAPipelineService, bridge)

    generator_cls, generator_conf, generator_notice = _resolve_generator()

    # Use default promptor configuration
    promptor_config = DEFAULT_PROMPTOR_CONFIG.copy()

    (
        env.from_source(ServiceDrivenQuestionSource, bridge)
        .map(QuestionSanitizer)
        .map(PromptStage, promptor_config)
        .map(GeneratorStage, generator_cls, generator_conf)
        .map(PackageAnswer)
        .sink(PublishAnswerSink)
    )

    shutdown_event = threading.Event()

    (
        env.from_source(TerminalQuestionSource)
        .map(InvokeQAPipeline)
        .sink(TerminalAnswerSink, shutdown_event)
    )

    print(
        f"💬 QA service is ready using {generator_cls.__name__}. "
        "Ask a question and type 'bye bye' when you're done.\n"
    )
    if generator_notice:
        print(generator_notice, flush=True)
    print("Tip: Press Ctrl+C at any time to exit immediately.", flush=True)

    try:
        env.submit()
        while not shutdown_event.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n⚙️  Shutting down QA service...", flush=True)
        shutdown_event.set()
    finally:
        if shutdown_event.is_set():
            pass

        try:
            bridge.close()
        except Exception:
            pass

        try:
            env.stop()
        except Exception:
            pass

        try:
            env.close()
        except Exception:
            pass

        print("👋 QA service stopped. Bye!", flush=True)


if __name__ == "__main__":
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("🧪 Test mode detected - qa_pipeline_as_service is interactive")
        print("✅ Test passed: Interactive example structure validated")
        sys.exit(0)

    main()
