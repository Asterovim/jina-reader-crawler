# Jina Reader Sitemap Crawler

Convert sitemaps to clean markdown using Jina Reader API, with optional Dify import.

> ⚠️ **Disclaimer**: This is an independent project with no affiliation to Jina AI or Dify AI.

## Features

- **Clean markdown output** - Optimized for RAG/LLM ingestion
- **Smart content filtering** - Optional CSS selectors to remove ads, headers, footers
- **Single URL or sitemap support** - Works with sitemap.xml or individual pages
- **Resume crawling** - Start from any URL index for large sitemaps or interrupted crawls
- **Anti-detection crawling** - Random delays between requests (10-20s default)
- **Robust error handling** - Retry logic with timeout management
- **Metadata preservation** - Title, URL, domain, crawl date in YAML frontmatter
- **Duplicate detection** - Automatically identifies and isolates duplicate content
- **Dify integration** - Direct import to Dify knowledge base with metadata
- **Optional EU compliance** - Can use Jina's European servers

## Quick Start

### 1. Crawl websites

```bash
git clone https://github.com/Asterovim/jina-reader-crawler.git
cd jina-reader-crawler
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your sitemap URL
python crawler.py
```

### 2. Analyze duplicates (optional)

```bash
# Analyze existing crawl for duplicates without re-crawling
python crawler.py --duplicates-only
```

### 3. Import to Dify (optional)

```bash
# Configure Dify settings in .env
python dify.py
```

## Configuration

Edit `.env` file with your settings. See `.env.example` for detailed examples.

### Crawler Configuration (Required)
```bash
SITEMAP_URL=https://example.com/sitemap.xml  # Required: sitemap or single URL
JINA_API_KEY=your_key_here                   # Optional (20 RPM without, 500+ with)
```

### Dify Configuration (Optional)
```bash
DIFY_API_KEY=your_dify_api_key_here         # Required for Dify import
DIFY_DATASET_ID=your_dataset_id_here        # Required for Dify import
DIFY_BASE_URL=https://api.dify.ai           # Optional: Dify instance URL
```

### Advanced Options
```bash
OUTPUT_DIR=output                            # Output directory
CSS_SELECTOR=.ads,.sidebar,footer            # Remove unwanted elements
START_FROM_INDEX=1                           # Resume from specific URL
MIN_DELAY=10                                 # Min delay between requests (seconds)
MAX_DELAY=20                                 # Max delay between requests (seconds)
SKIP_EXISTING=false                          # Skip existing documents in Dify (true/false)
```

### Command Line Options
```bash
python crawler.py                           # Normal crawling with duplicate detection
python crawler.py --duplicates-only         # Analyze duplicates without crawling
```

## Project Structure

```
jina-reader-crawler/
├── crawler.py              # Main crawler script
├── dify.py                 # Dify import script
├── dify/                   # Dify integration modules
│   ├── __init__.py
│   ├── client.py           # Dify API client
│   ├── importer.py         # Import logic
│   └── metadata.py         # Metadata handling
├── .env.example            # Configuration template
├── requirements.txt        # Dependencies
└── crawl-result/           # Output directory
    └── output/             # Markdown files with metadata
```

## Output

Files saved to `crawl-result/{OUTPUT_DIR}/`:
- `domain_page.md` - Clean markdown with YAML frontmatter metadata
- `crawl_summary.txt` - Success/failure stats with duplicate analysis
- `failed_urls.txt` - Failed URLs (if any)
- `duplicates/` - Folder containing duplicate content organized by title

### File Structure
```
crawl-result/output/
├── unique_content_files.md
├── crawl_summary.txt
├── failed_urls.txt
└── duplicates/
    ├── page-non-trouvee/
    │   ├── domain_error1.md
    │   └── domain_error2.md
    └── acces-refuse/
        └── domain_forbidden.md
```

Each markdown file includes YAML frontmatter:
```markdown
---
title: "Page Title"
source_url: "https://example.com/page"
domain: "example.com"
crawl_date: "1755781483"
description: "Page meta description"
language: "en"
---

# Clean content without ads/navigation
```

### Duplicate Detection

The crawler automatically detects duplicate content based on page titles:
- **Unique content**: Kept in main directory for Dify import
- **Duplicates**: Moved to `duplicates/` folder organized by title
- **Common duplicates**: Error pages (404, 403), generic templates
- **Safety**: First occurrence kept, subsequent duplicates archived

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
