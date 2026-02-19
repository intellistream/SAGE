"""
sage.platform.runtime.adapters - Runtime Backend Adapters

Layer: L2 (sage-platform)

This package contains concrete adapter implementations that wrap external
runtime backends (e.g. sageFlownet) so they satisfy the
``RuntimeBackendProtocol`` defined in ``sage.platform.runtime.protocol``.

Available adapters
------------------
- ``flownet_adapter.FlownetRuntimeAdapter`` – wraps sageFlownet runtime.
  Requires ``isage-flow`` (sageFlownet) to be installed.
"""
