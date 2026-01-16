"""URL filtering and exclusion logic for sitemap synchronization.

Handles inclusive regex filters, pattern exclusions, and URL list processing.
"""

import re
from typing import Any

from .messages import get_message
from .url_processing import normalize_url


def apply_url_filter(urls: list[str], pattern: str) -> tuple[list[str], str | None]:
    """Apply inclusive regex filter to URLs.

    Args:
        urls: List of URLs to filter
        pattern: Regex pattern string

    Returns:
        Tuple of (filtered_urls, error_message or None)
    """
    if not pattern:
        return urls, None

    try:
        compiled = re.compile(pattern)
        return [u for u in urls if compiled.search(u)], None
    except re.error as e:
        return urls, str(e)


def apply_exclusion_patterns(urls: list[str], patterns_text: str) -> tuple[list[str], int]:
    """Apply exclusion patterns to URLs.

    Args:
        urls: List of URLs to filter
        patterns_text: Newline-separated patterns to exclude

    Returns:
        Tuple of (filtered_urls, count_excluded)
    """
    if not patterns_text:
        return urls, 0

    patterns = [p.strip().lower() for p in patterns_text.strip().split("\n") if p.strip()]
    if not patterns:
        return urls, 0

    before_count = len(urls)
    filtered = [u for u in urls if not any(p in u.lower() for p in patterns)]
    return filtered, before_count - len(filtered)


def apply_url_exclusions(urls: list[str], exclusions_text: str) -> tuple[list[str], int]:
    """Apply specific URL exclusions.

    Args:
        urls: List of URLs to filter
        exclusions_text: Newline-separated URLs to exclude

    Returns:
        Tuple of (filtered_urls, count_excluded)
    """
    if not exclusions_text:
        return urls, 0

    excluded_list = [u.strip() for u in exclusions_text.strip().split("\n") if u.strip()]
    if not excluded_list:
        return urls, 0

    excluded_normalized = {normalize_url(u) for u in excluded_list}
    before_count = len(urls)
    filtered = [u for u in urls if normalize_url(u) not in excluded_normalized]
    return filtered, before_count - len(filtered)


def apply_pagination(
    urls: list[str], start_from_index: int, max_urls: int | None
) -> tuple[list[str], dict[str, Any]]:
    """Apply pagination (start index and max limit) to URLs.

    Args:
        urls: List of URLs
        start_from_index: 1-based start index
        max_urls: Maximum URLs to return (None for no limit)

    Returns:
        Tuple of (paginated_urls, info_dict)
        info_dict contains: start_applied, max_applied, start_exceeds, original_count
    """
    info: dict[str, Any] = {
        "start_applied": False,
        "max_applied": False,
        "start_exceeds": False,
        "original_count": len(urls),
    }

    # Apply start_from_index
    if start_from_index > 1:
        if start_from_index > len(urls):
            info["start_exceeds"] = True
            return [], info
        urls = urls[start_from_index - 1:]
        info["start_applied"] = True

    # Apply max_urls limit
    if max_urls is not None and len(urls) > max_urls:
        urls = urls[:max_urls]
        info["max_applied"] = True

    return urls, info


class UrlFilterPipeline:
    """Pipeline for applying all URL filters in sequence."""

    def __init__(self, params: dict[str, Any]):
        """Initialize with filter parameters."""
        self.url_filter = params.get("url_filter", "")
        self.exclude_patterns = params.get("exclude_patterns", "")
        self.exclude_urls = params.get("exclude_urls", "")
        self.start_from_index = params.get("start_from_index", 1)
        self.max_urls = params.get("max_urls")
        self.lang = params.get("lang", "en")

    def apply_all(self, urls: list[str]) -> tuple[list[str], list[str]]:
        """Apply all filters and return filtered URLs with messages.

        Returns:
            Tuple of (filtered_urls, list_of_status_messages)
        """
        messages: list[str] = []

        # Regex filter
        urls, filter_error = apply_url_filter(urls, self.url_filter)
        if filter_error:
            messages.append(get_message(self.lang, "invalid_filter", error=filter_error))
        elif self.url_filter:
            messages.append(get_message(self.lang, "after_filtering", count=len(urls)))

        # Exclusion patterns
        urls, excluded_count = apply_exclusion_patterns(urls, self.exclude_patterns)
        if excluded_count > 0:
            messages.append(get_message(self.lang, "excluded_patterns", count=excluded_count))

        # Specific URL exclusions
        urls, excluded_count = apply_url_exclusions(urls, self.exclude_urls)
        if excluded_count > 0:
            messages.append(get_message(self.lang, "excluded_specific", count=excluded_count))

        # Pagination
        urls, pagination_info = apply_pagination(urls, self.start_from_index, self.max_urls)

        if pagination_info["start_exceeds"]:
            messages.append(get_message(
                self.lang, "start_index_exceeds",
                index=self.start_from_index, count=pagination_info["original_count"]
            ))
        elif pagination_info["start_applied"]:
            messages.append(get_message(
                self.lang, "resuming_from",
                index=self.start_from_index, count=len(urls)
            ))

        if pagination_info["max_applied"]:
            messages.append(get_message(self.lang, "limited_to", count=self.max_urls))

        return urls, messages

