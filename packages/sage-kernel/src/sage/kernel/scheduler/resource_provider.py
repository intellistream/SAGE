"""
ResourceProvider - 抽象资源提供接口

为 NodeSelector 解耦资源数据来源，支持多种后端：
  - LocalSnapshotProvider  : 本地单节点快照（默认，无需外部服务）
  - FlownetRuntimeProvider : 通过 Flownet ClusterView 获取集群资源（分布式模式）

使用方式::

    # 默认（本地单节点）
    provider = LocalSnapshotProvider()

    # Flownet 分布式
    from sage.flownet.runtime.cluster_view import ClusterView
    provider = FlownetRuntimeProvider(cluster_view)

    nodes = provider.get_nodes()
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from sage.kernel.scheduler.node_selector import NodeResources

if TYPE_CHECKING:
    # 避免循环导入，仅在类型检查时引用 FlownetClusterView
    pass

__all__ = [
    "ResourceProvider",
    "LocalSnapshotProvider",
    "FlownetRuntimeProvider",
]

# ---------------------------------------------------------------------------
# 抽象接口
# ---------------------------------------------------------------------------


class ResourceProvider(ABC):
    """
    资源提供者抽象接口。

    NodeSelector 通过此接口获取节点资源快照；实现类负责与具体数据源交互。
    """

    @abstractmethod
    def get_nodes(self) -> list[NodeResources]:
        """
        获取当前可调度的节点资源列表。

        Returns:
            节点资源快照列表（列表可为空，但不得为 None）
        """
        ...


# ---------------------------------------------------------------------------
# 本地单节点快照
# ---------------------------------------------------------------------------


def _try_import_psutil() -> object | None:
    """尝试导入 psutil；如果未安装则返回 None。"""
    try:
        import psutil  # type: ignore[import]

        return psutil
    except ImportError:
        return None


def _try_import_torch() -> object | None:
    """尝试导入 torch；如果未安装则返回 None。"""
    try:
        import torch  # type: ignore[import]

        return torch
    except ImportError:
        return None


def _get_local_snapshot(node_id: str, hostname: str, address: str) -> NodeResources:
    """
    通过系统调用采集本地节点资源信息。

    优先使用 psutil 获取精确的内存和 CPU 使用率；不可用时回退到 os / 标准库。
    GPU 信息通过 torch（若已安装）获取。
    """
    psutil = _try_import_psutil()
    torch = _try_import_torch()

    # --- CPU ---
    total_cpu = float(os.cpu_count() or 1)
    if psutil is not None:
        cpu_usage_pct = psutil.cpu_percent(interval=None) / 100.0  # type: ignore[attr-defined]
    else:
        cpu_usage_pct = 0.0
    available_cpu = total_cpu * (1.0 - cpu_usage_pct)

    # --- Memory ---
    if psutil is not None:
        vm = psutil.virtual_memory()  # type: ignore[attr-defined]
        total_memory = int(vm.total)
        available_memory = int(vm.available)
        memory_usage = vm.percent / 100.0
    else:
        # 无 psutil：保守估计 8 GB total，无法得知使用率
        total_memory = 8 * 1024**3
        available_memory = total_memory
        memory_usage = 0.0

    # --- GPU ---
    total_gpu = 0.0
    available_gpu = 0.0
    gpu_usage = 0.0
    if torch is not None:
        if torch.cuda.is_available():  # type: ignore[attr-defined]
            total_gpu = float(torch.cuda.device_count())  # type: ignore[attr-defined]
            # 简单估算：假设所有 GPU 均可用（无法在无 Ray/NVML 的情况下精确计算已分配数量）
            available_gpu = total_gpu
            gpu_usage = 0.0

    return NodeResources(
        node_id=node_id,
        hostname=hostname,
        address=address,
        total_cpu=total_cpu,
        total_gpu=total_gpu,
        total_memory=total_memory,
        custom_resources={},
        available_cpu=max(0.0, available_cpu),
        available_gpu=max(0.0, available_gpu),
        available_memory=max(0, available_memory),
        cpu_usage=cpu_usage_pct,
        gpu_usage=gpu_usage,
        memory_usage=memory_usage,
        task_count=0,
        alive=True,
    )


class LocalSnapshotProvider(ResourceProvider):
    """
    本地单节点资源快照 Provider（默认 provider）。

    适用于：
    - 开发/测试环境
    - 单机部署
    - Flownet ClusterView 不可用时的降级

    不依赖任何外部服务，通过 psutil / os 直接采集本地资源。

    Args:
        node_id:    本地节点 ID（默认 "local"）
        hostname:   主机名（默认 socket.gethostname()）
        address:    节点地址（默认 "127.0.0.1"）
        cache_ttl:  资源缓存时间（秒），避免频繁系统调用
    """

    def __init__(
        self,
        node_id: str = "local",
        hostname: str | None = None,
        address: str = "127.0.0.1",
        cache_ttl: float = 1.0,
    ) -> None:
        import socket

        self._node_id = node_id
        self._hostname = hostname or socket.gethostname()
        self._address = address
        self._cache_ttl = cache_ttl
        self._cache: list[NodeResources] | None = None
        self._cache_ts: float = 0.0

    def get_nodes(self) -> list[NodeResources]:
        """返回本地节点资源快照（带 TTL 缓存）。"""
        now = time.monotonic()
        if self._cache is not None and (now - self._cache_ts) < self._cache_ttl:
            return self._cache

        snapshot = _get_local_snapshot(self._node_id, self._hostname, self._address)
        self._cache = [snapshot]
        self._cache_ts = now
        return self._cache


# ---------------------------------------------------------------------------
# Flownet Runtime Provider（预留接口）
# ---------------------------------------------------------------------------


class FlownetRuntimeProvider(ResourceProvider):
    """
    通过 Flownet ClusterView 获取集群节点资源（分布式模式）。

    将 Flownet 的 ``ClusterNode.resource_summary`` 字段映射到 ``NodeResources``，
    保持调度策略不感知底层传输协议。

    Args:
        cluster_view: Flownet ``ClusterView`` 实例（运行时注入）
        healthy_only: 是否只返回健康节点（默认 True）

    字段映射规则（resource_summary 键 → NodeResources 字段）:
        ``cpu_total``       → total_cpu（浮点，核心数）
        ``cpu_available``   → available_cpu
        ``gpu_total``       → total_gpu
        ``gpu_available``   → available_gpu
        ``mem_total``       → total_memory（字节）
        ``mem_available``   → available_memory
        ``cpu_usage``       → cpu_usage（0-1）
        ``gpu_usage``       → gpu_usage（0-1）
        ``mem_usage``       → memory_usage（0-1）

    缺失字段将退化为 0，不抛出异常。
    """

    # 预设：resource_summary 中浮点字段的键名
    _FLOAT_FIELDS: dict[str, str] = {
        "cpu_total": "total_cpu",
        "cpu_available": "available_cpu",
        "gpu_total": "total_gpu",
        "gpu_available": "available_gpu",
        "cpu_usage": "cpu_usage",
        "gpu_usage": "gpu_usage",
        "mem_usage": "memory_usage",
    }
    _INT_FIELDS: dict[str, str] = {
        "mem_total": "total_memory",
        "mem_available": "available_memory",
    }

    def __init__(self, cluster_view: object, *, healthy_only: bool = True) -> None:
        self._cluster_view = cluster_view
        self._healthy_only = healthy_only

    def get_nodes(self) -> list[NodeResources]:
        """从 Flownet ClusterView 抓取节点列表并转换为 NodeResources。"""
        cv = self._cluster_view
        # ClusterView.list_nodes() -> list[ClusterNode]
        raw_nodes = cv.list_nodes()  # type: ignore[attr-defined]

        result: list[NodeResources] = []
        for raw in raw_nodes:
            if self._healthy_only:
                try:
                    if not cv.is_node_healthy(raw.node_id):  # type: ignore[attr-defined]
                        continue
                except Exception:
                    pass

            result.append(self._map_node(raw))
        return result

    def _map_node(self, raw: object) -> NodeResources:
        """将 Flownet ClusterNode 转换为 NodeResources。"""
        node_id: str = getattr(raw, "node_id", "unknown")
        address: str = getattr(raw, "address", "0.0.0.0")
        hostname: str = getattr(raw, "host_id", None) or node_id

        rs: dict[str, object] = {}
        raw_rs = getattr(raw, "resource_summary", None)
        if isinstance(raw_rs, dict):
            rs = raw_rs

        def _f(key: str) -> float:
            val = rs.get(key, 0)
            try:
                return float(val)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return 0.0

        def _i(key: str) -> int:
            val = rs.get(key, 0)
            try:
                return int(val)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return 0

        total_cpu = _f("cpu_total")
        available_cpu = _f("cpu_available")
        cpu_usage = _f("cpu_usage")

        # 如果没有显式的使用率字段，从 total/available 推算
        if cpu_usage == 0.0 and total_cpu > 0:
            cpu_usage = max(0.0, min(1.0, 1.0 - available_cpu / total_cpu))

        total_gpu = _f("gpu_total")
        available_gpu = _f("gpu_available")
        gpu_usage = _f("gpu_usage")
        if gpu_usage == 0.0 and total_gpu > 0:
            gpu_usage = max(0.0, min(1.0, 1.0 - available_gpu / total_gpu))

        total_memory = _i("mem_total")
        available_memory = _i("mem_available")
        mem_usage = _f("mem_usage")
        if mem_usage == 0.0 and total_memory > 0:
            mem_usage = max(0.0, min(1.0, 1.0 - available_memory / total_memory))

        # 自定义资源：取 resource_summary 中除已知键之外的数值型字段
        known_keys = (
            set(self._FLOAT_FIELDS)
            | set(self._INT_FIELDS)
            | {
                "schedulable",
                "worker_count",
            }
        )
        custom: dict[str, float] = {}
        for k, v in rs.items():
            if k in known_keys:
                continue
            try:
                custom[str(k)] = float(v)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                pass

        return NodeResources(
            node_id=node_id,
            hostname=hostname,
            address=address,
            total_cpu=total_cpu,
            total_gpu=total_gpu,
            total_memory=total_memory,
            custom_resources=custom,
            available_cpu=available_cpu,
            available_gpu=available_gpu,
            available_memory=available_memory,
            cpu_usage=cpu_usage,
            gpu_usage=gpu_usage,
            memory_usage=mem_usage,
            task_count=0,
            alive=True,
        )
