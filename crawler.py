#!/usr/bin/env python3
"""
Minimal Jina Reader Sitemap Crawler
Keep it simple: .env config + single script
"""

import os
import time
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from .env
JINA_API_KEY = os.getenv('JINA_API_KEY', '')
CSS_SELECTOR = os.getenv('CSS_SELECTOR', '')
SITEMAP_URL = os.getenv('SITEMAP_URL', '')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')

# Smart rate limiting based on API key presence
if JINA_API_KEY and JINA_API_KEY != 'your_jina_api_key_here':
    # With API key: 500 RPM limit, use 0.13s delay (~460 RPM safe)
    RATE_LIMIT_DELAY = float(os.getenv('RATE_LIMIT_DELAY', '0.13'))
else:
    # Without API key: 20 RPM limit, use 3.5s delay (~17 RPM safe)
    RATE_LIMIT_DELAY = float(os.getenv('RATE_LIMIT_DELAY', '3.5'))

def get_urls_from_sitemap(sitemap_url):
    """Extract URLs from sitemap.xml or handle single URL"""
    print(f"Processing: {sitemap_url}")

    # Check if it's a single URL (not a sitemap)
    if not sitemap_url.endswith('.xml'):
        print("Single URL detected, not a sitemap")
        return [sitemap_url]

    try:
        response = requests.get(sitemap_url, timeout=10)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        urls = []

        # Handle different sitemap namespaces
        for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
            loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc is not None and loc.text:
                urls.append(loc.text.strip())

        print(f"Found {len(urls)} URLs in sitemap")
        return urls

    except Exception as e:
        print(f"Error parsing sitemap: {e}")
        return []

