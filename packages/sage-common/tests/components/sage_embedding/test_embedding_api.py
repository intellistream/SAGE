"""Tests for the lightweight embedding API helpers."""

from unittest.mock import patch

import pytest

from sage.common.components.sage_embedding.embedding_api import apply_embedding_model
from sage.common.components.sage_embedding.embedding_model import (
    apply_embedding_model as apply_model_direct,
)


@pytest.mark.unit
@patch("sage.common.components.sage_embedding.embedding_api.EmbeddingModel")
def test_apply_embedding_model_forwards_arguments(mock_model):
    """apply_embedding_model should pass through method name and kwargs."""

    apply_embedding_model(name="mockembedder", dim=256, extra="value")

    mock_model.assert_called_once_with(method="mockembedder", dim=256, extra="value")


@pytest.mark.unit
@patch("sage.common.components.sage_embedding.embedding_api.EmbeddingModel")
def test_apply_embedding_model_defaults_to_name_argument(mock_model):
    """No name argument should still instantiate the EmbeddingModel."""

    apply_embedding_model()

    mock_model.assert_called_once_with(method="default")


@pytest.mark.unit
@patch("sage.common.components.sage_embedding.embedding_model.EmbeddingModel")
def test_apply_embedding_model_direct_alias(mock_model):
    """The duplicate helper in embedding_model should behave the same way."""

    apply_model_direct(name="mockembedder", dim=64)

    mock_model.assert_called_once_with(method="mockembedder", dim=64)
