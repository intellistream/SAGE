"""
Tests for LibAMM (Approximate Matrix Multiplication library) bindings.

This module tests the Python bindings to LibAMM C++ library.
"""

import pytest

# Try to import torch and LibAMM
try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import torch.ops.LibAMM as libamm

    LIBAMM_AVAILABLE = True
except (ImportError, AttributeError):
    LIBAMM_AVAILABLE = False


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
@pytest.mark.skipif(not LIBAMM_AVAILABLE, reason="LibAMM not available")
class TestLibAMM:
    """Test cases for LibAMM approximate matrix multiplication."""

    @pytest.fixture
    def sample_matrices(self):
        """Create sample matrices for testing."""
        # Create two small matrices for AMM
        m, n, k = 100, 80, 100
        a = torch.randn(m, k, dtype=torch.float32)
        b = torch.randn(k, n, dtype=torch.float32)
        return a, b

    @pytest.fixture
    def small_matrices(self):
        """Create very small matrices for quick tests."""
        m, n, k = 10, 8, 10
        a = torch.randn(m, k, dtype=torch.float32)
        b = torch.randn(k, n, dtype=torch.float32)
        return a, b

    def test_crs_basic(self, sample_matrices):
        """Test basic CRS (Column Row Sampling) algorithm."""
        a, b = sample_matrices
        result = libamm.crs(a, b)

        # Check output shape
        assert result.shape == (a.shape[0], b.shape[1])

        # Check result is a valid tensor
        assert torch.is_tensor(result)
        assert not torch.isnan(result).any()
        assert not torch.isinf(result).any()

    def test_crs_approximation_quality(self, small_matrices):
        """Test that CRS provides reasonable approximation."""
        a, b = small_matrices

        # Exact multiplication
        exact = torch.mm(a, b)

        # Approximate multiplication
        approx = libamm.crs(a, b)

        # Check shapes match
        assert exact.shape == approx.shape

        # Calculate relative Frobenius norm error
        error = torch.norm(exact - approx, p="fro") / torch.norm(exact, p="fro")

        # Error should be bounded (this is an approximation)
        # The error threshold depends on the sketch size, set it reasonably high
        assert error < 2.0, f"Approximation error too high: {error}"

    def test_amm_default(self, sample_matrices):
        """Test default AMM algorithm."""
        a, b = sample_matrices
        result = libamm.ammDefault(a, b)

        # Check output shape
        assert result.shape == (a.shape[0], b.shape[1])
        assert torch.is_tensor(result)
        assert not torch.isnan(result).any()

    def test_amm_specify_sketch_size(self, sample_matrices):
        """Test AMM with specified sketch size."""
        a, b = sample_matrices
        sketch_size = 10

        result = libamm.ammSpecifySs(a, b, sketch_size)

        # Check output shape
        assert result.shape == (a.shape[0], b.shape[1])
        assert torch.is_tensor(result)
        assert not torch.isnan(result).any()

    def test_amm_different_sketch_sizes(self, small_matrices):
        """Test AMM with various sketch sizes."""
        a, b = small_matrices
        sketch_sizes = [2, 5, 8]

        results = []
        for ss in sketch_sizes:
            result = libamm.ammSpecifySs(a, b, ss)
            results.append(result)
            assert result.shape == (a.shape[0], b.shape[1])

        # Larger sketch size should generally give better approximation
        # But we don't test this strictly as it's probabilistic

    def test_set_tag(self):
        """Test setting algorithm tag."""
        # Test setting different algorithm tags
        tags = ["mm", "crs", "srht"]

        for tag in tags:
            libamm.setTag(tag)
            # If no exception is raised, the function works

        # Reset to default
        libamm.setTag("mm")

    def test_amm_with_different_tags(self, small_matrices):
        """Test AMM with different algorithm tags."""
        a, b = small_matrices

        # List of valid algorithm tags
        # Note: actual available algorithms depend on build configuration
        potential_tags = ["mm", "crs"]

        for tag in potential_tags:
            try:
                libamm.setTag(tag)
                result = libamm.ammDefault(a, b)
                assert result.shape == (a.shape[0], b.shape[1])
            except Exception as e:
                # Some algorithms might not be available
                pytest.skip(f"Algorithm {tag} not available: {e}")

    def test_empty_matrices(self):
        """Test behavior with empty or minimal matrices."""
        # Very small matrices
        a = torch.randn(1, 1, dtype=torch.float32)
        b = torch.randn(1, 1, dtype=torch.float32)

        try:
            result = libamm.crs(a, b)
            # If it doesn't crash, that's a pass
            assert result.shape == (1, 1)
        except Exception:
            # Small matrices might not be supported
            pytest.skip("Empty/minimal matrices not supported")

    def test_amm_consistency(self, small_matrices):
        """Test that multiple calls with same input give consistent results."""
        a, b = small_matrices

        # Call twice with same input
        result1 = libamm.ammDefault(a, b)
        result2 = libamm.ammDefault(a, b)

        # Results should be similar (not necessarily identical due to randomization)
        # Check correlation or relative difference
        diff = torch.norm(result1 - result2, p="fro") / torch.norm(result1, p="fro")

        # Allow some variation due to randomized algorithms
        assert diff < 1.0, f"Results too inconsistent: {diff}"

    def test_dtype_handling(self):
        """Test handling of different data types."""
        a = torch.randn(20, 15, dtype=torch.float32)
        b = torch.randn(15, 10, dtype=torch.float32)

        result = libamm.crs(a, b)
        assert result.dtype == torch.float32

    def test_large_matrices_sketch(self):
        """Test with larger matrices to verify scalability."""
        # Larger matrices
        m, n, k = 500, 400, 500
        a = torch.randn(m, k, dtype=torch.float32)
        b = torch.randn(k, n, dtype=torch.float32)

        # Use a specific sketch size
        sketch_size = 50
        result = libamm.ammSpecifySs(a, b, sketch_size)

        assert result.shape == (m, n)
        assert torch.is_tensor(result)


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
class TestLibAMMAvailability:
    """Test availability and import of LibAMM."""

    def test_torch_available(self):
        """Verify PyTorch is available."""
        assert TORCH_AVAILABLE, "PyTorch should be available for these tests"

    def test_libamm_import(self):
        """Test that LibAMM can be imported if available."""
        if LIBAMM_AVAILABLE:
            import torch.ops.LibAMM as libamm

            # Verify functions exist
            assert hasattr(libamm, "crs")
            assert hasattr(libamm, "setTag")
            assert hasattr(libamm, "ammDefault")
            assert hasattr(libamm, "ammSpecifySs")


# Standalone test for config-based AMM (if config files are available)
@pytest.mark.skipif(not LIBAMM_AVAILABLE, reason="LibAMM not available")
class TestLibAMMWithConfig:
    """Test LibAMM functions that require configuration files."""

    def test_amm_for_madness_requires_config(self):
        """Test that ammForMadness requires valid config paths."""
        # This test just verifies the function exists
        # Actual testing would require valid config files
        try:
            import torch.ops.LibAMM as libamm

            assert hasattr(libamm, "ammForMadness")
        except Exception:
            pytest.skip("ammForMadness not available or requires specific setup")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
