import urllib.request
import urllib.error
import json
import re
import os
import sys

USERNAME = "amalshajimichaelk"
README_PATH = "README.md"
TOP_N = 5

LANG_EMOJI = {
    "Python": "🐍", "JavaScript": "🟨", "TypeScript": "🔷",
    "Java": "☕", "C": "🔵", "C++": "🔵", "HTML": "🌐",
    "CSS": "🎨", "Shell": "🐚", "Markdown": "📝",
}

def gh_get(url):
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "readme-updater",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def get_repos():
    repos = []
    page = 1
    while True:
        url = (f"https://api.github.com/users/{USERNAME}/repos"
               f"?per_page=100&page={page}&type=owner")
        batch = gh_get(url)
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos

def get_commit_count(repo_name):
    """Get total commit count for a repo by the owner."""
    try:
        url = (f"https://api.github.com/repos/{USERNAME}/{repo_name}"
               f"/commits?author={USERNAME}&per_page=1")
        req_url = url
        token = os.environ.get("GITHUB_TOKEN", "")
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "readme-updater",
        }
        if token:
            headers["Authorization"] = f"token {token}"
        req = urllib.request.Request(req_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            link = r.headers.get("Link", "")
            # GitHub paginates — last page number = total pages = total commits (1/page)
            match = re.search(r'page=(\d+)>;\s*rel="last"', link)
            if match:
                return int(match.group(1))
            # If no Link header, count items in response
            data = json.loads(r.read().decode())
            return len(data)
    except Exception:
        return 0

def build_table(top_repos):
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    rows = []
    for i, (name, commits, lang, url) in enumerate(top_repos):
        emoji = LANG_EMOJI.get(lang, "💻") if lang else "💻"
        lang_display = f"{emoji} {lang}" if lang else "💻 Other"
        rows.append(
            f"| {medals[i]} | [{name}]({url}) | {commits} | {lang_display} |"
        )

    table = "\n".join([
        "| Rank | Repository | Commits | Language |",
        "|:----:|-----------|:-------:|:--------:|",
        *rows,
    ])
    return table

def update_readme(table):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace everything between the markers
    start_marker = "<!-- TOP_REPOS_START -->"
    end_marker = "<!-- TOP_REPOS_END -->"

    new_block = (
        f"{start_marker}\n"
        f"<div align=\"center\">\n\n"
        f"{table}\n\n"
        f"</div>\n"
        f"{end_marker}"
    )

    if start_marker in content and end_marker in content:
        # Update existing block
        pattern = re.escape(start_marker) + r".*?" + re.escape(end_marker)
        new_content = re.sub(pattern, new_block, content, flags=re.DOTALL)
    else:
        # Markers not found — append at end
        print("⚠️  Markers not found in README. Appending at end.")
        new_content = content.rstrip() + "\n\n" + new_block + "\n"

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("✅ README updated.")

def main():
    print("📦 Fetching repos...")
    repos = get_repos()
    print(f"   Found {len(repos)} repos.")

    # Filter out forks
    own_repos = [r for r in repos if not r.get("fork", False)]
    print(f"   {len(own_repos)} are your own (non-fork) repos.")

    print("🔢 Counting commits per repo...")
    results = []
    for r in own_repos:
        name = r["name"]
        lang = r.get("language")
        url  = r["html_url"]
        count = get_commit_count(name)
        print(f"   {name}: {count} commits")
        if count > 0:
            results.append((name, count, lang, url))

    if not results:
        print("❌ No commits found. Exiting.")
        sys.exit(1)

    results.sort(key=lambda x: -x[1])
    top = results[:TOP_N]

    print("\n🏆 Top repos:")
    for i, (name, commits, lang, _) in enumerate(top, 1):
        print(f"   {i}. {name} — {commits} commits ({lang})")

    table = build_table(top)
    update_readme(table)

if __name__ == "__main__":
    main()
