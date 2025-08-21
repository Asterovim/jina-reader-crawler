#!/usr/bin/env python3
"""
Minimal Jina Reader Sitemap Crawler
Keep it simple: .env config + single script
"""

import os
import time
import random
import json
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
WAIT_FOR_SELECTOR = os.getenv('WAIT_FOR_SELECTOR', '')
EU_COMPLIANCE = os.getenv('EU_COMPLIANCE', 'true').lower() == 'true'
NO_CACHE = os.getenv('NO_CACHE', 'false').lower() == 'true'
SITEMAP_URL = os.getenv('SITEMAP_URL', '')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
START_FROM_INDEX = int(os.getenv('START_FROM_INDEX', '1'))

# Simple anti-detection delay settings
MIN_DELAY = float(os.getenv('MIN_DELAY', '3'))
MAX_DELAY = float(os.getenv('MAX_DELAY', '6'))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '120'))
RETRY_COUNT = int(os.getenv('RETRY_COUNT', '2'))
CRAWLER_TIMEOUT = int(os.getenv('CRAWLER_TIMEOUT', '0'))



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
    # Choose server based on EU compliance setting
    if EU_COMPLIANCE:
        jina_url = "https://eu-r-beta.jina.ai/"
    else:
        jina_url = "https://r.jina.ai/"

    headers = {}
    # Always use API key if configured (not placeholder)
    if JINA_API_KEY and JINA_API_KEY != 'your_jina_api_key_here':
        headers['Authorization'] = f'Bearer {JINA_API_KEY}'

    # CSS selector to remove unwanted elements
    if CSS_SELECTOR:
        headers['X-Remove-Selector'] = CSS_SELECTOR

    # Essential headers for JSON API mode
    headers['Accept'] = 'application/json'
    headers['Content-Type'] = 'application/json'
    headers['X-Timeout'] = '30'  # 30 seconds timeout for complex pages
    headers['X-Retain-Images'] = 'false' # Don't retain images
    headers['X-Engine'] = 'browser' # High-quality engine designed to resolve rendering issues and deliver the best content output.

    # Cache control based on NO_CACHE setting
    if NO_CACHE:
        headers['X-No-Cache'] = 'true'

    # Wait for content to load before processing (helps with dynamic content)
    if WAIT_FOR_SELECTOR:
        headers['X-Wait-For-Selector'] = WAIT_FOR_SELECTOR

    # JSON payload with URL
    payload = {"url": url}

    print(f"Fetching: {url}")

    # Simple retry logic for timeouts
    for attempt in range(RETRY_COUNT + 1):
        try:
            response = requests.post(jina_url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)

            # Generic retry logic: anything not 2xx/3xx gets retried
            if response.status_code >= 400:
                if attempt < RETRY_COUNT:
                    print(f"⚠️ HTTP {response.status_code} error (attempt {attempt + 1}/{RETRY_COUNT + 1}). Retrying...")
                    time.sleep(2)
                    continue
                else:
                    print(f"❌ HTTP {response.status_code} error after {RETRY_COUNT + 1} attempts")
                    return None

            # Success! Parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON response for {url}")
                return None

            # Check for cached snapshot warning and retry if found
            warning = data.get('warning', '')
            if "cached snapshot" in warning.lower() and not NO_CACHE:
                print(f"⚠️ Cached snapshot detected, retrying with fresh fetch...")
                # Add X-No-Cache header for this retry
                retry_headers = headers.copy()
                retry_headers['X-No-Cache'] = 'true'

                try:
                    time.sleep(1)  # Small delay before retry
                    response = requests.post(jina_url, headers=retry_headers, json=payload, timeout=REQUEST_TIMEOUT)
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
                except requests.exceptions.RequestException as e:
                    print(f"❌ Error on cache retry: {e}")
                    return None

            # Extract content and metadata from nested data structure
            data_content = data.get('data', {})
            title = data_content.get('title', '')
            content = data_content.get('content', '')
            url_source = data_content.get('url', url)

            # Format with metadata like before
            formatted_content = f"Title: {title}\n\nURL Source: {url_source}\n\nMarkdown Content:\n{content}"

            return formatted_content

        except requests.exceptions.Timeout:
            if attempt < RETRY_COUNT:
                print(f"⚠️ Timeout (attempt {attempt + 1}/{RETRY_COUNT + 1}). Retrying...")
                time.sleep(2)  # Small delay before retry
                continue
            else:
                print(f"❌ Timeout after {RETRY_COUNT + 1} attempts")
                return None
        except requests.exceptions.ConnectionError:
            if attempt < RETRY_COUNT:
                print(f"⚠️ Connection error (attempt {attempt + 1}/{RETRY_COUNT + 1}). Retrying...")
                time.sleep(2)  # Small delay before retry
                continue
            else:
                print(f"❌ Connection error after {RETRY_COUNT + 1} attempts")
                return None



    # If we get here, all retries failed
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

    print("🚀 Starting Jina Reader Sitemap Crawler")
    print(f"URL/Sitemap: {SITEMAP_URL}")
    print(f"Output: crawl-result/{OUTPUT_DIR}")
    print(f"API Key: {'✅ Configured' if has_api_key else '❌ Not configured (using free tier)'}")
    print(f"EU Compliance: {'✅ Enabled' if EU_COMPLIANCE else '❌ Disabled'}")
    print(f"No Cache: {'✅ Enabled' if NO_CACHE else '❌ Disabled'}")
    print(f"CSS Selector: {CSS_SELECTOR if CSS_SELECTOR else '❌ Not set'}")
    print(f"Wait For Selector: {WAIT_FOR_SELECTOR if WAIT_FOR_SELECTOR else '❌ Not set'}")
    print(f"Delay: {MIN_DELAY}-{MAX_DELAY}s random between requests")
    print(f"Request timeout: {REQUEST_TIMEOUT}s, Retries: {RETRY_COUNT}")
    print(f"Start from index: {START_FROM_INDEX}")
    if CRAWLER_TIMEOUT > 0:
        print(f"Crawler timeout: {CRAWLER_TIMEOUT}s ({CRAWLER_TIMEOUT//3600}h {(CRAWLER_TIMEOUT%3600)//60}m)")
    else:
        print(f"Crawler timeout: No limit")
    print("-" * 50)

    # Get URLs from sitemap
    urls = get_urls_from_sitemap(SITEMAP_URL)
    if not urls:
        print("No URLs found. Exiting.")
        return

    # Validate START_FROM_INDEX
    total_urls = len(urls)
    if START_FROM_INDEX < 1:
        print(f"Error: START_FROM_INDEX must be >= 1, got {START_FROM_INDEX}")
        return
    if START_FROM_INDEX > total_urls:
        print(f"Error: START_FROM_INDEX ({START_FROM_INDEX}) exceeds total URLs ({total_urls})")
        return

    # Apply start index if specified
    if START_FROM_INDEX > 1:
        skipped_count = START_FROM_INDEX - 1
        urls = urls[skipped_count:]
        print(f"📍 Starting from URL #{START_FROM_INDEX} (skipping first {skipped_count} URLs)")
        print(f"Processing {len(urls)} URLs out of {total_urls} total")
    else:
        print(f"Processing all {total_urls} URLs")

    # Track results and timing
    successful_urls = []
    failed_urls = []
    start_time = time.time()

    # Process each URL
    for i, url in enumerate(urls, 1):
        # Check timeout if set
        if CRAWLER_TIMEOUT > 0:
            elapsed_time = time.time() - start_time
            if elapsed_time > CRAWLER_TIMEOUT:
                print(f"\n⏰ Crawler timeout reached ({CRAWLER_TIMEOUT}s). Stopping crawl.")
                current_url_number = START_FROM_INDEX + i - 2
                print(f"Processed {i-1}/{len(urls)} URLs (#{START_FROM_INDEX}-#{current_url_number}) in {elapsed_time:.0f}s")
                break

        # Display progress with global URL numbering
        current_url_number = START_FROM_INDEX + i - 1
        print(f"\n[{current_url_number}/{total_urls}]", end=" ")

        # Fetch content
        content = fetch_with_jina(url)

        # Save if successful
        if content:
            save_markdown(url, content, OUTPUT_DIR)
            successful_urls.append(url)
        else:
            failed_urls.append(url)

        # Simple random delay between requests
        if i < len(urls):  # Don't wait after last URL
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            print(f"Waiting {delay:.1f}s...")
            time.sleep(delay)

    # Generate report
    generate_report(successful_urls, failed_urls, OUTPUT_DIR)

    print(f"\n✅ Crawling complete! Check crawl-result/{OUTPUT_DIR}/ for markdown files")
    if failed_urls:
        print(f"⚠️ {len(failed_urls)} URLs failed. Check crawl-result/{OUTPUT_DIR}/failed_urls.txt for details")

if __name__ == "__main__":
    main()
