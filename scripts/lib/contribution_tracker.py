"""Contribution tracking system for managing repository contribution data."""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone
from .github_api import GitHubClient, parse_github_timestamp


class ContributionTracker:
    """Manages persistent contribution data and tracks latest personal commits."""

    SCHEMA_VERSION = 1

    def __init__(self, data_file: str, username: str):
        self.data_file = data_file
        self.username = username
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        """Load contribution data from JSON file."""
        if not os.path.exists(self.data_file):
            return self._create_empty_data()

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate schema version
            if data.get("schema_version") != self.SCHEMA_VERSION:
                print(f"⚠️  Schema version mismatch. Creating fresh data.")
                return self._create_empty_data()

            return data

        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Failed to load data file: {e}. Creating fresh data.")
            return self._create_empty_data()

    def _create_empty_data(self) -> Dict:
        """Create empty contribution data structure."""
        return {
            "schema_version": self.SCHEMA_VERSION,
            "username": self.username,
            "last_successful_reconciliation": None,
            "repositories": {}
        }

    def save(self):
        """Save contribution data to JSON file."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

        # Write atomically by writing to temp file first
        temp_file = self.data_file + ".tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)

            # Replace original file
            os.replace(temp_file, self.data_file)
            print(f"✅ Saved contribution data to {self.data_file}")

        except Exception as e:
            print(f"❌ Failed to save data: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise

    def update_repository(self, repo_info: Dict, latest_commit: Optional[Dict] = None):
        """Update or add repository with its latest personal contribution.

        Args:
            repo_info: Repository metadata from GitHub API
            latest_commit: Latest commit by the user from GitHub API (or None if repo was created by user)
        """
        full_name = repo_info["full_name"]

        # Verify repository is public
        if repo_info.get("private", False):
            print(f"⚠️  Repository {full_name} is private, skipping")
            return

        if latest_commit:
            commit_data = latest_commit.get("commit", {})
            committer_timestamp = commit_data.get("committer", {}).get("date")
            author_timestamp = commit_data.get("author", {}).get("date")
            commit_sha = latest_commit.get("sha")
            commit_url = latest_commit.get("html_url")
        elif repo_info.get("owner", {}).get("login") == self.username and not repo_info.get("fork", False):
            # User created the repository - repo creation is a personal contribution
            committer_timestamp = repo_info.get("created_at")
            author_timestamp = repo_info.get("created_at")
            commit_sha = None
            commit_url = repo_info.get("html_url")
        else:
            print(f"⚠️  No personal contributions for {full_name}, skipping")
            return

        if not committer_timestamp:
            print(f"⚠️  No committer timestamp for {full_name}, skipping")
            return

        self.data["repositories"][full_name] = {
            "name": repo_info["name"],
            "full_name": full_name,
            "html_url": repo_info["html_url"],
            "latest_commit_sha": commit_sha,
            "latest_commit_url": commit_url,
            "latest_personal_commit_timestamp": committer_timestamp,
            "author_timestamp": author_timestamp,
            "language": repo_info.get("language"),
            "visibility": "public",
            "last_verified_at": datetime.now(timezone.utc).isoformat()
        }

        print(f"✅ Updated {full_name}: {committer_timestamp}")

    def remove_repository(self, full_name: str):
        """Remove a repository from tracking."""
        if full_name in self.data["repositories"]:
            del self.data["repositories"][full_name]
            print(f"🗑️  Removed {full_name}")

    def get_repository(self, full_name: str) -> Optional[Dict]:
        """Get repository contribution data."""
        return self.data["repositories"].get(full_name)

    def get_all_repositories(self) -> List[Dict]:
        """Get all tracked repositories."""
        return list(self.data["repositories"].values())

    def sort_by_latest_contribution(self) -> List[Dict]:
        """Sort repositories by latest personal contribution timestamp (newest first)."""
        repos = self.get_all_repositories()

        def get_timestamp(repo):
            ts = repo.get("latest_personal_commit_timestamp")
            if ts:
                return parse_github_timestamp(ts)
            return datetime.min.replace(tzinfo=timezone.utc)

        return sorted(repos, key=get_timestamp, reverse=True)

    def mark_reconciliation_complete(self):
        """Mark successful reconciliation timestamp."""
        self.data["last_successful_reconciliation"] = datetime.now(timezone.utc).isoformat()

    def bootstrap_from_github(self, github_client: GitHubClient):
        """Initial bootstrap: discover all repositories and their latest contributions.

        This performs a full scan of the user's repositories.
        """
        print(f"🔍 Bootstrapping contributions for {self.username}...")

        # Get all user repositories
        repos = github_client.get_user_repos(self.username)
        print(f"📦 Found {len(repos)} public repositories")

        # For each repository, get latest commit by user
        for repo in repos:
            full_name = repo["full_name"]
            owner, repo_name = full_name.split("/")

            print(f"🔎 Checking {full_name}...")

            latest_commit = github_client.get_latest_commit_by_author(
                owner, repo_name, self.username
            )

            if latest_commit or (owner == self.username and not repo.get("fork", False)):
                self.update_repository(repo, latest_commit)
            else:
                print(f"   No commits by {self.username}")

        self.mark_reconciliation_complete()
        print(f"✅ Bootstrap complete: {len(self.data['repositories'])} repositories tracked")

    def reconcile_with_github(self, github_client: GitHubClient):
        """Reconcile tracked repositories with current GitHub state.

        - Update existing repositories
        - Discover new repositories
        - Remove deleted or now-private repositories
        """
        print(f"🔄 Reconciling contributions for {self.username}...")

        current_repos = github_client.get_user_repos(self.username)
        current_full_names = {r["full_name"] for r in current_repos}

        # Update existing and discover new
        for repo in current_repos:
            full_name = repo["full_name"]
            owner, repo_name = full_name.split("/")

            latest_commit = github_client.get_latest_commit_by_author(
                owner, repo_name, self.username
            )

            if latest_commit or (owner == self.username and not repo.get("fork", False)):
                self.update_repository(repo, latest_commit)

        # Remove repositories that no longer exist or are now private
        tracked_repos = list(self.data["repositories"].keys())
        for full_name in tracked_repos:
            if full_name not in current_full_names:
                print(f"⚠️  Repository {full_name} no longer accessible, removing")
                self.remove_repository(full_name)

        self.mark_reconciliation_complete()
        print(f"✅ Reconciliation complete: {len(self.data['repositories'])} repositories tracked")

    def update_single_repository(self, github_client: GitHubClient, full_name: str):
        """Update a single repository's contribution data.

        Used for event-driven updates when a specific repository receives a push.
        """
        owner, repo_name = full_name.split("/")

        print(f"🔄 Updating {full_name}...")

        # Get repository info
        repo_info = github_client.get_repo_info(owner, repo_name)
        if not repo_info:
            print(f"❌ Repository {full_name} not found")
            return False

        # Verify it's public
        if repo_info.get("private", False):
            print(f"⚠️  Repository {full_name} is private, removing from public data")
            self.remove_repository(full_name)
            return False

        # Get latest commit by user
        latest_commit = github_client.get_latest_commit_by_author(
            owner, repo_name, self.username
        )

        if latest_commit or (owner == self.username and not repo_info.get("fork", False)):
            self.update_repository(repo_info, latest_commit)
            return True
        else:
            print(f"⚠️  No contributions by {self.username} in {full_name}")
            return False
