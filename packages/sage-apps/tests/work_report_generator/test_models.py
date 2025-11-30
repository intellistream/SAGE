"""Unit tests for Work Report Generator data models.

Tests for sage.apps.work_report_generator.models module.
"""

from sage.apps.work_report_generator.models import (
    ContributorSummary,
    DiaryEntry,
    GitHubCommit,
    GitHubPullRequest,
    WeeklyReport,
)


class TestGitHubCommit:
    """Test GitHubCommit dataclass."""

    def test_commit_creation(self):
        """Test creating a commit."""
        commit = GitHubCommit(
            sha="abc123def456",  # pragma: allowlist secret
            message="feat: Add new feature",
            author="developer1",
            author_email="dev1@example.com",
            committed_date="2024-01-15T10:00:00Z",
            repo="intellistream/SAGE",
            url="https://github.com/intellistream/SAGE/commit/abc123def456",
            additions=100,
            deletions=50,
            changed_files=5,
        )

        assert commit.sha == "abc123def456"  # pragma: allowlist secret
        assert commit.message == "feat: Add new feature"
        assert commit.author == "developer1"
        assert commit.additions == 100
        assert commit.deletions == 50

    def test_commit_from_graphql(self):
        """Test creating commit from GraphQL response."""
        graphql_data = {
            "oid": "abc123",
            "message": "fix: Bug fix\n\nDetailed description",
            "committedDate": "2024-01-15T10:00:00Z",
            "url": "https://github.com/test/repo/commit/abc123",
            "additions": 10,
            "deletions": 5,
            "changedFiles": 2,
            "author": {
                "name": "Test User",
                "email": "test@example.com",
                "user": {"login": "testuser"},
            },
        }

        commit = GitHubCommit.from_graphql(graphql_data, "test/repo")

        assert commit.sha == "abc123"
        assert commit.message == "fix: Bug fix"  # Only first line
        assert commit.author == "testuser"
        assert commit.author_email == "test@example.com"
        assert commit.repo == "test/repo"
        assert commit.additions == 10

    def test_commit_from_graphql_missing_user(self):
        """Test creating commit when user info is missing."""
        graphql_data = {
            "oid": "def456",
            "message": "Update file",
            "committedDate": "2024-01-15T10:00:00Z",
            "url": "https://github.com/test/repo/commit/def456",
            "additions": 5,
            "deletions": 2,
            "changedFiles": 1,
            "author": {
                "name": "External User",
                "email": "external@example.com",
                "user": None,
            },
        }

        commit = GitHubCommit.from_graphql(graphql_data, "test/repo")

        assert commit.sha == "def456"
        assert commit.author == "External User"


class TestGitHubPullRequest:
    """Test GitHubPullRequest dataclass."""

    def test_pr_creation(self):
        """Test creating a pull request."""
        pr = GitHubPullRequest(
            number=100,
            title="feat: Add weekly report generator",
            author="developer1",
            state="MERGED",
            created_at="2024-01-15T10:00:00Z",
            merged_at="2024-01-16T10:00:00Z",
            closed_at=None,
            repo="intellistream/SAGE",
            url="https://github.com/intellistream/SAGE/pull/100",
            additions=500,
            deletions=100,
            changed_files=15,
            labels=["feature", "enhancement"],
            reviewers=["reviewer1"],
        )

        assert pr.number == 100
        assert pr.state == "MERGED"
        assert len(pr.labels) == 2
        assert pr.merged_at is not None

    def test_pr_from_graphql(self):
        """Test creating PR from GraphQL response."""
        graphql_data = {
            "number": 42,
            "title": "Fix: Resolve issue",
            "state": "MERGED",
            "createdAt": "2024-01-15T10:00:00Z",
            "mergedAt": "2024-01-16T10:00:00Z",
            "closedAt": None,
            "url": "https://github.com/test/repo/pull/42",
            "additions": 20,
            "deletions": 10,
            "changedFiles": 3,
            "author": {"login": "developer"},
            "labels": {"nodes": [{"name": "bug"}, {"name": "priority:high"}]},
            "reviewRequests": {"nodes": []},
        }

        pr = GitHubPullRequest.from_graphql(graphql_data, "test/repo")

        assert pr.number == 42
        assert pr.title == "Fix: Resolve issue"
        assert pr.author == "developer"
        assert pr.state == "MERGED"
        assert "bug" in pr.labels


