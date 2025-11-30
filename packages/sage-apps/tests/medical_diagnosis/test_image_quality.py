#!/usr/bin/env python3
"""
测试影像质量评估算法
"""

import numpy as np
import pytest

from sage.apps.medical_diagnosis.agents.image_analyzer import ImageAnalyzer


class TestImageQualityAssessment:
    """测试影像质量评估功能"""

    @pytest.fixture
    def analyzer(self):
        """创建ImageAnalyzer实例"""
        config = {"models": {"vision_model": "test-model"}}
        return ImageAnalyzer(config)

    def test_assess_quality_none_image(self, analyzer):
        """测试None图像的质量评估"""
        score = analyzer._assess_quality(None)
        assert score == 0.0, "None图像应返回0.0分数"

    def test_assess_quality_high_quality_image(self, analyzer):
        """测试高质量图像（高对比度、清晰）"""
        # 创建一个清晰的高对比度图像（棋盘格）
        size = 100
        image = np.zeros((size, size), dtype=np.uint8)
        # 创建棋盘格模式
        for i in range(size):
            for j in range(size):
                if (i // 10 + j // 10) % 2 == 0:
                    image[i, j] = 255

        score = analyzer._assess_quality(image)
        # 高质量图像应该有较高分数
        assert 0.0 <= score <= 1.0, f"分数应在[0,1]范围内，实际: {score}"
        assert score > 0.6, f"高质量图像应有较高分数 (>0.6)，实际: {score}"

    def test_assess_quality_low_quality_blurry_image(self, analyzer):
        """测试低质量图像（模糊）"""
        # 创建模糊图像（均匀灰度）
        size = 100
        image = np.ones((size, size), dtype=np.uint8) * 128

        score = analyzer._assess_quality(image)
        assert 0.0 <= score <= 1.0, f"分数应在[0,1]范围内，实际: {score}"
        # 模糊图像应该有较低分数（对比度低、清晰度低）
        assert score < 0.8, f"模糊图像应有较低分数 (<0.8)，实际: {score}"

    def test_assess_quality_noisy_image(self, analyzer):
        """测试噪声图像"""
        # 创建随机噪声图像
        size = 100
        np.random.seed(42)
        image = np.random.randint(0, 256, (size, size), dtype=np.uint8)

        score = analyzer._assess_quality(image)
        assert 0.0 <= score <= 1.0, f"分数应在[0,1]范围内，实际: {score}"
        # 噪声图像可能有不同分数，主要测试不会崩溃

    def test_assess_quality_dark_image(self, analyzer):
        """测试暗图像（亮度过低）"""
        # 创建暗图像
        size = 100
        image = np.ones((size, size), dtype=np.uint8) * 30  # 很暗

        score = analyzer._assess_quality(image)
        assert 0.0 <= score <= 1.0, f"分数应在[0,1]范围内，实际: {score}"
        # 亮度不佳的图像分数应该受影响

    def test_assess_quality_bright_image(self, analyzer):
        """测试亮图像（亮度过高）"""
        # 创建亮图像
        size = 100
        image = np.ones((size, size), dtype=np.uint8) * 240  # 很亮

        score = analyzer._assess_quality(image)
        assert 0.0 <= score <= 1.0, f"分数应在[0,1]范围内，实际: {score}"

    def test_assess_quality_normalized_image(self, analyzer):
        """测试已归一化图像（0-1范围）"""
        # 创建0-1范围的图像
        size = 100
        image = np.random.rand(size, size).astype(np.float32)

        score = analyzer._assess_quality(image)
        assert 0.0 <= score <= 1.0, f"分数应在[0,1]范围内，实际: {score}"

    def test_assess_quality_edge_cases(self, analyzer):
        """测试边缘情况"""
        # 测试单像素图像
        small_image = np.array([[128]], dtype=np.uint8)
        score = analyzer._assess_quality(small_image)
        assert 0.0 <= score <= 1.0, "单像素图像应返回有效分数"

        # 测试全黑图像
        black_image = np.zeros((50, 50), dtype=np.uint8)
        score = analyzer._assess_quality(black_image)
        assert 0.0 <= score <= 1.0, "全黑图像应返回有效分数"

        # 测试全白图像
        white_image = np.ones((50, 50), dtype=np.uint8) * 255
        score = analyzer._assess_quality(white_image)
        assert 0.0 <= score <= 1.0, "全白图像应返回有效分数"

    def test_assess_quality_realistic_medical_image(self, analyzer):
        """测试模拟真实医学影像"""
        # 创建模拟MRI影像（带有结构和渐变）
        size = 200
        image = np.zeros((size, size), dtype=np.uint8)

        # 添加背景渐变
        for i in range(size):
            for j in range(size):
                image[i, j] = int(100 + 50 * np.sin(i / 20) * np.cos(j / 20))

        # 添加一些"结构"（模拟椎体）
        for k in range(5):
            y_center = 40 + k * 30
            for i in range(max(0, y_center - 15), min(size, y_center + 15)):
                for j in range(80, 120):
                    dist = np.sqrt((i - y_center) ** 2 + (j - 100) ** 2)
                    if dist < 15:
                        image[i, j] = 180

        score = analyzer._assess_quality(image)
        assert 0.0 <= score <= 1.0, f"分数应在[0,1]范围内，实际: {score}"
        # 有结构的图像应该有合理的分数
        assert 0.3 <= score <= 0.9, f"模拟医学影像应有合理分数，实际: {score}"

    def test_assess_quality_consistency(self, analyzer):
        """测试评估一致性（同一图像多次评估应得到相同结果）"""
        size = 100
        image = np.random.RandomState(42).randint(0, 256, (size, size), dtype=np.uint8)

        score1 = analyzer._assess_quality(image)
        score2 = analyzer._assess_quality(image)

        assert score1 == score2, "同一图像的评估应该一致"

    def test_assess_quality_different_types(self, analyzer):
        """测试不同数据类型的图像"""
        size = 50

        # uint8 类型
        img_uint8 = np.random.RandomState(42).randint(0, 256, (size, size), dtype=np.uint8)
        score_uint8 = analyzer._assess_quality(img_uint8)
        assert 0.0 <= score_uint8 <= 1.0

        # float32 类型 (0-1)
        img_float32 = img_uint8.astype(np.float32) / 255.0
        score_float32 = analyzer._assess_quality(img_float32)
        assert 0.0 <= score_float32 <= 1.0

        # 两种类型应该给出相近的结果
        assert abs(score_uint8 - score_float32) < 0.1, "不同类型相同内容应给出相近分数"

    def test_quality_penalizes_added_noise(self, analyzer):
        """干净图像应比加噪图像获得更高分"""
        size = 128
        gradient = np.tile(np.linspace(30, 220, size, dtype=np.float32), (size, 1))
        clean = gradient.astype(np.uint8)
        rng = np.random.RandomState(7)
        noisy = np.clip(clean + rng.normal(0, 25, clean.shape), 0, 255).astype(np.uint8)

        clean_score = analyzer._assess_quality(clean)
        noisy_score = analyzer._assess_quality(noisy)

        assert clean_score > noisy_score, "加噪后应降低质量分数"

    def test_brightness_histogram_balance(self, analyzer):
        """亮度直方图平衡的图像应优于过曝/欠曝图像"""
        size = 200
        balanced_line = np.linspace(0, 255, size, dtype=np.float32)
        balanced = np.tile(balanced_line, (size, 1)).astype(np.uint8)
        bright = np.ones((size, size), dtype=np.uint8) * 240
        dark = np.ones((size, size), dtype=np.uint8) * 15

        balanced_score = analyzer._assess_quality(balanced)
        bright_score = analyzer._assess_quality(bright)
        dark_score = analyzer._assess_quality(dark)

        assert balanced_score > bright_score
        assert balanced_score > dark_score
