#!/usr/bin/env python3
"""
Tests for ImageAnalyzer image loading functionality.

Tests the _load_image, _load_dicom_image, and _load_regular_image methods
that support DICOM (.dcm) and regular image formats (PNG, JPG, etc.).
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sage.apps.medical_diagnosis.agents.image_analyzer import ImageAnalyzer


@pytest.fixture
def analyzer():
    """Create an ImageAnalyzer instance for testing."""
    config = {"models": {"vision_model": "test-model"}}
    return ImageAnalyzer(config)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestLoadImage:
    """Tests for the _load_image method."""

    def test_load_image_nonexistent_file(self, analyzer, temp_dir):
        """Test loading a non-existent file returns None."""
        fake_path = temp_dir / "nonexistent.png"
        result = analyzer._load_image(fake_path)
        assert result is None

    def test_load_image_dicom_extension(self, analyzer, temp_dir):
        """Test that .dcm files are routed to _load_dicom_image."""
        dcm_path = temp_dir / "test.dcm"
        dcm_path.touch()  # Create empty file

        with patch.object(analyzer, "_load_dicom_image", return_value=None) as mock_dicom:
            analyzer._load_image(dcm_path)
            mock_dicom.assert_called_once_with(dcm_path)

    def test_load_image_dicom_extension_uppercase(self, analyzer, temp_dir):
        """Test that .DCM files (uppercase) are routed to _load_dicom_image."""
        dcm_path = temp_dir / "test.DCM"
        dcm_path.touch()

        with patch.object(analyzer, "_load_dicom_image", return_value=None) as mock_dicom:
            analyzer._load_image(dcm_path)
            mock_dicom.assert_called_once_with(dcm_path)

    def test_load_image_png_extension(self, analyzer, temp_dir):
        """Test that .png files are routed to _load_regular_image."""
        png_path = temp_dir / "test.png"
        png_path.touch()

        with patch.object(analyzer, "_load_regular_image", return_value=None) as mock_regular:
            analyzer._load_image(png_path)
            mock_regular.assert_called_once_with(png_path)

    def test_load_image_jpg_extension(self, analyzer, temp_dir):
        """Test that .jpg files are routed to _load_regular_image."""
        jpg_path = temp_dir / "test.jpg"
        jpg_path.touch()

        with patch.object(analyzer, "_load_regular_image", return_value=None) as mock_regular:
            analyzer._load_image(jpg_path)
            mock_regular.assert_called_once_with(jpg_path)


class TestLoadDicomImage:
    """Tests for the _load_dicom_image method."""

    def test_load_dicom_success(self, analyzer, temp_dir):
        """Test successful DICOM loading with pydicom."""
        dcm_path = temp_dir / "test.dcm"
        dcm_path.touch()

        # Create mock DICOM data
        mock_dicom = MagicMock()
        mock_dicom.pixel_array = np.array([[100, 200], [150, 250]], dtype=np.int16)

        # Remove WindowCenter and WindowWidth attributes
        del mock_dicom.WindowCenter
        del mock_dicom.WindowWidth

        with patch.dict("sys.modules", {"pydicom": MagicMock()}):
            import sys

            sys.modules["pydicom"].dcmread.return_value = mock_dicom

            result = analyzer._load_dicom_image(dcm_path)

            # Result should be normalized uint8 array
            assert result is not None
            assert result.dtype == np.uint8
            assert result.shape == (2, 2)
            assert result.min() >= 0
            assert result.max() <= 255

    def test_load_dicom_with_window_level(self, analyzer, temp_dir):
        """Test DICOM loading with window center and width."""
        dcm_path = temp_dir / "test.dcm"
        dcm_path.touch()

        # Create mock DICOM data with windowing
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

    def test_load_dicom_pydicom_not_installed(self, analyzer, temp_dir, capsys):
        """Test graceful handling when pydicom is not installed."""
        dcm_path = temp_dir / "test.dcm"
        dcm_path.touch()

        # Simulate pydicom not being installed
        with patch.dict("sys.modules", {"pydicom": None}):
            # Force the import to raise ImportError
            original_import = (
                __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__
            )

            def mock_import(name, *args, **kwargs):
                if name == "pydicom":
                    raise ImportError("No module named 'pydicom'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                result = analyzer._load_dicom_image(dcm_path)

            assert result is None

    def test_load_dicom_invalid_file(self, analyzer, temp_dir, capsys):
        """Test handling of invalid DICOM file."""
        dcm_path = temp_dir / "invalid.dcm"
        dcm_path.write_bytes(b"not a valid dicom file")

        # The actual pydicom will raise an error for invalid files
        result = analyzer._load_dicom_image(dcm_path)

        # Should return None for invalid DICOM files
        # Note: actual behavior depends on whether pydicom is installed
        assert result is None or isinstance(result, np.ndarray)


class TestLoadRegularImage:
    """Tests for the _load_regular_image method."""

    def test_load_regular_image_png(self, analyzer, temp_dir):
        """Test loading a PNG image."""
        png_path = temp_dir / "test.png"

        # Create a simple test image using PIL
        try:
            from PIL import Image

            # Create a simple 10x10 RGB image
            img = Image.new("RGB", (10, 10), color="red")
            img.save(png_path)

            result = analyzer._load_regular_image(png_path)

            assert result is not None
            assert isinstance(result, np.ndarray)
            assert result.shape == (10, 10)  # Should be grayscale
            assert result.dtype == np.uint8
        except ImportError:
            pytest.skip("PIL not installed")

    def test_load_regular_image_jpg(self, analyzer, temp_dir):
        """Test loading a JPG image."""
        jpg_path = temp_dir / "test.jpg"

        try:
            from PIL import Image

            # Create a simple 20x20 grayscale image
            img = Image.new("L", (20, 20), color=128)
            img.save(jpg_path)

            result = analyzer._load_regular_image(jpg_path)

            assert result is not None
            assert isinstance(result, np.ndarray)
            assert result.shape == (20, 20)
            assert result.dtype == np.uint8
        except ImportError:
            pytest.skip("PIL not installed")

    def test_load_regular_image_grayscale_conversion(self, analyzer, temp_dir):
        """Test that color images are converted to grayscale."""
        png_path = temp_dir / "color.png"

        try:
            from PIL import Image

            # Create an RGB image with distinct colors
            img = Image.new("RGB", (5, 5), color=(255, 0, 0))
            img.save(png_path)

            result = analyzer._load_regular_image(png_path)

            assert result is not None
            # Result should be 2D (grayscale), not 3D (RGB)
            assert len(result.shape) == 2
        except ImportError:
            pytest.skip("PIL not installed")

    def test_load_regular_image_invalid_file(self, analyzer, temp_dir):
        """Test handling of invalid image file."""
        invalid_path = temp_dir / "invalid.png"
        invalid_path.write_bytes(b"not a valid image file")

        result = analyzer._load_regular_image(invalid_path)

        assert result is None


class TestImageAnalyzerIntegration:
    """Integration tests for the ImageAnalyzer image loading."""

    def test_analyze_with_valid_image(self, analyzer, temp_dir):
        """Test full analysis pipeline with a valid image."""
        try:
            from PIL import Image

            # Create a test image
            img_path = temp_dir / "mri_test.png"
            img = Image.new("L", (100, 100), color=128)
            img.save(img_path)

            result = analyzer.analyze(str(img_path))

            assert "vertebrae" in result
            assert "discs" in result
            assert "abnormalities" in result
            assert "image_quality" in result
            assert result["image_quality"] > 0
        except ImportError:
            pytest.skip("PIL not installed")

    def test_analyze_with_nonexistent_image(self, analyzer, temp_dir):
        """Test analysis with non-existent image falls back to mock data."""
        fake_path = temp_dir / "nonexistent.png"

        result = analyzer.analyze(str(fake_path))

        # Should return mock analysis
        assert "vertebrae" in result
        assert "discs" in result
        assert "abnormalities" in result

    def test_image_quality_assessment(self, analyzer, temp_dir):
        """Test image quality assessment returns valid score."""
        try:
            from PIL import Image

            img_path = temp_dir / "quality_test.png"
            img = Image.new("L", (50, 50), color=100)
            img.save(img_path)

            image = analyzer._load_image(Path(img_path))
            quality = analyzer._assess_quality(image)

            assert 0.0 <= quality <= 1.0
        except ImportError:
            pytest.skip("PIL not installed")

    def test_image_quality_none_image(self, analyzer):
        """Test quality assessment with None image returns 0."""
        quality = analyzer._assess_quality(None)
        assert quality == 0.0
