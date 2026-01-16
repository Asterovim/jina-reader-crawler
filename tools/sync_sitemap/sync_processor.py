"""URL synchronization processor for sitemap sync operations.

Handles individual URL processing, content fetching, and document creation/updates.
"""

import hashlib
from typing import Any

from .content import build_document_content, is_content_unchanged_by_lastmod
from .dify_client import DifyClient
from .jina_client import JinaClient
from .url_processing import generate_doc_name, generate_url_hash, normalize_url


class SyncStats:
    """Statistics tracker for sync operations."""

    def __init__(self):
        """Initialize all counters to zero."""
        self.processed = 0
        self.created = 0
        self.updated = 0
        self.skipped = 0
        self.unchanged = 0
        self.failed = 0
        self.duplicates = 0
        self.cleaned = 0
        self.would_clean = 0
        self.lastmod_skipped = 0
        self.manifest_skipped = 0

    def update(self, action: str, result: dict) -> None:
        """Update statistics based on action result."""
        if action == "duplicate_skipped":
            self.duplicates += 1
        elif action == "would_create":
            self.created += 1
        elif action == "would_update":
            self.updated += 1
        elif action == "skipped" and result.get("reason") == "unchanged":
            self.unchanged += 1
        elif action == "skipped" and result.get("reason") == "lastmod_unchanged":
            self.lastmod_skipped += 1
        elif action == "created":
            self.created += 1
        elif action == "updated":
            self.updated += 1
        elif action == "skipped":
            self.skipped += 1
        elif action == "failed":
            self.failed += 1

    def to_dict(self) -> dict[str, int]:
        """Convert stats to dictionary."""
        return {
            "processed": self.processed,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "unchanged": self.unchanged,
            "failed": self.failed,
            "duplicates": self.duplicates,
            "cleaned": self.cleaned,
            "would_clean": self.would_clean,
            "lastmod_skipped": self.lastmod_skipped,
            "manifest_skipped": self.manifest_skipped,
        }


class UrlProcessor:
    """Processor for individual URL sync operations."""

    def __init__(
        self,
        jina_client: JinaClient,
        dify_client: DifyClient,
        config: dict[str, Any],
    ):
        """Initialize URL processor.

        Args:
            jina_client: Jina Reader API client
            dify_client: Dify Knowledge Base API client
            config: Configuration dict with lastmod settings
        """
        self.jina_client = jina_client
        self.dify_client = dify_client
        self.config = config

    def process_url(
        self,
        url: str,
        hash_to_doc: dict[str, dict],
        skip_existing: bool,
        skip_duplicates: bool,
        seen_urls: set[str],
        dry_run: bool,
    ) -> tuple[str, str, dict[str, Any], str]:
        """Process a single URL and return the result.

        Args:
            url: URL to process
            hash_to_doc: Existing document cache
            skip_existing: If True, skip existing documents
            skip_duplicates: If True, skip duplicate URLs
            seen_urls: Set of already processed URLs (modified in place)
            dry_run: If True, simulate without making changes

        Returns:
            Tuple of (action, title, result_dict, failure_reason)
        """
        try:
            url_hash = generate_url_hash(url)
            normalized_url = normalize_url(url)

            # Duplicate check
            if skip_duplicates and normalized_url in seen_urls:
                return "duplicate_skipped", "", {"action": "duplicate_skipped"}, ""
            seen_urls.add(normalized_url)

            existing_doc = hash_to_doc.get(url_hash)

            # Lastmod optimization check
            if self.config.get("use_lastmod_optimization") and existing_doc:
                result = self._check_lastmod_skip(url, existing_doc)
                if result:
                    return result

            # Fetch content from Jina
            content_data = self.jina_client.fetch(url)
            if not content_data:
                return "failed", "", {"action": "failed", "reason": "jina_null_response"}, "jina_null_response"

            if content_data.get("_error"):
                reason = f"jina_{content_data.get('_error')}"
                return "failed", "", {"action": "failed", "reason": reason}, reason

            if not content_data.get("content"):
                return "failed", content_data.get("title", ""), {"action": "failed", "reason": "jina_empty_content"}, "jina_empty_content"

            title = content_data.get("title", "")
            doc_name = generate_doc_name(url, title)

            # Skip existing if requested
            if existing_doc and skip_existing:
                return "skipped", title, {"action": "skipped"}, ""

            # Check content change for existing docs
            if existing_doc:
                unchanged = self._check_content_unchanged(existing_doc, content_data, url)
                if unchanged:
                    return "skipped", title, {"action": "skipped", "reason": "unchanged"}, ""

            # Dry run - simulate
            if dry_run:
                action = "would_update" if existing_doc else "would_create"
                return action, title, {"action": action}, ""

            # Execute create/update
            return self._execute_sync(existing_doc, doc_name, content_data, url, title)

        except Exception as e:
            reason = f"exception:{str(e)[:80]}"
            return "failed", "", {"action": "failed", "reason": reason}, reason

    def _check_lastmod_skip(
        self, url: str, existing_doc: dict
    ) -> tuple[str, str, dict, str] | None:
        """Check if URL can be skipped based on lastmod optimization.

        Returns:
            Result tuple if should skip, None otherwise
        """
        url_lastmod_map = self.config.get("url_lastmod_map", {})
        sitemap_lastmod = url_lastmod_map.get(url)

        if not sitemap_lastmod:
            return None

        doc_last_synced = self.dify_client.extract_last_synced(existing_doc["id"])
        if doc_last_synced and is_content_unchanged_by_lastmod(sitemap_lastmod, doc_last_synced):
            title = existing_doc.get("name", "").split(" (")[0] if existing_doc.get("name") else ""
            return "skipped", title, {"action": "skipped", "reason": "lastmod_unchanged"}, ""

        return None

    def _check_content_unchanged(
        self, existing_doc: dict, content_data: dict, url: str
    ) -> bool:
        """Check if content is unchanged compared to existing document.

        Returns:
            True if content is unchanged, False otherwise
        """
        existing_hash = self.dify_client.get_existing_content_hash(existing_doc["id"])
        if not existing_hash:
            return False

        content = build_document_content(content_data, url)
        new_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        return existing_hash == new_hash

    def _execute_sync(
        self, existing_doc: dict | None, doc_name: str, content_data: dict, url: str, title: str
    ) -> tuple[str, str, dict[str, Any], str]:
        """Execute the actual create/update operation.

        Returns:
            Result tuple (action, title, result_dict, failure_reason)
        """
        content = build_document_content(content_data, url)

        if existing_doc:
            result = self.dify_client.update_document(existing_doc["id"], doc_name, content)
            if result.get("success"):
                return "updated", title, {"action": "updated", "doc_id": existing_doc["id"]}, ""
            reason = f"dify_update:{result.get('status', 0)}:{result.get('error', 'unknown')[:60]}"
            return "failed", title, {"action": "failed", "reason": reason}, reason
        else:
            result = self.dify_client.create_document(doc_name, content)
            if result.get("success"):
                return "created", title, {"action": "created", "doc_id": result.get("doc_id")}, ""
            reason = f"dify_create:{result.get('status', 0)}:{result.get('error', 'unknown')[:60]}"
            return "failed", title, {"action": "failed", "reason": reason}, reason

