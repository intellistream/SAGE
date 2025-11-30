#!/usr/bin/env python3
"""Tests for ImageAnalyzer image loading and feature extraction."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sage.apps.medical_diagnosis.agents.image_analyzer import TORCH_AVAILABLE, ImageAnalyzer


# ---------------------------------------------------------------------------
# Common fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def analyzer():
    """Create an ImageAnalyzer instance for image-loading tests."""
    config = {"models": {"vision_model": "test-model"}}
    return ImageAnalyzer(config)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def basic_config():
    """Configuration used for feature extraction tests."""
    return {
        "models": {"vision_model": "Qwen/Qwen2-VL-7B-Instruct"},
        "image_processing": {"feature_extraction": {"method": "clip", "dimension": 768}},
    }


@pytest.fixture
def dinov2_config():
    """Configuration for testing DINOv2 feature extraction."""
    return {
        "models": {"vision_model": "Qwen/Qwen2-VL-7B-Instruct"},
        "image_processing": {"feature_extraction": {"method": "dinov2", "dimension": 768}},
    }


@pytest.fixture
def mock_image():
    """Create a mock grayscale numpy image."""
    return np.random.randint(0, 255, (512, 512), dtype=np.uint8)


@pytest.fixture
def mock_pil_image():
    """Create a mock RGB PIL image for feature extraction tests."""
    if not TORCH_AVAILABLE:
        pytest.skip("PyTorch not available")

    from PIL import Image

    return Image.fromarray(np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8))


# ---------------------------------------------------------------------------
# Image loading unit tests
# ---------------------------------------------------------------------------
class TestLoadImage:
    """Tests for the _load_image method."""

    def test_load_image_nonexistent_file(self, analyzer, temp_dir):
        fake_path = temp_dir / "nonexistent.png"
        result = analyzer._load_image(fake_path)
        assert result is None

    def test_load_image_dicom_extension(self, analyzer, temp_dir):
        dcm_path = temp_dir / "test.dcm"
        dcm_path.touch()

        with patch.object(analyzer, "_load_dicom_image", return_value=None) as mock_dicom:
            analyzer._load_image(dcm_path)
            mock_dicom.assert_called_once_with(dcm_path)

    def test_load_image_dicom_extension_uppercase(self, analyzer, temp_dir):
        dcm_path = temp_dir / "test.DCM"
        dcm_path.touch()

        with patch.object(analyzer, "_load_dicom_image", return_value=None) as mock_dicom:
            analyzer._load_image(dcm_path)
            mock_dicom.assert_called_once_with(dcm_path)

    def test_load_image_png_extension(self, analyzer, temp_dir):
        png_path = temp_dir / "test.png"
        png_path.touch()

        with patch.object(analyzer, "_load_regular_image", return_value=None) as mock_regular:
            analyzer._load_image(png_path)
            mock_regular.assert_called_once_with(png_path)

    def test_load_image_jpg_extension(self, analyzer, temp_dir):
        jpg_path = temp_dir / "test.jpg"
        jpg_path.touch()

        with patch.object(analyzer, "_load_regular_image", return_value=None) as mock_regular:
            analyzer._load_image(jpg_path)
            mock_regular.assert_called_once_with(jpg_path)


class TestLoadDicomImage:
    """Tests for the _load_dicom_image method."""

    def test_load_dicom_success(self, analyzer, temp_dir):
        dcm_path = temp_dir / "test.dcm"
        dcm_path.touch()

        mock_dicom = MagicMock()
        mock_dicom.pixel_array = np.array([[100, 200], [150, 250]], dtype=np.int16)
        del mock_dicom.WindowCenter
        del mock_dicom.WindowWidth

        with patch.dict("sys.modules", {"pydicom": MagicMock()}):
            import sys

            sys.modules["pydicom"].dcmread.return_value = mock_dicom
            result = analyzer._load_dicom_image(dcm_path)

        assert result is not None
        assert result.dtype == np.uint8
        assert result.shape == (2, 2)
        assert result.min() >= 0
        assert result.max() <= 255

    def test_load_dicom_with_window_level(self, analyzer, temp_dir):
        dcm_path = temp_dir / "test.dcm"
        dcm_path.touch()

        mock_dicom = MagicMock()
        mock_dicom.pixel_array = np.array([[0, 500], [1000, 2000]], dtype=np.int16)
        mock_dicom.WindowCenter = 500
        mock_dicom.WindowWidth = 1000

        with patch.dict("sys.modules", {"pydicom": MagicMock()}):
            import sys

            sys.modules["pydicom"].dcmread.return_value = mock_dicom
            result = analyzer._load_dicom_image(dcm_path)

        assert result is not None
        assert result.dtype == np.uint8

    def test_load_dicom_pydicom_not_installed(self, analyzer, temp_dir):
        dcm_path = temp_dir / "test.dcm"
        dcm_path.touch()

        with patch.dict("sys.modules", {"pydicom": None}):
            original_import = __import__

            def mock_import(name, *args, **kwargs):
                if name == "pydicom":
                    raise ImportError("No module named 'pydicom'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                result = analyzer._load_dicom_image(dcm_path)

        assert result is None

    def test_load_dicom_invalid_file(self, analyzer, temp_dir):
        dcm_path = temp_dir / "invalid.dcm"
        dcm_path.write_bytes(b"not a valid dicom file")

        result = analyzer._load_dicom_image(dcm_path)
        assert result is None or isinstance(result, np.ndarray)


class TestLoadRegularImage:
    """Tests for the _load_regular_image method."""

    def test_load_regular_image_png(self, analyzer, temp_dir):
        png_path = temp_dir / "test.png"

        try:
            from PIL import Image

            img = Image.new("RGB", (10, 10), color="red")
            img.save(png_path)
            result = analyzer._load_regular_image(png_path)
        except ImportError:
            pytest.skip("PIL not installed")

        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.shape == (10, 10)
        assert result.dtype == np.uint8

    def test_load_regular_image_jpg(self, analyzer, temp_dir):
        jpg_path = temp_dir / "test.jpg"

        try:
            from PIL import Image

            img = Image.new("L", (20, 20), color=128)
            img.save(jpg_path)
            result = analyzer._load_regular_image(jpg_path)
        except ImportError:
            pytest.skip("PIL not installed")

        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.shape == (20, 20)
        assert result.dtype == np.uint8

    def test_load_regular_image_grayscale_conversion(self, analyzer, temp_dir):
        png_path = temp_dir / "color.png"

        try:
            from PIL import Image

            img = Image.new("RGB", (5, 5), color=(255, 0, 0))
            img.save(png_path)
            result = analyzer._load_regular_image(png_path)
        except ImportError:
            pytest.skip("PIL not installed")

        assert result is not None
        assert len(result.shape) == 2

    def test_load_regular_image_invalid_file(self, analyzer, temp_dir):
        invalid_path = temp_dir / "invalid.png"
        invalid_path.write_bytes(b"not a valid image file")

        result = analyzer._load_regular_image(invalid_path)
        assert result is None


class TestImageAnalyzerLoadingIntegration:
    """Integration tests for the image loading pipeline."""

    def test_analyze_with_valid_image(self, analyzer, temp_dir):
        try:
            from PIL import Image

            img_path = temp_dir / "mri_test.png"
            img = Image.new("L", (100, 100), color=128)
            img.save(img_path)
            result = analyzer.analyze(str(img_path))
        except ImportError:
            pytest.skip("PIL not installed")

        assert "vertebrae" in result
        assert "discs" in result
        assert "abnormalities" in result
        assert "image_quality" in result
        assert result["image_quality"] > 0

    def test_analyze_with_nonexistent_image(self, analyzer, temp_dir):
        fake_path = temp_dir / "nonexistent.png"
        result = analyzer.analyze(str(fake_path))

        assert "vertebrae" in result
        assert "discs" in result
        assert "abnormalities" in result

    def test_image_quality_assessment(self, analyzer, temp_dir):
        try:
            from PIL import Image

            img_path = temp_dir / "quality_test.png"
            img = Image.new("L", (50, 50), color=100)
            img.save(img_path)
            image = analyzer._load_image(Path(img_path))
            quality = analyzer._assess_quality(image)
        except ImportError:
            pytest.skip("PIL not installed")

        assert 0.0 <= quality <= 1.0

    def test_image_quality_none_image(self, analyzer):
        assert analyzer._assess_quality(None) == 0.0


# ---------------------------------------------------------------------------
# Feature extraction tests from main-dev
# ---------------------------------------------------------------------------
class TestImageAnalyzerFeatureExtraction:
    """Unit tests for ImageAnalyzer feature extraction."""

    def test_initialization_without_torch(self, basic_config):
        with patch("sage.apps.medical_diagnosis.agents.image_analyzer.TORCH_AVAILABLE", False):
            analyzer = ImageAnalyzer(basic_config)
            assert analyzer.feature_model is None
            assert analyzer.feature_processor is None

    def test_initialization_with_clip(self, basic_config):
        if not TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")

        with (
            patch("sage.apps.medical_diagnosis.agents.image_analyzer.CLIPProcessor") as mock_proc,
            patch("sage.apps.medical_diagnosis.agents.image_analyzer.CLIPModel") as mock_model,
        ):
            mock_proc.from_pretrained.return_value = MagicMock()
            mock_model.from_pretrained.return_value = MagicMock()
            analyzer = ImageAnalyzer(basic_config)

        assert analyzer.feature_method == "clip"

    def test_initialization_with_dinov2(self, dinov2_config):
        if not TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")

        with (
            patch(
                "sage.apps.medical_diagnosis.agents.image_analyzer.AutoImageProcessor"
            ) as mock_proc,
            patch("sage.apps.medical_diagnosis.agents.image_analyzer.AutoModel") as mock_model,
        ):
            mock_proc.from_pretrained.return_value = MagicMock()
            mock_model.from_pretrained.return_value = MagicMock()
            analyzer = ImageAnalyzer(dinov2_config)

        assert analyzer.feature_method == "dinov2"

    def test_mock_features_fallback(self, basic_config, mock_image):
        with patch("sage.apps.medical_diagnosis.agents.image_analyzer.TORCH_AVAILABLE", False):
            analyzer = ImageAnalyzer(basic_config)
            features = analyzer._extract_features(mock_image)

        assert features is not None
        assert isinstance(features, np.ndarray)
        assert features.shape == (768,)
        assert features.dtype == np.float32

    def test_extract_features_with_none_image(self, basic_config):
        analyzer = ImageAnalyzer(basic_config)
        assert analyzer._extract_features(None) is None

    def test_extract_features_with_numpy_array(self, basic_config, mock_image):
        with patch("sage.apps.medical_diagnosis.agents.image_analyzer.TORCH_AVAILABLE", False):
            analyzer = ImageAnalyzer(basic_config)
            features = analyzer._extract_features(mock_image)

        assert features is not None
        assert isinstance(features, np.ndarray)
        assert len(features.shape) == 1

    def test_extract_features_error_handling(self, basic_config, mock_image):
        if not TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")

        with (
            patch("sage.apps.medical_diagnosis.agents.image_analyzer.CLIPProcessor") as mock_proc,
            patch("sage.apps.medical_diagnosis.agents.image_analyzer.CLIPModel") as mock_model,
        ):
            mock_proc.from_pretrained.return_value = MagicMock()
            mock_model_instance = MagicMock()
            mock_model_instance.cuda.return_value = mock_model_instance
            mock_model_instance.get_image_features.side_effect = RuntimeError("Model error")
            mock_model.from_pretrained.return_value = mock_model_instance
            analyzer = ImageAnalyzer(basic_config)
            features = analyzer._extract_features(mock_image)

        assert features is not None
        assert isinstance(features, np.ndarray)

    def test_feature_dimension_config(self, mock_image):
        custom_config = {
            "models": {"vision_model": "test"},
            "image_processing": {"feature_extraction": {"method": "clip", "dimension": 512}},
        }

        with patch("sage.apps.medical_diagnosis.agents.image_analyzer.TORCH_AVAILABLE", False):
            analyzer = ImageAnalyzer(custom_config)
            features = analyzer._extract_features(mock_image)

        assert features.shape == (512,)

    def test_analyze_with_nonexistent_image(self, basic_config):
        analyzer = ImageAnalyzer(basic_config)
        result = analyzer.analyze("nonexistent_image.jpg")

        assert "vertebrae" in result
        assert "discs" in result
        assert "abnormalities" in result
        assert "image_quality" in result
        assert "image_embedding" in result

    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_clip_feature_extraction_shape(self, basic_config, mock_pil_image):
        with (
            patch(
                "sage.apps.medical_diagnosis.agents.image_analyzer.CLIPProcessor"
            ) as mock_proc_cls,
            patch("sage.apps.medical_diagnosis.agents.image_analyzer.CLIPModel") as mock_model_cls,
        ):
            import torch

            mock_processor = MagicMock()
            mock_processor.return_value = {"pixel_values": torch.randn(1, 3, 224, 224)}
            mock_proc_cls.from_pretrained.return_value = mock_processor

            mock_model = MagicMock()
            mock_features = torch.randn(1, 512)
            mock_model.get_image_features.return_value = mock_features
            mock_model_cls.from_pretrained.return_value = mock_model

            analyzer = ImageAnalyzer(basic_config)
            analyzer.feature_processor = mock_processor
            analyzer.feature_model = mock_model
            features = analyzer._extract_clip_features(mock_pil_image)

        assert isinstance(features, np.ndarray)
        assert features.dtype == np.float32
        assert len(features.shape) == 1
        assert np.isclose(np.linalg.norm(features), 1.0, rtol=1e-5)

    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_dinov2_feature_extraction_shape(self, dinov2_config, mock_pil_image):
        with (
            patch(
                "sage.apps.medical_diagnosis.agents.image_analyzer.AutoImageProcessor"
            ) as mock_proc_cls,
            patch("sage.apps.medical_diagnosis.agents.image_analyzer.AutoModel") as mock_model_cls,
        ):
            import torch

            mock_processor = MagicMock()
            mock_processor.return_value = {"pixel_values": torch.randn(1, 3, 224, 224)}
            mock_proc_cls.from_pretrained.return_value = mock_processor

            mock_model = MagicMock()
            mock_output = MagicMock()
            mock_output.last_hidden_state = torch.randn(1, 197, 768)
            mock_model.return_value = mock_output
            mock_model_cls.from_pretrained.return_value = mock_model

            analyzer = ImageAnalyzer(dinov2_config)
            analyzer.feature_processor = mock_processor
            analyzer.feature_model = mock_model
            features = analyzer._extract_dinov2_features(mock_pil_image)

        assert isinstance(features, np.ndarray)
        assert features.dtype == np.float32
        assert len(features.shape) == 1
        assert np.isclose(np.linalg.norm(features), 1.0, rtol=1e-5)

    def test_unknown_feature_method(self, mock_image):
        config = {
            "models": {"vision_model": "test"},
            "image_processing": {"feature_extraction": {"method": "unknown", "dimension": 768}},
        }

        analyzer = ImageAnalyzer(config)
        features = analyzer._extract_features(mock_image)

        assert features is not None
        assert features.shape == (768,)


class TestImageAnalyzerFeatureIntegration:
    """Integration-style tests focusing on feature extraction pipeline."""

    def test_full_analysis_pipeline(self, basic_config, tmp_path):
        if not TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")

        from PIL import Image

        test_image_path = tmp_path / "test_mri.png"
        test_image = Image.fromarray(
            np.random.randint(0, 255, (512, 512), dtype=np.uint8), mode="L"
        )
        test_image.save(test_image_path)

        with (
            patch("sage.apps.medical_diagnosis.agents.image_analyzer.CLIPProcessor") as mock_proc,
            patch("sage.apps.medical_diagnosis.agents.image_analyzer.CLIPModel") as mock_model,
        ):
            mock_proc.from_pretrained.return_value = MagicMock()
            mock_model.from_pretrained.return_value = MagicMock()
            analyzer = ImageAnalyzer(basic_config)
            result = analyzer.analyze(str(test_image_path))

        assert "vertebrae" in result
        assert "discs" in result
        assert "abnormalities" in result
        assert "image_quality" in result
        assert "image_embedding" in result
        assert result["image_path"] == str(test_image_path)
        assert len(result["vertebrae"]) == 5
        assert len(result["discs"]) == 5

    def test_create_mock_analysis(self, basic_config):
        analyzer = ImageAnalyzer(basic_config)
        result = analyzer._create_mock_analysis()

        assert isinstance(result["vertebrae"], list)
        assert isinstance(result["discs"], list)
        assert isinstance(result["abnormalities"], list)
        assert isinstance(result["image_quality"], float)
        assert isinstance(result["image_embedding"], np.ndarray)
        assert result["image_embedding"].shape == (768,)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
