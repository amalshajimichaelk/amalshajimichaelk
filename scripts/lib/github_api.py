"""GitHub API client for fetching repository and commit data."""

import urllib.request
import urllib.error
import json
import os
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""
    pass


class GitHubClient:
    """GitHub API client with authentication and rate limit handling."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        if not self.token:
            raise GitHubAPIError("GITHUB_TOKEN not found in environment")

    def _make_request(self, url: str, max_retries: int = 3) -> Tuple[Dict, Dict]:
        """Make authenticated GitHub API request with retry logic.

        Returns:
            Tuple of (response_data, headers)
        """
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "github-profile-updater",
        }

        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as response:
                    data = json.loads(response.read().decode())
                    return data, dict(response.headers)

            except urllib.error.HTTPError as e:
                if e.code == 403:
                    # Rate limit or forbidden
                    reset_time = e.headers.get("X-RateLimit-Reset")
                    if reset_time:
                        wait_time = int(reset_time) - int(time.time())
                        if wait_time > 0 and wait_time < 300:  # Wait max 5 minutes
                            print(f"⏳ Rate limit hit. Waiting {wait_time}s...")
                            time.sleep(wait_time + 1)
                            continue
                    raise GitHubAPIError(f"HTTP 403: {e.read().decode()}")

                elif e.code == 404:
                    return None, {}

                elif e.code >= 500 and attempt < max_retries - 1:
                    # Server error, retry with exponential backoff
                    wait = 2 ** attempt
                    print(f"⚠️  Server error {e.code}, retrying in {wait}s...")
                    time.sleep(wait)
                    continue

                raise GitHubAPIError(f"HTTP {e.code}: {e.read().decode()}")

            except urllib.error.URLError as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"⚠️  Network error, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                raise GitHubAPIError(f"Network error: {e.reason}")

        raise GitHubAPIError(f"Max retries ({max_retries}) exceeded")

    def get_user_repos(self, username: str) -> List[Dict]:
        """Fetch all repositories for a user (owned, not forks by default)."""
        repos = []
        page = 1

        while True:
            url = f"{self.BASE_URL}/users/{username}/repos?per_page=100&page={page}&type=owner"
            data, _ = self._make_request(url)

            if not data:
                break

            repos.extend(data)

            if len(data) < 100:
                break

            page += 1

        # Filter out forks and private repos
        return [r for r in repos if not r.get("fork", False) and not r.get("private", False)]

    def get_repo_info(self, owner: str, repo: str) -> Optional[Dict]:
        """Fetch repository metadata."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        data, _ = self._make_request(url)
        return data

    def get_latest_commit_by_author(self, owner: str, repo: str, author: str) -> Optional[Dict]:
        """Get the latest commit authored by a specific user.

        Returns:
            Commit dict with sha, author, committer timestamps, or None if no commits found
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits?author={author}&per_page=1"
        data, _ = self._make_request(url)

        if not data or len(data) == 0:
            return None

        return data[0]

    def verify_commit_author(self, owner: str, repo: str, sha: str, expected_author: str) -> bool:
        """Verify that a commit was authored by the expected user.

        Args:
            owner: Repository owner
            repo: Repository name
            sha: Commit SHA
            expected_author: Expected GitHub username

        Returns:
            True if commit author matches expected_author
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits/{sha}"
        data, _ = self._make_request(url)

        if not data:
            return False

        # Check GitHub author association
        author_login = data.get("author", {}).get("login") if data.get("author") else None

        # Also check commit author info
        commit_author = data.get("commit", {}).get("author", {}).get("name", "")

        return author_login == expected_author

    def search_user_commits(self, username: str, max_repos: int = 100) -> List[Dict]:
        """Search for commits by a user across all public repositories.

        Note: GitHub Search API has limitations and may not return all results.
        Use this as a discovery mechanism, not the sole source of truth.

        Returns:
            List of commit search results with repository info
        """
        # Search commits by author
        url = f"{self.BASE_URL}/search/commits?q=author:{username}&sort=committer-date&order=desc&per_page=100"

        try:
            data, _ = self._make_request(url)
            return data.get("items", [])[:max_repos]
        except GitHubAPIError as e:
            print(f"⚠️  Commit search failed: {e}")
            return []

    def get_repo_commits_page(self, owner: str, repo: str, author: str, page: int = 1) -> List[Dict]:
        """Get a page of commits for a repository by a specific author."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits?author={author}&per_page=100&page={page}"
        data, _ = self._make_request(url)
        return data if data else []


def parse_github_timestamp(timestamp_str: str) -> datetime:
    """Parse GitHub ISO 8601 timestamp to datetime object."""
    # GitHub returns timestamps like: 2026-11-04T04:30:00Z
    return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))


def format_contribution_date(timestamp_str: str) -> str:
    """Format timestamp for display in README (e.g., 'Nov 04, 2026')."""
    dt = parse_github_timestamp(timestamp_str)
    return dt.strftime("%b %d, %Y")
