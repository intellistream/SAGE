# Changelog

All notable changes to the SAGE project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Memory Services Refactoring (Phase 1)

#### New Memory Services (3 Services, 72 Tests)

**Hierarchical Services:**

- **SemanticInvertedKnowledgeGraph Service** (23 tests)
  - Three-layer architecture: Semantic (FAISS 768D) + Inverted (BM25) + KG (Segment)
  - Three routing strategies: cascade, parallel, adaptive
  - Cross-layer query support with multi-hop reasoning framework
  - Configuration: `config/memory_v2/semantic_inverted_kg.yaml`

**Partitional Services:**

- **FeatureSummaryVectorStore Service** (23 tests)

  - Triple-index combination: FAISS + BM25 + FIFO
  - Three fusion strategies: weighted, voting, cascade
  - Auto feature extraction and summary generation
  - Configuration: `config/memory_v2/feature_summary_vectorstore.yaml`

- **InvertedVectorStore Service** (26 tests)

  - Dual-index hybrid retrieval: BM25 (sparse) + FAISS (dense)
  - Two fusion algorithms: RRF (Reciprocal Rank Fusion) and Linear weighted
  - Score normalization and configurable fusion weights
  - Configuration: `config/memory_v2/inverted_vectorstore.yaml`

#### Extended Indexes (49 Tests)

- **LSHIndex** (21 tests)

  - MinHash-based Locality-Sensitive Hashing for text similarity
  - Extended with vector parameter support (placeholder with NotImplementedError guidance)
  - Deduplication and approximate nearest neighbor search
  - Compatible with B's service interface requirements

- **SegmentIndex** (28 tests)

  - Multi-strategy segmentation: time/keyword/custom/topic/hybrid
  - Extended with topic and hybrid strategies (fallback to time with warnings)
  - Counter-based segment IDs with customizable separator
  - Configurable segment size for time-based segmentation

#### Integration Testing (14 Tests)

- **Service Integration Test Suite** (`test_services_integration.py`)
  - Multi-service coexistence testing
  - Service switching and handoff scenarios
  - Cross-service data sharing verification
  - Configuration compatibility checks
  - Cross-service query coordination
  - Performance baseline establishment
  - Error handling and recovery testing
  - Resource cleanup verification

#### Configuration System v2.0

**Configuration Files** (13 YAML files):

- Format: YAML v2.0 with mandatory version, service.name, service.description
- Partitional Services (5 configs):
  - `inverted_vectorstore.yaml` - BM25 + FAISS hybrid
  - `feature_summary_vectorstore.yaml` - Triple-index with auto-summarization
  - `feature_queue_vectorstore.yaml` - FIFO + FAISS + BM25
  - `feature_queue_segment.yaml` - Queue + Segment combination
  - `lsh_inverted.yaml` - LSH + Inverted index
- Hierarchical Services (8 configs):
  - `semantic_inverted_kg.yaml` - Three-layer semantic architecture
  - `feature_graph_vectorstore.yaml` - Feature + Graph + Vector
  - `feature_knowledge_graph.yaml` - Feature + KG combination
  - `graph_inverted.yaml` - Graph + Inverted index
  - `keyword_graph.yaml` - Keyword extraction + Graph
  - `semantic_graph.yaml` - Semantic + Graph layers
  - `semantic_inverted.yaml` - Semantic + Inverted layers
  - `topic_segment_summary.yaml` - Topic + Segment + Summary

**Configuration Tools** (2 Scripts):

- **config_migration.py** (380 lines)

  - Automated migration from old format to v2.0
  - Batch processing with dry-run mode
  - Format detection and conversion
  - Migration reports with before/after comparison
  - Usage: `python config_migration.py <config_dir> [--dry-run] [--output-dir DIR]`

- **config_validator.py** (350 lines)

  - YAML configuration validation
  - Required field checking (version, service.name, service.type, service.description)
  - Service and index type validation against registry
  - JSON and text report formats
  - Strict mode for CI/CD pipelines
  - Usage: `python config_validator.py <config_dir> [--strict] [--report-format json]`
  - CI Integration: Runs automatically in build-test workflow

#### Developer Experience

- **Test Coverage**: 135 tests total, 100% passing

  - 49 index tests (LSH + Segment)
  - 72 service tests (3 new services)
  - 14 integration tests

- **Code Quality**:

  - Full type hints with mypy validation
  - Comprehensive docstrings
  - Ruff formatting (line length 100)
  - Pre-commit hooks integration

- **CI/CD Integration**:

  - Configuration validation step in GitHub Actions
  - Dedicated service implementation test step
  - Integration test suite execution
  - Coverage reporting for new components

#### Documentation

- **Progress Tracking**: `IMPLEMENTATION_PROGRESS.md`
  - Task completion status (8/11 tasks complete)
  - Statistics: 21 files, 4152 lines, 135 tests
  - Test coverage breakdown by component
  - Next actions and remaining work

### Changed

- **UnifiedCollection Interface**: Services now use `query_by_index()` method returning data_ids
- **IndexFactory**: Extended to support LSH and Segment index creation
- **MemoryServiceRegistry**: Registered 3 new service types

### Fixed

- **Service-Collection Interface Compatibility**: Fixed services to work with actual
  UnifiedCollection API

  - Removed incorrect `collection.close()` calls
  - Changed from `collection.retrieve()` to `collection.query_by_index()`
  - Added `_ids_to_results()` wrapper for proper result formatting

- **Test Fixtures**: Removed collection cleanup methods not present in actual interface

- **Configuration Format**: Batch updated all 13 configs to include mandatory v2.0 fields

### Technical Details

#### Architecture Improvements

- **Factory Pattern**: Consistent creation interface for all indexes and services
- **Strategy Pattern**: Multiple fusion and routing strategies per service
- **Abstract Base Classes**: `BaseIndex`, `BaseMemoryService` for polymorphism
- **Dependency Injection**: Services accept pre-configured UnifiedCollection instances

#### Performance Characteristics

- **LSHIndex**: O(1) average lookup for similar documents
- **SegmentIndex**: O(log n) segment lookup with binary search
- **Fusion Algorithms**:
  - RRF: No score normalization required
  - Weighted: Score normalization with configurable weights
  - Cascade: Early termination on threshold satisfaction

#### Dependencies

- **datasketch**: MinHash LSH implementation
- **FAISS**: Dense vector similarity search
- **rank-bm25**: Sparse text retrieval
- **PyYAML**: Configuration file parsing

______________________________________________________________________

## [Previous Versions]

(To be filled with historical changelog entries)
