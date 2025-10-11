"""Service integration operators for the video intelligence demo."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
from sage.kernel.api.function.map_function import MapFunction


class SageMiddlewareIntegrator(MapFunction):
    """Publishes frame embeddings to SageDB and SageFlow services."""

    def __init__(
        self,
        enable_db: bool = True,
        db_service_name: str = "video_scene_db",
        db_neighbor_k: int = 3,
        enable_flow: bool = True,
        flow_service_name: str = "video_vector_flow",
        flow_auto_flush: int = 1,
    ) -> None:
        super().__init__()
        self.enable_db = enable_db and bool(db_service_name)
        self.db_service_name = db_service_name
        self.db_neighbor_k = max(0, int(db_neighbor_k))
        self.enable_flow = enable_flow and bool(flow_service_name)
        self.flow_service_name = flow_service_name
        self.flow_auto_flush = max(1, int(flow_auto_flush))
        self._flow_since_flush = 0

    def _format_neighbors(
        self, neighbors: List[Dict[str, Any]], entry_id: Any
    ) -> List[Dict[str, Any]]:
        formatted: List[Dict[str, Any]] = []
        for item in neighbors:
            if item.get("id") == entry_id:
                continue
            meta = item.get("metadata", {}) or {}
            formatted.append(
                {
                    "score": round(float(item.get("score", 0.0)), 4),
                    "frame_id": meta.get("frame_id"),
                    "timestamp": meta.get("timestamp"),
                    "primary_scene": meta.get("primary_scene"),
                }
            )
        return formatted[: self.db_neighbor_k]

    def _flush_flow(self) -> None:
        if not self.enable_flow or self._flow_since_flush <= 0:
            return
        try:
            self.call_service(self.flow_service_name, method="run")
        except Exception as exc:  # pragma: no cover - runtime safety
            self.logger.warning("SageFlow flush failed: %s", exc)
        finally:
            self._flow_since_flush = 0

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        embedding = data.get("clip_image_embedding")
        if embedding is None:
            return data

        vector = np.asarray(embedding, dtype=np.float32)
        vector_list = vector.tolist()
        integrations = data.setdefault("integrations", {})

        if self.enable_db:
            metadata = {
                "frame_id": str(data.get("frame_id")),
                "timestamp": f"{float(data.get('timestamp', 0.0)):.3f}",
                "primary_scene": data.get("primary_scene", ""),
            }
            try:
                entry_id = self.call_service(
                    self.db_service_name,
                    vector_list,
                    metadata=metadata,
                    method="add",
                )
                integrations["sage_db_entry_id"] = entry_id

                if self.db_neighbor_k > 0:
                    neighbors = self.call_service(
                        self.db_service_name,
                        vector_list,
                        method="search",
                        k=self.db_neighbor_k + 1,
                        include_metadata=True,
                    )
                    integrations["sage_db_similar"] = self._format_neighbors(
                        neighbors or [], entry_id
                    )
            except Exception as exc:  # pragma: no cover - service resilience
                self.logger.warning("SageDB service call failed: %s", exc)

        if self.enable_flow:
            try:
                uid = int(data.get("frame_id", 0))
                self.call_service(
                    self.flow_service_name,
                    uid,
                    vector_list,
                    method="push",
                )
                self._flow_since_flush += 1
                if self._flow_since_flush >= self.flow_auto_flush:
                    self._flush_flow()
            except Exception as exc:  # pragma: no cover - service resilience
                self.logger.warning("SageFlow service call failed: %s", exc)

        data.pop("clip_image_embedding", None)
        return data

    def __del__(self):  # pragma: no cover - best-effort flush
        try:
            self._flush_flow()
        except Exception:
            pass


class SummaryMemoryAugmentor(MapFunction):
    """Enriches summaries with NeuroMem memory retrieval results."""

    def __init__(
        self,
        enable: bool = True,
        service_name: str = "video_memory_service",
        top_k: int = 3,
        collection_name: Optional[str] = None,
        with_metadata: bool = True,
    ) -> None:
        super().__init__()
        self.enable = enable and bool(service_name)
        self.service_name = service_name
        self.top_k = max(1, int(top_k))
        self.collection_name = collection_name
        self.with_metadata = with_metadata

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enable:
            return data

        query = data.get("generated_summary") or " ".join(
            data.get("top_scene_concepts", [])
        )
        if not query:
            return data

        try:
            results = self.call_service(
                self.service_name,
                query,
                method="retrieve",
                topk=self.top_k,
                collection_name=self.collection_name,
                with_metadata=self.with_metadata,
            )
        except Exception as exc:  # pragma: no cover - service resilience
            self.logger.warning("NeuroMem retrieval failed: %s", exc)
            return data

        if results:
            formatted: List[Dict[str, Any]] = []
            for item in results:
                if isinstance(item, dict):
                    formatted.append(
                        {
                            "text": item.get("text") or item.get("history_query"),
                            "answer": item.get("answer")
                            or item.get("metadata", {}).get("answer"),
                            "source": item.get("source_collection"),
                        }
                    )
                else:
                    formatted.append({"text": str(item), "source": None})
            data["memory_recall"] = formatted

        return data
