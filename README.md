# Jina Reader Sitemap Crawler

Minimal sitemap crawler using Jina Reader API to convert web pages to markdown for RAG.

## Setup

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy and configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. Run the crawler:
```bash
python crawler.py
```

## Configuration (.env)

- `SITEMAP_URL` - Required: URL of sitemap.xml to crawl
- `JINA_API_KEY` - Required: API key for optimal performance (get at https://jina.ai/reader/)
- `CSS_SELECTOR` - Optional: Remove unwanted elements (e.g., `.ads,.sidebar`)
- `OUTPUT_DIR` - Optional: Output directory (default: `output`)
- `RATE_LIMIT_DELAY` - Auto-configured based on API key presence

## Output

Markdown files saved as `{domain}_{path}.md` with metadata headers.

## Rate Limits (Auto-Configured)

- **Without API key**: 20 RPM (3.5s delay)
- **With API key**: 500 RPM (0.13s delay) ⚡
- **Premium API key**: 5000 RPM

The crawler automatically detects your API key and optimizes rate limits accordingly.