class TestDiaryEntry:
    """Test DiaryEntry dataclass."""

    def test_diary_creation(self):
        """Test creating a diary entry."""
        entry = DiaryEntry(
            date="2024-01-15",
            author="developer1",
            content="Today I worked on the report generator.",
            tags=["development", "feature"],
            category="work",
        )

        assert entry.date == "2024-01-15"
        assert entry.author == "developer1"
        assert len(entry.tags) == 2

    def test_diary_from_dict(self):
        """Test creating diary entry from dictionary."""
        data = {
            "date": "2024-01-15",
            "author": "user1",
            "content": "Daily standup notes",
            "tags": ["meeting"],
            "category": "notes",
        }

        entry = DiaryEntry.from_dict(data)

        assert entry.date == "2024-01-15"
        assert entry.author == "user1"
        assert entry.category == "notes"

    def test_diary_from_dict_defaults(self):
        """Test diary entry defaults when creating from incomplete dict."""
        data = {"content": "Some content"}

        entry = DiaryEntry.from_dict(data)

        assert entry.author == "Unknown"
        assert entry.category == "general"
        assert entry.tags == []


class TestContributorSummary:
    """Test ContributorSummary dataclass."""

    def test_contributor_creation(self):
        """Test creating a contributor summary."""
        summary = ContributorSummary(username="developer1")

        assert summary.username == "developer1"
        assert len(summary.commits) == 0
        assert summary.total_commits == 0

    def test_contributor_calculate_stats(self):
        """Test calculating contributor statistics."""
        summary = ContributorSummary(username="developer1")

        # Add commits
        summary.commits = [
            GitHubCommit(
                sha="abc",
                message="Commit 1",
                author="developer1",
                author_email="dev@example.com",
                committed_date="2024-01-15T10:00:00Z",
                repo="test/repo",
                url="https://github.com/test/repo/commit/abc",
                additions=100,
                deletions=50,
                changed_files=5,
            ),
            GitHubCommit(
                sha="def",
                message="Commit 2",
                author="developer1",
                author_email="dev@example.com",
                committed_date="2024-01-16T10:00:00Z",
                repo="test/repo",
                url="https://github.com/test/repo/commit/def",
                additions=50,
                deletions=20,
                changed_files=3,
            ),
        ]

        # Add PRs
        summary.pull_requests = [
            GitHubPullRequest(
                number=1,
                title="PR 1",
                author="developer1",
                state="MERGED",
                created_at="2024-01-15T10:00:00Z",
                merged_at="2024-01-16T10:00:00Z",
                closed_at=None,
                repo="test/repo",
                url="https://github.com/test/repo/pull/1",
                additions=200,
                deletions=100,
            ),
        ]

        summary.calculate_stats()

        assert summary.total_commits == 2
        assert summary.total_prs == 1
        assert summary.merged_prs == 1
        assert summary.total_additions == 350  # 100 + 50 + 200
        assert summary.total_deletions == 170  # 50 + 20 + 100


class TestWeeklyReport:
    """Test WeeklyReport dataclass."""

    def test_report_creation(self):
        """Test creating a weekly report."""
        report = WeeklyReport(
            start_date="2024-01-08",
            end_date="2024-01-15",
            repos=["intellistream/SAGE"],
        )

        assert report.start_date == "2024-01-08"
        assert report.end_date == "2024-01-15"
        assert len(report.repos) == 1
        assert report.total_commits == 0

    def test_report_calculate_overall_stats(self):
        """Test calculating overall report statistics."""
        report = WeeklyReport(
            start_date="2024-01-08",
            end_date="2024-01-15",
            repos=["test/repo"],
        )

        # Create contributors
        contrib1 = ContributorSummary(username="dev1")
        contrib1.total_commits = 10
        contrib1.total_prs = 3
        contrib1.merged_prs = 2

        contrib2 = ContributorSummary(username="dev2")
        contrib2.total_commits = 5
        contrib2.total_prs = 2
        contrib2.merged_prs = 1

        report.contributors = [contrib1, contrib2]
        report.calculate_overall_stats()

        assert report.total_commits == 15
        assert report.total_prs == 5
        assert report.total_merged_prs == 3
        assert report.generated_at != ""
