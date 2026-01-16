"""Progress reporting and summary output for sitemap synchronization.

Handles progress messages, final summaries, and failure reporting.
"""

from typing import Any

from .messages import get_message
from .url_processing import get_url_path, truncate_title


def get_action_display(
    action: str, result: dict, dry_run: bool, lang: str
) -> tuple[str, str]:
    """Get status icon and action key for display.

    Args:
        action: Action string (created, updated, skipped, failed, etc.)
        result: Result dict with reason info
        dry_run: Whether in dry run mode
        lang: Language code

    Returns:
        Tuple of (status_icon, action_key)
    """
    if dry_run and action in ["would_create", "would_update"]:
        icon = "🔍"
        key = "status_would_create" if action == "would_create" else "status_would_update"
        return icon, key

    is_unchanged = action == "skipped" and result.get("reason") == "unchanged"
    is_lastmod = action == "skipped" and result.get("reason") == "lastmod_unchanged"

    if action == "created":
        return "✅", "status_created"
    elif action == "updated":
        return "🔄", "status_updated"
    elif is_unchanged:
        return "✓", "status_unchanged"
    elif is_lastmod:
        return "⚡", "lastmod_skipped"
    elif action in ["skipped", "duplicate_skipped"]:
        return "⏭️", "status_skipped"
    else:
        return "❌", "status_failed"


def format_progress_message(
    index: int,
    total: int,
    action: str,
    title: str,
    failure_reason: str,
    result: dict,
    dry_run: bool,
    lang: str,
) -> str:
    """Format a progress message for a single URL.

    Args:
        index: Current URL index (1-based)
        total: Total URL count
        action: Action performed
        title: Document title
        failure_reason: Reason for failure (if any)
        result: Result dict
        dry_run: Whether in dry run mode
        lang: Language code

    Returns:
        Formatted progress message string
    """
    status_icon, action_key = get_action_display(action, result, dry_run, lang)
    action_word = get_message(lang, action_key)
    display_name = truncate_title(title) if title else get_url_path(result.get("url", ""))
    fail_suffix = f" [{failure_reason}]" if action == "failed" and failure_reason else ""
    return f"{status_icon} [{index}/{total}] {action_word}: {display_name}{fail_suffix}\n"


def format_summary(stats: dict[str, int], params: dict[str, Any]) -> str:
    """Format the final sync summary message.

    Args:
        stats: Statistics dictionary
        params: Tool parameters including lang and dry_run

    Returns:
        Formatted summary message string
    """
    lang = params.get("lang", "en")
    dry_run = params.get("dry_run", False)

    lastmod_summary = ""
    if stats.get("lastmod_skipped", 0) > 0:
        lastmod_summary = get_message(lang, "summary_lastmod_skipped", count=stats["lastmod_skipped"])

    manifest_summary = ""
    if stats.get("manifest_skipped", 0) > 0:
        manifest_summary = get_message(lang, "summary_manifest_skipped", count=stats["manifest_skipped"])

    if dry_run:
        return (
            get_message(lang, "dry_run_completed")
            + get_message(lang, "summary_processed", processed=stats["processed"], total=stats["processed"])
            + get_message(lang, "summary_would_create", count=stats["created"])
            + get_message(lang, "summary_would_update", count=stats["updated"])
            + get_message(lang, "summary_skipped", count=stats["skipped"])
            + get_message(lang, "summary_unchanged", count=stats["unchanged"])
            + lastmod_summary + manifest_summary
            + get_message(lang, "summary_duplicates", count=stats["duplicates"])
            + get_message(lang, "summary_would_clean", count=stats.get("would_clean", 0))
            + get_message(lang, "summary_failed", count=stats["failed"])
        )
    else:
        return (
            get_message(lang, "sync_completed")
            + get_message(lang, "summary_processed", processed=stats["processed"], total=stats["processed"])
            + get_message(lang, "summary_created", count=stats["created"])
            + get_message(lang, "summary_updated", count=stats["updated"])
            + get_message(lang, "summary_skipped", count=stats["skipped"])
            + get_message(lang, "summary_unchanged", count=stats["unchanged"])
            + lastmod_summary + manifest_summary
            + get_message(lang, "summary_duplicates", count=stats["duplicates"])
            + get_message(lang, "summary_cleaned", count=stats.get("cleaned", 0))
            + get_message(lang, "summary_failed", count=stats["failed"])
        )


def format_failure_breakdown(failed_reasons: dict[str, int]) -> str:
    """Format failure breakdown message.

    Args:
        failed_reasons: Dict mapping reason to count

    Returns:
        Formatted breakdown string
    """
    if not failed_reasons:
        return ""

    lines = ["\n📊 Failure breakdown:"]
    for reason, count in sorted(failed_reasons.items(), key=lambda x: -x[1]):
        lines.append(f"  • {reason}: {count}")
    return "\n".join(lines) + "\n"


def format_failed_urls(failed_urls: list[str], lang: str) -> str:
    """Format failed URLs list message.

    Args:
        failed_urls: List of failed URL descriptions
        lang: Language code

    Returns:
        Formatted message string
    """
    if not failed_urls:
        return ""

    header = get_message(lang, "failed_urls_header")
    url_list = "\n".join(failed_urls[:10])
    suffix = "\n..." if len(failed_urls) > 10 else ""
    return header + url_list + suffix + "\n"


def format_legacy_docs(legacy_docs: list[str], lang: str) -> str:
    """Format legacy documents message.

    Args:
        legacy_docs: List of document names needing manual review
        lang: Language code

    Returns:
        Formatted message string
    """
    if not legacy_docs:
        return ""

    header = get_message(lang, "manual_review_header", count=len(legacy_docs))
    doc_list = "\n".join([f"  • {name}" for name in legacy_docs[:10]])
    suffix = "\n  ..." if len(legacy_docs) > 10 else ""
    return header + doc_list + suffix + "\n"


def format_cache_issues(
    legacy_docs: list[str], collision_warnings: list[dict], lang: str
) -> list[str]:
    """Format cache issue messages.

    Args:
        legacy_docs: List of documents with unextractable URLs
        collision_warnings: List of hash collision warnings
        lang: Language code

    Returns:
        List of formatted message strings
    """
    messages: list[str] = []

    if legacy_docs:
        messages.append(get_message(lang, "unextractable_warning", count=len(legacy_docs)))

    if collision_warnings:
        msg = f"⚠️ Detected {len(collision_warnings)} hash collision(s) - duplicate documents may exist:\n"
        for cw in collision_warnings[:5]:
            msg += f"  • Hash [{cw['hash']}]: '{cw['doc1'][:40]}...' vs '{cw['doc2'][:40]}...'\n"
        if len(collision_warnings) > 5:
            msg += f"  ... and {len(collision_warnings) - 5} more\n"
        messages.append(msg)

    return messages

