"""Content processing utilities for document building and change detection.

Handles document content formatting, hashing, and timestamp management.
"""

import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse


def generate_sync_timestamp() -> str:
    """Generate current UTC timestamp in ISO 8601 format for Last Synced field."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_document_content(content_data: dict, original_url: str | None = None) -> str:
    """Build document content string from content data.

    Includes Last Synced timestamp for lastmod-based change detection.

    Args:
        content_data: Dict with title, content, url (from Jina), description
        original_url: The original URL from sitemap (use this for Source URL to ensure
                     consistent lookup). If None, falls back to content_data['url'].

    IMPORTANT: We store the original sitemap URL (not Jina's response URL) because:
    1. Jina may follow redirects and return a different URL
    2. Jina may decode/encode URLs differently (e.g., %C3%AE vs î)
    3. Cache lookup uses sitemap URL, so storage must match for skip/update to work
    """
    source_url = original_url if original_url else content_data.get("url", "")
    parsed_url = urlparse(source_url)
    domain = parsed_url.netloc.replace("www.", "")

    sync_timestamp = generate_sync_timestamp()

    content = f"# {content_data['title']}\n\n"
    content += f"**Source URL:** {source_url}\n**Domain:** {domain}\n"
    if content_data.get("description"):
        content += f"**Description:** {content_data['description']}\n"
    content += f"**Last Synced:** {sync_timestamp}\n"
    content += f"\n---\n\n{content_data['content']}"
    return content


def compute_content_hash(content: str) -> str:
    """Compute MD5 hash of content string."""
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def content_changed(existing_hash: str | None, new_content_data: dict, original_url: str | None = None) -> bool:
    """Check if new content differs from existing document content.

    Args:
        existing_hash: MD5 hash of existing document content (or None if unavailable)
        new_content_data: New content data from Jina
        original_url: Original sitemap URL for consistent content building

    Returns True if content has changed and update is needed.
    Returns True if we can't determine (fail-safe: update if unsure).
    """
    if existing_hash is None:
        return True  # Can't get existing content, assume it changed

    new_content = build_document_content(new_content_data, original_url)
    new_hash = compute_content_hash(new_content)

    return existing_hash != new_hash


def parse_timestamp(timestamp_str: str | None) -> datetime | None:
    """Parse various timestamp formats to datetime.

    Handles:
    - ISO 8601 with Z suffix: 2024-01-15T10:30:00Z
    - ISO 8601 with timezone: 2024-01-15T10:30:00+00:00
    - Date only: 2024-01-15
    - Sitemap W3C format: 2024-01-15T10:30:00.000+00:00

    Returns:
        datetime in UTC timezone, or None if parsing fails
    """
    if not timestamp_str:
        return None

    timestamp_str = timestamp_str.strip()

    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(timestamp_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    try:
        normalized = timestamp_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        pass

    return None


def is_content_unchanged_by_lastmod(
    sitemap_lastmod: str | None, doc_last_synced: str | None
) -> bool:
    """Check if content is unchanged based on lastmod comparison.

    Returns True if we can confidently say content hasn't changed
    (sitemap_lastmod <= doc_last_synced), meaning we can skip processing.

    Returns False (proceed with normal processing) if:
    - Either timestamp is missing
    - Either timestamp fails to parse
    - sitemap_lastmod > doc_last_synced (content may have changed)
    """
    if not sitemap_lastmod or not doc_last_synced:
        return False

    parsed_lastmod = parse_timestamp(sitemap_lastmod)
    parsed_synced = parse_timestamp(doc_last_synced)

    if not parsed_lastmod or not parsed_synced:
        return False

    return parsed_lastmod <= parsed_synced

