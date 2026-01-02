# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""GPU resource monitoring and reservation utilities for the Control Plane."""

from __future__ import annotations

import logging
import os
import re
import threading
from typing import TypedDict

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import pynvml  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    pynvml = None  # type: ignore[misc]

if pynvml:  # pragma: no cover - guarded by import
    NvmlError = pynvml.NVMLError  # type: ignore[attr-defined]
else:

    class NvmlError(Exception):
        """Fallback NVML error when pynvml is not present."""

        pass


_BYTES_IN_GB = 1024**3
_DEFAULT_OVERHEAD_GB = 4.0
_ENV_DISABLE_NVML = "SAGE_DISABLE_NVML"
_ENV_MOCK_GPU_COUNT = "SAGE_GPU_MOCK_COUNT"
_ENV_MOCK_GPU_MEMORY = "SAGE_GPU_MOCK_MEMORY_GB"
_MODEL_SIZE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:b|B)")
_MODEL_HINTS_GB: dict[str, float] = {
    "qwen2.5-0.5b": 6.0,
    "qwen2.5-1.5b": 10.0,
    "qwen2.5-7b": 18.0,
    "qwen2.5-14b": 36.0,
    "llama3.1-8b": 20.0,
    "llama3.1-70b": 160.0,
    "mixtral-8x7b": 64.0,
}


class GPUStatus(TypedDict, total=False):
    """Typed dictionary representing a single GPU status snapshot."""

    index: int
    name: str
    memory_total_gb: float
    memory_used_gb: float
    memory_free_gb: float
    memory_reserved_gb: float
    utilization: float
    is_mock: bool


