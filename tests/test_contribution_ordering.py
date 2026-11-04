"""Test suite for contribution ordering and chronological sorting."""

import sys
import os
from datetime import datetime, timezone, timedelta

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from lib.contribution_tracker import ContributionTracker
from lib.github_api import parse_github_timestamp


def test_contribution_ordering():
    """Test that repositories are sorted by latest contribution timestamp."""
    print("🧪 Test: Contribution Ordering")

    # Create test data
    now = datetime.now(timezone.utc)

    repos = [
        {
            "name": "Repository A",
            "full_name": "user/repo-a",
            "html_url": "https://github.com/user/repo-a",
            "latest_commit_sha": "sha1",
            "latest_commit_url": "https://github.com/user/repo-a/commit/sha1",
            "latest_personal_commit_timestamp": (now - timedelta(days=3)).isoformat(),
            "author_timestamp": (now - timedelta(days=3)).isoformat(),
            "language": "Python",
            "visibility": "public",
            "last_verified_at": now.isoformat()
        },
        {
            "name": "Repository B",
            "full_name": "user/repo-b",
            "html_url": "https://github.com/user/repo-b",
            "latest_commit_sha": "sha2",
            "latest_commit_url": "https://github.com/user/repo-b/commit/sha2",
            "latest_personal_commit_timestamp": now.isoformat(),
            "author_timestamp": now.isoformat(),
            "language": "JavaScript",
            "visibility": "public",
            "last_verified_at": now.isoformat()
        },
        {
            "name": "Repository C",
            "full_name": "user/repo-c",
            "html_url": "https://github.com/user/repo-c",
            "latest_commit_sha": "sha3",
            "latest_commit_url": "https://github.com/user/repo-c/commit/sha3",
            "latest_personal_commit_timestamp": (now - timedelta(days=1)).isoformat(),
            "author_timestamp": (now - timedelta(days=1)).isoformat(),
            "language": "Java",
            "visibility": "public",
            "last_verified_at": now.isoformat()
        },
    ]

    # Create temporary tracker
    tracker = ContributionTracker("test_data.json", "testuser")
    tracker.data["repositories"] = {r["full_name"]: r for r in repos}

    # Sort by latest contribution
    sorted_repos = tracker.sort_by_latest_contribution()

    # Verify order: B (today) > C (1 day ago) > A (3 days ago)
    assert sorted_repos[0]["name"] == "Repository B", "Most recent should be first"
    assert sorted_repos[1]["name"] == "Repository C", "Second most recent should be second"
    assert sorted_repos[2]["name"] == "Repository A", "Oldest should be last"

    print("   ✅ Repositories correctly sorted by latest contribution")
    print(f"   Order: {sorted_repos[0]['name']} > {sorted_repos[1]['name']} > {sorted_repos[2]['name']}")

    # Cleanup
    if os.path.exists("test_data.json"):
        os.remove("test_data.json")

    return True


def test_other_contributor_commit():
    """Test that another contributor's commit doesn't affect ranking."""
    print("\n🧪 Test: Other Contributor's Commit")

    now = datetime.now(timezone.utc)

    # Repository A: My last commit 3 days ago
    # Repository B: My last commit 1 day ago
    # Another user commits to Repository A today (shouldn't affect my ranking)

    repos = [
        {
            "name": "Repository A",
            "full_name": "user/repo-a",
            "html_url": "https://github.com/user/repo-a",
            "latest_commit_sha": "sha1",
            "latest_commit_url": "https://github.com/user/repo-a/commit/sha1",
            "latest_personal_commit_timestamp": (now - timedelta(days=3)).isoformat(),
            "author_timestamp": (now - timedelta(days=3)).isoformat(),
            "language": "Python",
            "visibility": "public",
            "last_verified_at": now.isoformat()
        },
        {
            "name": "Repository B",
            "full_name": "user/repo-b",
            "html_url": "https://github.com/user/repo-b",
            "latest_commit_sha": "sha2",
            "latest_commit_url": "https://github.com/user/repo-b/commit/sha2",
            "latest_personal_commit_timestamp": (now - timedelta(days=1)).isoformat(),
            "author_timestamp": (now - timedelta(days=1)).isoformat(),
            "language": "JavaScript",
            "visibility": "public",
            "last_verified_at": now.isoformat()
        },
    ]

    tracker = ContributionTracker("test_data2.json", "testuser")
    tracker.data["repositories"] = {r["full_name"]: r for r in repos}

    sorted_repos = tracker.sort_by_latest_contribution()

    # Repository B should still be first (my most recent contribution)
    assert sorted_repos[0]["name"] == "Repository B", "My latest contribution should determine ranking"
    assert sorted_repos[1]["name"] == "Repository A", "Older contribution should be second"

    print("   ✅ Other contributor's commits correctly ignored")
    print(f"   Ranking based only on personal contributions: {sorted_repos[0]['name']} > {sorted_repos[1]['name']}")

    # Cleanup
    if os.path.exists("test_data2.json"):
        os.remove("test_data2.json")

    return True


def test_timestamp_parsing():
    """Test GitHub timestamp parsing."""
    print("\n🧪 Test: Timestamp Parsing")

    test_timestamp = "2026-11-04T06:30:00Z"
    parsed = parse_github_timestamp(test_timestamp)

    assert isinstance(parsed, datetime), "Should parse to datetime"
    assert parsed.year == 2026, "Year should match"
    assert parsed.month == 11, "Month should match"
    assert parsed.day == 4, "Day should match"

    print(f"   ✅ Timestamp parsed correctly: {test_timestamp} → {parsed}")

    return True


def test_empty_repository_list():
    """Test handling of empty repository list."""
    print("\n🧪 Test: Empty Repository List")

    tracker = ContributionTracker("test_data3.json", "testuser")
    sorted_repos = tracker.sort_by_latest_contribution()

    assert sorted_repos == [], "Empty list should return empty list"

    print("   ✅ Empty repository list handled correctly")

    # Cleanup
    if os.path.exists("test_data3.json"):
        os.remove("test_data3.json")

    return True


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("🧪 CONTRIBUTION TRACKER TEST SUITE")
    print("=" * 60)

    tests = [
        test_contribution_ordering,
        test_other_contributor_commit,
        test_timestamp_parsing,
        test_empty_repository_list,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"   ❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
