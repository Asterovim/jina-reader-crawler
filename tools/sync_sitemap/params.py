"""Parameter extraction and configuration building for sync sitemap tool.

Handles extraction and normalization of tool parameters from user input.
"""

from typing import Any

from .manifest import get_manifest_path


def extract_parameters(tool_parameters: dict[str, Any], runtime: Any) -> dict[str, Any]:
    """Extract and normalize all tool parameters.

    Args:
        tool_parameters: Raw parameters from tool invocation
        runtime: Dify runtime object with credentials

    Returns:
        Normalized parameter dictionary
    """
    max_urls_param = tool_parameters.get("max_urls")
    dataset_id = tool_parameters.get("dataset_id", "")

    # Auto-generate manifest path if incremental sync is enabled
    enable_incremental = tool_parameters.get("enable_incremental_sync", False)
    manifest_path = get_manifest_path(dataset_id) if enable_incremental and dataset_id else ""

    return {
        # Sources (at least one required)
        "sitemap_url": tool_parameters.get("sitemap_url", "") or "",
        "manual_urls": tool_parameters.get("manual_urls", "") or "",

        # Required
        "dataset_id": dataset_id,

        # Pagination
        "max_urls": int(max_urls_param) if max_urls_param is not None else None,
        "start_from_index": max(1, int(tool_parameters.get("start_from_index", 1))),

        # Filtering
        "url_filter": tool_parameters.get("url_filter", ""),
        "exclude_patterns": tool_parameters.get("exclude_patterns", ""),
        "exclude_urls": tool_parameters.get("exclude_urls", ""),

        # Behavior
        "skip_existing": tool_parameters.get("skip_existing", False),
        "skip_duplicates": tool_parameters.get("skip_duplicates", True),
        "use_lastmod_optimization": tool_parameters.get("use_lastmod_optimization", False),
        "probe_head_for_manual_urls": tool_parameters.get("probe_head_for_manual_urls", True),

        # Cleanup
        "cleanup_removed": tool_parameters.get("cleanup_removed", False),
        "max_cleanup_count": int(tool_parameters.get("max_cleanup_count", 20)),

        # Modes
        "dry_run": tool_parameters.get("dry_run", False),
        "force_full_sync": tool_parameters.get("force_full_sync", False),

        # Jina settings
        "eu_compliance": tool_parameters.get("eu_compliance", False),
        "css_selector": tool_parameters.get("css_selector", ""),
        "no_cache": tool_parameters.get("no_cache", False),
        "wait_for_selector": tool_parameters.get("wait_for_selector", ""),
        "return_format": tool_parameters.get("return_format", "") or "",
        "streaming_mode": tool_parameters.get("streaming_mode", "disabled") == "enabled",

        # Timing
        "min_delay": float(tool_parameters.get("min_delay", 3)),
        "max_delay": float(tool_parameters.get("max_delay", 6)),
        "retry_count": int(tool_parameters.get("retry_count", 2)),
        "request_timeout": int(tool_parameters.get("request_timeout", 60)),
        "chunk_size": int(tool_parameters.get("chunk_size", 3)),
        "chunk_cooldown": int(tool_parameters.get("chunk_cooldown", 30)),

        # Incremental sync (auto-managed manifest)
        "enable_incremental_sync": enable_incremental,
        "manifest_path": manifest_path,

        # Display
        "lang": tool_parameters.get("display_language", "en"),

        # API Keys
        "jina_api_key": tool_parameters.get("jina_api_key", "") or runtime.credentials.get("jina_api_key", ""),
        "dify_api_key": runtime.credentials.get("dify_api_key", ""),
        "dify_base_url": runtime.credentials.get("dify_base_url", "https://api.dify.ai").rstrip("/"),
    }


def build_jina_config(params: dict[str, Any]) -> dict[str, Any]:
    """Build configuration dictionary for Jina client.

    Args:
        params: Normalized parameters

    Returns:
        Jina client configuration
    """
    return {
        "jina_api_key": params["jina_api_key"],
        "eu_compliance": params["eu_compliance"],
        "css_selector": params["css_selector"],
        "no_cache": params["no_cache"],
        "wait_for_selector": params["wait_for_selector"],
        "return_format": params["return_format"],
        "request_timeout": params["request_timeout"],
        "retry_count": params["retry_count"],
        "streaming_mode": params["streaming_mode"],
    }


def build_dify_config(params: dict[str, Any]) -> dict[str, Any]:
    """Build configuration dictionary for Dify client.

    Args:
        params: Normalized parameters

    Returns:
        Dify client configuration
    """
    return {
        "dify_api_key": params["dify_api_key"],
        "dify_base_url": params["dify_base_url"],
        "dataset_id": params["dataset_id"],
    }


def build_processor_config(
    params: dict[str, Any], url_lastmod_map: dict[str, str | None]
) -> dict[str, Any]:
    """Build configuration dictionary for URL processor.

    Args:
        params: Normalized parameters
        url_lastmod_map: Map of URL to lastmod timestamp

    Returns:
        Processor configuration
    """
    return {
        "use_lastmod_optimization": params["use_lastmod_optimization"],
        "url_lastmod_map": url_lastmod_map,
        "dry_run": params["dry_run"],
    }


def validate_required_params(params: dict[str, Any]) -> bool:
    """Validate that required parameters are present.

    Args:
        params: Normalized parameters

    Returns:
        True if valid, False otherwise
    """
    if not params.get("dataset_id"):
        return False
    return bool(params.get("sitemap_url") or params.get("manual_urls"))

