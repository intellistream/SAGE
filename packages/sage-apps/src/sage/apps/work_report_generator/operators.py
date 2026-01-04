"""
SAGE Operators for Work Report Generator.

Implements source, map, and sink operators for the work report pipeline.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from sage.common.core import BatchFunction, MapFunction, SinkFunction

from .models import (
    ContributorSummary,
    DiaryEntry,
    GitHubCommit,
    GitHubPullRequest,
    ReportPeriod,
    WeeklyReport,
)


def calculate_period_dates(
    period: ReportPeriod, reference_date: datetime | None = None
) -> tuple[datetime, datetime]:
    """
    Calculate start and end dates for a given report period.

    Args:
        period: The report period type (weekly, monthly, quarterly, yearly).
        reference_date: The reference date to calculate from. Defaults to now.

    Returns:
        Tuple of (start_date, end_date) for the period.
    """
    if reference_date is None:
        reference_date = datetime.now()

    if period == ReportPeriod.WEEKLY:
        # Last 7 days
        end_date = reference_date
        start_date = end_date - timedelta(days=7)
    elif period == ReportPeriod.MONTHLY:
        # Last calendar month or last 30 days
        end_date = reference_date
        # Go to first day of current month, then back one day to get last month
        first_of_month = reference_date.replace(day=1)
        start_date = (first_of_month - timedelta(days=1)).replace(day=1)
        end_date = first_of_month - timedelta(days=1)
        # If we're past the 7th, use last 30 days instead for more recent data
        if reference_date.day > 7:
            end_date = reference_date
            start_date = end_date - timedelta(days=30)
    elif period == ReportPeriod.QUARTERLY:
        # Last quarter (3 months / ~90 days)
        end_date = reference_date
        start_date = end_date - timedelta(days=90)
    elif period == ReportPeriod.YEARLY:
        # Last year (365 days)
        end_date = reference_date
        start_date = end_date - timedelta(days=365)
    else:
        # Default to weekly
        end_date = reference_date
        start_date = end_date - timedelta(days=7)

    return start_date, end_date


def get_period_days(period: ReportPeriod) -> int:
    """Get the number of days for a report period."""
    days_map = {
        ReportPeriod.WEEKLY: 7,
        ReportPeriod.MONTHLY: 30,
        ReportPeriod.QUARTERLY: 90,
        ReportPeriod.YEARLY: 365,
    }
    return days_map.get(period, 7)


class GitHubDataSource(BatchFunction):
    """
    BatchFunction source that fetches commits and PRs from GitHub.

    Uses GitHub GraphQL API to fetch contribution data for specified repositories.
    Supports fetching from specific branches (e.g., main-dev) and submodule repos.
    """

    # SAGE main repository and all submodule repositories
    SAGE_REPOS = [
        "intellistream/SAGE",
        "intellistream/SAGE-Pub",  # docs-public submodule
        "intellistream/sageData",  # benchmark data submodule
        "intellistream/sageLLM",  # sageLLM submodule
        "intellistream/LibAMM",  # libamm submodule
        "intellistream/sageVDB",  # sageVDB submodule
        "intellistream/sageFlow",  # sageFlow submodule
        "intellistream/neuromem",  # neuromem submodule
        "intellistream/sageTSDB",  # sageTSDB submodule
    ]

    def __init__(
        self,
        repos: list[str] | None = None,
        days: int | None = None,
        period: ReportPeriod | str = ReportPeriod.WEEKLY,
        branch: str = "main-dev",
        github_token: str | None = None,
        include_submodules: bool = True,
        **kwargs,
    ) -> None:
        """
        Initialize GitHub data source.

        Args:
            repos: List of repositories in "owner/repo" format.
                   If None, defaults to SAGE_REPOS (main + submodules).
            days: Number of days to look back for contributions (overrides period).
            period: Report period type (weekly/monthly/quarterly/yearly).
            branch: Branch name to fetch commits from. Default "main-dev".
            github_token: GitHub personal access token. If not provided,
                         will try GITHUB_TOKEN or GIT_TOKEN environment variables.
            include_submodules: If True and repos is None, include all SAGE submodules.
        """
        super().__init__(**kwargs)

        # Use SAGE repos by default if none specified
        if repos is None:
            self.repos = self.SAGE_REPOS if include_submodules else ["intellistream/SAGE"]
        else:
            self.repos = repos

        # Handle period parameter
        if isinstance(period, str):
            period = ReportPeriod(period.lower())
        self.period = period

        # Days can override period
        if days is not None:
            self.days = days
        else:
            self.days = get_period_days(period)

        self.branch = branch
        self.github_token = github_token or os.environ.get(
            "GITHUB_TOKEN", os.environ.get("GIT_TOKEN", "")
        )
        self.graphql_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Content-Type": "application/json",
        }

        # Data storage
        self.commits: list[GitHubCommit] = []
        self.pull_requests: list[GitHubPullRequest] = []
        self.current_index = 0
        self.fetched = False

        # Calculate date range based on period or days
        self.start_date, self.end_date = calculate_period_dates(period)

    def _execute_graphql(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = requests.post(
                self.graphql_url,
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"GraphQL request failed: {e}")
            return {"errors": [str(e)]}

    def _fetch_commits(self, owner: str, repo: str) -> list[GitHubCommit]:
        """Fetch commits for a repository within the date range from specific branch."""
        commits = []
        since = self.start_date.isoformat()

        # Query that supports fetching from a specific branch (ref)
        # Also fetches associated PR info to determine who assigned Copilot
        query = """
        query($owner: String!, $repo: String!, $branch: String!, $since: GitTimestamp!, $after: String) {
            repository(owner: $owner, name: $repo) {
                ref(qualifiedName: $branch) {
                    target {
                        ... on Commit {
                            history(since: $since, first: 100, after: $after) {
                                pageInfo {
                                    hasNextPage
                                    endCursor
                                }
                                nodes {
                                    oid
                                    message
                                    committedDate
                                    url
                                    additions
                                    deletions
                                    changedFiles
                                    author {
                                        name
                                        email
                                        user {
                                            login
                                        }
                                    }
                                    committer {
                                        name
                                        email
                                        user {
                                            login
                                        }
                                    }
                                    associatedPullRequests(first: 1) {
                                        nodes {
                                            author {
                                                login
                                            }
                                            assignees(first: 5) {
                                                nodes {
                                                    login
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        after = None
        repo_full = f"{owner}/{repo}"

        while True:
            variables = {
                "owner": owner,
                "repo": repo,
                "branch": f"refs/heads/{self.branch}",
                "since": since,
                "after": after,
            }
            result = self._execute_graphql(query, variables)

            if "errors" in result:
                self.logger.error(
                    f"Error fetching commits from {repo_full}@{self.branch}: {result['errors']}"
                )
                # Try fallback to default branch
                fallback_commits = self._fetch_commits_default_branch(owner, repo)
                return fallback_commits

            data = result.get("data", {}).get("repository", {}).get("ref", {})

            if not data:
                self.logger.warning(
                    f"Branch '{self.branch}' not found in {repo_full}. Trying default branch..."
                )
                return self._fetch_commits_default_branch(owner, repo)

            history = data.get("target", {}).get("history", {})
            nodes = history.get("nodes", [])

            for node in nodes:
                commit = GitHubCommit.from_graphql(node, repo_full)
                commits.append(commit)

            page_info = history.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            after = page_info.get("endCursor")
            time.sleep(0.2)  # Rate limiting

        return commits

    def _fetch_commits_default_branch(self, owner: str, repo: str) -> list[GitHubCommit]:
        """Fallback: Fetch commits from the default branch if specified branch not found."""
        commits = []
        since = self.start_date.isoformat()

        query = """
        query($owner: String!, $repo: String!, $since: GitTimestamp!, $after: String) {
            repository(owner: $owner, name: $repo) {
                defaultBranchRef {
                    name
                    target {
                        ... on Commit {
                            history(since: $since, first: 100, after: $after) {
                                pageInfo {
                                    hasNextPage
                                    endCursor
                                }
                                nodes {
                                    oid
                                    message
                                    committedDate
                                    url
                                    additions
                                    deletions
                                    changedFiles
                                    author {
                                        name
                                        email
                                        user {
                                            login
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        after = None
        repo_full = f"{owner}/{repo}"
        branch_name = None

        while True:
            variables = {
                "owner": owner,
                "repo": repo,
                "since": since,
                "after": after,
            }
            result = self._execute_graphql(query, variables)

            if "errors" in result:
                self.logger.error(f"Error fetching commits: {result['errors']}")
                break

            data = result.get("data", {}).get("repository", {}).get("defaultBranchRef", {})

            if not branch_name and data:
                branch_name = data.get("name", "unknown")
                self.logger.info(f"  Using default branch: {branch_name}")

            history = data.get("target", {}).get("history", {})
            nodes = history.get("nodes", [])

            for node in nodes:
                commit = GitHubCommit.from_graphql(node, repo_full)
                commits.append(commit)

            page_info = history.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            after = page_info.get("endCursor")
            time.sleep(0.2)  # Rate limiting

        return commits

    def _fetch_pull_requests(self, owner: str, repo: str) -> list[GitHubPullRequest]:
        """Fetch pull requests for a repository within the date range."""
        pull_requests = []

        query = """
        query($owner: String!, $repo: String!, $after: String) {
            repository(owner: $owner, name: $repo) {
                pullRequests(first: 100, after: $after, orderBy: {field: CREATED_AT, direction: DESC}) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        number
                        title
                        state
                        createdAt
                        mergedAt
                        closedAt
                        url
                        additions
                        deletions
                        changedFiles
                        author {
                            login
                        }
                        assignees(first: 5) {
                            nodes {
                                login
                            }
                        }
                        labels(first: 10) {
                            nodes {
                                name
                            }
                        }
                        reviewRequests(first: 10) {
                            nodes {
                                requestedReviewer {
                                    ... on User {
                                        login
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        after = None
        repo_full = f"{owner}/{repo}"

        while True:
            variables = {
                "owner": owner,
                "repo": repo,
                "after": after,
            }
            result = self._execute_graphql(query, variables)

            if "errors" in result:
                self.logger.error(f"Error fetching PRs: {result['errors']}")
                break

            data = result.get("data", {}).get("repository", {}).get("pullRequests", {})

            nodes = data.get("nodes", [])
            for node in nodes:
                # Filter by date range
                created_at = node.get("createdAt", "")
                if created_at:
                    created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if created_date.replace(tzinfo=None) < self.start_date:
                        # PRs are sorted by created_at DESC, so we can stop
                        break

                pr = GitHubPullRequest.from_graphql(node, repo_full)
                pull_requests.append(pr)

            page_info = data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break

            # Check if we've gone past our date range
            if nodes:
                last_created = nodes[-1].get("createdAt", "")
                if last_created:
                    last_date = datetime.fromisoformat(last_created.replace("Z", "+00:00"))
                    if last_date.replace(tzinfo=None) < self.start_date:
                        break

            after = page_info.get("endCursor")
            time.sleep(0.2)  # Rate limiting

        return pull_requests

    def _fetch_all_data(self) -> None:
        """Fetch all commits and PRs from all repositories."""
        if not self.github_token:
            self.logger.warning("No GitHub token provided. Using mock data.")
            self._use_mock_data()
            return

        self.logger.info(f"Target branch: {self.branch}")
        self.logger.info(f"Repositories to fetch: {len(self.repos)}")

        for repo in self.repos:
            parts = repo.split("/")
            if len(parts) != 2:
                self.logger.warning(f"Invalid repo format: {repo}")
                continue

            owner, repo_name = parts
            self.logger.info(f"Fetching data from {repo} @ {self.branch}...")

            # Fetch commits from specified branch
            commits = self._fetch_commits(owner, repo_name)
            self.commits.extend(commits)
            self.logger.info(f"  Found {len(commits)} commits")

            # Fetch PRs (PRs are not branch-specific in the same way)
            prs = self._fetch_pull_requests(owner, repo_name)
            self.pull_requests.extend(prs)
            self.logger.info(f"  Found {len(prs)} pull requests")

    def _use_mock_data(self) -> None:
        """Generate mock data for testing."""
        mock_commits = [
            {
                "oid": "abc123",
                "message": "feat: Add weekly report generator",
                "committedDate": datetime.now().isoformat(),
                "url": "https://github.com/intellistream/SAGE/commit/abc123",
                "additions": 500,
                "deletions": 100,
                "changedFiles": 10,
                "author": {
                    "name": "Developer One",
                    "email": "dev1@example.com",
                    "user": {"login": "dev1"},
                },
            },
            {
                "oid": "def456",
                "message": "fix: Resolve pipeline issue",
                "committedDate": (datetime.now() - timedelta(days=1)).isoformat(),
                "url": "https://github.com/intellistream/SAGE/commit/def456",
                "additions": 50,
                "deletions": 30,
                "changedFiles": 3,
                "author": {
                    "name": "Developer Two",
                    "email": "dev2@example.com",
                    "user": {"login": "dev2"},
                },
            },
        ]

        mock_prs = [
            {
                "number": 100,
                "title": "feat: Weekly report generator implementation",
                "state": "MERGED",
                "createdAt": datetime.now().isoformat(),
                "mergedAt": datetime.now().isoformat(),
                "closedAt": None,
                "url": "https://github.com/intellistream/SAGE/pull/100",
                "additions": 1000,
                "deletions": 200,
                "changedFiles": 15,
                "author": {"login": "dev1"},
                "labels": {"nodes": [{"name": "feature"}]},
                "reviewRequests": {"nodes": []},
            },
        ]

        for commit_data in mock_commits:
            self.commits.append(GitHubCommit.from_graphql(commit_data, "intellistream/SAGE"))

        for pr_data in mock_prs:
            self.pull_requests.append(GitHubPullRequest.from_graphql(pr_data, "intellistream/SAGE"))

    def execute(self) -> dict[str, Any] | None:
        """Execute batch function to emit data packets."""
        if not self.fetched:
            self.logger.info(f"Fetching GitHub data for past {self.days} days...")
            self._fetch_all_data()
            self.fetched = True
            self.logger.info(f"Fetched {len(self.commits)} commits, {len(self.pull_requests)} PRs")

        # Emit commits first, then PRs
        total_items = len(self.commits) + len(self.pull_requests)
        if self.current_index < len(self.commits):
            commit = self.commits[self.current_index]
            self.current_index += 1
            return {
                "type": "commit",
                "data": commit,
                "repo": commit.repo,
                "author": commit.author,
            }
        elif self.current_index < total_items:
            pr_index = self.current_index - len(self.commits)
            pr = self.pull_requests[pr_index]
            self.current_index += 1
            return {
                "type": "pull_request",
                "data": pr,
                "repo": pr.repo,
                "author": pr.author,
            }

        return None


class DiaryEntrySource(BatchFunction):
    """
    BatchFunction source that loads diary entries from files.

    Supports JSON and Markdown formats.
    """

    def __init__(
        self,
        diary_path: str | Path | None = None,
        days: int | None = None,
        period: ReportPeriod | str = ReportPeriod.WEEKLY,
        **kwargs,
    ) -> None:
        """
        Initialize diary entry source.

        Args:
            diary_path: Path to diary directory or file.
            days: Number of days to look back (overrides period).
            period: Report period type (weekly/monthly/quarterly/yearly).
        """
        super().__init__(**kwargs)
        self.diary_path = Path(diary_path) if diary_path else None

        # Handle period parameter
        if isinstance(period, str):
            period = ReportPeriod(period.lower())
        self.period = period

        # Days can override period
        if days is not None:
            self.days = days
        else:
            self.days = get_period_days(period)

        self.entries: list[DiaryEntry] = []
        self.current_index = 0
        self.fetched = False

        # Calculate date range based on period
        self.start_date, self.end_date = calculate_period_dates(period)

    def _load_entries(self) -> None:
        """Load diary entries from the specified path."""
        if not self.diary_path or not self.diary_path.exists():
            self.logger.info("No diary path specified or path doesn't exist")
            return

        if self.diary_path.is_file():
            self._load_file(self.diary_path)
        elif self.diary_path.is_dir():
            # Load all JSON and MD files
            for file_path in self.diary_path.glob("**/*.json"):
                self._load_file(file_path)
            for file_path in self.diary_path.glob("**/*.md"):
                self._load_markdown_file(file_path)

    def _load_file(self, file_path: Path) -> None:
        """Load entries from a JSON file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                for item in data:
                    entry = DiaryEntry.from_dict(item)
                    if self._is_in_date_range(entry.date):
                        self.entries.append(entry)
            elif isinstance(data, dict):
                entry = DiaryEntry.from_dict(data)
                if self._is_in_date_range(entry.date):
                    self.entries.append(entry)

        except Exception as e:
            self.logger.warning(f"Error loading {file_path}: {e}")

    def _load_markdown_file(self, file_path: Path) -> None:
        """Load a single markdown file as a diary entry."""
        try:
            content = file_path.read_text(encoding="utf-8")

            # Extract date from filename (e.g., 2024-01-15.md)
            date_str = file_path.stem
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                date_str = datetime.now().strftime("%Y-%m-%d")

            if self._is_in_date_range(date_str):
                entry = DiaryEntry(
                    date=date_str,
                    author="Unknown",
                    content=content,
                    category="diary",
                )
                self.entries.append(entry)

        except Exception as e:
            self.logger.warning(f"Error loading markdown {file_path}: {e}")

    def _is_in_date_range(self, date_str: str) -> bool:
        """Check if a date string is within the configured range."""
        try:
            date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            return self.start_date <= date <= self.end_date
        except ValueError:
            return True  # Include if can't parse

    def execute(self) -> dict[str, Any] | None:
        """Execute batch function to emit diary entries."""
        if not self.fetched:
            self._load_entries()
            self.fetched = True
            self.logger.info(f"Loaded {len(self.entries)} diary entries")

        if self.current_index < len(self.entries):
            entry = self.entries[self.current_index]
            self.current_index += 1
            return {
                "type": "diary_entry",
                "data": entry,
                "author": entry.author,
            }

        return None


class ContributorAggregator(MapFunction):
    """
    MapFunction that aggregates data by contributor.

    Collects commits, PRs, and diary entries for each contributor.
    """

    # Class-level storage for aggregation across all instances
    _contributors: dict[str, ContributorSummary] = {}

    # Username aliases: map alternative names to canonical names
    # Key: lowercase alias, Value: canonical name
    USERNAME_ALIASES: dict[str, str] = {
        # ShuhaoZhangTony variants
        "shuhao zhang": "ShuhaoZhangTony",
        "shuhaozhangtony": "ShuhaoZhangTony",
        "shuhaozhang": "ShuhaoZhangTony",
        # Copilot variants - these will be reassigned to their assigners
        "copilot": "Copilot",
        "copilot-swe-agent": "Copilot",
        "github-copilot": "Copilot",
    }

    # Copilot usernames (lowercase)
    COPILOT_USERS: set[str] = {"copilot", "copilot-swe-agent", "github-copilot"}

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    @classmethod
    def normalize_username(cls, username: str) -> str:
        """Normalize username to canonical form."""
        if not username:
            return "Unknown"
        # Check if lowercase version matches any alias
        lower_name = username.lower().strip()
        return cls.USERNAME_ALIASES.get(lower_name, username)

    @classmethod
    def is_copilot_user(cls, username: str) -> bool:
        """Check if the username is a Copilot variant."""
        return username.lower().strip() in cls.COPILOT_USERS

    def _resolve_author(
        self, raw_author: str, item: GitHubCommit | GitHubPullRequest | DiaryEntry | None
    ) -> tuple[str, bool]:
        """
        Resolve the final author for contribution attribution.

        Returns:
            tuple: (final_author, is_copilot_assisted)
        """
        normalized = self.normalize_username(raw_author)

        # Check if this is a Copilot commit with an assigned user
        if isinstance(item, GitHubCommit) and self.is_copilot_user(raw_author):
            if item.assigned_by:
                # Attribute to the assigning user, but mark as Copilot-assisted
                final_author = self.normalize_username(item.assigned_by)
                return final_author, True

        # Check if this is a Copilot PR with an assigned user
        if isinstance(item, GitHubPullRequest) and self.is_copilot_user(raw_author):
            if item.assigned_by:
                # Attribute to the assigning user, but mark as Copilot-assisted
                final_author = self.normalize_username(item.assigned_by)
                return final_author, True

        return normalized, False

    def execute(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Aggregate data by contributor."""
        # Skip non-dict data (e.g., StopSignal)
        if not isinstance(data, dict):
            return None

        raw_author = data.get("author", "Unknown")
        data_type = data.get("type")
        item = data.get("data")

        # Resolve author (handle Copilot attribution)
        author, is_copilot_assisted = self._resolve_author(raw_author, item)

        if author not in ContributorAggregator._contributors:
            ContributorAggregator._contributors[author] = ContributorSummary(username=author)

        contributor = ContributorAggregator._contributors[author]

        if data_type == "commit" and isinstance(item, GitHubCommit):
            contributor.commits.append(item)
            if is_copilot_assisted:
                # Track Copilot-assisted commits separately
                if not hasattr(contributor, "copilot_assisted_commits"):
                    contributor.copilot_assisted_commits = 0
                contributor.copilot_assisted_commits += 1
        elif data_type == "pull_request" and isinstance(item, GitHubPullRequest):
            contributor.pull_requests.append(item)
            if is_copilot_assisted:
                # Track Copilot-assisted PRs separately
                if not hasattr(contributor, "copilot_assisted_prs"):
                    contributor.copilot_assisted_prs = 0
                contributor.copilot_assisted_prs += 1
        elif data_type == "diary_entry" and isinstance(item, DiaryEntry):
            contributor.diary_entries.append(item)

        # Return the updated contributor summary
        contributor.calculate_stats()
        return {
            "type": "contributor_update",
            "author": author,
            "contributor": contributor,
        }

    @classmethod
    def get_all_contributors(cls) -> dict[str, ContributorSummary]:
        """Get all aggregated contributors."""
        return cls._contributors

    @classmethod
    def reset(cls) -> None:
        """Reset the aggregator state."""
        cls._contributors = {}


class LLMReportGenerator(MapFunction):
    """
    MapFunction that generates LLM-powered summaries for contributors.

    Uses UnifiedInferenceClient to generate natural language summaries.
    """

    def __init__(
        self,
        language: str = "zh",
        **kwargs,
    ) -> None:
        """
        Initialize LLM report generator.

        Args:
            language: Output language ("zh" for Chinese, "en" for English).
        """
        super().__init__(**kwargs)
        self.language = language
        self._client = None
        self._processed_authors: set[str] = set()

    def _get_client(self):
        """Lazy initialization of LLM client."""
        if self._client is None:
            try:
                from sage.llm import UnifiedInferenceClient

                self._client = UnifiedInferenceClient.create()
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM client: {e}")
                self._client = None
        return self._client

    def _generate_summary(self, contributor: ContributorSummary) -> str:
        """Generate a summary for a contributor using LLM."""
        client = self._get_client()
        if client is None:
            return self._generate_simple_summary(contributor)

        # Build context for LLM
        commits_text = "\n".join(
            f"- {c.message} ({c.additions}+ / {c.deletions}-)"
            for c in contributor.commits[:10]  # Limit to recent 10
        )

        prs_text = "\n".join(f"- [{pr.state}] {pr.title}" for pr in contributor.pull_requests[:5])

        diary_text = "\n".join(
            f"- [{e.date}] {e.content[:100]}..." for e in contributor.diary_entries[:3]
        )

        if self.language == "zh":
            prompt = f"""请为以下贡献者生成一份简洁的周报总结：

贡献者：{contributor.username}

本周提交记录：
{commits_text or "无提交记录"}

Pull Requests：
{prs_text or "无PR记录"}

个人日志：
{diary_text or "无日志"}

统计数据：
- 提交次数：{contributor.total_commits}
- PR数量：{contributor.total_prs}（已合并：{contributor.merged_prs}）
- 代码变更：+{contributor.total_additions} / -{contributor.total_deletions}

请生成一份100-200字的工作总结，突出主要贡献和成果。"""
        else:
            prompt = f"""Generate a brief weekly report summary for the following contributor:

Contributor: {contributor.username}

Commits this week:
{commits_text or "No commits"}

Pull Requests:
{prs_text or "No PRs"}

Personal notes:
{diary_text or "No notes"}

Statistics:
- Commits: {contributor.total_commits}
- PRs: {contributor.total_prs} (Merged: {contributor.merged_prs})
- Lines changed: +{contributor.total_additions} / -{contributor.total_deletions}

Generate a 100-200 word work summary highlighting key contributions."""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = client.chat(messages)
            if hasattr(response, "content"):
                return response.content
            return str(response)
        except Exception as e:
            self.logger.warning(f"LLM generation failed: {e}")
            return self._generate_simple_summary(contributor)

    def _generate_simple_summary(self, contributor: ContributorSummary) -> str:
        """Generate a simple summary without LLM."""
        if self.language == "zh":
            return (
                f"{contributor.username} 本周贡献了 {contributor.total_commits} 次提交，"
                f"提交了 {contributor.total_prs} 个PR（已合并 {contributor.merged_prs} 个），"
                f"代码变更 +{contributor.total_additions}/-{contributor.total_deletions} 行。"
            )
        else:
            return (
                f"{contributor.username} contributed {contributor.total_commits} commits, "
                f"submitted {contributor.total_prs} PRs ({contributor.merged_prs} merged), "
                f"with +{contributor.total_additions}/-{contributor.total_deletions} lines changed."
            )

    def execute(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Generate summary for contributor updates."""
        if data.get("type") != "contributor_update":
            return data

        author = data.get("author", "")
        contributor = data.get("contributor")

        # Only generate summary once per author
        if author in self._processed_authors:
            return None

        self._processed_authors.add(author)

        if contributor:
            summary = self._generate_summary(contributor)
            data["llm_summary"] = summary

        return data


class ReportSink(SinkFunction):
    """
    SinkFunction that collects and outputs the final report.

    Supports multiple output formats: console, markdown, JSON.
    """

    def __init__(
        self,
        output_format: str = "markdown",
        output_path: str | Path | None = None,
        repos: list[str] | None = None,
        days: int | None = None,
        period: ReportPeriod | str = ReportPeriod.WEEKLY,
        language: str = "zh",
        use_llm: bool = True,
        **kwargs,
    ) -> None:
        """
        Initialize report sink.

        Args:
            output_format: Output format ("console", "markdown", "json").
            output_path: Path to save the report file.
            repos: List of repositories being tracked.
            days: Number of days in the report period (overrides period).
            period: Report period type (weekly/monthly/quarterly/yearly).
            language: Output language ("zh" or "en").
            use_llm: Whether to use LLM for leaderboard generation.
        """
        super().__init__(**kwargs)
        self.output_format = output_format
        self.output_path = Path(output_path) if output_path else None
        self.repos = repos or []

        # Handle period parameter
        if isinstance(period, str):
            period = ReportPeriod(period.lower())
        self.period = period

        # Days can override period
        if days is not None:
            self.days = days
        else:
            self.days = get_period_days(period)

        self.language = language
        self.use_llm = use_llm
        self.contributors: dict[str, dict[str, Any]] = {}
        self.start_time = time.time()
        self._llm_client = None

        # Date range based on period
        self.start_date, self.end_date = calculate_period_dates(period)

    def _get_llm_client(self):
        """Lazy initialization of LLM client."""
        if self._llm_client is None:
            try:
                from sage.llm import UnifiedInferenceClient

                self._llm_client = UnifiedInferenceClient.create()
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM client: {e}")
                self._llm_client = None
        return self._llm_client

    def _get_period_text(self) -> dict[str, str]:
        """Get period-specific text for report generation."""
        period_texts = {
            ReportPeriod.WEEKLY: {
                "zh_title": "本周贡献排行榜",
                "en_title": "Weekly Contribution Leaderboard",
                "zh_period": "本周",
                "en_period": "this week",
                "zh_summary_type": "周报",
                "en_summary_type": "weekly report",
            },
            ReportPeriod.MONTHLY: {
                "zh_title": "本月贡献排行榜",
                "en_title": "Monthly Contribution Leaderboard",
                "zh_period": "本月",
                "en_period": "this month",
                "zh_summary_type": "月报",
                "en_summary_type": "monthly report",
            },
            ReportPeriod.QUARTERLY: {
                "zh_title": "本季度贡献排行榜",
                "en_title": "Quarterly Contribution Leaderboard",
                "zh_period": "本季度",
                "en_period": "this quarter",
                "zh_summary_type": "季报",
                "en_summary_type": "quarterly report",
            },
            ReportPeriod.YEARLY: {
                "zh_title": "年度贡献排行榜",
                "en_title": "Yearly Contribution Leaderboard",
                "zh_period": "本年度",
                "en_period": "this year",
                "zh_summary_type": "年报",
                "en_summary_type": "yearly report",
            },
        }
        return period_texts.get(self.period, period_texts[ReportPeriod.WEEKLY])

    def _generate_leaderboard(self, report: WeeklyReport) -> str:
        """Generate a contribution leaderboard with visual chart and optional LLM comments."""
        # Sort contributors by contribution score
        sorted_contributors = sorted(
            report.contributors,
            key=lambda c: c.total_commits + c.merged_prs * 3,
            reverse=True,
        )

        # Always generate visual chart first
        chart = self._generate_leaderboard_chart(sorted_contributors)

        if not self.use_llm:
            return self._generate_simple_leaderboard(report)

        client = self._get_llm_client()
        if client is None:
            return self._generate_simple_leaderboard(report)

        # Build contributor stats for LLM
        contributors_data = []
        for c in report.contributors:
            contributors_data.append(
                {
                    "name": c.username,
                    "commits": c.total_commits,
                    "prs": c.total_prs,
                    "merged_prs": c.merged_prs,
                    "additions": c.total_additions,
                    "deletions": c.total_deletions,
                }
            )

        # Sort by contribution (commits + merged PRs * 3)
        contributors_data.sort(key=lambda x: x["commits"] + x["merged_prs"] * 3, reverse=True)

        stats_text = "\n".join(
            f"- {i + 1}. {c['name']}: {c['commits']} commits, "
            f"{c['prs']} PRs ({c['merged_prs']} merged), "
            f"+{c['additions']}/-{c['deletions']} lines"
            for i, c in enumerate(contributors_data)
        )

        # Get period-specific text
        period_text = self._get_period_text()

        if self.language == "zh":
            prompt = f"""根据以下贡献者数据，生成一份简洁有趣的{period_text["zh_period"]}贡献度排行榜评语。
请用emoji和简短评语让排行榜更生动。

贡献者数据（按贡献度排序）：
{stats_text}

时间范围：{report.start_date} ~ {report.end_date}
总提交数：{report.total_commits}
总PR数：{report.total_prs}（已合并：{report.total_merged_prs}）

要求：
1. 用🥇🥈🥉标注前三名
2. 每个人配一句简短有趣的评语（10-20字）
3. 最后加一句团队总结或鼓励语
4. 保持简洁，总共不超过300字"""
        else:
            prompt = f"""Based on the contributor data below, generate brief and fun {period_text["en_period"]} contribution leaderboard comments.
Use emojis and short comments to make it engaging.

Contributor data (sorted by contribution):
{stats_text}

Period: {report.start_date} ~ {report.end_date}
Total commits: {report.total_commits}
Total PRs: {report.total_prs} (merged: {report.total_merged_prs})

Requirements:
1. Use 🥇🥈🥉 for top 3
2. Add a short fun comment for each person (10-20 words)
3. End with a team summary or encouragement
4. Keep it concise, under 300 words total"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = client.chat(messages)
            llm_comments = response.content if hasattr(response, "content") else str(response)

            # Combine chart with LLM comments
            title = (
                f"## 🏆 {period_text['zh_title']}"
                if self.language == "zh"
                else f"## 🏆 {period_text['en_title']}"
            )
            return f"{title}\n\n{chart}\n\n{llm_comments}"
        except Exception as e:
            self.logger.warning(f"LLM leaderboard generation failed: {e}")
            return self._generate_simple_leaderboard(report)

    def _generate_simple_leaderboard(self, report: WeeklyReport) -> str:
        """Generate a simple leaderboard without LLM."""
        # Sort contributors by contribution score
        sorted_contributors = sorted(
            report.contributors,
            key=lambda c: c.total_commits + c.merged_prs * 3,
            reverse=True,
        )

        # Generate visual bar chart
        chart = self._generate_leaderboard_chart(sorted_contributors)

        # Get period-specific text
        period_text = self._get_period_text()

        if self.language == "zh":
            lines = [f"## 🏆 {period_text['zh_title']}", ""]
            lines.append(chart)
            lines.append("")
            medals = ["🥇", "🥈", "🥉"]
            for i, c in enumerate(sorted_contributors):
                medal = medals[i] if i < 3 else f"{i + 1}."
                lines.append(
                    f"{medal} **{c.username}** - "
                    f"{c.total_commits} commits, {c.merged_prs} merged PRs"
                )
            lines.append("")
            lines.append(
                f"*{period_text['zh_period']}团队共完成 {report.total_commits} 次提交，"
                f"合并 {report.total_merged_prs} 个PR，继续加油。*"
            )
        else:
            lines = [f"## 🏆 {period_text['en_title']}", ""]
            lines.append(chart)
            lines.append("")
            medals = ["🥇", "🥈", "🥉"]
            for i, c in enumerate(sorted_contributors):
                medal = medals[i] if i < 3 else f"{i + 1}."
                lines.append(
                    f"{medal} **{c.username}** - "
                    f"{c.total_commits} commits, {c.merged_prs} merged PRs"
                )
            lines.append("")
            lines.append(
                f"*Team completed {report.total_commits} commits and "
                f"merged {report.total_merged_prs} PRs {period_text['en_period']}. Keep it up.*"
            )

        return "\n".join(lines)

    def _generate_leaderboard_chart(self, sorted_contributors: list) -> str:
        """Generate an ASCII/Unicode bar chart for the leaderboard."""
        if not sorted_contributors:
            return ""

        # Calculate contribution scores
        scores = []
        for c in sorted_contributors:
            score = c.total_commits + c.merged_prs * 3
            scores.append((c.username, score, c.total_commits, c.merged_prs))

        max_score = max(s[1] for s in scores) if scores else 1
        max_name_len = max(len(s[0]) for s in scores) if scores else 10
        max_name_len = min(max_name_len, 20)  # Cap at 20 chars

        # Bar characters
        bar_full = "█"
        bar_width = 30

        lines = ["```"]
        lines.append(f"{'Contributor':<{max_name_len}} │ {'Score':>6} │ Progress")
        lines.append(f"{'─' * max_name_len}─┼{'─' * 8}┼{'─' * (bar_width + 10)}")

        medals = ["🥇", "🥈", "🥉"]

        for i, (name, score, commits, prs) in enumerate(scores):
            # Truncate long names
            display_name = name[:max_name_len] if len(name) > max_name_len else name

            # Calculate bar length
            bar_len = int((score / max_score) * bar_width) if max_score > 0 else 0
            bar = bar_full * bar_len

            # Medal for top 3
            medal = medals[i] if i < 3 else "  "

            # Color-like indicators using different bar styles
            lines.append(
                f"{display_name:<{max_name_len}} │ {score:>6} │ {bar} {medal} ({commits}c+{prs}pr)"
            )

        lines.append("```")
        lines.append("")
        lines.append("*Score = commits + merged_prs × 3*")

        return "\n".join(lines)

    def execute(self, data: dict[str, Any]) -> None:
        """Collect data for the report."""
        if data.get("type") == "contributor_update":
            author = data.get("author", "Unknown")
            self.contributors[author] = {
                "contributor": data.get("contributor"),
                "llm_summary": data.get("llm_summary", ""),
            }

    def close(self) -> None:
        """Generate and output the final report."""
        elapsed = time.time() - self.start_time

        # Build report
        report = WeeklyReport(
            start_date=self.start_date.strftime("%Y-%m-%d"),
            end_date=self.end_date.strftime("%Y-%m-%d"),
            repos=self.repos,
        )

        for author, data in self.contributors.items():
            contributor = data.get("contributor")
            if contributor:
                report.contributors.append(contributor)

        report.calculate_overall_stats()

        # Output based on format
        if self.output_format == "console":
            self._output_console(report, elapsed)
        elif self.output_format == "markdown":
            self._output_markdown(report, elapsed)
        elif self.output_format == "json":
            self._output_json(report, elapsed)

    def _output_console(self, report: WeeklyReport, elapsed: float) -> None:
        """Output report to console."""
        print("\n" + "=" * 70)
        print("Weekly Work Report / 周报")
        print("=" * 70)
        print(f"Period: {report.start_date} ~ {report.end_date}")
        print(f"Repositories: {', '.join(report.repos)}")
        print("=" * 70)

        print(
            f"\n Total: {report.total_commits} commits, "
            f"{report.total_prs} PRs ({report.total_merged_prs} merged)"
        )
        print("-" * 70)

        for contributor in report.contributors:
            print(f"\n {contributor.username}")
            print(f"   Commits: {contributor.total_commits}")
            print(f"   PRs: {contributor.total_prs} (merged: {contributor.merged_prs})")
            print(f"   Lines: +{contributor.total_additions} / -{contributor.total_deletions}")

            # Recent commits
            if contributor.commits:
                print("   Recent commits:")
                for commit in contributor.commits[:3]:
                    print(f"     - {commit.message[:60]}")

            # LLM Summary
            llm_summary = self.contributors.get(contributor.username, {}).get("llm_summary", "")
            if llm_summary:
                print(f"   Summary: {llm_summary[:200]}...")

        # Generate and print leaderboard
        print("\n" + "-" * 70)
        leaderboard = self._generate_leaderboard(report)
        print(leaderboard)

        print("\n" + "=" * 70)
        print(f" Generated in {elapsed:.2f}s")
        print("=" * 70 + "\n")

    def _output_markdown(self, report: WeeklyReport, elapsed: float) -> None:
        """Output report as Markdown."""
        lines = [
            "# Weekly Work Report",
            "",
            f"**Period:** {report.start_date} ~ {report.end_date}",
            f"**Repositories:** {', '.join(report.repos)}",
            f"**Generated:** {report.generated_at}",
            "",
            "## Summary",
            "",
            f"- Total Commits: {report.total_commits}",
            f"- Total PRs: {report.total_prs} ({report.total_merged_prs} merged)",
            "",
            "## Contributors",
            "",
        ]

        for contributor in report.contributors:
            lines.extend(
                [
                    f"### {contributor.username}",
                    "",
                    f"- **Commits:** {contributor.total_commits}",
                    f"- **PRs:** {contributor.total_prs} (merged: {contributor.merged_prs})",
                    f"- **Lines Changed:** +{contributor.total_additions} / -{contributor.total_deletions}",
                    "",
                ]
            )

            if contributor.commits:
                lines.append("**Recent Commits:**")
                for commit in contributor.commits[:5]:
                    lines.append(f"- [{commit.sha[:7]}]({commit.url}) {commit.message[:60]}")
                lines.append("")

            if contributor.pull_requests:
                lines.append("**Pull Requests:**")
                for pr in contributor.pull_requests[:5]:
                    status = "" if pr.state == "MERGED" else f"[{pr.state}] "
                    lines.append(f"- {status}[#{pr.number}]({pr.url}) {pr.title}")
                lines.append("")

            llm_summary = self.contributors.get(contributor.username, {}).get("llm_summary", "")
            if llm_summary:
                lines.extend(
                    [
                        "**AI Summary:**",
                        "",
                        f"> {llm_summary}",
                        "",
                    ]
                )

        # Add leaderboard section
        leaderboard = self._generate_leaderboard(report)
        lines.extend(
            [
                "",
                leaderboard,
                "",
                "---",
                f"*Report generated in {elapsed:.2f}s by SAGE Work Report Generator*",
            ]
        )

        content = "\n".join(lines)

        if self.output_path:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self.output_path.write_text(content, encoding="utf-8")
            print(f" Report saved to: {self.output_path}")
        else:
            print(content)

    def _output_json(self, report: WeeklyReport, elapsed: float) -> None:
        """Output report as JSON."""
        data = {
            "start_date": report.start_date,
            "end_date": report.end_date,
            "repos": report.repos,
            "generated_at": report.generated_at,
            "summary": {
                "total_commits": report.total_commits,
                "total_prs": report.total_prs,
                "total_merged_prs": report.total_merged_prs,
            },
            "contributors": [],
        }

        for contributor in report.contributors:
            contrib_data = {
                "username": contributor.username,
                "stats": {
                    "commits": contributor.total_commits,
                    "prs": contributor.total_prs,
                    "merged_prs": contributor.merged_prs,
                    "additions": contributor.total_additions,
                    "deletions": contributor.total_deletions,
                },
                "commits": [
                    {
                        "sha": c.sha,
                        "message": c.message,
                        "url": c.url,
                        "date": c.committed_date,
                    }
                    for c in contributor.commits
                ],
                "pull_requests": [
                    {
                        "number": pr.number,
                        "title": pr.title,
                        "state": pr.state,
                        "url": pr.url,
                    }
                    for pr in contributor.pull_requests
                ],
                "llm_summary": self.contributors.get(contributor.username, {}).get(
                    "llm_summary", ""
                ),
            }
            data["contributors"].append(contrib_data)

        # Add leaderboard
        leaderboard = self._generate_leaderboard(report)
        data["leaderboard"] = leaderboard

        content = json.dumps(data, indent=2, ensure_ascii=False)

        if self.output_path:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self.output_path.write_text(content, encoding="utf-8")
            print(f" Report saved to: {self.output_path}")
        else:
            print(content)


class ConsoleSink(SinkFunction):
    """Simple sink that logs each item processed."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.count = 0

    def execute(self, data: dict[str, Any]) -> None:
        """Log processing progress."""
        self.count += 1
        data_type = data.get("type", "unknown")
        author = data.get("author", "Unknown")
        self.logger.info(f"[{self.count}] Processed {data_type} from {author}")
