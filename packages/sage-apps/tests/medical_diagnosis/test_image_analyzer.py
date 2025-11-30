#!/usr/bin/env python3
"""
Unit tests for ImageAnalyzer feature extraction
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Import the ImageAnalyzer
from sage.apps.medical_diagnosis.agents.image_analyzer import TORCH_AVAILABLE, ImageAnalyzer


@pytest.fixture
def basic_config():
    """Basic configuration for testing"""
    return {
        "models": {"vision_model": "Qwen/Qwen2-VL-7B-Instruct"},
        "image_processing": {"feature_extraction": {"method": "clip", "dimension": 768}},
    }


@pytest.fixture
def dinov2_config():
    """Configuration for DINOv2"""
    return {
        "models": {"vision_model": "Qwen/Qwen2-VL-7B-Instruct"},
        "image_processing": {"feature_extraction": {"method": "dinov2", "dimension": 768}},
    }


@pytest.fixture
def mock_image():
    """Create a mock grayscale image"""
    return np.random.randint(0, 255, (512, 512), dtype=np.uint8)


@pytest.fixture
def mock_pil_image():
    """Create a mock PIL image"""
    if not TORCH_AVAILABLE:
        pytest.skip("PyTorch not available")
    from PIL import Image

    return Image.fromarray(np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8))


class TestImageAnalyzerFeatureExtraction:
    """Test feature extraction functionality"""

    def test_initialization_without_torch(self, basic_config):
        """Test initialization when PyTorch is not available"""
        with patch("sage.apps.medical_diagnosis.agents.image_analyzer.TORCH_AVAILABLE", False):
            analyzer = ImageAnalyzer(basic_config)
            assert analyzer.feature_model is None
            assert analyzer.feature_processor is None

    def test_initialization_with_clip(self, basic_config):
        """Test initialization with CLIP model"""
        if not TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")

        # Mock the model loading to avoid downloading
        with (
            patch(
                "sage.apps.medical_diagnosis.agents.image_analyzer.CLIPProcessor"
            ) as mock_processor,
            patch("sage.apps.medical_diagnosis.agents.image_analyzer.CLIPModel") as mock_model,
        ):
            mock_processor.from_pretrained.return_value = MagicMock()
            mock_model.from_pretrained.return_value = MagicMock()

            analyzer = ImageAnalyzer(basic_config)
            assert analyzer.feature_method == "clip"

    def test_initialization_with_dinov2(self, dinov2_config):
        """Test initialization with DINOv2 model"""
        if not TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")

        # Mock the model loading to avoid downloading
        with (
            patch(
                "sage.apps.medical_diagnosis.agents.image_analyzer.AutoImageProcessor"
            ) as mock_processor,
            patch("sage.apps.medical_diagnosis.agents.image_analyzer.AutoModel") as mock_model,
        ):
            mock_processor.from_pretrained.return_value = MagicMock()
            mock_model.from_pretrained.return_value = MagicMock()

            analyzer = ImageAnalyzer(dinov2_config)
            assert analyzer.feature_method == "dinov2"

    def test_mock_features_fallback(self, basic_config, mock_image):
        """Test fallback to mock features when model is not available"""
        # Disable torch to force mock features
        with patch("sage.apps.medical_diagnosis.agents.image_analyzer.TORCH_AVAILABLE", False):
            analyzer = ImageAnalyzer(basic_config)
            features = analyzer._extract_features(mock_image)

            assert features is not None
            assert isinstance(features, np.ndarray)
            assert features.shape == (768,)
            assert features.dtype == np.float32

    def test_extract_features_with_none_image(self, basic_config):
        """Test feature extraction with None image"""
        analyzer = ImageAnalyzer(basic_config)
        features = analyzer._extract_features(None)
        assert features is None

    def test_extract_features_with_numpy_array(self, basic_config, mock_image):
        """Test feature extraction with numpy array input"""
        # Mock the model to avoid actual inference
        with patch("sage.apps.medical_diagnosis.agents.image_analyzer.TORCH_AVAILABLE", False):
            analyzer = ImageAnalyzer(basic_config)
            features = analyzer._extract_features(mock_image)

            assert features is not None
            assert isinstance(features, np.ndarray)
            assert len(features.shape) == 1  # Should be 1D vector

    def test_extract_features_error_handling(self, basic_config, mock_image):
        """Test error handling in feature extraction"""
        if not TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")

        # Mock model that raises an error
        with (
            patch(
                "sage.apps.medical_diagnosis.agents.image_analyzer.CLIPProcessor"
            ) as mock_processor,
            patch("sage.apps.medical_diagnosis.agents.image_analyzer.CLIPModel") as mock_model,
        ):
            mock_processor.from_pretrained.return_value = MagicMock()
            mock_model_instance = MagicMock()
            mock_model_instance.get_image_features.side_effect = RuntimeError("Model error")
            mock_model.from_pretrained.return_value = mock_model_instance

            analyzer = ImageAnalyzer(basic_config)
            # Should fallback to mock features on error
            features = analyzer._extract_features(mock_image)

            assert features is not None
            assert isinstance(features, np.ndarray)

    def test_feature_dimension_config(self, mock_image):
        """Test custom feature dimension configuration"""
        custom_config = {
            "models": {"vision_model": "test"},
            "image_processing": {"feature_extraction": {"method": "clip", "dimension": 512}},
        }

        with patch("sage.apps.medical_diagnosis.agents.image_analyzer.TORCH_AVAILABLE", False):
            analyzer = ImageAnalyzer(custom_config)
            features = analyzer._extract_features(mock_image)

            assert features.shape == (512,)

    def test_analyze_with_nonexistent_image(self, basic_config):
        """Test analyze method with non-existent image"""
        analyzer = ImageAnalyzer(basic_config)
        result = analyzer.analyze("nonexistent_image.jpg")

        # Should return mock analysis
        assert "vertebrae" in result
        assert "discs" in result
        assert "abnormalities" in result
        assert "image_quality" in result
        assert "image_embedding" in result

    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_clip_feature_extraction_shape(self, basic_config, mock_pil_image):
        """Test CLIP feature extraction output shape"""
        with (
            patch(
                "sage.apps.medical_diagnosis.agents.image_analyzer.CLIPProcessor"
            ) as mock_processor_class,
            patch(
                "sage.apps.medical_diagnosis.agents.image_analyzer.CLIPModel"
            ) as mock_model_class,
        ):
            import torch

            # Create mock processor
            mock_processor = MagicMock()
            mock_processor.return_value = {"pixel_values": torch.randn(1, 3, 224, 224)}
            mock_processor_class.from_pretrained.return_value = mock_processor

            # Create mock model
            mock_model = MagicMock()
            mock_features = torch.randn(1, 512)  # CLIP base outputs 512-dim features
            mock_model.get_image_features.return_value = mock_features
            mock_model_class.from_pretrained.return_value = mock_model

            analyzer = ImageAnalyzer(basic_config)
            analyzer.feature_processor = mock_processor
            analyzer.feature_model = mock_model

            features = analyzer._extract_clip_features(mock_pil_image)

            assert isinstance(features, np.ndarray)
            assert features.dtype == np.float32
            assert len(features.shape) == 1
            # Check if normalized
            assert np.isclose(np.linalg.norm(features), 1.0, rtol=1e-5)

    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_dinov2_feature_extraction_shape(self, dinov2_config, mock_pil_image):
        """Test DINOv2 feature extraction output shape"""
        with (
            patch(
                "sage.apps.medical_diagnosis.agents.image_analyzer.AutoImageProcessor"
            ) as mock_processor_class,
            patch(
                "sage.apps.medical_diagnosis.agents.image_analyzer.AutoModel"
            ) as mock_model_class,
        ):
            import torch

            # Create mock processor
            mock_processor = MagicMock()
            mock_processor.return_value = {"pixel_values": torch.randn(1, 3, 224, 224)}
            mock_processor_class.from_pretrained.return_value = mock_processor

            # Create mock model with last_hidden_state
            mock_model = MagicMock()
            mock_output = MagicMock()
            mock_output.last_hidden_state = torch.randn(1, 197, 768)  # DINOv2 base
            mock_model.return_value = mock_output
            mock_model_class.from_pretrained.return_value = mock_model

            analyzer = ImageAnalyzer(dinov2_config)
            analyzer.feature_processor = mock_processor
            analyzer.feature_model = mock_model

            features = analyzer._extract_dinov2_features(mock_pil_image)

            assert isinstance(features, np.ndarray)
            assert features.dtype == np.float32
            assert len(features.shape) == 1
            # Check if normalized
            assert np.isclose(np.linalg.norm(features), 1.0, rtol=1e-5)

    def test_unknown_feature_method(self, mock_image):
        """Test handling of unknown feature extraction method"""
        config = {
            "models": {"vision_model": "test"},
            "image_processing": {
                "feature_extraction": {"method": "unknown_method", "dimension": 768}
            },
        }

        analyzer = ImageAnalyzer(config)
        features = analyzer._extract_features(mock_image)

        # Should fallback to mock features
        assert features is not None
        assert features.shape == (768,)


class TestImageAnalyzerIntegration:
    """Integration tests for ImageAnalyzer"""

    def test_full_analysis_pipeline(self, basic_config, tmp_path):
        """Test full analysis pipeline with temporary image"""
        if not TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")

        from PIL import Image

        # Create a temporary test image
        test_image_path = tmp_path / "test_mri.png"
        test_image = Image.fromarray(
            np.random.randint(0, 255, (512, 512), dtype=np.uint8), mode="L"
        )
        test_image.save(test_image_path)

        # Mock the models
        with (
            patch(
                "sage.apps.medical_diagnosis.agents.image_analyzer.CLIPProcessor"
            ) as mock_processor,
            patch("sage.apps.medical_diagnosis.agents.image_analyzer.CLIPModel") as mock_model,
        ):
            mock_processor.from_pretrained.return_value = MagicMock()
            mock_model.from_pretrained.return_value = MagicMock()

            analyzer = ImageAnalyzer(basic_config)
            result = analyzer.analyze(str(test_image_path))

            assert "vertebrae" in result
            assert "discs" in result
            assert "abnormalities" in result
            assert "image_quality" in result
            assert "image_embedding" in result
            assert result["image_path"] == str(test_image_path)

            # Check vertebrae structure
            assert len(result["vertebrae"]) == 5
            for vertebra in result["vertebrae"]:
                assert "name" in vertebra
                assert "position" in vertebra

            # Check discs structure
            assert len(result["discs"]) == 5
            for disc in result["discs"]:
                assert "level" in disc
                assert "features" in disc

    def test_create_mock_analysis(self, basic_config):
        """Test mock analysis creation"""
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
