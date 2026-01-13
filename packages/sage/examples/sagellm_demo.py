#!/usr/bin/env python3
"""Minimal example: Use isagellm for LLM inference in SAGE.

Requirements:
    pip install "isagellm[cuda]" torch transformers accelerate

Usage:
    # Mock mode (no GPU required)
    python sagellm_demo.py --mock

    # Real CUDA inference
    python sagellm_demo.py --model TinyLlama/TinyLlama-1.1B-Chat-v1.0

    # Streaming mode
    python sagellm_demo.py --model TinyLlama/TinyLlama-1.1B-Chat-v1.0 --stream
"""

from __future__ import annotations

import argparse
import asyncio


async def run_mock_demo() -> None:
    """Run inference with MockEngine (no GPU)."""
    from sagellm_backend.engine.mock import MockEngine, MockEngineConfig
    from sagellm_protocol.types import Request

    print("=== MockEngine Demo ===")
    config = MockEngineConfig(engine_id="mock-001")
    engine = MockEngine(config)
    await engine.start()

    request = Request(
        request_id="demo-001",
        trace_id="trace-001",
        model="mock-model",
        prompt="What is SAGE?",
        max_tokens=64,
        stream=False,
    )

    response = await engine.execute(request)
    print(f"Prompt: {request.prompt}")
    print(f"Response: {response.output_text}")
    print(f"Metrics: TTFT={response.metrics.ttft_ms}ms, TBT={response.metrics.tbt_ms}ms")

    await engine.stop()


async def run_cuda_demo(model_path: str, stream: bool = False) -> None:
    """Run inference with HFCudaEngine (real GPU)."""
    from sagellm_backend.engine.hf_cuda import HFCudaEngine, HFCudaEngineConfig
    from sagellm_protocol.types import Request

    print(f"=== HFCudaEngine Demo (model={model_path}) ===")

    # All required fields explicitly set (fail-fast design)
    config = HFCudaEngineConfig(
        engine_id="hf-001",
        model_path=model_path,
        device="cuda",
        device_map="auto",
        dtype="float16",
        load_in_8bit=False,
        load_in_4bit=False,
        trust_remote_code=False,
        max_new_tokens=128,
    )
    engine = HFCudaEngine(config)

    print("Loading model...")
    await engine.start()
    print("Model loaded!")

    request = Request(
        request_id="demo-001",
        trace_id="trace-001",
        model=model_path,
        prompt="<|user|>\nWhat is SAGE (Streaming-Augmented Generative Execution)?\n<|assistant|>\n",
        max_tokens=128,
        stream=stream,
    )

    print(f"\nPrompt: {request.prompt}")

    if stream:
        print("\nStreaming response:", end="", flush=True)
        async for event in engine.stream(request):
            # StreamEventDelta has 'chunk' field (not 'delta')
            if hasattr(event, "chunk") and event.chunk:
                print(event.chunk, end="", flush=True)
            elif hasattr(event, "metrics"):
                print(
                    f"\n\nMetrics: TTFT={event.metrics.ttft_ms:.1f}ms, "
                    f"TBT={event.metrics.tbt_ms:.1f}ms, "
                    f"Throughput={event.metrics.throughput_tps:.1f} tps"
                )
    else:
        response = await engine.execute(request)
        print(f"\nResponse: {response.output_text}")
        print(
            f"\nMetrics: TTFT={response.metrics.ttft_ms:.1f}ms, "
            f"TBT={response.metrics.tbt_ms:.1f}ms, "
            f"Throughput={response.metrics.throughput_tps:.1f} tps"
        )

    await engine.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="sageLLM inference demo for SAGE")
    parser.add_argument("--mock", action="store_true", help="Use MockEngine (no GPU)")
    parser.add_argument("--model", type=str, default="", help="HuggingFace model path")
    parser.add_argument("--stream", action="store_true", help="Use streaming mode")
    args = parser.parse_args()

    if args.mock:
        asyncio.run(run_mock_demo())
    elif args.model:
        asyncio.run(run_cuda_demo(args.model, args.stream))
    else:
        print("Usage:")
        print("  Mock mode:  python sagellm_demo.py --mock")
        print("  CUDA mode:  python sagellm_demo.py --model TinyLlama/TinyLlama-1.1B-Chat-v1.0")
        print("  Streaming:  python sagellm_demo.py --model ... --stream")


if __name__ == "__main__":
    main()
