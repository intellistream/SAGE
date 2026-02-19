"""
sage.platform.runtime - Runtime Protocol Contracts (L2)

Layer: L2 (sage-platform)

This sub-package provides the **abstract interface layer** between SAGE L3
(sage-kernel) and the concrete distributed runtime backend (sageFlownet by
default).  No runtime implementation lives here – only ABCs and Protocol
types.

Per the Flownet→SAGE migration boundary (intellistream/SAGE#1430):
- SAGE L2 (this package) owns: protocol/ABC declarations only.
- sageFlownet keeps: runtime core implementation, transport, cluster internals.

Quick import
------------
::

    from sage.platform.runtime import (
        RuntimeBackendProtocol,
        ActorHandleProtocol,
        MethodRefProtocol,
        MethodCallFuture,
        FlowRunHandleProtocol,
        NodeInfoProtocol,
    )

To get the Flownet adapter (requires sageFlownet installed)::

    from sage.platform.runtime.adapters.flownet_adapter import FlownetRuntimeAdapter

Actor reference contract usage
-------------------------------
::

    actor = backend.create(MyService)

    # Synchronous
    result = actor.get_method("process").call(payload)

    # Asynchronous (non-blocking)
    future: MethodCallFuture = actor.get_method("process").async_call(payload)
    result = future.result(timeout=30.0)

    # Cancellation
    cancelled = actor.get_method("process").cancel()
    cancelled = actor.cancel()  # actor-level teardown

References
----------
- migration boundary:          intellistream/SAGE#1430
- runtime protocol (Issue 4):  intellistream/SAGE#1433
- actor ref interfaces (Issue 7): intellistream/SAGE#1436
"""

from sage.platform.runtime.protocol import (
    ActorHandleProtocol,
    FlowRunHandleProtocol,
    MethodCallFuture,
    MethodRefProtocol,
    NodeInfoProtocol,
    RuntimeBackendProtocol,
)

__all__ = [
    "RuntimeBackendProtocol",
    "ActorHandleProtocol",
    "MethodRefProtocol",
    "MethodCallFuture",
    "FlowRunHandleProtocol",
    "NodeInfoProtocol",
]
