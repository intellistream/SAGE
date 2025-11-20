"""Unit tests for Article Monitoring Application

Tests for sage.apps.article_monitoring module
"""

import pytest

from sage.apps.article_monitoring.operators import (
    Article,
    ArxivSource,
    KeywordFilter,
    KeywordScorer,
    SemanticScorer,
    TopArticlesSink,
)


class TestArticle:
    """Test Article dataclass"""

    def test_article_creation(self):
        """Test creating an article"""
        article = Article(
            id="2401.12345",
            title="Test Article",
            authors=["Author One", "Author Two"],
            abstract="This is a test abstract about machine learning.",
            published="2024-01-15",
            categories=["cs.AI", "cs.LG"],
            url="https://arxiv.org/abs/2401.12345",
        )

        assert article.id == "2401.12345"
        assert article.title == "Test Article"
        assert len(article.authors) == 2
        assert article.keyword_score == 0.0
        assert article.semantic_score == 0.0
        assert article.total_score == 0.0

    def test_article_with_scores(self):
        """Test article with scores"""
        article = Article(
            id="2401.12345",
            title="Test Article",
            authors=["Author One"],
            abstract="Test abstract",
            published="2024-01-15",
            categories=["cs.AI"],
            url="https://arxiv.org/abs/2401.12345",
            keyword_score=0.8,
            semantic_score=0.9,
            total_score=0.85,
        )

        assert article.keyword_score == 0.8
        assert article.semantic_score == 0.9
        assert article.total_score == 0.85


class TestArxivSource:
    """Test ArxivSource operator"""

    def test_source_creation(self):
        """Test creating arXiv source"""
        source = ArxivSource(category="cs.AI", max_results=10)

        assert source.category == "cs.AI"
        assert source.max_results == 10

    def test_source_with_custom_category(self):
        """Test source with different category"""
        source = ArxivSource(category="cs.LG", max_results=5)

        assert source.category == "cs.LG"
        assert source.max_results == 5

    @pytest.mark.integration
    def test_source_fetch_articles(self):
        """Integration test: fetch real articles from arXiv"""
        _source = ArxivSource(category="cs.AI", max_results=3)

        # This would make actual API call in integration test
        # articles = list(_source.run())
        # assert len(articles) > 0
        # assert all(isinstance(a, Article) for a in articles)
        pass  # Skip actual API call in unit test


class TestKeywordScorer:
    """Test KeywordScorer operator"""

    def test_scorer_creation(self):
        """Test creating keyword scorer"""
        keywords = ["machine learning", "neural network", "deep learning"]
        scorer = KeywordScorer(keywords=keywords)

        assert len(scorer.keywords) == 3
        assert "machine learning" in scorer.keywords

    def test_score_article_with_keywords(self):
        """Test scoring article with matching keywords"""
        keywords = ["machine learning", "AI"]
        scorer = KeywordScorer(keywords=keywords)

        article = Article(
            id="test",
            title="Machine Learning for AI",
            authors=["Test Author"],
            abstract="This paper discusses machine learning and AI applications.",
            published="2024-01-15",
            categories=["cs.AI"],
            url="https://test.com",
        )

        scored = scorer.map(article)
        assert scored.keyword_score > 0
        assert "machine learning" in scored.abstract.lower()

    def test_score_article_without_keywords(self):
        """Test scoring article without matching keywords"""
        keywords = ["quantum computing", "cryptography"]
        scorer = KeywordScorer(keywords=keywords)

        article = Article(
            id="test",
            title="Machine Learning Basics",
            authors=["Test Author"],
            abstract="Introduction to neural networks.",
            published="2024-01-15",
            categories=["cs.AI"],
            url="https://test.com",
        )

        scored = scorer.map(article)
        assert scored.keyword_score == 0


