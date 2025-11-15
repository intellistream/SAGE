"""
Tests for Multimodal SAGE DB (multimodal_sage_db.py).

This module tests the multimodal fusion and search capabilities of SAGE DB.
"""

import numpy as np
import pytest

# Try to import multimodal_sage_db components
try:
    from sage.middleware.components.sage_db.python.multimodal_sage_db import (
        FusionParams,
        FusionStrategy,
        ModalData,
        ModalityType,
        MultimodalData,
        MultimodalSageDB,
        MultimodalSearchParams,
        QueryResult,
        create_audio_visual_db,
        create_text_image_db,
    )

    MULTIMODAL_AVAILABLE = True
except ImportError:
    MULTIMODAL_AVAILABLE = False


@pytest.mark.skipif(not MULTIMODAL_AVAILABLE, reason="Multimodal SAGE DB not available")
class TestModalityType:
    """Test ModalityType enumeration."""

    def test_modality_types_exist(self):
        """Test that all expected modality types exist."""
        expected_types = ["TEXT", "IMAGE", "AUDIO", "VIDEO", "TABULAR", "TIME_SERIES", "CUSTOM"]

        for type_name in expected_types:
            assert hasattr(ModalityType, type_name)

    def test_modality_type_values(self):
        """Test modality type values."""
        assert ModalityType.TEXT.value == 0
        assert ModalityType.IMAGE.value == 1
        assert ModalityType.AUDIO.value == 2


@pytest.mark.skipif(not MULTIMODAL_AVAILABLE, reason="Multimodal SAGE DB not available")
class TestFusionStrategy:
    """Test FusionStrategy enumeration."""

    def test_fusion_strategies_exist(self):
        """Test that all expected fusion strategies exist."""
        expected_strategies = [
            "CONCATENATION",
            "WEIGHTED_AVERAGE",
            "ATTENTION_BASED",
            "CROSS_MODAL_TRANSFORMER",
            "TENSOR_FUSION",
            "BILINEAR_POOLING",
            "CUSTOM",
        ]

        for strategy_name in expected_strategies:
            assert hasattr(FusionStrategy, strategy_name)

    def test_fusion_strategy_values(self):
        """Test fusion strategy values."""
        assert FusionStrategy.CONCATENATION.value == 0
        assert FusionStrategy.WEIGHTED_AVERAGE.value == 1


@pytest.mark.skipif(not MULTIMODAL_AVAILABLE, reason="Multimodal SAGE DB not available")
class TestModalData:
    """Test ModalData class."""

    def test_create_modal_data(self):
        """Test creating modal data."""
        embedding = np.random.randn(128).astype(np.float32)
        metadata = {"key": "value"}

        modal_data = ModalData(
            modality_type=ModalityType.TEXT, embedding=embedding, metadata=metadata
        )

        assert modal_data.type == ModalityType.TEXT
        assert modal_data.embedding.shape == (128,)
        assert modal_data.metadata == metadata

    def test_modal_data_without_metadata(self):
        """Test creating modal data without metadata."""
        embedding = np.random.randn(64).astype(np.float32)

        modal_data = ModalData(modality_type=ModalityType.IMAGE, embedding=embedding)

        assert modal_data.metadata == {}

    def test_modal_data_with_raw_data(self):
        """Test creating modal data with raw data."""
        embedding = np.random.randn(256).astype(np.float32)
        raw_data = b"sample raw data"

        modal_data = ModalData(
            modality_type=ModalityType.AUDIO, embedding=embedding, raw_data=raw_data
        )

        assert modal_data.raw_data == raw_data

    def test_embedding_dtype_conversion(self):
        """Test that embeddings are converted to float32."""
        embedding = np.random.randn(100).astype(np.float64)

        modal_data = ModalData(modality_type=ModalityType.TEXT, embedding=embedding)

        assert modal_data.embedding.dtype == np.float32