def fetch_with_jina(url):
    """Fetch URL content using Jina Reader API"""
    jina_url = "https://r.jina.ai/"

    headers = {}
    # Always use API key if configured (not placeholder)
    if JINA_API_KEY and JINA_API_KEY != 'your_jina_api_key_here':
        headers['Authorization'] = f'Bearer {JINA_API_KEY}'
    if CSS_SELECTOR:
        headers['X-Remove-Selector'] = CSS_SELECTOR

    # Essential headers for JSON API mode
    headers['Accept'] = 'application/json'
    headers['Content-Type'] = 'application/json'
    headers['X-Engine'] = 'browser'
    headers['X-Return-Format'] = 'markdown'
    headers['X-No-Cache'] = 'true'
    headers['X-Retain-Images'] = 'none'  # Remove images for cleaner RAG content

    # Wait for main content to load before processing (helps with dynamic content)
    headers['X-Wait-For-Selector'] = 'main, .elementor-widget-container, .elementor-section'

    # JSON payload with URL
    payload = {"url": url}

    try:
        print(f"Fetching: {url}")
        import json
        response = requests.post(jina_url, headers=headers, json=payload, timeout=60)

        # Handle specific error cases
        if response.status_code == 401:
            print(f"❌ API Key invalid or expired. Please check your JINA_API_KEY in .env")
            return None
        elif response.status_code == 429:
            print(f"⚠️ Rate limit exceeded. Consider increasing RATE_LIMIT_DELAY")
            return None

        response.raise_for_status()

        # Parse JSON response
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON response for {url}")
            return None

        # Check for cached snapshot warning and retry if found
        warning = data.get('warning', '')
        if "cached snapshot" in warning.lower():
            print(f"⚠️ Cached snapshot detected, retrying with fresh fetch...")
            time.sleep(1)  # Small delay before retry
            response = requests.post(jina_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()

            try:
                data = response.json()
                warning = data.get('warning', '')
                # If still cached after retry, it's a persistent issue
                if "cached snapshot" in warning.lower():
                    print(f"❌ Still getting cached content after retry for {url}")
                    return None
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON response on retry for {url}")
                return None

        # Extract content and metadata from nested data structure
        data_content = data.get('data', {})
        title = data_content.get('title', '')
        content = data_content.get('content', '')
        url_source = data_content.get('url', url)

        # Format with metadata like before
        formatted_content = f"Title: {title}\n\nURL Source: {url_source}\n\nMarkdown Content:\n{content}"

        return formatted_content

    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching {url}: {e}")
        return None

def save_markdown(url, content, output_dir):
    """Save content as markdown file"""
    if not content:
        return

    # Create filename from URL
    parsed = urlparse(url)
    domain = parsed.netloc.replace('www.', '')
    path = parsed.path.strip('/').replace('/', '_') or 'index'
    filename = f"{domain}_{path}.md"

    # Create crawl-result directory structure
    crawl_result_dir = Path("crawl-result") / output_dir
    crawl_result_dir.mkdir(parents=True, exist_ok=True)

    filepath = crawl_result_dir / filename

    # Save content as-is from Jina Reader (includes Title, URL Source, Markdown Content)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Saved: {filepath}")

def generate_report(successful_urls, failed_urls, output_dir):
    """Generate crawling report"""
    crawl_result_dir = Path("crawl-result") / output_dir
    crawl_result_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

    # Write failed URLs report
    if failed_urls:
        failed_report_path = crawl_result_dir / "failed_urls.txt"
        with open(failed_report_path, 'w', encoding='utf-8') as f:
            f.write(f"# Failed URLs Report\n")
            f.write(f"Generated: {timestamp}\n")
            f.write(f"Total failed: {len(failed_urls)}\n\n")
            for url in failed_urls:
                f.write(f"{url}\n")
        print(f"Failed URLs report: {failed_report_path}")

    # Write summary report
    summary_path = crawl_result_dir / "crawl_summary.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"# Crawl Summary Report\n")
        f.write(f"Generated: {timestamp}\n")
        f.write(f"Total URLs processed: {len(successful_urls) + len(failed_urls)}\n")
        f.write(f"Successful: {len(successful_urls)}\n")
        f.write(f"Failed: {len(failed_urls)}\n")
        f.write(f"Success rate: {len(successful_urls)/(len(successful_urls) + len(failed_urls))*100:.1f}%\n")
    print(f"Summary report: {summary_path}")

def main():
    """Main crawler function"""
    if not SITEMAP_URL:
        print("Error: SITEMAP_URL not set in .env file")
        return

    # Check API key status
    has_api_key = JINA_API_KEY and JINA_API_KEY != 'your_jina_api_key_here'
    rpm_limit = "500 RPM" if has_api_key else "20 RPM"

    print("🚀 Starting Jina Reader Sitemap Crawler")
    print(f"URL/Sitemap: {SITEMAP_URL}")
    print(f"Output: crawl-result/{OUTPUT_DIR}")
    print(f"API Key: {'✅ Configured' if has_api_key else '❌ Not configured (using free tier)'}")
    print(f"Rate limit: {rpm_limit} ({RATE_LIMIT_DELAY}s delay)")
    print("-" * 50)

    # Get URLs from sitemap
    urls = get_urls_from_sitemap(SITEMAP_URL)
    if not urls:
        print("No URLs found. Exiting.")
        return

    # Track results
    successful_urls = []
    failed_urls = []

    # Process each URL
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}]", end=" ")

        # Fetch content
        content = fetch_with_jina(url)

        # Save if successful
        if content:
            save_markdown(url, content, OUTPUT_DIR)
            successful_urls.append(url)
        else:
            failed_urls.append(url)

        # Rate limiting
        if i < len(urls):  # Don't wait after last URL
            print(f"Waiting {RATE_LIMIT_DELAY}s...")
            time.sleep(RATE_LIMIT_DELAY)

    # Generate report
    generate_report(successful_urls, failed_urls, OUTPUT_DIR)

    print(f"\n✅ Crawling complete! Check crawl-result/{OUTPUT_DIR}/ for markdown files")
    if failed_urls:
        print(f"⚠️ {len(failed_urls)} URLs failed. Check crawl-result/{OUTPUT_DIR}/failed_urls.txt for details")

if __name__ == "__main__":
    main()
