"""Unit tests for LLM Client singleton and caching functionality.

Tests for Task C5: LLM Service Caching Mechanism.
"""

from unittest.mock import MagicMock, patch


class TestLLMClientSingleton:
    """Test LLM client singleton/caching functionality."""

    def setup_method(self):
        """Clear instances before each test."""
        # Import and clear the global cache
        from sage.common.components.sage_llm import client as client_module

        client_module._llm_client_instances.clear()

    def teardown_method(self):
        """Clear instances after each test."""
        from sage.common.components.sage_llm import client as client_module

        client_module._llm_client_instances.clear()

    def test_get_instance_creates_new_instance(self):
        """Test that get_instance creates a new instance when cache is empty."""
        from sage.common.components.sage_llm.client import IntelligentLLMClient

        # Mock create_auto to avoid actual network calls
        mock_client = MagicMock(spec=IntelligentLLMClient)
        with patch.object(IntelligentLLMClient, "create_auto", return_value=mock_client):
            client = IntelligentLLMClient.get_instance(cache_key="test1")

            assert client is mock_client
            IntelligentLLMClient.create_auto.assert_called_once()

    def test_get_instance_returns_cached_instance(self):
        """Test that get_instance returns cached instance on second call."""
        from sage.common.components.sage_llm.client import IntelligentLLMClient

        mock_client = MagicMock(spec=IntelligentLLMClient)

        with patch.object(IntelligentLLMClient, "create_auto", return_value=mock_client):
            client1 = IntelligentLLMClient.get_instance(cache_key="test2")
            client2 = IntelligentLLMClient.get_instance(cache_key="test2")

            assert client1 is client2
            # create_auto should only be called once
            assert IntelligentLLMClient.create_auto.call_count == 1

    def test_get_instance_different_keys(self):
        """Test that different cache keys create different instances."""
        from sage.common.components.sage_llm.client import IntelligentLLMClient

        mock_client_a = MagicMock(spec=IntelligentLLMClient)
        mock_client_b = MagicMock(spec=IntelligentLLMClient)

        with patch.object(
            IntelligentLLMClient, "create_auto", side_effect=[mock_client_a, mock_client_b]
        ):
            client_a = IntelligentLLMClient.get_instance(cache_key="key_a")
            client_b = IntelligentLLMClient.get_instance(cache_key="key_b")

            assert client_a is not client_b
            assert IntelligentLLMClient.create_auto.call_count == 2

    def test_get_instance_default_key(self):
        """Test get_instance with default cache key."""
        from sage.common.components.sage_llm.client import IntelligentLLMClient

        mock_client = MagicMock(spec=IntelligentLLMClient)

        with patch.object(IntelligentLLMClient, "create_auto", return_value=mock_client):
            client1 = IntelligentLLMClient.get_instance()
            client2 = IntelligentLLMClient.get_instance()

            assert client1 is client2
            assert IntelligentLLMClient.create_auto.call_count == 1

    def test_clear_instances_all(self):
        """Test clearing all cached instances."""
        from sage.common.components.sage_llm.client import IntelligentLLMClient

        mock_client = MagicMock(spec=IntelligentLLMClient)

        with patch.object(IntelligentLLMClient, "create_auto", return_value=mock_client):
            IntelligentLLMClient.get_instance(cache_key="a")
            IntelligentLLMClient.get_instance(cache_key="b")
            IntelligentLLMClient.get_instance(cache_key="c")

            count = IntelligentLLMClient.clear_instances()

            assert count == 3
            assert len(IntelligentLLMClient.get_cached_keys()) == 0

    def test_clear_instances_specific_key(self):
        """Test clearing a specific cached instance."""
        from sage.common.components.sage_llm.client import IntelligentLLMClient

        mock_client = MagicMock(spec=IntelligentLLMClient)

        with patch.object(IntelligentLLMClient, "create_auto", return_value=mock_client):
            IntelligentLLMClient.get_instance(cache_key="keep")
            IntelligentLLMClient.get_instance(cache_key="remove")

            count = IntelligentLLMClient.clear_instances(cache_key="remove")

            assert count == 1
            assert "keep" in IntelligentLLMClient.get_cached_keys()
            assert "remove" not in IntelligentLLMClient.get_cached_keys()

    def test_clear_instances_nonexistent_key(self):
        """Test clearing a non-existent cache key."""
        from sage.common.components.sage_llm.client import IntelligentLLMClient

        count = IntelligentLLMClient.clear_instances(cache_key="nonexistent")
        assert count == 0

    def test_get_cached_keys(self):
        """Test getting list of cached keys."""
        from sage.common.components.sage_llm.client import IntelligentLLMClient

        mock_client = MagicMock(spec=IntelligentLLMClient)

        with patch.object(IntelligentLLMClient, "create_auto", return_value=mock_client):
            IntelligentLLMClient.get_instance(cache_key="alpha")
            IntelligentLLMClient.get_instance(cache_key="beta")

            keys = IntelligentLLMClient.get_cached_keys()

            assert set(keys) == {"alpha", "beta"}


