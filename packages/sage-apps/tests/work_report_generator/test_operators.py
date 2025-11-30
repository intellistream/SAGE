"""Unit tests for Work Report Generator operators.

Tests for sage.apps.work_report_generator.operators module.
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from sage.apps.work_report_generator.models import (
    ContributorSummary,
    DiaryEntry,
    GitHubCommit,
    GitHubPullRequest,
)
from sage.apps.work_report_generator.operators import (
    ConsoleSink,
    ContributorAggregator,
    DiaryEntrySource,
    GitHubDataSource,
    LLMReportGenerator,
    ReportSink,
)


class TestGitHubDataSource:
    """Test GitHubDataSource operator."""

    def test_source_creation(self):
        """Test creating GitHub data source."""
        source = GitHubDataSource(
            repos=["intellistream/SAGE"],
            days=7,
        )

        assert source.repos == ["intellistream/SAGE"]
        assert source.days == 7
        assert source.current_index == 0
        assert source.fetched is False

    def test_source_creation_with_token(self):
        """Test creating source with token."""
        source = GitHubDataSource(
            repos=["test/repo"],
            days=14,
            github_token="test_token",
        )

        assert source.github_token == "test_token"
        assert "Bearer test_token" in source.headers["Authorization"]

    def test_source_date_range(self):
        """Test source calculates correct date range."""
        source = GitHubDataSource(repos=["test/repo"], days=7)

        expected_start = datetime.now() - timedelta(days=7)
        assert abs((source.start_date - expected_start).total_seconds()) < 1
        assert abs((source.end_date - datetime.now()).total_seconds()) < 1

    def test_source_mock_data(self):
        """Test source generates mock data when no token."""
        source = GitHubDataSource(repos=["test/repo"], days=7, github_token="")

        source._use_mock_data()

        assert len(source.commits) > 0
        assert len(source.pull_requests) > 0

    def test_source_execute_returns_commits_then_prs(self):
        """Test source emits commits first, then PRs."""
        source = GitHubDataSource(repos=["test/repo"], days=7, github_token="")

        # Use mock data
        source._use_mock_data()
        source.fetched = True

        # First items should be commits
        result = source.execute()
        assert result is not None
        assert result["type"] == "commit"

    @patch("sage.apps.work_report_generator.operators.requests.post")
    def test_source_graphql_error_handling(self, mock_post):
        """Test source handles GraphQL errors gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"errors": ["Test error"]}
        mock_post.return_value = mock_response

        source = GitHubDataSource(
            repos=["test/repo"],
            days=7,
            github_token="test_token",
        )

        result = source._execute_graphql("query { viewer { login } }")
        assert "errors" in result


class TestDiaryEntrySource:
    """Test DiaryEntrySource operator."""

    def test_source_creation(self):
        """Test creating diary entry source."""
        source = DiaryEntrySource(diary_path="/tmp/diaries", days=7)

        assert source.diary_path == Path("/tmp/diaries")
        assert source.days == 7
        assert source.fetched is False

    def test_source_no_path(self):
        """Test source with no path specified."""
        source = DiaryEntrySource(diary_path=None, days=7)

        assert source.diary_path is None

    def test_source_load_json_entries(self):
        """Test loading entries from JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test JSON file
            diary_file = Path(tmpdir) / "diaries.json"
            entries = [
                {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "author": "testuser",
                    "content": "Test entry",
                    "tags": ["test"],
                }
            ]
            diary_file.write_text(json.dumps(entries))

            source = DiaryEntrySource(diary_path=diary_file, days=7)
            source._load_entries()

            assert len(source.entries) == 1
            assert source.entries[0].author == "testuser"

    def test_source_load_markdown_entries(self):
        """Test loading entries from Markdown files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test markdown file
            date_str = datetime.now().strftime("%Y-%m-%d")
            md_file = Path(tmpdir) / f"{date_str}.md"
            md_file.write_text("# Daily Log\n\nWorked on tests.")

            source = DiaryEntrySource(diary_path=tmpdir, days=7)
            source._load_entries()

            assert len(source.entries) == 1
            assert "Daily Log" in source.entries[0].content

    def test_source_date_range_filter(self):
        """Test entries are filtered by date range."""
        source = DiaryEntrySource(diary_path=None, days=7)

        # Date within range
        recent_date = datetime.now().strftime("%Y-%m-%d")
        assert source._is_in_date_range(recent_date) is True

        # Date outside range
        old_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        assert source._is_in_date_range(old_date) is False

    def test_source_execute(self):
        """Test source execution returns entries one by one."""
        source = DiaryEntrySource(diary_path=None, days=7)

        # Manually add entries
        source.entries = [
            DiaryEntry(
                date="2024-01-15",
                author="user1",
                content="Entry 1",
            ),
            DiaryEntry(
                date="2024-01-16",
                author="user2",
                content="Entry 2",
            ),
        ]
        source.fetched = True

        # Get first entry
        result1 = source.execute()
        assert result1 is not None
        assert result1["type"] == "diary_entry"
        assert result1["data"].content == "Entry 1"

        # Get second entry
        result2 = source.execute()
        assert result2 is not None
        assert result2["data"].content == "Entry 2"

        # No more entries
        result3 = source.execute()
        assert result3 is None


