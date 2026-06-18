# Jina Reader KB Sync - Dify Plugin

A Dify Plugin that crawls websites via Jina Reader API and syncs content to your Dify Knowledge Base.

> ⚠️ **Disclaimer**: This is an independent project with no affiliation to Jina AI or Dify AI.

## Features

- **Native Dify Integration** - Install directly in Dify as a Tool Plugin
- **Scheduled Sync** - Use with Dify's Schedule Trigger (v1.10.0+) for automated updates
- **Clean Markdown Output** - Optimized for RAG/LLM ingestion
- **Smart Content Filtering** - CSS selectors for element removal, regex URL filtering
- **Resume Crawling** - Start from any URL index for large sitemaps or interrupted crawls
- **Anti-detection Crawling** - Randomized delays between requests
- **Robust Error Handling** - Retry logic with exponential backoff
- **Duplicate Detection** - Skip duplicate URLs in sync session
- **Incremental Sync** - One-click toggle for 90% faster repeat syncs (auto-managed manifest)
- **Lastmod Optimization** - Use sitemap timestamps to skip unchanged content
- **Dry Run Mode** - Preview changes before making them
- **Stale Document Cleanup** - Remove KB documents for deleted URLs (with safety limits)
- **EU Compliance Mode** - Option to use Jina's European servers
- **Multi-language Support** - English and French status messages

## Project Structure

```
jina-reader-kb-sync/
├── manifest.yaml              # Plugin manifest
├── main.py                    # Plugin entrypoint
├── requirements.txt           # Python dependencies
├── icon.svg                   # Plugin icon
├── _assets/
│   └── icon.svg
├── provider/
│   ├── jina_reader_kb_sync.yaml   # Provider configuration
│   └── jina_reader_kb_sync.py     # Provider implementation
└── tools/
    ├── sync_sitemap.yaml          # Tool parameter definitions
    └── sync_sitemap/              # Modular package
        ├── __init__.py            # Package exports
        ├── tool.py                # Main orchestrator
        ├── params.py              # Parameter extraction
        ├── filters.py             # URL filtering pipeline
        ├── cleanup.py             # Stale document cleanup
        ├── sync_processor.py      # URL processing logic
        ├── reporting.py           # Progress and summary output
        ├── jina_client.py         # Jina Reader API client
        ├── dify_client.py         # Dify Knowledge Base API client
        ├── sitemap_parser.py      # Sitemap XML parsing
        ├── manifest.py            # Incremental sync manifest
        ├── content.py             # Document content building
        ├── url_processing.py      # URL normalization and hashing
        └── messages.py            # i18n message handling
```

## Installation

### Prerequisites
- Dify v1.10.0+ (for Schedule Trigger support)
- Dify Dataset API Key
- Optional: Jina Reader API Key (for higher rate limits)

### Package & Install

1. **Clone and package the plugin:**
```bash
git clone https://github.com/Asterovim/jina-reader-crawler.git
cd jina-reader-crawler

# Ensure you have Dify CLI installed
dify plugin package .

# This creates jina_reader_kb_sync.difypkg in the current directory
```

2. **Install in Dify:**
   - Go to Dify → Plugins → Install Plugin
   - Upload `jina_reader_kb_sync.difypkg`
   - Configure credentials (Dify API Key, optional Jina API Key)

## Configuration

When installing, provide these credentials:

