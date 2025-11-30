"""
影像分析Agent
负责MRI影像的特征提取和初步分析
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

try:
    import torch
    from PIL import Image as PILImage
    from transformers import (
        AutoImageProcessor,
        AutoModel,
        CLIPModel,
        CLIPProcessor,
    )

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    PILImage = None
    AutoImageProcessor = None
    AutoModel = None
    CLIPModel = None
    CLIPProcessor = None


DEFAULT_DISC_LEVELS = ["L1/L2", "L2/L3", "L3/L4", "L4/L5", "L5/S1"]


@dataclass
class ImageFeatures:
    """影像特征"""

    vertebrae: list[dict[str, Any]]  # 椎体信息
    discs: list[dict[str, Any]]  # 椎间盘信息
    abnormalities: list[dict[str, Any]]  # 异常发现
    image_quality: float  # 影像质量评分
    image_embedding: np.ndarray | None = None  # 影像嵌入向量


class ImageAnalyzer:
    """
    MRI影像分析器

    功能:
    1. 图像预处理和质量评估
    2. 椎体和椎间盘分割定位
    3. 病变区域检测
    4. 影像特征提取和向量化
    """

    def __init__(self, config: dict):
        """
        初始化影像分析器

        Args:
            config: 配置字典
        """
        self.config = config
        self.vision_model = None
        self.segmentation_model = None
        self.segmenter_type = None
        self.segmenter_device = "cpu"
        self.segmentation_config: dict[str, Any] = {}
        self.segmentation_enabled = False
        self.disc_levels = DEFAULT_DISC_LEVELS.copy()
        self.segmentation_thresholds: dict[str, float] = {}
        self.pixel_spacing_mm = 180.0
        self.baseline_disc_height_mm = 9.0
        self._setup_models()

    def _setup_models(self):
        """设置视觉模型"""
        # TODO: 集成 SAGE VLLMService 或其他视觉模型
        # Issue URL: https://github.com/intellistream/SAGE/issues/899
        print(f"   Loading vision model: {self.config['models']['vision_model']}")

        # 这里可以集成:
        # 1. Qwen2-VL for general vision understanding
        # 2. SAM (Segment Anything Model) for segmentation
        # 3. Medical imaging specific models

        self.vision_model = "placeholder"  # 实际应该加载模型

        image_processing_cfg = self.config.get("image_processing", {})

        # 设置特征提取模型
        self.feature_model = None
        self.feature_processor = None
        self.feature_method = image_processing_cfg.get("feature_extraction", {}).get(
            "method", "clip"
        )

        if TORCH_AVAILABLE:
            try:
                if self.feature_method == "clip":
                    self._setup_clip_model()
                elif self.feature_method == "dinov2":
                    self._setup_dinov2_model()
                else:
                    print(
                        f"   Warning: Unknown feature method '{self.feature_method}', using mock features"
                    )
            except Exception as e:
                print(f"   Warning: Failed to load feature extraction model: {e}")
                print("   Falling back to mock features")
        else:
            print("   Warning: PyTorch not available, feature extraction will use mock features")

        # 设置分割参数
        self.segmentation_config = image_processing_cfg.get("segmentation", {}) or {}
        self.segmentation_enabled = bool(self.segmentation_config.get("enabled", False))
        disc_levels_cfg = self.segmentation_config.get("disc_levels")
        self.disc_levels = list(disc_levels_cfg) if disc_levels_cfg else DEFAULT_DISC_LEVELS.copy()
        self.pixel_spacing_mm = float(
            self.segmentation_config.get("pixel_spacing_mm", self.pixel_spacing_mm)
        )
        self.baseline_disc_height_mm = float(
            self.segmentation_config.get(
                "baseline_disc_height_mm",
                self.segmentation_config.get("expected_height_mm", self.baseline_disc_height_mm),
            )
        )
        self.segmentation_thresholds = {
            "min_height_ratio": 0.02,
            "max_height_ratio": 0.18,
            "min_aspect_ratio": 1.5,
            "min_width_ratio": 0.12,
            "min_vertical_pos": 0.08,
            "max_vertical_pos": 0.95,
            "min_confidence": 0.35,
            "min_separation_ratio": 0.05,
        }
        thresholds_cfg = self.segmentation_config.get("thresholds", {}) or {}
        for key, value in thresholds_cfg.items():
            try:
                self.segmentation_thresholds[key] = float(value)
            except (TypeError, ValueError):
                continue

        if self.segmentation_enabled:
            self._setup_segmentation_model()

    def _setup_clip_model(self):
        """设置 CLIP 模型用于特征提取"""
        try:
            model_name = "openai/clip-vit-base-patch32"
            print(f"   Loading CLIP model: {model_name}")
            self.feature_processor = CLIPProcessor.from_pretrained(model_name)
            self.feature_model = CLIPModel.from_pretrained(model_name)

            # 移动到 GPU (如果可用)
            if torch.cuda.is_available():
                self.feature_model = self.feature_model.cuda()
                print("   CLIP model loaded on GPU")
            else:
                print("   CLIP model loaded on CPU")

            self.feature_model.eval()  # 设置为评估模式
        except Exception as e:
            print(f"   Failed to load CLIP model: {e}")
            raise

    def _setup_dinov2_model(self):
        """设置 DINOv2 模型用于特征提取"""
        try:
            model_name = "facebook/dinov2-base"
            print(f"   Loading DINOv2 model: {model_name}")
            self.feature_processor = AutoImageProcessor.from_pretrained(model_name)
            self.feature_model = AutoModel.from_pretrained(model_name)

            # 移动到 GPU (如果可用)
            if torch.cuda.is_available():
                self.feature_model = self.feature_model.cuda()
                print("   DINOv2 model loaded on GPU")
            else:
                print("   DINOv2 model loaded on CPU")

            self.feature_model.eval()  # 设置为评估模式
        except Exception as e:
            print(f"   Failed to load DINOv2 model: {e}")
            raise

    def _setup_segmentation_model(self):
        """设置椎间盘分割模型"""
        if not TORCH_AVAILABLE:
            print("   Warning: Segmentation requires PyTorch, falling back to heuristics")
            return

        model_name = (self.segmentation_config.get("model") or "sam").lower()
        try:
            if model_name.startswith("sam") or model_name.startswith("medsam"):
                self.segmentation_model = self._setup_sam_segmenter(model_name)
                self.segmenter_type = "sam"
            else:
                print(
                    f"   Warning: Unsupported segmentation model '{model_name}', using heuristics"
                )
                self.segmentation_model = None
        except Exception as exc:
            print(f"   Warning: Failed to initialize segmentation model '{model_name}': {exc}")
            self.segmentation_model = None
            self.segmenter_type = None

    def _setup_sam_segmenter(self, model_name: str):
        """初始化 Segment Anything 模型"""
        try:
            from segment_anything import SamAutomaticMaskGenerator, sam_model_registry
        except ImportError as exc:  # pragma: no cover - 可选依赖
            raise RuntimeError(
                "segment_anything is not installed. Please install it to use SAM segmentation"
            ) from exc

        checkpoint_path = self.segmentation_config.get("checkpoint_path")
        if not checkpoint_path:
            raise ValueError("Segmentation config missing 'checkpoint_path'")

        checkpoint = Path(checkpoint_path).expanduser()
        if not checkpoint.exists():
            raise FileNotFoundError(f"Segmentation checkpoint not found: {checkpoint}")

        variant = self.segmentation_config.get("sam_variant")
        variant = variant or {
            "sam": "vit_h",
            "sam-vit-h": "vit_h",
            "sam-vit-b": "vit_b",
            "sam-vit-l": "vit_l",
            "medsam": "vit_b",
        }.get(model_name, model_name.replace("sam-", ""))

        if variant not in sam_model_registry:
            raise ValueError(f"Unsupported SAM variant '{variant}'")

        print(f"   Loading SAM segmentation model ({variant}) from {checkpoint}")
        sam = sam_model_registry[variant](checkpoint=str(checkpoint))
        self.segmenter_device = "cuda" if torch.cuda.is_available() else "cpu"
        sam.to(device=self.segmenter_device)

        generator_kwargs = {
            "points_per_side": self.segmentation_config.get("points_per_side", 16),
            "pred_iou_thresh": self.segmentation_config.get("pred_iou_thresh", 0.86),
            "stability_score_thresh": self.segmentation_config.get("stability_score_thresh", 0.92),
            "crop_n_layers": self.segmentation_config.get("crop_n_layers", 1),
            "crop_n_points_downscale_factor": self.segmentation_config.get(
                "crop_n_points_downscale_factor", 2
            ),
            "min_mask_region_area": self.segmentation_config.get("min_mask_region_area", 200),
        }

        print(
            "   SAM segmentation ready "
            f"(points_per_side={generator_kwargs['points_per_side']}, device={self.segmenter_device})"
        )
        return SamAutomaticMaskGenerator(sam, **generator_kwargs)

    def analyze(self, image_path: str) -> dict[str, Any]:
        """
        分析MRI影像

        Args:
            image_path: 影像文件路径

        Returns:
            影像特征字典
        """
        image_path_obj = Path(image_path)

        if not image_path_obj.exists():
            # 创建模拟数据用于演示
            return self._create_mock_analysis()

        # Step 1: 加载和预处理图像
        image = self._load_image(image_path_obj)

        # Step 2: 质量评估
        quality_score = self._assess_quality(image)

        # Step 3: 解剖结构分割
        vertebrae = self._segment_vertebrae(image)
        discs = self._segment_discs(image)

        # Step 4: 病变检测
        abnormalities = self._detect_abnormalities(image, vertebrae, discs)

        # Step 5: 特征提取
        image_embedding = self._extract_features(image)

        return {
            "vertebrae": vertebrae,
            "discs": discs,
            "abnormalities": abnormalities,
            "image_quality": quality_score,
            "image_embedding": image_embedding,
            "image_path": str(image_path),
        }

    def _load_image(self, image_path: Path):
        """加载影像"""
        # TODO: 实现 DICOM 或常规图像加载
        # Issue URL: https://github.com/intellistream/SAGE/issues/898
        try:
            from PIL import Image

            return np.array(Image.open(image_path).convert("L"))
        except Exception as e:
            print(f"   Warning: 无法加载图像 {image_path}: {e}")
            return None

    def _assess_quality(self, image) -> float:
        """评估影像质量"""
        if image is None:
            return 0.0

        # 简单质量评估：对比度、清晰度等
        # TODO: 实现更复杂的质量评估算法
        # Issue URL: https://github.com/intellistream/SAGE/issues/897
        return 0.85

    def _segment_vertebrae(self, image) -> list[dict[str, Any]]:
        """分割椎体"""
        # TODO: 使用分割模型识别 L1-L5 椎体
        # Issue URL: https://github.com/intellistream/SAGE/issues/896

        # 模拟输出
        vertebrae_names = ["L1", "L2", "L3", "L4", "L5"]
        return [
            {
                "name": name,
                "position": {"x": 100, "y": 50 + i * 80},
                "size": {"width": 40, "height": 30},
                "features": {
                    "signal_intensity": 0.7 + i * 0.02,
                    "shape_regularity": 0.9,
                },
            }
            for i, name in enumerate(vertebrae_names)
        ]

    def _segment_discs(self, image) -> list[dict[str, Any]]:
        """分割椎间盘"""
        if image is None:
            return self._generate_heuristic_discs(image)

        if self.segmentation_enabled and self.segmentation_model is not None:
            try:
                rgb_image = self._prepare_segmentation_input(image)
                mask_outputs = self._run_segmentation_model(rgb_image)
                discs = self._build_discs_from_masks(mask_outputs, image)
                if discs:
                    return discs
                print(
                    "   Warning: Segmentation produced no disc candidates, using heuristic fallback"
                )
            except Exception as exc:
                print(f"   Warning: Disc segmentation failed ({exc}), using heuristic fallback")

        return self._generate_heuristic_discs(image)

    def _prepare_segmentation_input(self, image: np.ndarray) -> np.ndarray:
        """将灰度图转换为分割模型可用的 RGB 图"""
        array = np.array(image)

        if array.dtype != np.uint8:
            min_val = float(array.min()) if array.size else 0.0
            max_val = float(array.max()) if array.size else 0.0
            if max_val - min_val > 1e-5:
                array = ((array - min_val) / (max_val - min_val) * 255).astype(np.uint8)
            else:
                array = np.zeros_like(array, dtype=np.uint8)

        if array.ndim == 2:
            array = np.stack([array] * 3, axis=-1)
        elif array.ndim == 3 and array.shape[2] == 1:
            array = np.repeat(array, 3, axis=2)

        return array

    def _run_segmentation_model(self, rgb_image: np.ndarray) -> list[dict[str, Any]]:
        """运行分割模型"""
        if hasattr(self.segmentation_model, "generate"):
            return self.segmentation_model.generate(rgb_image)
        if callable(self.segmentation_model):
            return self.segmentation_model(rgb_image)
        raise RuntimeError("Segmentation model does not expose a generate() method")

    def _build_discs_from_masks(
        self, masks: list[dict[str, Any]], original_image: np.ndarray
    ) -> list[dict[str, Any]]:
        """根据分割掩码构建椎间盘信息"""
        if not masks:
            return []

        height, width = original_image.shape[:2]
        candidates = self._select_disc_masks(masks, (height, width))
        if not candidates:
            return []

        candidates.sort(key=lambda item: item["center"][1])
        discs: list[dict[str, Any]] = []

        for idx, candidate in enumerate(candidates):
            if idx >= len(self.disc_levels):
                break
            features, position = self._compute_disc_features(original_image, candidate)
            discs.append(
                {
                    "level": self.disc_levels[idx],
                    "position": position,
                    "features": features,
                }
            )

        return discs

    def _select_disc_masks(
        self, masks: list[dict[str, Any]], image_shape: tuple[int, int]
    ) -> list[dict[str, Any]]:
        """筛选椎间盘候选掩码"""
        height, width = image_shape
        filtered: list[dict[str, Any]] = []

        for mask in masks:
            segmentation = mask.get("segmentation")
            if segmentation is None:
                continue

            segmentation = np.asarray(segmentation, dtype=bool)

            bbox = mask.get("bbox")
            if bbox is None:
                bbox = self._mask_to_bbox(segmentation)
            if bbox is None:
                continue

            x, y, w, h = [int(value) for value in bbox]
            if w <= 0 or h <= 0:
                continue

            height_ratio = h / max(height, 1)
            width_ratio = w / max(width, 1)
            aspect_ratio = w / (h + 1e-5)
            center = (x + w / 2.0, y + h / 2.0)
            vertical_pos = center[1] / max(height, 1)
            confidence = float(mask.get("predicted_iou", mask.get("stability_score", 0.0)))
            stability = float(mask.get("stability_score", confidence))

            if height_ratio < self.segmentation_thresholds["min_height_ratio"]:
                continue
            if height_ratio > self.segmentation_thresholds["max_height_ratio"]:
                continue
            if width_ratio < self.segmentation_thresholds["min_width_ratio"]:
                continue
            if aspect_ratio < self.segmentation_thresholds["min_aspect_ratio"]:
                continue
            if not (
                self.segmentation_thresholds["min_vertical_pos"]
                <= vertical_pos
                <= self.segmentation_thresholds["max_vertical_pos"]
            ):
                continue
            if confidence < self.segmentation_thresholds["min_confidence"]:
                continue

            filtered.append(
                {
                    "segmentation": segmentation,
                    "bbox": (x, y, w, h),
                    "center": center,
                    "confidence": confidence,
                    "stability": stability,
                    "area": float(mask.get("area", float(segmentation.sum()))),
                }
            )

        if not filtered:
            return []

        # 移除过于接近的候选，保证每个椎间盘只保留一个掩码
        min_sep = self.segmentation_thresholds.get("min_separation_ratio", 0.05) * height
        deduped: list[dict[str, Any]] = []
        filtered.sort(key=lambda item: (-item["confidence"], item["center"][1]))
        for candidate in filtered:
            if any(
                abs(candidate["center"][1] - existing["center"][1]) < min_sep
                for existing in deduped
            ):
                continue
            deduped.append(candidate)

        deduped.sort(key=lambda item: item["center"][1])
        return deduped

    def _mask_to_bbox(self, mask: np.ndarray) -> tuple[int, int, int, int] | None:
        """根据掩码计算包围盒"""
        if mask.ndim != 2 or not mask.any():
            return None

        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        y_indices = np.where(rows)[0]
        x_indices = np.where(cols)[0]
        if y_indices.size == 0 or x_indices.size == 0:
            return None

        y_min, y_max = int(y_indices[0]), int(y_indices[-1])
        x_min, x_max = int(x_indices[0]), int(x_indices[-1])
        return x_min, y_min, x_max - x_min + 1, y_max - y_min + 1

    def _compute_disc_features(
        self, image: np.ndarray, mask_info: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """从掩码中提取椎间盘特征"""
        x, y, w, h = mask_info["bbox"]
        height, width = image.shape[:2]
        crop = image[y : y + h, x : x + w]
        segmentation = mask_info["segmentation"][y : y + h, x : x + w]

        if crop.ndim == 3:
            crop_gray = crop[:, :, 0]
        else:
            crop_gray = crop

        if segmentation.any():
            disc_pixels = crop_gray[segmentation]
            intensity = float(disc_pixels.mean() / 255.0) if disc_pixels.size else 0.0
        else:
            intensity = float(crop_gray.mean() / 255.0) if crop_gray.size else 0.0

        height_ratio = h / max(height, 1)
        height_mm = round(height_ratio * self.pixel_spacing_mm, 2)
        degeneration_score = max(0.0, 1.0 - height_mm / max(self.baseline_disc_height_mm, 1e-3))
        irregularity = 1.0 - mask_info["area"] / max(w * h, 1)
        lateral_shift = self._compute_lateral_imbalance(segmentation)

        herniation = bool(
            irregularity > self.segmentation_config.get("irregularity_threshold", 0.35)
            or lateral_shift > self.segmentation_config.get("lateral_shift_threshold", 0.18)
            or degeneration_score > 0.35
        )

        features = {
            "height": max(height_mm, 0.1),
            "height_ratio": round(height_ratio, 4),
            "signal_intensity": round(max(min(intensity, 1.0), 0.0), 3),
            "degeneration_score": round(degeneration_score, 3),
            "irregularity": round(max(irregularity, 0.0), 3),
            "lateral_shift": round(lateral_shift, 3),
            "herniation": herniation,
            "mask_confidence": round(mask_info.get("confidence", 0.0), 3),
            "stability": round(mask_info.get("stability", 0.0), 3),
        }

        position = {"x": int(x + w / 2), "y": int(y + h / 2)}
        return features, position

    def _compute_lateral_imbalance(self, mask: np.ndarray) -> float:
        """计算左右侧面积差异，用于判断椎间盘偏移"""
        if mask.size == 0:
            return 0.0

        column_profile = mask.sum(axis=0).astype(np.float32)
        mid = column_profile.size // 2
        left = column_profile[:mid].sum()
        right = column_profile[mid:].sum()
        total = left + right
        if total == 0:
            return 0.0
        return float(abs(left - right) / total)

    def _generate_heuristic_discs(self, image: np.ndarray | None) -> list[dict[str, Any]]:
        """基于几何启发式生成椎间盘信息（在缺少模型时使用）"""
        height, width = image.shape[:2] if isinstance(image, np.ndarray) else (512, 512)
        discs: list[dict[str, Any]] = []

        for idx, level in enumerate(self.disc_levels):
            y = int((0.2 + idx * 0.12) * height)
            x = width // 2
            window = None
            if isinstance(image, np.ndarray):
                y0 = max(y - 4, 0)
                y1 = min(y + 4, height)
                window = image[y0:y1, :]

            if window is not None and window.size:
                intensity = float(window.mean() / 255.0)
            else:
                intensity = max(0.0, 0.75 - idx * 0.08)

            height_value = max(self.baseline_disc_height_mm - idx * 0.45, 4.0)
            discs.append(
                {
                    "level": level,
                    "position": {"x": x, "y": y},
                    "features": {
                        "height": round(height_value, 2),
                        "height_ratio": round(
                            height_value / max(self.baseline_disc_height_mm, 1e-3), 3
                        ),
                        "signal_intensity": round(max(min(intensity, 1.0), 0.0), 3),
                        "herniation": idx >= 3,
                        "degeneration_score": round(idx * 0.1, 3),
                        "irregularity": 0.2 + idx * 0.05,
                        "lateral_shift": 0.05 * idx,
                        "mask_confidence": 0.0,
                        "stability": 0.0,
                    },
                }
            )

        return discs

    def _detect_abnormalities(
        self, image, vertebrae: list[dict], discs: list[dict]
    ) -> list[dict[str, Any]]:
        """检测异常"""
        abnormalities = []

        # 检查椎间盘突出
        for disc in discs:
            if disc["features"].get("herniation"):
                abnormalities.append(
                    {
                        "type": "disc_herniation",
                        "location": disc["level"],
                        "severity": "moderate",
                        "description": f"{disc['level']} 椎间盘突出",
                    }
                )

        # 检查椎间盘退变
        for disc in discs:
            if disc["features"]["height"] < 6.0:
                abnormalities.append(
                    {
                        "type": "disc_degeneration",
                        "location": disc["level"],
                        "severity": ("mild" if disc["features"]["height"] > 5.0 else "moderate"),
                        "description": f"{disc['level']} 椎间盘退行性变",
                    }
                )

        # 检查信号强度异常
        for disc in discs:
            if disc["features"]["signal_intensity"] < 0.6:
                abnormalities.append(
                    {
                        "type": "signal_change",
                        "location": disc["level"],
                        "severity": "mild",
                        "description": f"{disc['level']} 椎间盘信号减低",
                    }
                )

        return abnormalities

    def _extract_features(self, image) -> np.ndarray | None:
        """提取影像特征向量

        使用预训练模型 (CLIP/DINOv2) 提取影像特征
        如果模型不可用，回退到模拟特征

        Args:
            image: 输入图像 (numpy array 或 PIL Image)

        Returns:
            特征向量 (numpy array) 或 None
        """
        if image is None:
            return None

        # 如果没有加载特征提取模型，使用模拟特征
        if self.feature_model is None or not TORCH_AVAILABLE:
            print("   Using mock features (model not available)")
            return self._create_mock_features()

        try:
            # 转换图像为 PIL Image (如果是 numpy array)
            if isinstance(image, np.ndarray):
                # 确保是 uint8 类型
                if image.dtype != np.uint8:
                    image = ((image - image.min()) / (image.max() - image.min()) * 255).astype(
                        np.uint8
                    )
                # 转换灰度图为 RGB
                if len(image.shape) == 2:
                    image = np.stack([image] * 3, axis=-1)
                pil_image = PILImage.fromarray(image)
            else:
                pil_image = image

            # 使用对应的模型提取特征
            if self.feature_method == "clip":
                features = self._extract_clip_features(pil_image)
            elif self.feature_method == "dinov2":
                features = self._extract_dinov2_features(pil_image)
            else:
                print(f"   Unknown feature method: {self.feature_method}")
                features = self._create_mock_features()

            return features

        except Exception as e:
            print(f"   Warning: Feature extraction failed: {e}")
            print("   Falling back to mock features")
            return self._create_mock_features()

    def _extract_clip_features(self, image: "PILImage.Image") -> np.ndarray:
        """使用 CLIP 提取特征"""
        with torch.no_grad():
            # 预处理图像
            inputs = self.feature_processor(images=image, return_tensors="pt")

            # 移动到正确的设备
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}

            # 提取图像特征
            image_features = self.feature_model.get_image_features(**inputs)

            # 转换为 numpy array
            features = image_features.cpu().numpy().squeeze()

            # 归一化
            features = features / np.linalg.norm(features)

            return features.astype(np.float32)

    def _extract_dinov2_features(self, image: "PILImage.Image") -> np.ndarray:
        """使用 DINOv2 提取特征"""
        with torch.no_grad():
            # 预处理图像
            inputs = self.feature_processor(images=image, return_tensors="pt")

            # 移动到正确的设备
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}

            # 提取特征
            outputs = self.feature_model(**inputs)

            # 使用 [CLS] token 的输出作为图像特征
            features = outputs.last_hidden_state[:, 0].cpu().numpy().squeeze()

            # 归一化
            features = features / np.linalg.norm(features)

            return features.astype(np.float32)

    def _create_mock_features(self) -> np.ndarray:
        """创建模拟特征向量 (用于测试或回退)"""
        # 获取配置的特征维度，默认 768
        dimension = (
            self.config.get("image_processing", {})
            .get("feature_extraction", {})
            .get("dimension", 768)
        )
        return np.random.randn(dimension).astype(np.float32)

    def _create_mock_analysis(self) -> dict[str, Any]:
        """创建模拟分析结果（用于演示）"""
        return {
            "vertebrae": [
                {"name": f"L{i}", "position": {"x": 100, "y": 50 + i * 80}} for i in range(1, 6)
            ],
            "discs": self._generate_heuristic_discs(None),
            "abnormalities": [
                {
                    "type": "disc_herniation",
                    "location": "L4/L5",
                    "severity": "moderate",
                    "description": "L4/L5 椎间盘突出",
                },
                {
                    "type": "disc_degeneration",
                    "location": "L5/S1",
                    "severity": "mild",
                    "description": "L5/S1 椎间盘退行性变",
                },
            ],
            "image_quality": 0.85,
            "image_embedding": np.random.randn(768).astype(np.float32),
        }


if __name__ == "__main__":
    # 测试
    config = {"models": {"vision_model": "Qwen/Qwen2-VL-7B-Instruct"}}

    analyzer = ImageAnalyzer(config)
    result = analyzer.analyze("test.jpg")

    print(f"椎体数量: {len(result['vertebrae'])}")
    print(f"椎间盘数量: {len(result['discs'])}")
    print(f"异常数量: {len(result['abnormalities'])}")
