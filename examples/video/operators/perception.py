"""Perception operators for the video intelligence demo."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision.models import MobileNet_V3_Large_Weights, mobilenet_v3_large

from sage.kernel.api.function.map_function import MapFunction

try:
    from transformers import CLIPModel, CLIPProcessor
except ImportError as exc:  # pragma: no cover - surface a friendly error
    raise RuntimeError(
        "transformers is required for SceneConceptExtractor. Install it via `pip install transformers`"
    ) from exc


class SceneConceptExtractor(MapFunction):
    """Zero-shot scene understanding using CLIP templates."""

    def __init__(
        self,
        templates: Iterable[str],
        top_k: int = 3,
        device: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.templates = list(templates)
        if not self.templates:
            raise ValueError("CLIP templates list cannot be empty")

        self.top_k = max(1, top_k)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # Use smaller CLIP model to reduce memory usage
        # Options ranked by size (smallest to largest):
        # - openai/clip-vit-base-patch32: ~150MB, 86M params (BEST for memory)
        # For even lower memory, we can use CPU and half precision
        model_name = "openai/clip-vit-base-patch32"
        
        self.logger.info(f"Loading CLIP model: {model_name} on {self.device}")
        
        # Load with memory optimization
        try:
            # Use dtype instead of torch_dtype (torch_dtype is deprecated)
            self.model = CLIPModel.from_pretrained(
                model_name,
                dtype=torch.float16 if self.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True
            ).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(model_name)
            self.logger.info("CLIP model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load CLIP model: {e}")
            raise

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pil_image: Image.Image = data.get("pil_image")
        if pil_image is None:
            return data

        inputs = self.processor(
            text=self.templates,
            images=pil_image,
            return_tensors="pt",
            padding=True,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            scores = outputs.logits_per_image.softmax(dim=1)[0]

            if hasattr(outputs, "image_embeds") and outputs.image_embeds is not None:
                image_features = outputs.image_embeds
            else:
                image_features = self.model.get_image_features(
                    pixel_values=inputs.get("pixel_values")
                )

            image_features = F.normalize(image_features, dim=-1)
            data["clip_image_embedding"] = (
                image_features[0].detach().cpu().numpy().astype(np.float32)
            )

        top_k = min(self.top_k, scores.shape[-1])
        top_scores, top_indices = torch.topk(scores, top_k)
        concepts: List[Dict[str, Any]] = []
        for score, idx in zip(top_scores.tolist(), top_indices.tolist()):
            concepts.append({
                "label": self.templates[idx],
                "score": float(score),
            })

        data["scene_concepts"] = concepts
        data["primary_scene"] = concepts[0]["label"] if concepts else "Unknown"
        data["scene_confidence"] = float(concepts[0]["score"]) if concepts else 0.0
        return data


class FrameObjectClassifier(MapFunction):
    """Image classification via MobileNetV3 over ImageNet classes."""

    def __init__(self, top_k: int = 5, device: Optional[str] = None) -> None:
        super().__init__()
        self.top_k = max(1, top_k)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.logger.info(f"Loading MobileNetV3 model on {self.device}")
        weights = MobileNet_V3_Large_Weights.DEFAULT
        self.model = mobilenet_v3_large(weights=weights).to(self.device)
        self.model.eval()
        
        # Enable half precision for GPU to save memory
        if self.device == "cuda":
            self.model = self.model.half()
            
        self.preprocess = weights.transforms()
        self.categories = weights.meta["categories"]
        self.logger.info("MobileNetV3 model loaded successfully")

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pil_image: Image.Image = data.get("pil_image")
        if pil_image is None:
            return data

        tensor = self.preprocess(pil_image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.nn.functional.softmax(logits, dim=1)[0]

        k = min(self.top_k, probs.shape[0])
        top_scores, top_indices = torch.topk(probs, k)
        predictions: List[Dict[str, Any]] = []
        for score, idx in zip(top_scores.tolist(), top_indices.tolist()):
            predictions.append({
                "label": self.categories[idx],
                "score": float(score),
            })

        data["object_predictions"] = predictions
        return data
