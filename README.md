# Jina Reader Sitemap Crawler

Convert sitemaps to clean markdown using Jina Reader API.

> ⚠️ **Disclaimer**: This is an independent project with no affiliation to Jina AI.

## Features

- **Clean markdown output** - Optimized for RAG/LLM ingestion
- **Smart content filtering** - Optional CSS selectors to remove ads, headers, footers
- **Single URL or sitemap support** - Works with sitemap.xml or individual pages
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