@pytest.mark.skipif(not MULTIMODAL_AVAILABLE, reason="Multimodal SAGE DB not available")
class TestMultimodalData:
    """Test MultimodalData class."""

    def test_create_multimodal_data(self):
        """Test creating multimodal data."""
        data = MultimodalData(data_id=123)

        assert data.id == 123
        assert len(data.modalities) == 0

    def test_add_modality(self):
        """Test adding modalities to multimodal data."""
        data = MultimodalData()

        text_embedding = np.random.randn(768).astype(np.float32)
        text_modal = ModalData(ModalityType.TEXT, text_embedding)

        data.add_modality(text_modal)

        assert len(data.modalities) == 1
        assert ModalityType.TEXT in data.modalities

    def test_add_multiple_modalities(self):
        """Test adding multiple modalities."""
        data = MultimodalData()

        text_modal = ModalData(ModalityType.TEXT, np.random.randn(768).astype(np.float32))
        image_modal = ModalData(ModalityType.IMAGE, np.random.randn(2048).astype(np.float32))
        audio_modal = ModalData(ModalityType.AUDIO, np.random.randn(512).astype(np.float32))

        data.add_modality(text_modal)
        data.add_modality(image_modal)
        data.add_modality(audio_modal)

        assert len(data.modalities) == 3

    def test_get_modality(self):
        """Test getting specific modality."""
        data = MultimodalData()

        text_embedding = np.random.randn(768).astype(np.float32)
        text_modal = ModalData(ModalityType.TEXT, text_embedding)
        data.add_modality(text_modal)

        retrieved = data.get_modality(ModalityType.TEXT)

        assert retrieved is not None
        assert retrieved.type == ModalityType.TEXT

    def test_get_nonexistent_modality(self):
        """Test getting a modality that doesn't exist."""
        data = MultimodalData()

        retrieved = data.get_modality(ModalityType.VIDEO)

        assert retrieved is None

    def test_global_metadata(self):
        """Test global metadata."""
        data = MultimodalData()
        data.global_metadata = {"source": "test", "timestamp": "2024-01-01"}

        assert data.global_metadata["source"] == "test"


@pytest.mark.skipif(not MULTIMODAL_AVAILABLE, reason="Multimodal SAGE DB not available")
class TestFusionParams:
    """Test FusionParams class."""

    def test_create_fusion_params(self):
        """Test creating fusion parameters."""
        params = FusionParams(FusionStrategy.WEIGHTED_AVERAGE)

        assert params.strategy == FusionStrategy.WEIGHTED_AVERAGE
        assert params.target_dimension == 512

    def test_default_modality_weights(self):
        """Test default modality weights."""
        params = FusionParams()

        assert params.modality_weights[ModalityType.TEXT] == 0.4
        assert params.modality_weights[ModalityType.IMAGE] == 0.3

    def test_custom_params(self):
        """Test custom parameters."""
        params = FusionParams()
        params.custom_params = {"learning_rate": 0.001, "temperature": 0.5}

        assert params.custom_params["learning_rate"] == 0.001


@pytest.mark.skipif(not MULTIMODAL_AVAILABLE, reason="Multimodal SAGE DB not available")
class TestMultimodalSearchParams:
    """Test MultimodalSearchParams class."""

    def test_create_search_params(self):
        """Test creating search parameters."""
        params = MultimodalSearchParams(k=10)

        assert params.k == 10
        assert params.include_metadata

    def test_target_modalities(self):
        """Test target modalities."""
        params = MultimodalSearchParams()
        params.target_modalities = [ModalityType.TEXT, ModalityType.IMAGE]

        assert len(params.target_modalities) == 2

    def test_cross_modal_search_flag(self):
        """Test cross-modal search flag."""
        params = MultimodalSearchParams()
        params.use_cross_modal_search = True

        assert params.use_cross_modal_search


