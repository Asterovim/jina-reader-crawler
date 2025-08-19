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
- ✅ **Rate limiting** - Auto-configured based on API key tier
- ✅ **Error handling** - Comprehensive retry logic and reporting
- ✅ **Metadata preservation** - Title, URL, and structured content

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `SITEMAP_URL` | ✅ | Sitemap XML URL or single page URL |
| `JINA_API_KEY` | ✅ | Get free key at [jina.ai/reader](https://jina.ai/reader/) |
| `CSS_SELECTOR` | ❌ | Remove elements (e.g., `.ads,.sidebar,.footer`) |
| `OUTPUT_DIR` | ❌ | Output directory (default: `output`) |

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

| API Tier | Rate Limit | Auto Delay |
|----------|------------|------------|
| Free | 20 RPM | 3.5s |
| Paid | 500 RPM | 0.13s |
| Premium | 5000 RPM | Custom |

## Contributing

Contributions welcome! This is an open-source project for the community.

## License

Apache License 2.0 - See LICENSE file for details.