| Credential | Required | Description |
|------------|----------|-------------|
| `dify_api_key` | Yes | Your Dify Dataset API key |
| `jina_api_key` | No | Jina Reader API key (increases rate limit) |
| `dify_base_url` | No | Dify API URL (default: https://api.dify.ai) |

### Sync Sitemap Tool

Crawl all URLs from a sitemap and sync to your Knowledge Base. Supports resume from index, retry logic, duplicate detection, incremental sync, and cleanup of stale documents.

**Parameters:**
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `sitemap_url` | No | - | URL of sitemap.xml or single page URL. Required if `manual_urls` is not provided. |
| `manual_urls` | No | - | Newline- or comma-separated list of URLs to crawl. Alternative or complement to `sitemap_url` (merged & deduped). Lines starting with `#` are ignored. Non-http(s) URLs are dropped. |
| `dataset_id` | Yes | - | Knowledge Base ID |
| `max_urls` | No | (all) | Max URLs to process (leave empty to process all) |
| `start_from_index` | No | 1 | 1-based index to start from (for resuming interrupted crawls) |
| `url_filter` | No | - | Regex pattern to include matching URLs only |
| `exclude_patterns` | No | - | Newline-separated patterns to exclude (e.g., `/admin/`, `.pdf`) |
| `exclude_urls` | No | - | Specific URLs to exclude (one per line) |
| `skip_existing` | No | false | Skip documents that already exist in KB |
| `skip_duplicates` | No | true | Skip URLs with duplicate titles in this sync |
| `use_lastmod_optimization` | No | false | Skip unchanged URLs using sitemap lastmod timestamps |
| `probe_head_for_manual_urls` | No | true | Send HEAD to each manual URL to capture Last-Modified/ETag (enables incremental skipping of unchanged manual URLs, same mechanism as sitemap lastmod) |
| `enable_incremental_sync` | No | false | ⚡⚡ Enable automatic incremental sync (90% faster for repeat syncs) |
| `force_full_sync` | No | false | Force full sync, ignoring manifest |
| `cleanup_removed` | No | false | Delete KB documents for URLs no longer in sitemap |
| `max_cleanup_count` | No | 20 | Max documents to delete during cleanup |
| `dry_run` | No | false | Preview mode: show what would change without making changes |
| `eu_compliance` | No | false | Use EU servers (GDPR compliant) |
| `css_selector` | No | - | CSS selector for elements to remove |
| `no_cache` | No | false | Bypass cache and fetch fresh content |
| `wait_for_selector` | No | - | CSS selector to wait for (for dynamic content) |
| `return_format` | No | (default) | Output format: markdown, html, text, screenshot, pageshot |
| `streaming_mode` | No | disabled | Enable for more complete dynamic content extraction |
| `min_delay` | No | 3 | Minimum delay between requests (seconds) |
| `max_delay` | No | 6 | Maximum delay between requests (seconds) |
| `chunk_size` | No | 3 | Dify updates per batch before cooldown |
| `chunk_cooldown` | No | 30 | Seconds to wait between batches |
| `retry_count` | No | 2 | Number of retry attempts with exponential backoff |
| `request_timeout` | No | 60 | Timeout for Jina Reader requests (seconds) |
| `display_language` | No | en | Language for status messages (en, fr) |
| `jina_api_key` | No | - | Override provider-level Jina API key |

## Rate Limits (Jina Reader API)

| API Tier | Rate Limit | Notes |
|----------|------------|-------|
| Free | 20 RPM | No API key required |
| Paid | 500 RPM | API key required |
| Premium | 5000 RPM | Premium API key |

## Setting Up Scheduled Sync (Dify v1.10.0+)

Dify v1.10.0 introduced **Schedule Triggers** that allow workflows to run automatically on a schedule. Here's how to set up automated Knowledge Base synchronization:

### Step 1: Create a New Workflow

1. Go to **Studio** → **Create App** → **Workflow**
2. Name it "KB Sync - [Your Site Name]"

### Step 2: Add Schedule Trigger

1. In the workflow canvas, click on the **Start** node
2. Change it to **Schedule Trigger**
3. Configure the schedule:
   - **Daily at 2 AM**: `0 2 * * *`
   - **Weekly on Sunday**: `0 0 * * 0`
   - **Every 6 hours**: `0 */6 * * *`
   - **First of month**: `0 0 1 * *`

### Step 3: Add the Sync Tool

1. Add a new node after the trigger
2. Select **Tools** → **Jina Reader KB Sync** → **Sync Sitemap**
3. Configure the parameters:
   ```yaml
   sitemap_url: "https://your-site.com/sitemap.xml"
   dataset_id: "your-kb-id-here"
   max_urls: 100
   skip_existing: false
   skip_duplicates: true
   min_delay: 3
   max_delay: 6
   retry_count: 2
   ```

### Step 4: Add Error Handling (Optional)

1. Add a **Conditional** node after sync
2. Check if `statistics.failed > 0`
3. If true, add notification (email, Slack, etc.)

### Step 5: Publish & Enable

1. Click **Publish** to save the workflow
2. The workflow will now run automatically on schedule

### Example Workflow Configurations

#### Daily Blog Sync with Duplicate Detection
```
Schedule Trigger (0 2 * * *)
    ↓
Sync Sitemap Tool
    sitemap_url: "https://blog.example.com/sitemap.xml"
    dataset_id: "kb-123456"
    url_filter: "/blog/"
    max_urls: 50
    skip_duplicates: true
    min_delay: 3
    max_delay: 6
    ↓
End
```

#### Resume Interrupted Crawl
```
# If a previous crawl stopped at index 150:
Sync Sitemap Tool
    sitemap_url: "https://docs.example.com/sitemap.xml"
    dataset_id: "kb-docs-789"
    start_from_index: 151  # Resume from where we left off
    max_urls: 100
    ↓
End
```

#### Weekly Documentation Update with Incremental Sync
```
Schedule Trigger (0 0 * * 0)
    ↓
Sync Sitemap Tool
    sitemap_url: "https://docs.example.com/sitemap.xml"
    dataset_id: "kb-docs-789"
    enable_incremental_sync: true  # ⚡⚡ 90% faster for repeat syncs
    use_lastmod_optimization: true  # Skip unchanged pages
    retry_count: 3  # More retries for reliability
    ↓
Conditional (failed > 0?)
    ↓ Yes
Send Slack Notification
    ↓ No
End
```

### Alternative: External Scheduler (Pre-v1.10.0 or Complex Needs)

For Dify versions before v1.10.0 or if you need more complex scheduling logic, you can use external schedulers:

#### GitHub Actions Example
```yaml
name: Sync KB Daily
on:
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Dify Workflow
        run: |
          curl -X POST "${{ secrets.DIFY_WORKFLOW_URL }}" \
            -H "Authorization: Bearer ${{ secrets.DIFY_API_KEY }}" \
            -H "Content-Type: application/json" \
            -d '{"inputs": {}}'
```

#### Cron Job Example
```bash
# Add to crontab -e
0 2 * * * curl -X POST "https://api.dify.ai/v1/workflows/run" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"inputs": {}}'
```

---

## ⚠️ Timeout Limitations & Configuration (Important!)

### Problem Description

When syncing large sitemaps (100+ URLs), the sync_sitemap tool may timeout before completion. This is **not a plugin bug** but a **Dify platform limitation** related to how long-running operations are handled.

**Symptoms:**
- Workflow stops mid-execution without error message
- Progress messages stop appearing in the UI
- Browser tab/window switch may trigger timeout
- Sync completes partially (e.g., 50 of 200 URLs processed)

### Root Cause

Dify uses Server-Sent Events (SSE) for streaming plugin output to the browser. Several timeout configurations control how long operations can run:

| Variable | Default | Unit | Purpose |
|----------|---------|------|---------|
| `PLUGIN_MAX_EXECUTION_TIMEOUT` | **600** | seconds | ⚠️ **Maximum plugin execution timeout** (enforced by Plugin Daemon) |
| `TEXT_GENERATION_TIMEOUT_MS` | 60000 | milliseconds | Timeout for text generation and workflow node execution |
| `GUNICORN_TIMEOUT` | 360 | seconds | HTTP request handling timeout |
| `WORKFLOW_MAX_EXECUTION_TIME` | 1200 | seconds | Maximum total workflow execution time |
| `APP_MAX_EXECUTION_TIME` | 1200 | seconds | Maximum app execution time |
| `FORCE_VERIFYING_SIGNATURE` | true | boolean | Verify plugin signatures (set to `false` for development) |
| `SERVER_WORKER_AMOUNT` | 1 | count | Number of Gunicorn server workers |
| `SERVER_WORKER_CONNECTIONS` | 50 | count | Number of connections per worker |
| `CELERY_WORKER_AMOUNT` | 4 | count | Number of Celery workers for async tasks |
| `CELERY_AUTO_SCALE` | false | boolean | Enable Celery worker auto-scaling |

> ⚠️ **CRITICAL:** The most common culprit is `PLUGIN_MAX_EXECUTION_TIMEOUT` with a default of just **600 seconds (10 minutes)**. If your workflow stops at exactly 10 minutes with error `PluginDaemonInternalServerError: killed by timeout`, this is the cause!

### For Dify Cloud Users

**Unfortunately, timeout limits on Dify Cloud are platform-controlled and cannot be changed by users.**

**Workarounds:**
1. **Use `max_urls` parameter** - Process sitemaps in smaller chunks
   ```yaml
   # Instead of processing 500 URLs at once:
   max_urls: 50  # Process 50 URLs per run
   ```

2. **Use `start_from_index` for batching** - Run multiple syncs sequentially
   ```yaml
   # First run
   max_urls: 50
   start_from_index: 1

   # Second run (after first completes)
   max_urls: 50
   start_from_index: 51

   # And so on...
   ```

3. **Schedule multiple smaller syncs** - Create separate workflow runs for different URL ranges

### For Self-Hosted Dify Users

Self-hosted users can modify timeout settings to support long-running sitemap syncs.

#### Step 1: Locate Configuration File

Dify uses environment variables stored in the `.env` file within your Docker deployment directory.

```bash
# Typical location for Docker Compose deployment
cd /path/to/dify/docker
ls -la .env
```

The configuration is based on the `.env.example` template. If you don't have a `.env` file, copy from the example:

```bash
cp .env.example .env
```

#### Step 2: Modify Timeout Settings

Edit the `.env` file and add/modify these variables:

```bash
# Open the .env file
nano .env  # or vim, code, etc.
```

Add or update these lines:

```bash
# ===========================================
# TIMEOUT CONFIGURATION FOR LONG-RUNNING PLUGINS
# ===========================================

# ⚠️ CRITICAL: Plugin execution timeout (in SECONDS)
# Default: 600 (10 minutes) - THIS IS OFTEN THE CULPRIT!
# If your workflow stops at exactly 10 minutes with error
# "PluginDaemonInternalServerError: killed by timeout", this is why!
# Recommended for large sitemaps: 28800 (8 hours)
PLUGIN_MAX_EXECUTION_TIMEOUT=28800

# Text generation timeout (in MILLISECONDS)
# Default: 60000 (60 seconds)
# Recommended for large sitemaps: 1800000 (30 minutes)
TEXT_GENERATION_TIMEOUT_MS=1800000

# HTTP request handling timeout (in SECONDS)
# Default: 360 (6 minutes)
# Recommended: 28800 (8 hours)
GUNICORN_TIMEOUT=28800

# Maximum workflow execution time (in SECONDS)
# Default: 1200 (20 minutes)
# Recommended for very large sitemaps: 28800 (8 hours)
WORKFLOW_MAX_EXECUTION_TIME=28800

# Maximum app execution time (in SECONDS)
# Default: 1200 (20 minutes)
APP_MAX_EXECUTION_TIME=28800
```

**Recommended values based on sitemap size:**

| Sitemap Size | PLUGIN_MAX_EXECUTION_TIMEOUT | TEXT_GENERATION_TIMEOUT_MS | WORKFLOW_MAX_EXECUTION_TIME |
|--------------|------------------------------|---------------------------|----------------------------|
| < 50 URLs | 600 (default) | 60000 (default) | 1200 (default) |
| 50-100 URLs | 1800 (30 min) | 120000 (2 min) | 1800 (30 min) |
| 100-200 URLs | 3600 (1 hour) | 300000 (5 min) | 3600 (1 hour) |
| 200-500 URLs | 14400 (4 hours) | 600000 (10 min) | 14400 (4 hours) |
| 500+ URLs | 28800 (8 hours) | 1800000 (30 min) | 28800 (8 hours) |

#### Step 3: Restart Dify Services

After modifying `.env`, restart Dify for changes to take effect:

```bash
# Using Docker Compose v2
docker compose down
docker compose up -d

# Or using Docker Compose v1
docker-compose down
docker-compose up -d
```

#### Step 4: Verify Changes

1. Check that containers restarted successfully:
   ```bash
   docker compose ps
   ```

2. Verify environment variables are loaded:
   ```bash
   docker compose exec api env | grep -E "(TIMEOUT|EXECUTION_TIME)"
   ```

   Expected output:
   ```
   PLUGIN_MAX_EXECUTION_TIMEOUT=28800
   TEXT_GENERATION_TIMEOUT_MS=1800000
   GUNICORN_TIMEOUT=28800
   WORKFLOW_MAX_EXECUTION_TIME=28800
   APP_MAX_EXECUTION_TIME=28800
   ```

3. Test with a small sitemap first to confirm the sync completes successfully

### Configuration Reference

Here's a complete reference of timeout-related environment variables from the official Dify `.env.example`:

```bash
# Container Startup Related Configuration
# (Only effective when starting with docker image or docker-compose)

# Defaults to gevent. If using windows, it can be switched to sync or solo.
SERVER_WORKER_CLASS=gevent

# Server worker configuration
SERVER_WORKER_AMOUNT=1
SERVER_WORKER_CONNECTIONS=50

# Request handling timeout. The default is 360,
# it is recommended to set it to 360 to support a longer sse connection time.
GUNICORN_TIMEOUT=360

# Celery worker configuration (for async tasks)
CELERY_WORKER_AMOUNT=4
CELERY_AUTO_SCALE=false

# Workflow runtime configuration
WORKFLOW_MAX_EXECUTION_STEPS=500
WORKFLOW_MAX_EXECUTION_TIME=1200
WORKFLOW_CALL_MAX_DEPTH=5

# App execution time
APP_MAX_EXECUTION_TIME=1200

# The timeout for the text generation in millisecond
TEXT_GENERATION_TIMEOUT_MS=60000

# ⚠️ Plugin execution timeout (often overlooked!)
# Default: 600 seconds (10 minutes)
PLUGIN_MAX_EXECUTION_TIMEOUT=600

# Plugin signature verification (set to false for local development)
FORCE_VERIFYING_SIGNATURE=true

# Sandbox worker timeout (for code execution nodes)
SANDBOX_WORKER_TIMEOUT=15
```

### Browser Tab/Window Behavior

You may notice that switching browser tabs or windows seems to trigger timeouts. This is a **known browser behavior**, not specific to Dify:

- Modern browsers throttle JavaScript execution in background tabs
- SSE connections may be deprioritized when tabs are inactive
- However, the server-side execution typically continues - it's the UI that stops updating

**Tips:**
- Keep the Dify workflow tab in the foreground during long syncs
- Use a dedicated browser window for monitoring sync progress
- For very long syncs, the workflow will complete even if the UI stops updating - check the Knowledge Base directly to verify

### Plugin Design Notes

The sync_sitemap plugin is designed to be **timeout-resilient**:

1. **Frequent yields** - Progress messages are yielded after every URL to keep the SSE connection alive
2. **Streaming output** - Uses generator pattern to stream results rather than batch them
3. **Clear progress** - Shows `[X/Y]` progress so you know exactly where a sync stopped if interrupted

If a sync times out, you can resume from where it stopped using `start_from_index`:
```yaml
# If sync stopped at 75/200, resume with:
start_from_index: 76
```

---

## Contributing

Contributions welcome! This is an open-source project for the community.

## License

Apache License 2.0
