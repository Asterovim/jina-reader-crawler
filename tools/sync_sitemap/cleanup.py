"""Stale document cleanup operations for sitemap synchronization.

Handles detection and removal of documents whose URLs are no longer in the sitemap.
"""

from typing import Any

from .dify_client import DifyClient
from .messages import get_message
from .url_processing import generate_url_hash


def find_stale_documents(
    hash_to_doc: dict[str, dict], sitemap_url_hashes: set[str]
) -> list[str]:
    """Find document IDs that are no longer in the sitemap.

    Args:
        hash_to_doc: Dict mapping URL hash to document info
        sitemap_url_hashes: Set of URL hashes from current sitemap

    Returns:
        List of document IDs to delete
    """
    docs_to_delete = []
    for url_hash, doc_info in hash_to_doc.items():
        if url_hash not in sitemap_url_hashes:
            docs_to_delete.append(doc_info["id"])
    return docs_to_delete


def check_cleanup_safety(
    docs_to_delete: list[str],
    total_docs: int,
    sitemap_url_count: int,
    max_cleanup_count: int,
) -> tuple[bool, str]:
    """Check if cleanup operation is safe to proceed.

    Args:
        docs_to_delete: List of document IDs to delete
        total_docs: Total documents in knowledge base
        sitemap_url_count: Number of URLs in sitemap
        max_cleanup_count: Maximum allowed deletions

    Returns:
        Tuple of (is_safe, reason_if_not_safe)
    """
    if sitemap_url_count == 0:
        return False, "empty_sitemap"

    if total_docs < 5:
        return False, "too_few_docs"

    if not docs_to_delete:
        return True, ""

    if len(docs_to_delete) > max_cleanup_count:
        return False, "exceeds_max_count"

    if len(docs_to_delete) > total_docs * 0.1:
        return False, "exceeds_percentage"

    return True, ""


def execute_cleanup(
    dify_client: DifyClient, doc_ids: list[str]
) -> int:
    """Execute document deletion.

    Args:
        dify_client: Dify API client
        doc_ids: List of document IDs to delete

    Returns:
        Number of successfully deleted documents
    """
    deleted = 0
    for doc_id in doc_ids:
        if dify_client.delete_document(doc_id):
            deleted += 1
    return deleted


class CleanupManager:
    """Manager for stale document cleanup operations."""

    def __init__(self, dify_client: DifyClient, lang: str = "en"):
        """Initialize cleanup manager.

        Args:
            dify_client: Dify API client instance
            lang: Language code for messages
        """
        self.dify_client = dify_client
        self.lang = lang

    def cleanup_stale_documents(
        self,
        hash_to_doc: dict[str, dict],
        sitemap_url_hashes: set[str],
        max_cleanup_count: int,
        dry_run: bool,
    ) -> dict[str, Any]:
        """Perform stale document cleanup with safety checks.

        Args:
            hash_to_doc: Dict mapping URL hash to document info
            sitemap_url_hashes: Set of URL hashes from current sitemap
            max_cleanup_count: Maximum documents to delete
            dry_run: If True, simulate without deleting

        Returns:
            Result dict with: deleted, would_delete, skipped_safety, reason, dry_run
        """
        total_docs = len(hash_to_doc)
        docs_to_delete = find_stale_documents(hash_to_doc, sitemap_url_hashes)

        # Safety check
        is_safe, reason = check_cleanup_safety(
            docs_to_delete, total_docs, len(sitemap_url_hashes), max_cleanup_count
        )

        if not is_safe:
            return {
                "deleted": 0,
                "would_delete": len(docs_to_delete),
                "skipped_safety": True,
                "reason": reason,
            }

        if not docs_to_delete:
            return {"deleted": 0, "would_delete": 0, "skipped_safety": False}

        if dry_run:
            return {
                "deleted": 0,
                "would_delete": len(docs_to_delete),
                "skipped_safety": False,
                "dry_run": True,
            }

        deleted = execute_cleanup(self.dify_client, docs_to_delete)
        return {
            "deleted": deleted,
            "would_delete": len(docs_to_delete),
            "skipped_safety": False,
        }

    def get_cleanup_message(
        self, result: dict[str, Any], params: dict[str, Any]
    ) -> str:
        """Get appropriate message for cleanup result.

        Args:
            result: Cleanup result dict
            params: Tool parameters

        Returns:
            Formatted message string
        """
        if result.get("skipped_safety"):
            reason = result.get("reason", "")
            if reason == "empty_sitemap":
                return get_message(self.lang, "cleanup_skipped_empty_sitemap")
            elif reason == "too_few_docs":
                return get_message(self.lang, "cleanup_skipped_too_few_docs")
            elif reason == "exceeds_max_count":
                return get_message(
                    self.lang, "cleanup_skipped_max_limit",
                    would_delete=result.get("would_delete", 0),
                    max_count=params.get("max_cleanup_count", 20)
                )
            else:
                return get_message(
                    self.lang, "cleanup_skipped",
                    would_delete=result.get("would_delete", 0),
                    total=params.get("total_docs", 0),
                    threshold=10
                )
        elif params.get("dry_run") and result.get("would_delete", 0) > 0:
            return get_message(self.lang, "cleanup_dry_run", count=result.get("would_delete", 0))
        elif result.get("deleted", 0) > 0:
            return get_message(self.lang, "deleted_stale", count=result.get("deleted", 0))
        else:
            return get_message(self.lang, "no_stale_found")

