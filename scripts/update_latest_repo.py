"""Main script to update Latest Contributed Repo section.

This script can be run in multiple modes:
1. Bootstrap: Initial discovery of all repositories
2. Reconcile: Full reconciliation with GitHub
3. Update: Update specific repository (event-driven)
4. Generate: Just regenerate README from existing data
"""

import sys
import os
import argparse
from datetime import datetime, timezone

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from lib.github_api import GitHubClient, GitHubAPIError
from lib.contribution_tracker import ContributionTracker
from lib.readme_generator import generate_markdown_table, update_readme, migrate_old_markers


USERNAME = "amalshajimichaelk"
DATA_FILE = "data/latest-contributions.json"
README_PATH = "README.md"
MAX_REPOS = int(os.environ.get("MAX_REPOS", "5"))  # Default 5 repos (0 = unlimited)


def main():
    parser = argparse.ArgumentParser(description="Update Latest Contributed Repo section")
    parser.add_argument(
        "--mode",
        choices=["bootstrap", "reconcile", "update", "generate", "migrate"],
        default="reconcile",
        help="Operation mode"
    )
    parser.add_argument(
        "--repository",
        help="Repository to update (format: owner/repo) - used with --mode=update"
    )
    parser.add_argument(
        "--skip-readme",
        action="store_true",
        help="Skip README update (only update contribution data)"
    )

    args = parser.parse_args()

    print(f"🚀 Latest Contributed Repo Updater")
    print(f"📅 {datetime.now(timezone.utc).isoformat()}")
    print(f"👤 User: {USERNAME}")
    print(f"📝 Mode: {args.mode}")
    print()

    # Special case: migrate markers only
    if args.mode == "migrate":
        print("🔄 Migrating old markers to new format...")
        migrate_old_markers(README_PATH)
        return

    try:
        # Initialize GitHub client
        github_client = GitHubClient()
        print("✅ GitHub client initialized")

        # Initialize contribution tracker
        tracker = ContributionTracker(DATA_FILE, USERNAME)
        print(f"✅ Contribution tracker initialized")
        print()

        # Execute based on mode
        if args.mode == "bootstrap":
            print("🔍 Running initial bootstrap...")
            tracker.bootstrap_from_github(github_client)

        elif args.mode == "reconcile":
            print("🔄 Running full reconciliation...")
            tracker.reconcile_with_github(github_client)

        elif args.mode == "update":
            if not args.repository:
                print("❌ --repository required for update mode")
                sys.exit(1)

            print(f"🔄 Updating single repository: {args.repository}")
            success = tracker.update_single_repository(github_client, args.repository)
            if not success:
                print(f"⚠️  Failed to update {args.repository}")

        elif args.mode == "generate":
            print("📝 Generating README from existing data...")
            # No GitHub API calls needed

        # Save contribution data
        tracker.save()
        print()

        # Generate and update README unless skipped
        if not args.skip_readme:
            print("📝 Generating README table...")
            sorted_repos = tracker.sort_by_latest_contribution()

            if sorted_repos:
                print(f"📊 Found {len(sorted_repos)} repositories with contributions")
                print("\n🏆 Top 10 repositories by latest contribution:")
                for i, repo in enumerate(sorted_repos[:10], 1):
                    name = repo["name"]
                    timestamp = repo.get("latest_personal_commit_timestamp", "Unknown")
                    language = repo.get("language", "N/A")
                    print(f"   {i:2d}. {name:30s} | {timestamp} | {language}")
                print()

            markdown_table = generate_markdown_table(sorted_repos, MAX_REPOS)
            changed = update_readme(README_PATH, markdown_table)

            if changed:
                print("✅ README successfully updated")
            else:
                print("ℹ️  README unchanged (no new data)")
        else:
            print("⏭️  Skipping README update")

        print()
        print("✅ Update complete!")

    except GitHubAPIError as e:
        print(f"❌ GitHub API error: {e}")
        sys.exit(1)

    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        sys.exit(1)

    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