class TestContributorAggregator:
    """Test ContributorAggregator operator."""

    def setup_method(self):
        """Reset aggregator state before each test."""
        ContributorAggregator.reset()

    def test_aggregator_creation(self):
        """Test creating aggregator."""
        aggregator = ContributorAggregator()
        assert aggregator is not None

    def test_aggregator_commit(self):
        """Test aggregating commits."""
        aggregator = ContributorAggregator()

        commit = GitHubCommit(
            sha="abc123",
            message="Test commit",
            author="developer1",
            author_email="dev@example.com",
            committed_date="2024-01-15T10:00:00Z",
            repo="test/repo",
            url="https://github.com/test/repo/commit/abc123",
        )

        result = aggregator.execute(
            {
                "type": "commit",
                "data": commit,
                "author": "developer1",
            }
        )

        assert result["author"] == "developer1"
        assert result["contributor"].total_commits == 1

    def test_aggregator_pull_request(self):
        """Test aggregating pull requests."""
        aggregator = ContributorAggregator()

        pr = GitHubPullRequest(
            number=1,
            title="Test PR",
            author="developer1",
            state="MERGED",
            created_at="2024-01-15T10:00:00Z",
            merged_at="2024-01-16T10:00:00Z",
            closed_at=None,
            repo="test/repo",
            url="https://github.com/test/repo/pull/1",
        )

        result = aggregator.execute(
            {
                "type": "pull_request",
                "data": pr,
                "author": "developer1",
            }
        )

        assert result["contributor"].total_prs == 1
        assert result["contributor"].merged_prs == 1

    def test_aggregator_diary_entry(self):
        """Test aggregating diary entries."""
        aggregator = ContributorAggregator()

        entry = DiaryEntry(
            date="2024-01-15",
            author="developer1",
            content="Test entry",
        )

        result = aggregator.execute(
            {
                "type": "diary_entry",
                "data": entry,
                "author": "developer1",
            }
        )

        assert len(result["contributor"].diary_entries) == 1

    def test_aggregator_multiple_contributors(self):
        """Test aggregating data for multiple contributors."""
        aggregator = ContributorAggregator()

        # Add data for dev1
        commit1 = GitHubCommit(
            sha="abc",
            message="Commit 1",
            author="dev1",
            author_email="",
            committed_date="2024-01-15T10:00:00Z",
            repo="test/repo",
            url="",
        )
        aggregator.execute({"type": "commit", "data": commit1, "author": "dev1"})

        # Add data for dev2
        commit2 = GitHubCommit(
            sha="def",
            message="Commit 2",
            author="dev2",
            author_email="",
            committed_date="2024-01-15T11:00:00Z",
            repo="test/repo",
            url="",
        )
        aggregator.execute({"type": "commit", "data": commit2, "author": "dev2"})

        contributors = ContributorAggregator.get_all_contributors()
        assert len(contributors) == 2
        assert "dev1" in contributors
        assert "dev2" in contributors

    def test_aggregator_reset(self):
        """Test resetting aggregator state."""
        aggregator = ContributorAggregator()

        commit = GitHubCommit(
            sha="abc",
            message="Test",
            author="dev1",
            author_email="",
            committed_date="",
            repo="",
            url="",
        )
        aggregator.execute({"type": "commit", "data": commit, "author": "dev1"})

        assert len(ContributorAggregator.get_all_contributors()) > 0

        ContributorAggregator.reset()

        assert len(ContributorAggregator.get_all_contributors()) == 0

    def test_aggregator_username_normalization(self):
        """Test username normalization for duplicate contributors."""
        ContributorAggregator.reset()
        aggregator = ContributorAggregator()

        # Test ShuhaoZhangTony variants
        commit1 = GitHubCommit(
            sha="abc1",
            message="Commit from ShuhaoZhangTony",
            author="ShuhaoZhangTony",
            author_email="",
            committed_date="2024-01-15T10:00:00Z",
            repo="test/repo",
            url="",
        )
        aggregator.execute({"type": "commit", "data": commit1, "author": "ShuhaoZhangTony"})

        commit2 = GitHubCommit(
            sha="abc2",
            message="Commit from Shuhao Zhang",
            author="Shuhao Zhang",
            author_email="",
            committed_date="2024-01-15T11:00:00Z",
            repo="test/repo",
            url="",
        )
        result = aggregator.execute({"type": "commit", "data": commit2, "author": "Shuhao Zhang"})

        # Both should map to ShuhaoZhangTony
        assert result["author"] == "ShuhaoZhangTony"
        contributors = ContributorAggregator.get_all_contributors()
        assert "ShuhaoZhangTony" in contributors
        assert "Shuhao Zhang" not in contributors
        assert contributors["ShuhaoZhangTony"].total_commits == 2

    def test_aggregator_copilot_normalization(self):
        """Test Copilot username normalization."""
        ContributorAggregator.reset()
        aggregator = ContributorAggregator()

        commit1 = GitHubCommit(
            sha="cop1",
            message="Commit from Copilot",
            author="Copilot",
            author_email="",
            committed_date="2024-01-15T10:00:00Z",
            repo="test/repo",
            url="",
        )
        aggregator.execute({"type": "commit", "data": commit1, "author": "Copilot"})

        commit2 = GitHubCommit(
            sha="cop2",
            message="Commit from copilot-swe-agent",
            author="copilot-swe-agent",
            author_email="",
            committed_date="2024-01-15T11:00:00Z",
            repo="test/repo",
            url="",
        )
        result = aggregator.execute(
            {"type": "commit", "data": commit2, "author": "copilot-swe-agent"}
        )

        # Both should map to Copilot
        assert result["author"] == "Copilot"
        contributors = ContributorAggregator.get_all_contributors()
        assert "Copilot" in contributors
        assert "copilot-swe-agent" not in contributors
        assert contributors["Copilot"].total_commits == 2

    def test_normalize_username_static_method(self):
        """Test the normalize_username static method."""
        # ShuhaoZhangTony variants
        assert ContributorAggregator.normalize_username("ShuhaoZhangTony") == "ShuhaoZhangTony"
        assert ContributorAggregator.normalize_username("Shuhao Zhang") == "ShuhaoZhangTony"
        assert ContributorAggregator.normalize_username("shuhao zhang") == "ShuhaoZhangTony"
        assert ContributorAggregator.normalize_username("shuhaozhangtony") == "ShuhaoZhangTony"

        # Copilot variants
        assert ContributorAggregator.normalize_username("Copilot") == "Copilot"
        assert ContributorAggregator.normalize_username("copilot-swe-agent") == "Copilot"
        assert ContributorAggregator.normalize_username("github-copilot") == "Copilot"

        # Unknown users should stay unchanged
        assert ContributorAggregator.normalize_username("some-random-user") == "some-random-user"

        # Empty string should return Unknown
        assert ContributorAggregator.normalize_username("") == "Unknown"


