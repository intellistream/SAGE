"""
Data models for Work Report Generator.

Contains dataclasses for commits, PRs, diary entries, and reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class GitHubCommit:
    """Represents a GitHub commit."""

    sha: str
    message: str
    author: str
    author_email: str
    committed_date: str
    repo: str
    url: str
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0

    @classmethod
    def from_graphql(cls, data: dict[str, Any], repo: str) -> GitHubCommit:
        """Create from GraphQL response."""
        author = data.get("author", {}) or {}
        user = author.get("user", {}) or {}
        return cls(
            sha=data.get("oid", ""),
            message=data.get("message", "").split("\n")[0],  # First line only
            author=user.get("login", author.get("name", "Unknown")),
            author_email=author.get("email", ""),
            committed_date=data.get("committedDate", ""),
            repo=repo,
            url=data.get("url", ""),
            additions=data.get("additions", 0),
            deletions=data.get("deletions", 0),
            changed_files=data.get("changedFiles", 0),
        )


@dataclass
class GitHubPullRequest:
    """Represents a GitHub Pull Request."""

    number: int
    title: str
    author: str
    state: str  # OPEN, CLOSED, MERGED
    created_at: str
    merged_at: str | None
    closed_at: str | None
    repo: str
    url: str
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    labels: list[str] = field(default_factory=list)
    reviewers: list[str] = field(default_factory=list)

    @classmethod
    def from_graphql(cls, data: dict[str, Any], repo: str) -> GitHubPullRequest:
        """Create from GraphQL response."""
        author = data.get("author", {}) or {}
        labels = [
            label.get("name", "") for label in (data.get("labels", {}) or {}).get("nodes", [])
        ]
        reviewers = [
            reviewer.get("login", "")
            for reviewer in (data.get("reviewRequests", {}) or {}).get("nodes", [])
            if reviewer.get("requestedReviewer")
        ]
        return cls(
            number=data.get("number", 0),
            title=data.get("title", ""),
            author=author.get("login", "Unknown"),
            state=data.get("state", "UNKNOWN"),
            created_at=data.get("createdAt", ""),
            merged_at=data.get("mergedAt"),
            closed_at=data.get("closedAt"),
            repo=repo,
            url=data.get("url", ""),
            additions=data.get("additions", 0),
            deletions=data.get("deletions", 0),
            changed_files=data.get("changedFiles", 0),
            labels=labels,
            reviewers=reviewers,
        )


@dataclass
class DiaryEntry:
    """Represents a diary/note entry."""

    date: str
    author: str
    content: str
    tags: list[str] = field(default_factory=list)
    category: str = "general"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiaryEntry:
        """Create from dictionary."""
        return cls(
            date=data.get("date", ""),
            author=data.get("author", "Unknown"),
            content=data.get("content", ""),
            tags=data.get("tags", []),
            category=data.get("category", "general"),
        )


@dataclass
class ContributorSummary:
    """Summary of contributions for a single contributor."""

    username: str
    commits: list[GitHubCommit] = field(default_factory=list)
    pull_requests: list[GitHubPullRequest] = field(default_factory=list)
    diary_entries: list[DiaryEntry] = field(default_factory=list)

    # Aggregated stats
    total_commits: int = 0
    total_prs: int = 0
    merged_prs: int = 0
    total_additions: int = 0
    total_deletions: int = 0
    total_changed_files: int = 0

    def calculate_stats(self) -> None:
        """Calculate aggregated statistics."""
        self.total_commits = len(self.commits)
        self.total_prs = len(self.pull_requests)
        self.merged_prs = sum(1 for pr in self.pull_requests if pr.state == "MERGED")
        self.total_additions = sum(c.additions for c in self.commits) + sum(
            pr.additions for pr in self.pull_requests
        )
        self.total_deletions = sum(c.deletions for c in self.commits) + sum(
            pr.deletions for pr in self.pull_requests
        )
        self.total_changed_files = sum(c.changed_files for c in self.commits)


@dataclass
class WeeklyReport:
    """Weekly report for all contributors."""

    start_date: str
    end_date: str
    repos: list[str]
    contributors: list[ContributorSummary] = field(default_factory=list)
    generated_at: str = ""
    llm_summary: str = ""

    # Overall stats
    total_commits: int = 0
    total_prs: int = 0
    total_merged_prs: int = 0

    def calculate_overall_stats(self) -> None:
        """Calculate overall statistics."""
        self.total_commits = sum(c.total_commits for c in self.contributors)
        self.total_prs = sum(c.total_prs for c in self.contributors)
        self.total_merged_prs = sum(c.merged_prs for c in self.contributors)
        self.generated_at = datetime.now().isoformat()