class TestCheckLLMService:
    """Test the check_llm_service utility function."""

    def test_check_llm_service_local_available(self):
        """Test when local service is available."""
        from sage.common.components.sage_llm.client import (
            IntelligentLLMClient,
            check_llm_service,
        )

        with patch.object(
            IntelligentLLMClient, "_probe_vllm_service", return_value="Qwen/Qwen2.5-7B-Instruct"
        ):
            status = check_llm_service(verbose=False)

            assert status["local_available"] is True
            assert status["local_model"] == "Qwen/Qwen2.5-7B-Instruct"
            assert "localhost:8001" in status["local_endpoint"]

    def test_check_llm_service_local_unavailable(self):
        """Test when local service is not available."""
        from sage.common.components.sage_llm.client import (
            IntelligentLLMClient,
            check_llm_service,
        )

        with patch.object(IntelligentLLMClient, "_probe_vllm_service", return_value=None):
            with patch.dict("os.environ", {}, clear=True):
                status = check_llm_service(verbose=False)

                assert status["local_available"] is False
                assert status["local_model"] is None

    def test_check_llm_service_cloud_configured(self):
        """Test when cloud API is configured."""
        from sage.common.components.sage_llm.client import (
            IntelligentLLMClient,
            check_llm_service,
        )

        with patch.object(IntelligentLLMClient, "_probe_vllm_service", return_value=None):
            with patch.dict(
                "os.environ",
                {"SAGE_CHAT_API_KEY": "test-api-key-fake"},  # pragma: allowlist secret
            ):
                status = check_llm_service(verbose=False)

                assert status["cloud_configured"] is True

    def test_check_llm_service_nothing_available(self):
        """Test when neither local nor cloud is available."""
        from sage.common.components.sage_llm.client import (
            IntelligentLLMClient,
            check_llm_service,
        )

        with patch.object(IntelligentLLMClient, "_probe_vllm_service", return_value=None):
            with patch.dict(
                "os.environ", {"SAGE_CHAT_API_KEY": "", "OPENAI_API_KEY": ""}, clear=True
            ):
                status = check_llm_service(verbose=False)

                assert status["local_available"] is False
                assert status["cloud_configured"] is False
                assert "vllm serve" in status["recommended_action"]


class TestGetLLMClient:
    """Test the get_llm_client convenience function."""

    def setup_method(self):
        """Clear instances before each test."""
        from sage.common.components.sage_llm import client as client_module

        client_module._llm_client_instances.clear()

    def teardown_method(self):
        """Clear instances after each test."""
        from sage.common.components.sage_llm import client as client_module

        client_module._llm_client_instances.clear()

    def test_get_llm_client_function(self):
        """Test the convenience function."""
        from sage.common.components.sage_llm.client import (
            IntelligentLLMClient,
            get_llm_client,
        )

        mock_client = MagicMock(spec=IntelligentLLMClient)

        with patch.object(IntelligentLLMClient, "create_auto", return_value=mock_client):
            client = get_llm_client(cache_key="test")

            assert client is mock_client

    def test_get_llm_client_uses_singleton(self):
        """Test that get_llm_client uses singleton pattern."""
        from sage.common.components.sage_llm.client import (
            IntelligentLLMClient,
            get_llm_client,
        )

        mock_client = MagicMock(spec=IntelligentLLMClient)

        with patch.object(IntelligentLLMClient, "create_auto", return_value=mock_client):
            client1 = get_llm_client()
            client2 = get_llm_client()

            assert client1 is client2
            assert IntelligentLLMClient.create_auto.call_count == 1
