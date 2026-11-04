# GitHub Profile Auto-Update System

## Overview

This system automatically tracks and displays your **latest personal contributions** across all GitHub repositories in real-time. Unlike traditional systems that rank by total commit count, this implementation ranks repositories chronologically by your most recent contribution to each one.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Push Event                        │
│                (New commit to any repository)                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    GitHub App Webhook                        │
│              (Installed on your account)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│             Cloudflare Worker (Webhook Receiver)             │
│   • HMAC signature verification                              │
│   • Event validation and filtering                           │
│   • Duplicate delivery detection                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│          GitHub Actions Workflow Dispatch                    │
│              (Profile repository)                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Python Contribution Tracker                     │
│   • Fetch repository information via GitHub API              │
│   • Verify commit author identity                            │
│   • Update persistent contribution index                     │
│   • Sort repositories by latest personal commit              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 README Generator                             │
│   • Generate Markdown table                                  │
│   • Replace content between markers                          │
│   • Preserve all other sections                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Commit and Push to GitHub                       │
│           (Updated profile README visible)                   │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Event-Driven Updates
- **Primary mechanism**: GitHub App webhooks trigger updates immediately when you push to any repository
- **Fallback mechanism**: Scheduled reconciliation every 15 minutes catches missed events
- **Manual trigger**: Can be run manually from GitHub Actions

### 2. Chronological Ranking
- Repositories are ranked by your **latest personal commit timestamp**
- Other contributors' commits do not affect your ranking
- Newly created repositories automatically appear after their first commit

### 3. Author Verification
- Each commit is verified to be authored by your GitHub account
- Distinguishes between commit author, committer, and push sender
- Prevents other users' commits from incorrectly updating your profile

### 4. Persistent Contribution Index
- `data/latest-contributions.json` stores repository contribution data
- Enables efficient updates without full account scans
- Preserves data across workflow runs

### 5. Private Repository Protection
- Private repositories are never exposed in the public README
- Explicit filtering at multiple levels
- Webhook receiver and workflow both verify repository visibility

## Components

### 1. Python Scripts (`scripts/`)

#### `update_latest_repo.py` (Main Script)
Main entry point with multiple operation modes:

```bash
# Initial discovery of all repositories
python scripts/update_latest_repo.py --mode bootstrap

# Full reconciliation (scheduled fallback)
python scripts/update_latest_repo.py --mode reconcile

# Update single repository (event-driven)
python scripts/update_latest_repo.py --mode update --repository owner/repo

# Just regenerate README from existing data
python scripts/update_latest_repo.py --mode generate
```

#### `lib/github_api.py`
- Authenticated GitHub API client
- Rate limit handling with exponential backoff
- Repository and commit fetching
- Author verification

#### `lib/contribution_tracker.py`
- Persistent contribution data management
- Repository discovery and updates
- Chronological sorting by latest personal commit
- Reconciliation with GitHub state

#### `lib/readme_generator.py`
- Markdown table generation
- README updating with marker preservation
- Language emoji mapping
- Date formatting

### 2. Webhook Receiver (`webhook/`)

TypeScript Cloudflare Worker that:
- Receives GitHub webhook POST requests
- Validates HMAC SHA-256 signatures
- Filters relevant events (push)
- Prevents private repository leaks
- Deduplicates webhook deliveries
- Triggers GitHub Actions workflow

**Files:**
- `src/index.ts` - Main webhook handler
- `wrangler.toml` - Cloudflare Worker configuration
- `package.json` - Dependencies
- `tsconfig.json` - TypeScript configuration

### 3. GitHub Actions Workflow (`.github/workflows/`)

#### `latest-contributed-repo.yml`
Workflow that updates the contribution data and README:

**Triggers:**
- `workflow_dispatch` - Event-driven from webhook
- `schedule` - Every 15 minutes (fallback)
- Manual - From Actions tab

