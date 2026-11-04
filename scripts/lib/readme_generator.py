"""README generator for Latest Contributed Repo section."""

import re
from typing import List, Dict
from .github_api import format_contribution_date


# Language to emoji mapping
LANG_EMOJI = {
    "Python": "🐍",
    "JavaScript": "🟨",
    "TypeScript": "🔷",
    "Java": "☕",
    "C": "🔵",
    "C++": "🔹",
    "HTML": "🟠",
    "CSS": "🎨",
    "Shell": "🐚",
    "Go": "🐹",
    "Rust": "🦀",
    "Ruby": "💎",
    "PHP": "🐘",
    "Swift": "🦅",
    "Kotlin": "🟣",
    "Dart": "🎯",
    "Markdown": "📝",
    "Jupyter Notebook": "🪐",
}

# Rank emojis
RANK_EMOJIS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


def generate_markdown_table(repositories: List[Dict], max_repos: int = 0) -> str:
    """Generate Markdown table for Latest Contributed Repo section.

    Args:
        repositories: List of repository dicts sorted by latest contribution (newest first)
        max_repos: Maximum number of repos to display (0 = unlimited)

    Returns:
        Markdown table string
    """
    if not repositories:
        return "No contributions found yet."

    # Limit repositories if specified
    repos_to_display = repositories[:max_repos] if max_repos > 0 else repositories

    rows = []
    for i, repo in enumerate(repos_to_display):
        # Rank emoji
        rank = RANK_EMOJIS[i] if i < len(RANK_EMOJIS) else f"{i + 1}️⃣"

        # Repository link
        repo_name = repo["name"]
        repo_url = repo["html_url"]
        repo_link = f"[{repo_name}]({repo_url})"

        # Last contribution date
        timestamp = repo.get("latest_personal_commit_timestamp")
        if timestamp:
            date_display = format_contribution_date(timestamp)
        else:
            date_display = "Unknown"

        # Language with emoji
        language = repo.get("language")
        if language:
            emoji = LANG_EMOJI.get(language, "💻")
            lang_display = f"{emoji} {language}"
        else:
            lang_display = "Not specified"

        rows.append(f"| {rank} | {repo_link} | {date_display} | {lang_display} |")

    # Build table
    table = "\n".join([
        "| Rank | Repository | Last Contribution | Language |",
        "|:---:|:---|:---:|:---:|",
        *rows,
    ])

    return table


def update_readme(
    readme_path: str,
    markdown_table: str,
    start_marker: str = "<!-- LATEST_REPO_START -->",
    end_marker: str = "<!-- LATEST_REPO_END -->"
) -> bool:
    """Update README with new Latest Contributed Repo table.

    Args:
        readme_path: Path to README.md
        markdown_table: Generated markdown table
        start_marker: Start marker comment
        end_marker: End marker comment

    Returns:
        True if README was modified, False if no changes needed
    """
    # Read current README
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Generate new block
    new_block = (
        f"{start_marker}\n"
        f"<div align=\"center\">\n\n"
        f"{markdown_table}\n\n"
        f"</div>\n"
        f"{end_marker}"
    )

    # Check if markers exist
    if start_marker not in content or end_marker not in content:
        raise ValueError(
            f"Markers not found in README: {start_marker} and {end_marker}\n"
            f"Please add these markers to your README.md where the table should appear."
        )

    # Validate marker ordering
    start_pos = content.index(start_marker)
    end_pos = content.index(end_marker)

    if start_pos >= end_pos:
        raise ValueError(
            f"Invalid marker ordering: {start_marker} must come before {end_marker}"
        )

    # Replace content between markers
    pattern = re.escape(start_marker) + r".*?" + re.escape(end_marker)
    new_content = re.sub(pattern, new_block, content, flags=re.DOTALL)

    # Check if content actually changed
    if new_content == content:
        print("ℹ️  README content unchanged, skipping write")
        return False

    # Write updated README
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ README updated: {readme_path}")
    return True


def migrate_old_markers(readme_path: str):
    """Migrate old TOP_REPOS markers to new LATEST_REPO markers.

    This is a one-time migration function.
    """
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    old_start = "<!-- TOP_REPOS_START -->"
    old_end = "<!-- TOP_REPOS_END -->"
    new_start = "<!-- LATEST_REPO_START -->"
    new_end = "<!-- LATEST_REPO_END -->"

    # Check if old markers exist
    if old_start not in content or old_end not in content:
        print("ℹ️  Old markers not found, no migration needed")
        return

    # Check if new markers already exist
    if new_start in content or new_end in content:
        print("⚠️  New markers already exist, manual review needed")
        return

    # Replace markers
    content = content.replace(old_start, new_start)
    content = content.replace(old_end, new_end)

    # Update heading if it exists near the markers
    # Look for the old heading pattern and replace it
    old_heading_pattern = r"###\s*🔝\s*Top Contributed Repo"
    new_heading = "### 🚀 Latest Contributed Repo"
    content = re.sub(old_heading_pattern, new_heading, content)

    # Write updated README
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Migrated markers and heading in {readme_path}")