class GPUResourceManager:
    """Monitor GPUs via NVML and track logical reservations for scheduling."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._allocations: dict[int, float] = {}
        self._nvml_available = False
        self._gpu_count = 0
        self._mock_mode = False
        self._mock_gpu_count = max(0, int(os.getenv(_ENV_MOCK_GPU_COUNT, "0")))
        self._mock_gpu_memory_gb = max(1.0, float(os.getenv(_ENV_MOCK_GPU_MEMORY, "24")))

        if os.getenv(_ENV_DISABLE_NVML, "").lower() in {"1", "true", "yes"}:
            self._enable_mock_mode("NVML explicitly disabled via environment")
            return

        if pynvml is None:
            self._enable_mock_mode("pynvml not available - running in CPU/mock mode")
            return

        try:
            pynvml.nvmlInit()  # type: ignore[union-attr]
            self._nvml_available = True
            self._gpu_count = pynvml.nvmlDeviceGetCount()  # type: ignore[union-attr]
            logger.info("NVML initialized with %d GPU(s)", self._gpu_count)
        except NvmlError as exc:  # pragma: no cover - depends on driver state
            logger.warning("Failed to initialize NVML (%s). Falling back to mock mode.", exc)
            self._enable_mock_mode(str(exc))

    def close(self) -> None:
        """Release NVML handle when available."""
        if not self._nvml_available or pynvml is None:
            return
        try:  # pragma: no cover - destructor path
            pynvml.nvmlShutdown()  # type: ignore[union-attr]
        except NvmlError as exc:
            logger.debug("nvmlShutdown failed: %s", exc)
        finally:
            self._nvml_available = False

    def __del__(self) -> None:  # pragma: no cover - best-effort cleanup
        try:
            self.close()
        except Exception:
            logger.debug(
                "Suppressing exception raised during GPUResourceManager cleanup",
                exc_info=True,
            )

    def get_system_status(self) -> list[GPUStatus]:
        """Return the status of all known (or mocked) GPU devices."""
        with self._lock:
            return self._snapshot_status_locked()

    def check_resource_availability(self, required_memory_gb: float, count: int = 1) -> list[int]:
        """Return GPU indices that currently satisfy the requested free memory."""
        if required_memory_gb <= 0 or count <= 0:
            return []

        statuses = self.get_system_status()
        available: list[int] = []

        for status in statuses:
            idx = status.get("index", -1)
            if idx < 0:
                continue
            free_gb = status.get("memory_free_gb", 0.0)
            if free_gb >= required_memory_gb:
                available.append(idx)
                if len(available) >= count:
                    break
        return available

    def allocate_resources(self, required_memory_gb: float, count: int = 1) -> list[int]:
        """Reserve GPU memory logically so schedulers can avoid double-booking."""
        if required_memory_gb <= 0 or count <= 0:
            return []

        with self._lock:
            statuses = self._snapshot_status_locked()
            candidate_ids = self._filter_available(statuses, required_memory_gb, count)
            if len(candidate_ids) < count:
                raise RuntimeError(
                    f"Insufficient GPU memory: requested {required_memory_gb:.2f} GB on "
                    f"{count} GPU(s), but only {len(candidate_ids)} available"
                )

            for gpu_id in candidate_ids:
                self._allocations[gpu_id] = self._allocations.get(gpu_id, 0.0) + required_memory_gb
                logger.info("Reserved %.2f GB on GPU %d", required_memory_gb, gpu_id)

            return candidate_ids

    def release_resources(self, gpu_ids: list[int], memory_gb: float) -> None:
        """Release previously reserved GPU memory."""
        if memory_gb <= 0 or not gpu_ids:
            return

        with self._lock:
            for gpu_id in gpu_ids:
                current = self._allocations.get(gpu_id, 0.0)
                if current == 0:
                    continue
                new_value = max(0.0, current - memory_gb)
                self._allocations[gpu_id] = new_value
                if new_value == 0.0:
                    self._allocations.pop(gpu_id, None)
                logger.info("Released %.2f GB on GPU %d", memory_gb, gpu_id)

    def estimate_model_memory(self, model_name: str, tensor_parallel_size: int = 1) -> float:
        """Estimate per-GPU memory consumption for a model using a heuristic."""
        normalized = model_name.lower()
        base_gb = self._lookup_model_hint(normalized)
        per_gpu = base_gb / max(1, tensor_parallel_size)
        total = per_gpu + _DEFAULT_OVERHEAD_GB
        return round(max(total, _DEFAULT_OVERHEAD_GB), 2)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _snapshot_status_locked(self) -> list[GPUStatus]:
        if self._nvml_available and pynvml is not None:
            return self._collect_nvml_status_locked()
        return self._collect_mock_status_locked()

    def _collect_nvml_status_locked(self) -> list[GPUStatus]:
        statuses: list[GPUStatus] = []
        for idx in range(self._gpu_count):
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(idx)  # type: ignore[union-attr]
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)  # type: ignore[union-attr]
                util_struct = pynvml.nvmlDeviceGetUtilizationRates(handle)  # type: ignore[union-attr]
                name = pynvml.nvmlDeviceGetName(handle)  # type: ignore[union-attr]
            except NvmlError as exc:
                logger.debug("Failed to query GPU %d: %s", idx, exc)
                statuses.append(
                    GPUStatus(
                        index=idx,
                        name=f"GPU-{idx}",
                        memory_total_gb=0.0,
                        memory_used_gb=0.0,
                        memory_free_gb=0.0,
                        memory_reserved_gb=self._allocations.get(idx, 0.0),
                        utilization=0.0,
                        is_mock=False,
                    )
                )
                continue

            total_gb = mem_info.total / _BYTES_IN_GB
            used_gb = mem_info.used / _BYTES_IN_GB
            reserved_gb = self._allocations.get(idx, 0.0)
            free_gb = max(total_gb - used_gb - reserved_gb, 0.0)

            statuses.append(
                GPUStatus(
                    index=idx,
                    name=name.decode("utf-8") if isinstance(name, bytes) else str(name),
                    memory_total_gb=round(total_gb, 2),
                    memory_used_gb=round(used_gb, 2),
                    memory_free_gb=round(free_gb, 2),
                    memory_reserved_gb=round(reserved_gb, 2),
                    utilization=float(getattr(util_struct, "gpu", 0.0)),
                    is_mock=False,
                )
            )
        return statuses

    def _collect_mock_status_locked(self) -> list[GPUStatus]:
        statuses: list[GPUStatus] = []
        gpu_count = self._mock_gpu_count
        if gpu_count <= 0:
            statuses.append(
                GPUStatus(
                    index=-1,
                    name="CPU",
                    memory_total_gb=0.0,
                    memory_used_gb=0.0,
                    memory_free_gb=0.0,
                    memory_reserved_gb=0.0,
                    utilization=0.0,
                    is_mock=True,
                )
            )
            return statuses

        for idx in range(gpu_count):
            reserved_gb = self._allocations.get(idx, 0.0)
            free_gb = max(self._mock_gpu_memory_gb - reserved_gb, 0.0)
            statuses.append(
                GPUStatus(
                    index=idx,
                    name=f"Mock GPU {idx}",
                    memory_total_gb=self._mock_gpu_memory_gb,
                    memory_used_gb=max(self._mock_gpu_memory_gb - free_gb, 0.0),
                    memory_free_gb=free_gb,
                    memory_reserved_gb=reserved_gb,
                    utilization=0.0,
                    is_mock=True,
                )
            )
        return statuses

    def _enable_mock_mode(self, reason: str) -> None:
        self._mock_mode = True
        logger.info("GPUResourceManager running in mock mode: %s", reason)

    def _filter_available(
        self,
        statuses: list[GPUStatus],
        required_memory_gb: float,
        count: int,
    ) -> list[int]:
        available: list[int] = []
        for status in statuses:
            idx = status.get("index", -1)
            if idx < 0:
                continue
            free_gb = status.get("memory_free_gb", 0.0)
            if free_gb >= required_memory_gb:
                available.append(idx)
                if len(available) >= count:
                    break
        return available

    def _lookup_model_hint(self, normalized_model_name: str) -> float:
        for hint_key, hint_value in _MODEL_HINTS_GB.items():
            if hint_key in normalized_model_name:
                return hint_value
        match = _MODEL_SIZE_PATTERN.search(normalized_model_name)
        if match:
            billions = float(match.group(1))
            return max(4.0, billions * 2.5)
        return 16.0


__all__ = ["GPUResourceManager", "GPUStatus"]
