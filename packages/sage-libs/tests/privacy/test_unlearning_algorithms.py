"""
Tests for privacy/unlearning algorithms

Tests cover:
- LaplaceMechanism: Noise generation, privacy cost
- GaussianMechanism: Noise generation, privacy cost
"""

import math

import numpy as np
import pytest


@pytest.mark.unit
class TestLaplaceMechanism:
    """Test LaplaceMechanism"""

    def test_init(self):
        """测试初始化"""
        from sage.libs.privacy.unlearning.algorithms.laplace_unlearning import LaplaceMechanism

        mechanism = LaplaceMechanism(epsilon=1.0, sensitivity=2.0)

        assert mechanism.epsilon == 1.0
        assert mechanism.sensitivity == 2.0
        assert mechanism.delta is None
        assert mechanism.name == "Laplace"

    def test_compute_noise(self):
        """测试生成噪声"""
        from sage.libs.privacy.unlearning.algorithms.laplace_unlearning import LaplaceMechanism

        mechanism = LaplaceMechanism(epsilon=1.0, sensitivity=1.0)

        # Set random seed for reproducibility
        np.random.seed(42)
        noise = mechanism.compute_noise()

        assert isinstance(noise, (float, np.floating))
        # Noise should be drawn from Laplace distribution

    def test_compute_noise_with_custom_params(self):
        """测试使用自定义参数生成噪声"""
        from sage.libs.privacy.unlearning.algorithms.laplace_unlearning import LaplaceMechanism

        mechanism = LaplaceMechanism(epsilon=1.0, sensitivity=1.0)

        np.random.seed(42)
        noise = mechanism.compute_noise(sensitivity=2.0, epsilon=0.5)

        assert isinstance(noise, (float, np.floating))

    def test_compute_noise_with_clipping(self):
        """测试带裁剪的噪声生成"""
        from sage.libs.privacy.unlearning.algorithms.laplace_unlearning import LaplaceMechanism

        mechanism = LaplaceMechanism(epsilon=1.0, sensitivity=1.0, clip_bound=5.0)

        np.random.seed(42)
        noise = mechanism.compute_noise()

        assert abs(noise) <= 5.0

    def test_privacy_cost(self):
        """测试隐私成本"""
        from sage.libs.privacy.unlearning.algorithms.laplace_unlearning import LaplaceMechanism

        mechanism = LaplaceMechanism(epsilon=1.0)
        epsilon, delta = mechanism.privacy_cost()

        assert epsilon == 1.0
        assert delta == 0.0  # Pure DP has no delta


@pytest.mark.unit
class TestGaussianMechanism:
    """Test GaussianMechanism"""

    def test_init(self):
        """测试初始化"""
        from sage.libs.privacy.unlearning.algorithms.gaussian_unlearning import GaussianMechanism

        mechanism = GaussianMechanism(epsilon=1.0, delta=1e-5, sensitivity=2.0)

        assert mechanism.epsilon == 1.0
        assert mechanism.delta == 1e-5
        assert mechanism.sensitivity == 2.0
        assert mechanism.name == "Gaussian"
        assert mechanism.sigma > 0

    def test_compute_sigma(self):
        """测试计算sigma"""
        from sage.libs.privacy.unlearning.algorithms.gaussian_unlearning import GaussianMechanism

        mechanism = GaussianMechanism(epsilon=1.0, delta=1e-5, sensitivity=1.0)

        # Verify sigma is computed correctly
        expected_sigma = 1.0 * math.sqrt(2 * math.log(1.25 / 1e-5)) / 1.0
        assert abs(mechanism.sigma - expected_sigma) < 1e-6

    def test_invalid_delta(self):
        """测试无效的delta值"""
        from sage.libs.privacy.unlearning.algorithms.gaussian_unlearning import GaussianMechanism

        with pytest.raises(ValueError, match="delta must be in"):
            GaussianMechanism(epsilon=1.0, delta=0.0, sensitivity=1.0)

        with pytest.raises(ValueError, match="delta must be in"):
            GaussianMechanism(epsilon=1.0, delta=1.0, sensitivity=1.0)

    def test_compute_noise(self):
        """测试生成噪声"""
        from sage.libs.privacy.unlearning.algorithms.gaussian_unlearning import GaussianMechanism

        mechanism = GaussianMechanism(epsilon=1.0, delta=1e-5, sensitivity=1.0)

        np.random.seed(42)
        noise = mechanism.compute_noise()

        assert isinstance(noise, (float, np.floating))

    def test_privacy_cost(self):
        """测试隐私成本"""
        from sage.libs.privacy.unlearning.algorithms.gaussian_unlearning import GaussianMechanism

        mechanism = GaussianMechanism(epsilon=1.0, delta=1e-5)
        epsilon, delta = mechanism.privacy_cost()

        assert epsilon == 1.0
        assert delta == 1e-5
