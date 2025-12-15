from unittest.mock import MagicMock, patch

import pytest

from sage.gateway.adapters.openai import ChatCompletionRequest, ChatMessage, OpenAIAdapter


class TestOpenAIAdapterModelPropagation:
    """Test that OpenAIAdapter correctly propagates the model parameter."""

    @pytest.mark.asyncio
    async def test_model_propagation_to_client(self):
        """Test that the model name is passed to the UnifiedInferenceClient."""

        # Mock UnifiedInferenceClient
        with patch("sage.common.components.sage_llm.UnifiedInferenceClient") as MockClientClass:
            mock_client = MagicMock()
            MockClientClass.create.return_value = mock_client
            mock_client.chat.return_value = "Mocked response"

            # Mock RAG components to avoid actual DB/Embedding initialization
            # We also need to mock RAGChatMap._get_llm_client to return our mock_client
            # because the pipeline creates its own client instance
            with (
                patch("sage.middleware.components.sage_db.python.sage_db.SageDB"),
                patch("sage.common.components.sage_embedding.get_embedding_model"),
                patch(
                    "sage.gateway.rag_pipeline.RAGChatMap._get_llm_client", return_value=mock_client
                ),
            ):
                adapter = OpenAIAdapter()

                # Force pipeline start (lazy initialization)
                adapter._ensure_pipeline_started()

                # Define a specific model name to test
                test_model = "pangu_embedded_1b"

                request = ChatCompletionRequest(
                    model=test_model,
                    messages=[ChatMessage(role="user", content="Hello")],
                    stream=False,
                )

                # Execute the chat completion
                await adapter.chat_completions(request)

                # Verify that client.chat was called
                assert mock_client.chat.called, (
                    "UnifiedInferenceClient.chat should have been called"
                )

                # Verify that the model parameter was passed correctly
                # We check all calls to find the one with our model
                found_model_call = False
                for call in mock_client.chat.call_args_list:
                    _, kwargs = call
                    if kwargs.get("model") == test_model:
                        found_model_call = True
                        break

                assert found_model_call, (
                    f"Expected client.chat to be called with model='{test_model}'"
                )
