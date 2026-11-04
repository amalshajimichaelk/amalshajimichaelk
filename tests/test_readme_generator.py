"""Test suite for README generator."""

import sys
import os
from datetime import datetime, timezone

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from lib.readme_generator import generate_markdown_table, update_readme


def test_readme_table_generation():
    """Test Markdown table generation."""
    print("🧪 Test: README Table Generation")

    repos = [
        {
            "name": "test-repo-1",
            "full_name": "user/test-repo-1",
            "html_url": "https://github.com/user/test-repo-1",
            "latest_personal_commit_timestamp": "2026-11-04T06:00:00Z",
            "language": "Python"
        },
        {
            "name": "test-repo-2",
            "full_name": "user/test-repo-2",
            "html_url": "https://github.com/user/test-repo-2",
            "latest_personal_commit_timestamp": "2026-11-03T06:00:00Z",
            "language": "JavaScript"
        },
    ]

    table = generate_markdown_table(repos)

    # Check table structure
    assert "| Rank | Repository | Last Contribution | Language |" in table
    assert "|:---:|:---|:---:|:---:|" in table
    assert "🥇" in table, "Should have gold medal"
    assert "🥈" in table, "Should have silver medal"
    assert "test-repo-1" in table, "Should include first repo"
    assert "test-repo-2" in table, "Should include second repo"
    assert "🐍 Python" in table, "Should include Python with emoji"
    assert "🟨 JavaScript" in table, "Should include JavaScript with emoji"

    print("   ✅ Table generated correctly")
    print(f"   Table has {len(table.split(chr(10)))} lines")

    return True


def test_readme_marker_validation():
    """Test README marker validation."""
    print("\n🧪 Test: README Marker Validation")

    # Create test README
    test_readme = """# Test README

Some content

<!-- LATEST_REPO_START -->
Old content
<!-- LATEST_REPO_END -->

More content
"""

    with open("test_readme.md", "w", encoding="utf-8") as f:
        f.write(test_readme)

    # Update with new table
    new_table = "| Rank | Repository | Last Contribution | Language |\n|:---:|:---|:---:|:---:|"

    changed = update_readme("test_readme.md", new_table)

    # Read back
    with open("test_readme.md", "r", encoding="utf-8") as f:
        updated = f.read()

    assert "<!-- LATEST_REPO_START -->" in updated
    assert "<!-- LATEST_REPO_END -->" in updated
    assert new_table in updated
    assert "Old content" not in updated
    assert "Some content" in updated
    assert "More content" in updated

    print("   ✅ README markers work correctly")
    print("   ✅ Content between markers replaced")
    print("   ✅ Other sections preserved")

    # Cleanup
    os.remove("test_readme.md")

    return True


def test_empty_repository_list():
    """Test handling of empty repository list."""
    print("\n🧪 Test: Empty Repository Table")

    table = generate_markdown_table([])

    assert table == "No contributions found yet."

    print("   ✅ Empty list handled correctly")

    return True


def test_language_without_emoji():
    """Test languages without predefined emojis."""
    print("\n🧪 Test: Language Without Emoji")

    repos = [
        {
            "name": "test-repo",
            "full_name": "user/test-repo",
            "html_url": "https://github.com/user/test-repo",
            "latest_personal_commit_timestamp": "2026-11-04T06:00:00Z",
            "language": "Brainfuck"  # Obscure language without emoji
        },
    ]

    table = generate_markdown_table(repos)

    assert "Brainfuck" in table or "💻" in table

    print("   ✅ Unknown language handled correctly")

    return True


def test_null_language():
    """Test repositories with null language."""
    print("\n🧪 Test: Null Language")

    repos = [
        {
            "name": "test-repo",
            "full_name": "user/test-repo",
            "html_url": "https://github.com/user/test-repo",
            "latest_personal_commit_timestamp": "2026-11-04T06:00:00Z",
            "language": None
        },
    ]

    table = generate_markdown_table(repos)

    assert "Not specified" in table

    print("   ✅ Null language handled correctly")

    return True


def test_max_repos_limit():
    """Test limiting number of displayed repositories."""
    print("\n🧪 Test: Max Repos Limit")

    repos = [
        {
            "name": f"repo-{i}",
            "full_name": f"user/repo-{i}",
            "html_url": f"https://github.com/user/repo-{i}",
            "latest_personal_commit_timestamp": f"2026-11-{4-i:02d}T06:00:00Z",
            "language": "Python"
        }
        for i in range(10)
    ]

    # Limit to 3
    table = generate_markdown_table(repos, max_repos=3)

    lines = table.split("\n")
    # Header (2 lines) + 3 repos = 5 lines
    assert len([l for l in lines if l.strip()]) == 5

    print("   ✅ Repository limit works correctly")
    print("   Limited to 3 repos from 10 total")

    return True


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("🧪 README GENERATOR TEST SUITE")
    print("=" * 60)

    tests = [
        test_readme_table_generation,
        test_readme_marker_validation,
        test_empty_repository_list,
        test_language_without_emoji,
        test_null_language,
        test_max_repos_limit,
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
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
