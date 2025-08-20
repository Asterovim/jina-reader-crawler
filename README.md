# Jina Reader Sitemap Crawler

**Unofficial open-source project** - Convert sitemaps to clean markdown for RAG using Jina Reader API.

> ⚠️ **Disclaimer**: This is an independent project with no affiliation to Jina AI.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/Asterovim/jina-reader-crawler.git
cd jina-reader-crawler
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your sitemap URL and Jina API key

# Run
python crawler.py
```

## Features

- ✅ **Clean markdown output** - Optimized for RAG/LLM ingestion
- ✅ **Smart content filtering** - Remove ads, headers, footers via CSS selectors
- ✅ **EU compliance** - Uses Jina's European servers
- ✅ **Anti-detection crawling** - Random jitter, progressive delays, smart timing
- ✅ **Robust error handling** - Exponential backoff retry with timeout management
- ✅ **Metadata preservation** - Title, URL, and structured content

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `SITEMAP_URL` | ✅ | Sitemap XML URL or single page URL |
| `JINA_API_KEY` | ✅ | Get free key at [jina.ai/reader](https://jina.ai/reader/) |
| `CSS_SELECTOR` | ❌ | Remove elements (e.g., `.ads,.sidebar,.footer`) |
| `WAIT_FOR_SELECTOR` | ❌ | Wait for elements before processing (e.g., `main,.content`) |
| `EU_COMPLIANCE` | ❌ | Use EU servers (default: `true`) |
| `NO_CACHE` | ❌ | Disable cache for fresh content (default: `false`) |
| `OUTPUT_DIR` | ❌ | Output directory (default: `output`) |
| `REQUEST_TIMEOUT` | ❌ | Request timeout in seconds (default: `120`) |
| `MIN_DELAY` | ❌ | Minimum delay between requests in seconds (default: `3`) |
| `MAX_DELAY` | ❌ | Maximum delay between requests in seconds (default: `6`) |
| `REQUEST_TIMEOUT` | ❌ | Request timeout in seconds (default: `120`) |
| `RETRY_COUNT` | ❌ | Number of retries for timeout/connection errors (default: `2`) |
| `CRAWLER_TIMEOUT` | ❌ | Maximum crawling time in seconds, 0=no limit (default: `0`) |

## Output Structure

```
crawl-result/
└── your-output-dir/
    ├── domain_page1.md
    ├── domain_page2.md
    ├── crawl_summary.txt
    └── failed_urls.txt (if any failures)
```

Each markdown file includes:
```markdown
Title: Page Title
URL Source: https://example.com/page
Markdown Content:
# Clean content without ads/navigation
```

## Rate Limits

| API Tier | Rate Limit | Delay | Anti-Detection |
|----------|------------|-------|----------------|
| Free | 20 RPM | 3-6s random | ✅ Random timing |
| Paid | 500 RPM | 3-6s random | ✅ Random timing |
| Premium | 5000 RPM | 3-6s random | ✅ Random timing |

## Contributing

Contributions welcome! This is an open-source project for the community.

## License

Apache License 2.0 - See LICENSE file for details.
