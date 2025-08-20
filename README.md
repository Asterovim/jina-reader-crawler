# Jina Reader Sitemap Crawler

Convert sitemaps to clean markdown using Jina Reader API.

> ⚠️ **Disclaimer**: This is an independent project with no affiliation to Jina AI.

## Features

- **Clean markdown output** - Optimized for RAG/LLM ingestion
- **Smart content filtering** - Optional CSS selectors to remove ads, headers, footers
- **Single URL or sitemap support** - Works with sitemap.xml or individual pages
- **Resume crawling** - Start from any URL index for large sitemaps or interrupted crawls
- **Anti-detection crawling** - Random delays between requests (3-6s default)
- **Robust error handling** - Retry logic with timeout management
- **Metadata preservation** - Title, URL, and structured content
- **Optional EU compliance** - Can use Jina's European servers (default: enabled)

## Quick Start

```bash
git clone https://github.com/Asterovim/jina-reader-crawler.git
cd jina-reader-crawler
pip install requests python-dotenv
cp .env.example .env
# Edit .env with your sitemap URL
python crawler.py
```

## Configuration

Edit `.env` file:

```bash
SITEMAP_URL=https://example.com/sitemap.xml  # Required
JINA_API_KEY=your_key_here                   # Optional (20 RPM without, 500+ with)
OUTPUT_DIR=output                            # Optional
CSS_SELECTOR=.ads,.sidebar,footer            # Optional: remove elements
WAIT_FOR_SELECTOR=main,.content              # Optional: wait for elements
EU_COMPLIANCE=true                           # Optional: use EU servers
NO_CACHE=false                               # Optional: force fresh content
START_FROM_INDEX=1                           # Optional: start from URL index (1-based)
MIN_DELAY=3                                  # Optional: min delay between requests
MAX_DELAY=6                                  # Optional: max delay between requests
REQUEST_TIMEOUT=120                          # Optional: request timeout
RETRY_COUNT=2                                # Optional: retry attempts
CRAWLER_TIMEOUT=0                            # Optional: max crawl time (0=unlimited)
```

## Output

Files saved to `crawl-result/{OUTPUT_DIR}/`:
- `domain_page.md` - Clean markdown with title, URL, content
- `crawl_summary.txt` - Success/failure stats
- `failed_urls.txt` - Failed URLs (if any)

Each markdown file includes:
```markdown
Title: Page Title
URL Source: https://example.com/page
Markdown Content:
# Clean content without ads/navigation
```

## Advanced Usage

### Resume Crawling from Specific Index

For large sitemaps or to resume interrupted crawls:

```bash
# Start from URL #500 (skip first 499 URLs)
START_FROM_INDEX=500

# Process URLs 1001-2000 for parallel crawling
START_FROM_INDEX=1001
CRAWLER_TIMEOUT=3600  # Stop after 1 hour
```

### Parallel Processing

Split large sitemaps across multiple instances:

```bash
# Instance 1: URLs 1-1000
START_FROM_INDEX=1
CRAWLER_TIMEOUT=3600

# Instance 2: URLs 1001-2000
START_FROM_INDEX=1001
CRAWLER_TIMEOUT=3600

# Instance 3: URLs 2001-3000
START_FROM_INDEX=2001
CRAWLER_TIMEOUT=3600
```

## Rate Limits

| API Tier | Rate Limit | Notes |
|----------|------------|-------|
| Free | 20 RPM | No API key required |
| Paid | 500 RPM | API key required |
| Premium | 5000 RPM | Premium API key |

## Contributing

Contributions welcome! This is an open-source project for the community.

## License

Apache License 2.0
