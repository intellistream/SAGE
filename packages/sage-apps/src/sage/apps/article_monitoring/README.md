# Article Monitoring System

An intelligent article monitoring system built on SAGE framework that continuously fetches papers
from arXiv, performs multi-level filtering, and provides personalized recommendations.

## Features

- **Real-time Data Stream Processing**: Built on SAGE operators for efficient stream processing
- **Multi-level Filtering**:
  - Keyword-based filtering using bag-of-words matching
  - Semantic filtering using text similarity
- **Personalized Recommendations**: Ranks articles based on user interests
- **SAGE Integration**: Uses BatchFunction, MapFunction, and SinkFunction
- **Configurable**: Easy to customize keywords and topics

## Quick Start

```python
from sage.apps.article_monitoring import run_article_monitoring_pipeline

# Run with default settings
run_article_monitoring_pipeline()

# Or customize parameters
run_article_monitoring_pipeline(
    keywords=["machine learning", "deep learning", "neural network"],
    interest_topics=[
        "artificial intelligence and machine learning applications",
        "natural language processing and text analysis"
    ],
    category="cs.AI",
    max_articles=20
)
```

## Command Line Usage

```bash
# Use default settings
python -m sage.apps.article_monitoring.pipeline

# Custom keywords and topics
python -m sage.apps.article_monitoring.pipeline \
    --keywords "transformer,attention,bert" \
    --topics "natural language processing and transformers" \
    --category cs.CL \
    --max-articles 30

# Verbose mode
python -m sage.apps.article_monitoring.pipeline --verbose
```

## Use Cases

- Academic researchers tracking papers in their field
- Research teams monitoring specific topics
- Students discovering relevant publications
- Literature review automation

## Configuration

### Categories

Common arXiv categories:

- `cs.AI` - Artificial Intelligence
- `cs.LG` - Machine Learning
- `cs.CL` - Computation and Language
- `cs.CV` - Computer Vision
- `stat.ML` - Machine Learning (Statistics)

### Filtering Parameters

- `keywords`: List of keywords for initial filtering
- `interest_topics`: List of topics for semantic analysis
- `max_articles`: Maximum number of articles to fetch per run

## Architecture

The pipeline consists of three main stages:

1. **Article Fetching**: Retrieves recent papers from arXiv API
1. **Keyword Filtering**: Filters based on exact keyword matches
1. **Semantic Filtering**: Further filters using semantic similarity

```
arXiv API → Fetch Articles → Keyword Filter → Semantic Filter → Ranked Results
```

## Example Output

```
======================================================================
SAGE Article Monitoring System
======================================================================
Category: cs.AI
Keywords: ['machine learning', 'deep learning']
Interest Topics: ['artificial intelligence applications']
======================================================================

## Pipeline Architecture

The system uses SAGE stream processing operators:

```

ArxivSource (BatchFunction) ↓ KeywordFilter (MapFunction) ↓ SemanticFilter (MapFunction) ↓
ArticleScorer (MapFunction) ↓ ArticleRankingSink (SinkFunction)

```

### Operators

- **ArxivSource**: Fetches articles from arXiv API
- **KeywordFilter**: Filters based on keyword matching
- **SemanticFilter**: Filters based on semantic similarity (Jaccard)
- **ArticleScorer**: Calculates final ranking scores
- **ArticleRankingSink**: Collects and displays ranked results

## Example Output

```

# ====================================================================== 🔍 SAGE Article Monitoring System

# Category: cs.AI Max Articles: 10 Keywords: ['machine learning', 'deep learning', 'neural network'] Interest Topics: artificial intelligence and machine...

📡 Starting pipeline...

# ====================================================================== 📚 Recommended Articles (8 found)

1. Deep Learning for Time Series Forecasting in Stream Processing Authors: John Doe, Jane Smith
   Score: 3.45 (keyword: 3.0, semantic: 0.45) URL: http://arxiv.org/abs/2401.00001 Abstract: We
   propose a novel deep learning approach for time series...

1. Machine Learning Pipeline Optimization Authors: David Lee Score: 2.30 (keyword: 2.0, semantic:
   0.30) URL: http://arxiv.org/abs/2401.00004 Abstract: Optimizing machine learning pipelines for
   better performance...

# ====================================================================== ✅ Pipeline completed in 2.34s Recommended 8 articles

```
```

## Testing

Run the example script:

```bash
python examples/apps/run_article_monitoring.py
```

Or with custom parameters:

```bash
python examples/apps/run_article_monitoring.py \
    --keywords "transformer,attention,bert" \
    --topics "natural language processing" \
    --category cs.CL \
    --max-articles 30
```

## Dependencies

- Python 3.8+
- Standard library only (no external dependencies for basic functionality)
- Optional: SAGE framework for advanced stream processing

## Future Enhancements

- Integration with embedding models for true semantic search
- User feedback learning
- Multi-source support (beyond arXiv)
- Email/Slack notifications
- Web dashboard
- Persistent storage with SageDB
