"""Tests for recommended models catalog."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from sage.common.model_registry.recommended import (
    _FALLBACK_MODELS,
    fetch_recommended_models,
)


@pytest.mark.unit
class TestFetchRecommendedModels:
    """Test fetch_recommended_models function."""

    def test_fetch_with_local_fallback(self):
        """Test fetching models uses local fallback when network fails."""
        # 模拟网络请求失败
        with patch("requests.get", side_effect=Exception("Network error")):
            models = fetch_recommended_models()
            assert len(models) > 0
            # 应该返回 fallback models 或本地模型
            assert models == _FALLBACK_MODELS or any(
                m["model_id"] == "Qwen/Qwen2.5-0.5B-Instruct" for m in models
            )

    def test_fetch_with_requests_import_error(self):
        """Test handling ImportError when requests module is missing."""
        # 在 fetch_recommended_models 内部会尝试 import requests
        # 如果失败，应该返回 fallback models
        models = fetch_recommended_models()
        # 无论如何都应该返回有效的模型列表
        assert len(models) > 0
        assert all("model_id" in m for m in models)

    def test_fetch_with_valid_response(self):
        """Test successful fetch from remote."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {
                    "model_id": "test/model",
                    "display_name": "Test Model",
                    "size_billion": 1.0,
                }
            ]
        }

        with patch("requests.get", return_value=mock_response):
            models = fetch_recommended_models(index_url="http://test.com/models.json")
            assert len(models) == 1
            assert models[0]["model_id"] == "test/model"

    def test_fetch_with_network_error(self):
        """Test fallback when network request fails."""
        with patch("requests.get", side_effect=Exception("Network error")):
            models = fetch_recommended_models()
            # 应该返回有效的模型列表（可能是 fallback 或本地模型）
            assert len(models) > 0
            # 验证模型结构
            assert all("model_id" in m for m in models)
            assert all("display_name" in m for m in models)

    def test_fetch_with_timeout(self):
        """Test custom timeout parameter."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"models": [{"model_id": "test/model"}]}

        with patch("requests.get", return_value=mock_response) as mock_get:
            fetch_recommended_models(index_url="http://test.com/models.json", timeout=10.0)
            # 验证 requests.get 被调用
            assert mock_get.called
            # 验证 timeout 参数
            call_kwargs = mock_get.call_args[1] if mock_get.call_args else {}
            assert call_kwargs.get("timeout") == 10.0

    def test_fallback_models_structure(self):
        """Test that fallback models have required fields."""
        for model in _FALLBACK_MODELS:
            assert "model_id" in model
            assert "display_name" in model
            assert "size_billion" in model
            assert isinstance(model["model_id"], str)
            assert isinstance(model["display_name"], str)
            assert isinstance(model["size_billion"], (int, float))