@pytest.mark.skipif(not MULTIMODAL_AVAILABLE, reason="Multimodal SAGE DB not available")
class TestQueryResult:
    """Test QueryResult class."""

    def test_create_query_result(self):
        """Test creating query result."""
        result = QueryResult(data_id=42, score=0.95)

        assert result.id == 42
        assert result.score == 0.95

    def test_query_result_with_metadata(self):
        """Test query result with metadata."""
        metadata = {"category": "test", "source": "db"}
        result = QueryResult(data_id=10, score=0.88, metadata=metadata)

        assert result.metadata == metadata


@pytest.mark.skipif(not MULTIMODAL_AVAILABLE, reason="Multimodal SAGE DB not available")
class TestMultimodalSageDB:
    """Test MultimodalSageDB class."""

    @pytest.fixture
    def sample_db(self):
        """Create a sample multimodal database."""
        config = {
            "dimension": 512,
            "index_type": "FLAT",
            "fusion_strategy": FusionStrategy.WEIGHTED_AVERAGE.value,
            "enable_modality_indexing": True,
            "max_modalities_per_item": 4,
        }
        db = MultimodalSageDB(config)
        return db

    def test_create_multimodal_db(self):
        """Test creating multimodal database."""
        config = {"dimension": 256, "index_type": "FLAT", "fusion_strategy": 1}
        db = MultimodalSageDB(config)

        assert db.dimension == 256

    def test_add_multimodal_data(self, sample_db):
        """Test adding multimodal data."""
        data = MultimodalData()

        text_modal = ModalData(ModalityType.TEXT, np.random.randn(768).astype(np.float32))
        image_modal = ModalData(ModalityType.IMAGE, np.random.randn(2048).astype(np.float32))

        data.add_modality(text_modal)
        data.add_modality(image_modal)

        data_id = sample_db.add_multimodal(data)

        assert isinstance(data_id, int)
        assert data_id > 0

    def test_add_from_embeddings(self, sample_db):
        """Test adding data from embeddings dictionary."""
        embeddings = {
            ModalityType.TEXT: np.random.randn(768).astype(np.float32),
            ModalityType.IMAGE: np.random.randn(2048).astype(np.float32),
        }
        metadata = {"category": "test"}

        data_id = sample_db.add_from_embeddings(embeddings, metadata)

        assert isinstance(data_id, int)

    def test_search_multimodal(self, sample_db):
        """Test multimodal search."""
        # Add some data first
        for i in range(5):
            embeddings = {
                ModalityType.TEXT: np.random.randn(768).astype(np.float32),
                ModalityType.IMAGE: np.random.randn(2048).astype(np.float32),
            }
            sample_db.add_from_embeddings(embeddings, {"id": str(i)})

        # Search
        query_modalities = {ModalityType.TEXT: np.random.randn(768).astype(np.float32)}
        params = MultimodalSearchParams(k=3)

        results = sample_db.search_multimodal(query_modalities, params)

        assert len(results) <= 3

    def test_cross_modal_search(self, sample_db):
        """Test cross-modal search."""
        # Add multimodal data
        for i in range(5):
            embeddings = {
                ModalityType.TEXT: np.random.randn(768).astype(np.float32),
                ModalityType.IMAGE: np.random.randn(2048).astype(np.float32),
            }
            sample_db.add_from_embeddings(embeddings)

        # Cross-modal search: query with text, find images
        query_embedding = np.random.randn(768).astype(np.float32)
        params = MultimodalSearchParams(k=3)

        results = sample_db.cross_modal_search(
            ModalityType.TEXT, query_embedding, [ModalityType.IMAGE], params
        )

        assert isinstance(results, list)

    def test_get_modality_statistics(self, sample_db):
        """Test getting modality statistics."""
        # Add some data
        embeddings = {
            ModalityType.TEXT: np.random.randn(768).astype(np.float32),
            ModalityType.IMAGE: np.random.randn(2048).astype(np.float32),
        }
        sample_db.add_from_embeddings(embeddings)

        stats = sample_db.get_modality_statistics()

        assert isinstance(stats, dict)

    def test_update_fusion_params(self, sample_db):
        """Test updating fusion parameters."""
        new_params = FusionParams(FusionStrategy.ATTENTION_BASED)
        new_params.target_dimension = 1024

        sample_db.update_fusion_params(new_params)

        assert sample_db.fusion_params.strategy == FusionStrategy.ATTENTION_BASED


