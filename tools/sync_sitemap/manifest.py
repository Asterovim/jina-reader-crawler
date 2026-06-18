"""Manifest management for incremental sitemap synchronization.

Handles loading, validating, and saving manifest files for tracking sync state.
"""

import json
import os
import shutil
from datetime import datetime, timezone
from typing import Any

from .url_processing import normalize_url

# Default manifest storage directory
DEFAULT_MANIFEST_DIR = "/tmp/jina_reader_kb_sync/manifests"


def get_manifest_path(dataset_id: str) -> str:
    """Generate manifest file path from dataset_id.

    Uses a predictable location that is automatically created and managed.
    Path pattern: /tmp/jina_reader_kb_sync/manifests/{dataset_id}.json

    Args:
        dataset_id: The Dify dataset/knowledge base ID

    Returns:
        Full path to the manifest file
    """
    # Allow environment variable override for advanced users
    base_dir = os.environ.get("JINA_MANIFEST_DIR", DEFAULT_MANIFEST_DIR)
    return os.path.join(base_dir, f"{dataset_id}.json")


def generate_sync_timestamp() -> str:
    """Generate current UTC timestamp in ISO 8601 format for Last Synced field."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_manifest(path: str) -> dict | None:
    """Load and validate manifest file.

    Returns:
        Parsed manifest dict if valid, None if missing/invalid/corrupted.
        Caller should fall back to full sync when None is returned.
    """
    if not path:
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        # Schema validation - require essential fields
        if manifest.get("version") != "1.0":
            return None
        if "urls" not in manifest or not isinstance(manifest["urls"], dict):
            return None
        if "sitemap_url" not in manifest or "dataset_id" not in manifest:
            return None

        return manifest

    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, PermissionError, OSError):
        return None


def validate_manifest_params(manifest: dict, current_params: dict) -> bool:
    """Check if manifest is valid for current sync parameters.

    Returns True if manifest can be used for incremental sync.
    Returns False if full sync is required (params changed).
    """
    if not manifest:
        return False

    if manifest.get("sitemap_url") != current_params.get("sitemap_url"):
        return False
    if manifest.get("manual_urls", "") != current_params.get("manual_urls", ""):
        return False
    if manifest.get("dataset_id") != current_params.get("dataset_id"):
        return False

    stored_filters = manifest.get("filter_params", {})
    if stored_filters.get("url_filter") != current_params.get("url_filter", ""):
        return False
    if stored_filters.get("exclude_patterns") != current_params.get("exclude_patterns", ""):
        return False
    if stored_filters.get("exclude_urls") != current_params.get("exclude_urls", ""):
        return False

    return True


def save_manifest_atomic(manifest: dict, path: str) -> tuple[bool, str]:
    """Save manifest with atomic write and backup.

    Uses write-to-temp-then-rename pattern for crash safety.

    Returns:
        (success: bool, error_message: str)
    """
    if not path:
        return False, "No manifest path specified"

    temp_path = path + ".tmp"
    backup_path = path + ".bak"

    try:
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        if os.path.exists(path):
            shutil.copy2(path, backup_path)

        os.replace(temp_path, path)
        return True, ""

    except PermissionError:
        return False, "Permission denied"
    except OSError as e:
        return False, str(e)[:50]
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def create_manifest(
    sitemap_url: str, dataset_id: str, filter_params: dict,
    manual_urls: str = ""
) -> dict:
    """Create a new empty manifest structure."""
    return {
        "version": "1.0",
        "sitemap_url": sitemap_url,
        "manual_urls": manual_urls,
        "dataset_id": dataset_id,
        "last_sync_completed": None,
        "sync_status": "in_progress",
        "urls_processed": 0,
        "filter_params": {
            "url_filter": filter_params.get("url_filter", ""),
            "exclude_patterns": filter_params.get("exclude_patterns", ""),
            "exclude_urls": filter_params.get("exclude_urls", ""),
        },
        "urls": {}
    }


def update_manifest_url(
    manifest: dict, url: str, lastmod: str | None,
    content_hash: str | None, doc_id: str | None
) -> None:
    """Update or add a URL entry in the manifest."""
    normalized = normalize_url(url)
    manifest["urls"][normalized] = {
        "url": url,
        "lastmod": lastmod,
        "content_hash": content_hash,
        "doc_id": doc_id,
        "synced_at": generate_sync_timestamp()
    }


def remove_manifest_url(manifest: dict, url: str) -> None:
    """Remove a URL entry from the manifest."""
    normalized = normalize_url(url)
    manifest["urls"].pop(normalized, None)


def finalize_manifest(manifest: dict, urls_processed: int) -> None:
    """Mark manifest as complete after successful sync."""
    manifest["last_sync_completed"] = generate_sync_timestamp()
    manifest["sync_status"] = "completed"
    manifest["urls_processed"] = urls_processed


def compute_incremental_diff(
    manifest: dict, current_sitemap: dict[str, str | None]
) -> dict:
    """Compute diff between manifest and current sitemap.

    Args:
        manifest: Loaded manifest from previous sync
        current_sitemap: Current sitemap data {url: lastmod}

    Returns:
        dict with:
            - new_urls: set of normalized URLs (in sitemap, not in manifest)
            - modified_urls: set of normalized URLs (lastmod changed)
            - removed_urls: set of normalized URLs (in manifest, not in sitemap)
            - unchanged_urls: set of normalized URLs (identical lastmod)
            - url_data: dict mapping normalized URL to {url, lastmod}
    """
    manifest_urls = set(manifest.get("urls", {}).keys())

    # Normalize current sitemap URLs
    url_data: dict[str, dict] = {}
    for url, lastmod in current_sitemap.items():
        normalized = normalize_url(url)
        url_data[normalized] = {"url": url, "lastmod": lastmod}

    current_urls = set(url_data.keys())

    # Set operations for diff
    new_urls = current_urls - manifest_urls
    removed_urls = manifest_urls - current_urls
    common_urls = current_urls & manifest_urls

    # Check common URLs for modifications (lastmod changed)
    modified_urls: set[str] = set()
    unchanged_urls: set[str] = set()

    for normalized in common_urls:
        current_lastmod = url_data[normalized].get("lastmod")
        manifest_entry = manifest["urls"].get(normalized, {})
        manifest_lastmod = manifest_entry.get("lastmod")

        if current_lastmod != manifest_lastmod:
            modified_urls.add(normalized)
        else:
            unchanged_urls.add(normalized)

    return {
        "new_urls": new_urls,
        "modified_urls": modified_urls,
        "removed_urls": removed_urls,
        "unchanged_urls": unchanged_urls,
        "url_data": url_data
    }