class TestLLMReportGenerator:
    """Test LLMReportGenerator operator."""

    def test_generator_creation(self):
        """Test creating LLM report generator."""
        generator = LLMReportGenerator(language="zh")

        assert generator.language == "zh"
        assert generator._client is None

    def test_generator_simple_summary_zh(self):
        """Test generating simple Chinese summary."""
        generator = LLMReportGenerator(language="zh")

        contributor = ContributorSummary(username="testuser")
        contributor.total_commits = 10
        contributor.total_prs = 3
        contributor.merged_prs = 2
        contributor.total_additions = 500
        contributor.total_deletions = 100

        summary = generator._generate_simple_summary(contributor)

        assert "testuser" in summary
        assert "10" in summary
        assert "3" in summary

    def test_generator_simple_summary_en(self):
        """Test generating simple English summary."""
        generator = LLMReportGenerator(language="en")

        contributor = ContributorSummary(username="testuser")
        contributor.total_commits = 5
        contributor.total_prs = 2
        contributor.merged_prs = 1
        contributor.total_additions = 200
        contributor.total_deletions = 50

        summary = generator._generate_simple_summary(contributor)

        assert "testuser" in summary
        assert "contributed" in summary

    def test_generator_execute_non_contributor(self):
        """Test generator passes through non-contributor data."""
        generator = LLMReportGenerator(language="zh")

        result = generator.execute({"type": "other", "data": "test"})

        assert result["type"] == "other"

    def test_generator_execute_contributor(self):
        """Test generator processes contributor updates."""
        generator = LLMReportGenerator(language="zh")

        contributor = ContributorSummary(username="testuser")
        contributor.total_commits = 5

        result = generator.execute(
            {
                "type": "contributor_update",
                "author": "testuser",
                "contributor": contributor,
            }
        )

        assert "llm_summary" in result

    def test_generator_skips_duplicate_authors(self):
        """Test generator only processes each author once."""
        generator = LLMReportGenerator(language="zh")

        contributor = ContributorSummary(username="testuser")

        # First call
        result1 = generator.execute(
            {
                "type": "contributor_update",
                "author": "testuser",
                "contributor": contributor,
            }
        )
        assert result1 is not None

        # Second call should return None
        result2 = generator.execute(
            {
                "type": "contributor_update",
                "author": "testuser",
                "contributor": contributor,
            }
        )
        assert result2 is None