**Inputs:**
- `source_repository` - Repository that triggered update
- `delivery_id` - Webhook delivery ID for deduplication
- `mode` - Operation mode (update/reconcile/bootstrap)

**Concurrency Control:**
- Uses `contribution-updater` concurrency group
- Prevents overlapping runs from corrupting data
- Serializes concurrent events safely

### 4. Data Files

#### `data/latest-contributions.json`
Persistent contribution index with schema:

```json
{
  "schema_version": 1,
  "username": "amalshajimichaelk",
  "last_successful_reconciliation": "2026-11-04T06:15:00Z",
  "repositories": {
    "owner/repository": {
      "name": "repository",
      "full_name": "owner/repository",
      "html_url": "https://github.com/owner/repository",
      "latest_commit_sha": "abc123...",
      "latest_commit_url": "https://github.com/owner/repository/commit/abc123",
      "latest_personal_commit_timestamp": "2026-11-04T05:30:00Z",
      "author_timestamp": "2026-11-04T05:25:00Z",
      "language": "Python",
      "visibility": "public",
      "last_verified_at": "2026-11-04T06:15:00Z"
    }
  }
}
```

## Setup Instructions

### Prerequisites

1. GitHub account: `amalshajimichaelk`
2. Profile repository: `amalshajimichaelk/amalshajimichaelk`
3. Cloudflare account (for webhook deployment)
4. GitHub CLI (`gh`) installed (optional, for testing)

### Step 1: Update README Markers

Your README already has the correct markers and section heading:

```markdown
### 🚀 Latest Contributed Repo
<!-- LATEST_REPO_START -->
[Content will be auto-generated here]
<!-- LATEST_REPO_END -->
```

### Step 2: Initial Bootstrap (Local)

Run the initial bootstrap to populate contribution data:

```bash
# Set your GitHub token
export GITHUB_TOKEN="ghp_your_token_here"

# Run bootstrap
cd /path/to/profile-repo
python scripts/update_latest_repo.py --mode bootstrap
```

This will:
- Discover all your public repositories
- Find your latest commit in each
- Populate `data/latest-contributions.json`
- Generate initial README table

### Step 3: Commit Initial Changes

```bash
git add data/latest-contributions.json README.md
git commit -m "chore: initialize latest contributed repo system"
git push
```

### Step 4: Create GitHub App

1. Go to **Settings** → **Developer settings** → **GitHub Apps** → **New GitHub App**

2. **GitHub App name**: `profile-updater` (or your choice)

3. **Homepage URL**: `https://github.com/amalshajimichaelk/amalshajimichaelk`

4. **Webhook URL**: `https://your-worker.workers.dev` (will be set after deploying worker)

5. **Webhook secret**: Generate a random secret (save it!)
   ```bash
   openssl rand -hex 32
   ```

6. **Repository permissions**:
   - Contents: Read-only (to read repository metadata and commits)
   - Metadata: Read-only (automatically added)
   - Actions: Read & Write (to dispatch workflows in profile repo)

7. **Subscribe to events**:
   - [x] Push

8. **Where can this GitHub App be installed?**
   - Only on this account

9. Click **Create GitHub App**

10. **Generate private key**:
    - Scroll to "Private keys" section
    - Click "Generate a private key"
    - Download and save the `.pem` file securely

11. **Install the App**:
    - Click "Install App" in the left sidebar
    - Select your account
    - Choose **All repositories** (recommended) or select specific repositories
    - Click Install

12. **Note the App ID and Installation ID**:
    - App ID is shown at the top of the app settings page
    - Installation ID can be found in the URL after installing: `https://github.com/settings/installations/<installation-id>`

### Step 5: Deploy Cloudflare Worker

1. **Install Wrangler** (Cloudflare CLI):
   ```bash
   npm install -g wrangler
   ```

2. **Login to Cloudflare**:
   ```bash
   wrangler login
   ```