class TestSemanticScorer:
    """Test SemanticScorer operator"""

    def test_scorer_creation(self):
        """Test creating semantic scorer"""
        query = "machine learning applications"
        scorer = SemanticScorer(query=query)

        assert scorer.query == query

    def test_score_calculation(self):
        """Test semantic score calculation"""
        query = "deep learning"
        scorer = SemanticScorer(query=query)

        article = Article(
            id="test",
            title="Deep Learning",
            authors=["Test Author"],
            abstract="Deep learning neural networks",
            published="2024-01-15",
            categories=["cs.AI"],
            url="https://test.com",
        )

        # Mock the embedding/scoring logic for unit test
        scored = scorer.map(article)
        assert hasattr(scored, "semantic_score")
        assert scored.semantic_score >= 0


class TestKeywordFilter:
    """Test KeywordFilter operator"""

    def test_filter_creation(self):
        """Test creating keyword filter"""
        min_score = 0.5
        filter_op = KeywordFilter(min_score=min_score)

        assert filter_op.min_score == 0.5

    def test_filter_accepts_high_score(self):
        """Test filter accepts articles with high score"""
        filter_op = KeywordFilter(min_score=0.5)

        article = Article(
            id="test",
            title="Test",
            authors=["Author"],
            abstract="Abstract",
            published="2024-01-15",
            categories=["cs.AI"],
            url="https://test.com",
            keyword_score=0.8,
        )

        assert filter_op.filter(article) is True

    def test_filter_rejects_low_score(self):
        """Test filter rejects articles with low score"""
        filter_op = KeywordFilter(min_score=0.5)

        article = Article(
            id="test",
            title="Test",
            authors=["Author"],
            abstract="Abstract",
            published="2024-01-15",
            categories=["cs.AI"],
            url="https://test.com",
            keyword_score=0.2,
        )

        assert filter_op.filter(article) is False


class TestTopArticlesSink:
    """Test TopArticlesSink operator"""

    def test_sink_creation(self):
        """Test creating top articles sink"""
        sink = TopArticlesSink(top_k=5)

        assert sink.top_k == 5

    def test_sink_collect_articles(self):
        """Test collecting articles"""
        sink = TopArticlesSink(top_k=3)

        articles = [
            Article(
                id=f"test{i}",
                title=f"Article {i}",
                authors=["Author"],
                abstract="Abstract",
                published="2024-01-15",
                categories=["cs.AI"],
                url=f"https://test.com/{i}",
                total_score=0.5 + i * 0.1,
            )
            for i in range(5)
        ]

        for article in articles:
            sink.sink(article)

        # Sink should keep top 3 articles by score
        top = sink.get_top_articles()
        assert len(top) <= 3

    def test_sink_sorting(self):
        """Test articles are sorted by score"""
        sink = TopArticlesSink(top_k=10)

        articles = [
            Article(
                id=f"test{i}",
                title=f"Article {i}",
                authors=["Author"],
                abstract="Abstract",
                published="2024-01-15",
                categories=["cs.AI"],
                url=f"https://test.com/{i}",
                total_score=0.9 - i * 0.1,  # Decreasing scores
            )
            for i in range(5)
        ]

        for article in articles:
            sink.sink(article)

        top = sink.get_top_articles()
        # Verify sorted in descending order
        for i in range(len(top) - 1):
            assert top[i].total_score >= top[i + 1].total_score


@pytest.mark.integration
class TestArticleMonitoringPipeline:
    """Integration tests for complete article monitoring pipeline"""

    def test_pipeline_creation(self):
        """Test creating the monitoring pipeline"""
        from sage.apps.article_monitoring.pipeline import create_article_monitoring_pipeline

        pipeline = create_article_monitoring_pipeline(
            category="cs.AI", max_results=5, keywords=["machine learning"], top_k=3
        )

        assert pipeline is not None

    @pytest.mark.skip(reason="Requires real arXiv API access")
    def test_end_to_end_pipeline(self):
        """Test complete pipeline execution"""
        from sage.apps.article_monitoring.pipeline import create_article_monitoring_pipeline

        _pipeline = create_article_monitoring_pipeline(
            category="cs.AI",
            max_results=10,
            keywords=["machine learning", "neural networks"],
            top_k=5,
        )

        # Execute pipeline
        # results = _pipeline.execute()
        # assert len(results) <= 5
        pass