class TestReportSink:
    """Test ReportSink operator."""

    def test_sink_creation(self):
        """Test creating report sink."""
        sink = ReportSink(
            output_format="markdown",
            repos=["test/repo"],
            days=7,
        )

        assert sink.output_format == "markdown"
        assert sink.repos == ["test/repo"]
        assert sink.days == 7

    def test_sink_execute_collects_data(self):
        """Test sink collects contributor data."""
        sink = ReportSink(output_format="console", repos=["test/repo"], days=7)

        contributor = ContributorSummary(username="testuser")
        contributor.total_commits = 5

        sink.execute(
            {
                "type": "contributor_update",
                "author": "testuser",
                "contributor": contributor,
                "llm_summary": "Test summary",
            }
        )

        assert "testuser" in sink.contributors

    def test_sink_markdown_output(self):
        """Test generating markdown output."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            output_path = Path(f.name)

        try:
            sink = ReportSink(
                output_format="markdown",
                output_path=output_path,
                repos=["test/repo"],
                days=7,
            )

            contributor = ContributorSummary(username="testuser")
            contributor.total_commits = 5
            contributor.calculate_stats()

            sink.execute(
                {
                    "type": "contributor_update",
                    "author": "testuser",
                    "contributor": contributor,
                }
            )

            sink.close()

            content = output_path.read_text()
            assert "Weekly Work Report" in content
            assert "testuser" in content
        finally:
            output_path.unlink(missing_ok=True)

    def test_sink_json_output(self):
        """Test generating JSON output."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            sink = ReportSink(
                output_format="json",
                output_path=output_path,
                repos=["test/repo"],
                days=7,
            )

            contributor = ContributorSummary(username="testuser")
            contributor.total_commits = 5
            contributor.calculate_stats()

            sink.execute(
                {
                    "type": "contributor_update",
                    "author": "testuser",
                    "contributor": contributor,
                }
            )

            sink.close()

            content = output_path.read_text()
            data = json.loads(content)
            assert "contributors" in data
            assert len(data["contributors"]) == 1
        finally:
            output_path.unlink(missing_ok=True)


class TestConsoleSink:
    """Test ConsoleSink operator."""

    def test_console_sink_counts(self):
        """Test console sink counts processed items."""
        sink = ConsoleSink()

        sink.execute({"type": "commit", "author": "dev1"})
        assert sink.count == 1

        sink.execute({"type": "pr", "author": "dev2"})
        assert sink.count == 2