3. **Configure secrets**:
   ```bash
   cd webhook
   
   # Set webhook secret (same as GitHub App webhook secret)
   wrangler secret put GITHUB_WEBHOOK_SECRET
   # Paste the secret you generated earlier
   
   # Set GitHub App ID
   wrangler secret put GITHUB_APP_ID
   # Paste your app ID
   
   # Set GitHub App private key
   wrangler secret put GITHUB_APP_PRIVATE_KEY
   # Paste the entire contents of the .pem file (including BEGIN/END lines)
   ```

4. **Deploy**:
   ```bash
   npm install
   wrangler deploy
   ```

5. **Note the worker URL**: `https://github-profile-webhook.<your-subdomain>.workers.dev`

6. **Update GitHub App webhook URL**:
   - Go back to GitHub App settings
   - Update Webhook URL to your worker URL
   - Save changes

### Step 6: Configure GitHub Actions Secrets

The workflow uses `secrets.GITHUB_TOKEN` which is automatically provided by GitHub Actions. No additional secrets needed unless you want to use a custom token.

### Step 7: Test the System

#### Test 1: Manual Workflow Run
```bash
# Go to Actions tab in your repository
# Select "Latest Contributed Repo Updater"
# Click "Run workflow"
# Select "reconcile" mode
# Click "Run workflow"
```

#### Test 2: Push to a Repository
```bash
# Make a commit to any of your repositories
git commit -m "test: trigger profile update" --allow-empty
git push

# Check GitHub Actions in your profile repo
# Should see a workflow run triggered within seconds
```

#### Test 3: Create New Repository
```bash
# Create a new repository on GitHub
# Make your first commit and push
# The profile should update automatically
```

### Step 8: Monitor and Verify

1. **Check webhook deliveries**:
   - GitHub App settings → Advanced → Recent Deliveries
   - Verify responses are 200 OK

2. **Check workflow runs**:
   - Actions tab in profile repository
   - Verify successful runs

3. **Check contribution data**:
   - View `data/latest-contributions.json` in your repository
   - Should contain all your repositories with timestamps

4. **Check README**:
   - View your profile: `https://github.com/amalshajimichaelk`
   - Verify "Latest Contributed Repo" section displays correctly

## Configuration Options

### Environment Variables

Set in `.github/workflows/latest-contributed-repo.yml`:

```yaml
env:
  MAX_REPOS: 0  # 0 = show all, or limit to N repositories
```

### Scheduled Reconciliation Interval

Default: Every 15 minutes

To change, edit `.github/workflows/latest-contributed-repo.yml`:

```yaml
schedule:
  - cron: '*/30 * * * *'  # Every 30 minutes
```

## Troubleshooting

### Webhook not triggering workflow

**Check:**
1. Webhook deliveries in GitHub App settings show 200 OK
2. Worker logs in Cloudflare dashboard
3. GitHub Actions workflow runs

**Fix:**
- Verify webhook secret matches
- Check worker deployment status
- Verify GitHub App has Actions permission

### Repository not updating position

**Check:**
1. Commit is authored by your account (not another user)
2. Repository is public
3. `data/latest-contributions.json` contains the repository

**Fix:**
- Run manual reconciliation
- Check workflow logs for errors
- Verify GitHub token has proper permissions

### README not updating

**Check:**
1. Markers are present: `<!-- LATEST_REPO_START -->` and `<!-- LATEST_REPO_END -->`
2. Workflow has write permissions
3. Commit shows in workflow run

**Fix:**
- Verify markers exist in README.md
- Check workflow permissions in `.github/workflows/`
- Look for git conflicts

### Rate limiting

GitHub API rate limits:
- Authenticated: 5,000 requests/hour
- Search API: 30 requests/minute

**Fix:**
- System is designed to minimize API calls
- Bootstrap uses pagination efficiently
- Event-driven updates only query affected repository
- Scheduled reconciliation is infrequent (15 min)

### Private repository exposure

**Protection mechanisms:**
1. Webhook receiver checks `repository.private` flag
2. Python script filters private repositories
3. Only public repository data written to README