@pytest.mark.skipif(not MULTIMODAL_AVAILABLE, reason="Multimodal SAGE DB not available")
class TestConvenienceFunctions:
    """Test convenience functions for creating multimodal databases."""

    def test_create_text_image_db(self):
        """Test creating text-image database."""
        db = create_text_image_db(dimension=512)

        assert db.dimension == 512
        assert db.fusion_params.strategy == FusionStrategy.WEIGHTED_AVERAGE

    def test_create_text_image_db_custom_dimension(self):
        """Test creating text-image database with custom dimension."""
        db = create_text_image_db(dimension=768)

        assert db.dimension == 768

    def test_create_audio_visual_db(self):
        """Test creating audio-visual database."""
        db = create_audio_visual_db(dimension=1024)

        assert db.dimension == 1024
        assert db.fusion_params.strategy == FusionStrategy.ATTENTION_BASED


@pytest.mark.skipif(not MULTIMODAL_AVAILABLE, reason="Multimodal SAGE DB not available")
class TestMultimodalIntegration:
    """Integration tests for multimodal functionality."""

    def test_end_to_end_workflow(self):
        """Test complete workflow from creation to search."""
        # 1. Create database
        db = create_text_image_db(dimension=512)

        # 2. Add multiple items
        for i in range(10):
            embeddings = {
                ModalityType.TEXT: np.random.randn(768).astype(np.float32),
                ModalityType.IMAGE: np.random.randn(2048).astype(np.float32),
            }
            metadata = {"item_id": str(i), "category": f"cat_{i % 3}"}
            db.add_from_embeddings(embeddings, metadata)

        # 3. Search
        query_embeddings = {ModalityType.TEXT: np.random.randn(768).astype(np.float32)}
        params = MultimodalSearchParams(k=5)
        results = db.search_multimodal(query_embeddings, params)

        assert len(results) > 0
        assert len(results) <= 5

    def test_different_modality_combinations(self):
        """Test with different modality combinations."""
        db = MultimodalSageDB(
            {"dimension": 512, "fusion_strategy": FusionStrategy.WEIGHTED_AVERAGE.value}
        )

        # Text only
        db.add_from_embeddings({ModalityType.TEXT: np.random.randn(768).astype(np.float32)})

        # Image only
        db.add_from_embeddings({ModalityType.IMAGE: np.random.randn(2048).astype(np.float32)})

        # Text + Image + Audio
        db.add_from_embeddings(
            {
                ModalityType.TEXT: np.random.randn(768).astype(np.float32),
                ModalityType.IMAGE: np.random.randn(2048).astype(np.float32),
                ModalityType.AUDIO: np.random.randn(512).astype(np.float32),
            }
        )

        # Search should work with any combination
        query = {ModalityType.TEXT: np.random.randn(768).astype(np.float32)}
        params = MultimodalSearchParams(k=3)
        results = db.search_multimodal(query, params)

        assert isinstance(results, list)

    def test_similarity_calculation(self):
        """Test internal similarity calculation."""
        db = MultimodalSageDB(
            {"dimension": 512, "fusion_strategy": FusionStrategy.WEIGHTED_AVERAGE.value}
        )

        # Add known vectors
        embedding1 = np.ones(128, dtype=np.float32)
        embedding1 /= np.linalg.norm(embedding1)

        db.add_from_embeddings({ModalityType.TEXT: embedding1}, {"id": "1"})

        # Search with similar vector
        query = {ModalityType.TEXT: embedding1.copy()}
        params = MultimodalSearchParams(k=1)
        results = db.search_multimodal(query, params)

        # Should find the item we added
        assert len(results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
