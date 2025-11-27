"""Unit tests for UnifiedInferenceClient singleton and caching functionality.

Tests for Task C5: LLM Service Caching Mechanism.

NOTE: This file tests the UnifiedInferenceClient which replaces the deprecated
IntelligentLLMClient.
"""

from unittest.mock import MagicMock, patch


class TestUnifiedClientSingleton:
    """Test UnifiedInferenceClient singleton/caching functionality."""

    def setup_method(self):
        """Clear instances before each test."""
        from sage.common.components.sage_llm import UnifiedInferenceClient

        UnifiedInferenceClient.clear_instances()

    def teardown_method(self):
        """Clear instances after each test."""
        from sage.common.components.sage_llm import UnifiedInferenceClient

        UnifiedInferenceClient.clear_instances()

    def test_get_instance_creates_new_instance(self):
        """Test that get_instance creates a new instance when cache is empty."""
        from sage.common.components.sage_llm import UnifiedInferenceClient

        # Mock create_auto to avoid actual network calls
        mock_client = MagicMock(spec=UnifiedInferenceClient)
        with patch.object(UnifiedInferenceClient, "create_auto", return_value=mock_client):
            client = UnifiedInferenceClient.get_instance(instance_key="test1")

            assert client is mock_client
            UnifiedInferenceClient.create_auto.assert_called_once()

    def test_get_instance_returns_cached_instance(self):
        """Test that get_instance returns cached instance on second call."""
        from sage.common.components.sage_llm import UnifiedInferenceClient

        mock_client = MagicMock(spec=UnifiedInferenceClient)

        with patch.object(UnifiedInferenceClient, "create_auto", return_value=mock_client):
            client1 = UnifiedInferenceClient.get_instance(instance_key="test2")
            client2 = UnifiedInferenceClient.get_instance(instance_key="test2")

            assert client1 is client2
            # create_auto should only be called once
            assert UnifiedInferenceClient.create_auto.call_count == 1

    def test_get_instance_different_keys(self):
        """Test that different instance keys create different instances."""
        from sage.common.components.sage_llm import UnifiedInferenceClient

        mock_client_a = MagicMock(spec=UnifiedInferenceClient)
        mock_client_b = MagicMock(spec=UnifiedInferenceClient)

        with patch.object(
            UnifiedInferenceClient, "create_auto", side_effect=[mock_client_a, mock_client_b]
        ):
            client_a = UnifiedInferenceClient.get_instance(instance_key="key_a")
            client_b = UnifiedInferenceClient.get_instance(instance_key="key_b")

            assert client_a is not client_b
            assert UnifiedInferenceClient.create_auto.call_count == 2

    def test_get_instance_default_key(self):
        """Test get_instance with default instance key."""
        from sage.common.components.sage_llm import UnifiedInferenceClient

        mock_client = MagicMock(spec=UnifiedInferenceClient)

        with patch.object(UnifiedInferenceClient, "create_auto", return_value=mock_client):
            client1 = UnifiedInferenceClient.get_instance()
            client2 = UnifiedInferenceClient.get_instance()

            assert client1 is client2
            assert UnifiedInferenceClient.create_auto.call_count == 1

    def test_clear_instances(self):
        """Test clearing all cached instances."""
        from sage.common.components.sage_llm import UnifiedInferenceClient

        mock_client = MagicMock(spec=UnifiedInferenceClient)

        with patch.object(UnifiedInferenceClient, "create_auto", return_value=mock_client):
            UnifiedInferenceClient.get_instance(instance_key="a")
            UnifiedInferenceClient.get_instance(instance_key="b")
            UnifiedInferenceClient.get_instance(instance_key="c")

            UnifiedInferenceClient.clear_instances()

            # After clearing, instances cache should be empty
            # Creating a new instance should call create_auto again
            UnifiedInferenceClient.get_instance(instance_key="a")
            assert UnifiedInferenceClient.create_auto.call_count == 4  # 3 + 1


class TestCheckEndpointHealth:
    """Test the _check_endpoint_health utility method."""

    def test_check_endpoint_health_available(self):
        """Test when endpoint is available."""
        from sage.common.components.sage_llm import UnifiedInferenceClient

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_class.return_value = mock_client

            result = UnifiedInferenceClient._check_endpoint_health("http://localhost:8001/v1")

            assert result is True

    def test_check_endpoint_health_unavailable(self):
        """Test when endpoint is not available."""
        from sage.common.components.sage_llm import UnifiedInferenceClient

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get.side_effect = Exception("Connection refused")
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_class.return_value = mock_client

            result = UnifiedInferenceClient._check_endpoint_health("http://localhost:8001/v1")

            assert result is False


class TestGetLLMClient:
    """Test the get_llm_client convenience function (deprecated)."""

    def setup_method(self):
        """Clear instances before each test."""
        from sage.common.components.sage_llm import UnifiedInferenceClient

        UnifiedInferenceClient.clear_instances()

    def teardown_method(self):
        """Clear instances after each test."""
        from sage.common.components.sage_llm import UnifiedInferenceClient

        UnifiedInferenceClient.clear_instances()

    def test_get_llm_client_function(self):
        """Test the convenience function returns UnifiedInferenceClient."""
        from sage.common.components.sage_llm import UnifiedInferenceClient, get_llm_client

        with patch.object(UnifiedInferenceClient, "create_auto") as mock_create:
            mock_client = MagicMock(spec=UnifiedInferenceClient)
            mock_create.return_value = mock_client

            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                client = get_llm_client()

            assert client is mock_client