**Verify:**
- Check `data/latest-contributions.json` contains no private repos
- Review README content

## Maintenance

### Update contribution data manually

```bash
# Full reconciliation
python scripts/update_latest_repo.py --mode reconcile

# Update specific repository
python scripts/update_latest_repo.py --mode update --repository owner/repo
```

### Clear and rebuild data

```bash
# Delete existing data
rm data/latest-contributions.json

# Run bootstrap
python scripts/update_latest_repo.py --mode bootstrap
```

### Check system status

```bash
# View last reconciliation time
python -c "import json; print(json.load(open('data/latest-contributions.json'))['last_successful_reconciliation'])"

# Count tracked repositories
python -c "import json; print(len(json.load(open('data/latest-contributions.json'))['repositories']))"
```

## Testing

### Run test suite

```bash
# Contribution ordering tests
python tests/test_contribution_ordering.py

# README generator tests
python tests/test_readme_generator.py
```

### Test coverage

- ✅ Chronological sorting
- ✅ Other contributor commits ignored
- ✅ Empty repository list handling
- ✅ Timestamp parsing
- ✅ README marker validation
- ✅ Language emoji mapping
- ✅ Max repos limit
- ✅ Null/unknown language handling

## Limitations and Considerations

### Known Limitations

1. **External repositories**: GitHub App only receives events for repositories where it's installed. For repositories owned by others, rely on scheduled reconciliation.

2. **Webhook delivery**: GitHub webhooks are not instantaneous (typically <1 second delay) and may occasionally be delayed or redelivered.

3. **Search API limitations**: GitHub's commit search API may have indexing delays for very recent commits.

4. **Rate limits**: Very large numbers of repositories (100+) may approach rate limits during bootstrap.

### Design Decisions

**Why committer timestamp instead of author timestamp?**
- Committer timestamp represents when the commit was finalized
- More accurate for "latest activity" chronology
- Author timestamp preserved for audit purposes

**Why persistent index instead of API-only?**
- Reduces API calls and rate limit pressure
- Faster workflow execution
- Resilient to temporary API failures
- Enables efficient incremental updates

**Why 15-minute reconciliation?**
- Balances freshness with API usage
- Catches missed webhooks
- Discovers external repository contributions
- Reasonable GitHub Actions usage

## Security Considerations

### Secrets Management

- Never commit private keys or tokens to the repository
- Use GitHub secrets and Cloudflare secrets for sensitive data
- Webhook secret validates request authenticity
- HMAC signature uses constant-time comparison

### Private Repository Protection

- Multiple layers of filtering
- Explicit visibility checks
- Webhook receiver validates privacy flag
- Python script validates repository metadata

### Webhook Validation

- HMAC SHA-256 signature verification
- Duplicate delivery detection
- Event type filtering
- Request size limits (implicit in Cloudflare)

## Future Enhancements

Potential improvements:

1. **Multiple user support**: Track contributions for team profiles
2. **Contribution heatmap**: Visual contribution history
3. **Language statistics**: Breakdown by programming language
4. **Contribution types**: PRs, issues, code reviews
5. **GraphQL API**: More efficient data fetching
6. **Caching layer**: Redis/KV for webhook deduplication
7. **Dashboard**: Web UI for system monitoring

## Support and Issues

If you encounter issues:

1. Check the troubleshooting section above
2. Review workflow logs in GitHub Actions
3. Check webhook deliveries in GitHub App settings
4. Verify Cloudflare Worker logs

## Credits

- GitHub Profile Trophy: [ryo-ma/github-profile-trophy](https://github.com/ryo-ma/github-profile-trophy)
- GitHub Streak Stats: [DenverCoder1/github-readme-streak-stats](https://github.com/DenverCoder1/github-readme-streak-stats)
- Profile inspiration: [GPRM](https://gprm.itsvg.in)

## License

This automation system is provided as-is for personal use.
