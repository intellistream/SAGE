from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from sage.runtime.flownet.api.declarations import FlowDeclaration


def _declaration() -> FlowDeclaration:
    def demo_flow(stream, stage_name: str):
        assert stage_name == "answer"
        return stream

    return FlowDeclaration(
        target=demo_flow,
        uri="sage://tests/reusable-flow",
        scheduler={},
        resources={},
        policies={},
        metadata={},
        dsl_name="demo_flow",
    )


def _compile(declaration: FlowDeclaration):
    return declaration.compile_reusable(
        structural_args=("answer",),
        schema={"input": "Question", "output": "Answer"},
        policy_version="v1",
        capabilities={"model": "chat"},
        retrieval_contract={"kind": "public"},
        resource_class="interactive",
    )


def test_real_flow_program_compile_is_reused() -> None:
    declaration = _declaration()
    first = _compile(declaration)
    second = _compile(declaration)

    assert first is second
    assert first.artifact is second.artifact
    assert declaration.compiled_plan_cache_stats().compiles == 1
    assert declaration.compiled_plan_cache_stats().hits == 1


def test_concurrent_real_flow_compile_is_single_flight() -> None:
    declaration = _declaration()
    with ThreadPoolExecutor(max_workers=20) as pool:
        plans = list(pool.map(lambda _: _compile(declaration), range(20)))

    assert len({id(plan.artifact) for plan in plans}) == 1
    assert declaration.compiled_plan_cache_stats().compiles == 1


def test_runtime_bindings_do_not_change_or_mutate_static_plan() -> None:
    declaration = _declaration()
    first = declaration.bind_reusable(
        "answer",
        in_="request-input-1",
        out="request-output-1",
        schema={"input": "Question", "output": "Answer"},
        policy_version="v1",
        capabilities={"model": "chat"},
        retrieval_contract={"kind": "public"},
        resource_class="interactive",
    )
    second = declaration.bind_reusable(
        "answer",
        in_="request-input-2",
        out="request-output-2",
        schema={"input": "Question", "output": "Answer"},
        policy_version="v1",
        capabilities={"model": "chat"},
        retrieval_contract={"kind": "public"},
        resource_class="interactive",
    )

    assert first.flow_program is second.flow_program
    assert first.compiled_plan_fingerprint == second.compiled_plan_fingerprint
    assert first._resolve_io_topics() == ("request-input-1", "request-output-1")
    assert second._resolve_io_topics() == ("request-input-2", "request-output-2")
