"""Native filtered branches rejoin once without entering the rejected path."""
from sage.runtime.execution_observation import ExecutionObserver
from sage.runtime.flownet import (
    bootstrap_runtime,
    build_runtime_client,
    flow,
    stateless,
)


@stateless(uri="stateless://test/choose-booking", namespace="test")
def choose_booking(value):
    return value["book"]


@stateless(uri="stateless://test/choose-answer", namespace="test")
def choose_answer(value):
    return not value["book"]


@stateless(uri="stateless://test/booking-effect", namespace="test")
def booking_effect(value):
    return {**value, "effect": True}


@stateless(uri="stateless://test/render-choice", namespace="test")
def render_choice(value):
    return value


@flow(uri="flow://test/exclusive-merge", namespace="test")
def exclusive(init_stream):
    return init_stream.filter(choose_booking).map(booking_effect, operator_key="booking").connect(
        init_stream.filter(choose_answer)).map(render_choice, operator_key="render")


@flow(uri="flow://test/composed-merge", namespace="test")
def composed(init_stream):
    first = init_stream.map(render_choice)
    pair = init_stream.map(render_choice).connect(init_stream.map(render_choice))
    second_pair = init_stream.map(render_choice).connect(init_stream.map(render_choice))
    return first.connect(pair).connect(second_pair).filter(choose_answer).map(render_choice)


def test_single_connected_and_connected_connected_preserve_every_upstream():
    runtime = bootstrap_runtime(node_mode="local")
    endpoint = None
    try:
        client = build_runtime_client(owner="test", runtime_host=runtime.runtime_host)
        endpoint = composed.bind("composed-in", "composed-out").endpoint(client=client, reuse_existing=False)
        assert endpoint.call({"book": False}, timeout=5) == [{"book": False}] * 5
        assert endpoint.call({"book": True}, timeout=5) == []
        assert endpoint._requests == {}
    finally:
        if endpoint is not None:
            endpoint.close()
        runtime.shutdown()


def test_filtered_native_paths_rejoin_once_and_reuse_graph():
    runtime = bootstrap_runtime(node_mode="local")
    endpoint = None
    try:
        client = build_runtime_client(owner="test", runtime_host=runtime.runtime_host)
        endpoint = exclusive.bind("exclusive-in", "exclusive-out").endpoint(client=client, reuse_existing=False)
        for booking in (False, True, False):
            events = []
            with ExecutionObserver(events.append).bind():
                result = endpoint.call({"book": booking}, timeout=5)
            assert result == [{"book": booking, **({"effect": True} if booking else {})}]
            completed = [e.operator_key for e in events if e.state == "completed"]
            assert completed.count("booking") == int(booking)
            assert completed.count("render") == 1
        assert endpoint._requests == {}
    finally:
        if endpoint is not None:
            endpoint.close()
        runtime.shutdown()
