"""Main synchronization tool for Dify plugin.

Thin orchestrator that delegates to specialized modules.
"""

import random
import time
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from .cleanup import CleanupManager
from .dify_client import DifyClient
from .filters import UrlFilterPipeline
from .jina_client import JinaClient
from .manifest import (
    compute_incremental_diff,
    create_manifest,
    finalize_manifest,
    load_manifest,
    save_manifest_atomic,
    update_manifest_url,
    validate_manifest_params,
)
from .messages import get_message
from .params import (
    build_dify_config,
    build_jina_config,
    build_processor_config,
    extract_parameters,
    validate_required_params,
)
from .reporting import (
    format_cache_issues,
    format_failed_urls,
    format_failure_breakdown,
    format_legacy_docs,
    format_progress_message,
    format_summary,
)
from .sitemap_parser import get_urls_from_sitemap
from .sync_processor import SyncStats, UrlProcessor
from .url_processing import (
    generate_url_hash,
    normalize_url,
    parse_manual_urls,
    probe_head_lastmod,
)


class SyncSitemapTool(Tool):
    """Dify plugin tool for synchronizing sitemap content to knowledge base."""

    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        """Main invocation method for the sync sitemap tool."""
        # Extract and validate parameters
        params = extract_parameters(tool_parameters, self.runtime)

        if not validate_required_params(params):
            yield self.create_text_message(get_message(params["lang"], "error_required_fields"))
            return

        # Build the URL list (sitemap + manual), then announce
        url_lastmod_map, url_etag_map, urls = self._get_sitemap_urls(params)
        if not urls:
            yield self.create_text_message(get_message(params["lang"], "no_urls_found"))
            return

        has_sitemap = bool(params.get("sitemap_url"))
        has_manual = bool(params.get("manual_urls"))
        if has_sitemap and has_manual:
            yield self.create_text_message(get_message(
                params["lang"], "starting_sync_both", count=len(urls)
            ))
        elif has_sitemap:
            yield self.create_text_message(get_message(
                params["lang"], "starting_sync", url=params["sitemap_url"]
            ))
        else:
            yield self.create_text_message(get_message(
                params["lang"], "starting_sync_manual", count=len(urls)
            ))

        # Surface HEAD probe summary if any signals were collected for manual URLs
        if has_manual and (url_lastmod_map or url_etag_map):
            probed = sum(
                1 for u in parse_manual_urls(params["manual_urls"])
                if url_lastmod_map.get(u) or url_etag_map.get(u)
            )
            yield self.create_text_message(get_message(
                params["lang"], "head_probe_summary",
                probed=probed, total=len(urls)
            ))

        if params["dry_run"]:
            yield self.create_text_message(get_message(params["lang"], "dry_run_mode"))
        if params["use_lastmod_optimization"]:
            yield self.create_text_message(get_message(params["lang"], "lastmod_enabled"))

        # Initialize clients
        jina_client = JinaClient(build_jina_config(params))
        dify_client = DifyClient(build_dify_config(params))

        # URLs already collected above; only need the count for the message
        total_in_sitemap = len(urls)
        yield self.create_text_message(get_message(params["lang"], "found_urls", count=total_in_sitemap))

        # Apply filters
        filter_pipeline = UrlFilterPipeline(params)
        urls, filter_messages = filter_pipeline.apply_all(urls)
        for msg in filter_messages:
            yield self.create_text_message(msg)
        if not urls:
            return

        # Handle incremental sync
        incremental_mode, manifest, unchanged_urls_set = yield from self._handle_incremental_sync(
            urls, url_lastmod_map, url_etag_map, params
        )

        # Load existing documents and build cache
        existing_docs = dify_client.load_existing_documents()
        yield self.create_text_message(get_message(params["lang"], "found_existing", count=len(existing_docs)))
        yield self.create_text_message(get_message(params["lang"], "building_cache"))

        hash_to_doc, legacy_docs, collision_warnings = dify_client.build_url_hash_cache(existing_docs)
        yield self.create_text_message(get_message(params["lang"], "mapped_docs", count=len(hash_to_doc)))

        for msg in format_cache_issues(legacy_docs, collision_warnings, params["lang"]):
            yield self.create_text_message(msg)

        # Cleanup stale documents
        cleanup_count, would_clean_count = yield from self._handle_cleanup(
            dify_client, hash_to_doc, urls, params
        )

        # Process URLs
        processor_config = build_processor_config(params, url_lastmod_map)
        processor = UrlProcessor(jina_client, dify_client, processor_config)

        stats, failed_urls, failed_reasons = yield from self._process_urls(
            urls, processor, hash_to_doc, unchanged_urls_set, incremental_mode,
            manifest, url_lastmod_map, url_etag_map, params
        )
        stats["cleaned"] = cleanup_count
        stats["would_clean"] = would_clean_count if params["dry_run"] else 0

        # Final summary
        yield self.create_text_message(format_summary(stats, params))
        if failed_reasons:
            yield self.create_text_message(format_failure_breakdown(failed_reasons))
        if failed_urls:
            yield self.create_text_message(format_failed_urls(failed_urls, params["lang"]))
        if legacy_docs:
            yield self.create_text_message(format_legacy_docs(legacy_docs, params["lang"]))

        # Save manifest
        if manifest is not None and params["manifest_path"]:
            finalize_manifest(manifest, stats["processed"])
            success, error = save_manifest_atomic(manifest, params["manifest_path"])
            msg_key = "manifest_saved" if success else "manifest_save_failed"
            yield self.create_text_message(get_message(
                params["lang"], msg_key,
                path=params["manifest_path"], error=error
            ))

        # JSON output
        yield self.create_json_message(self._build_json_output(
            stats, failed_urls, failed_reasons, legacy_docs, collision_warnings,
            incremental_mode, params
        ))

    def _get_sitemap_urls(
        self, params: dict[str, Any]
    ) -> tuple[dict[str, str | None], dict[str, str | None], list[str]]:
        """Get URLs from sitemap, manual_urls, or both, with lastmod + etag data.

        For sitemap URLs, lastmod comes from the sitemap XML (no etag).
        For manual URLs, when `probe_head_for_manual_urls` is enabled (and the
        URL was not already provided by the sitemap), a HEAD request is sent to
        capture Last-Modified and ETag headers. Both feeds are merged and
        deduplicated; sitemap URLs win on collision and keep their lastmod.

        Returns:
            (url_lastmod_map, url_etag_map, urls) where:
            - url_lastmod_map: {url: iso_lastmod_or_None}
            - url_etag_map: {url: etag_or_None} (only populated by HEAD probe)
            - urls: ordered list of unique URLs
        """
        sitemap_url: str = params.get("sitemap_url", "")
        manual_text: str = params.get("manual_urls", "")
        url_lastmod_map: dict[str, str | None] = {}
        url_etag_map: dict[str, str | None] = {}
        urls: list[str] = []

        # Sitemap source (skip fetch if no URL provided)
        if sitemap_url:
            if params["use_lastmod_optimization"]:
                url_data = get_urls_from_sitemap(sitemap_url, return_lastmod=True)
                if isinstance(url_data, dict):
                    url_lastmod_map.update(url_data)
                    urls.extend(url_data.keys())
                else:
                    urls.extend(url_data)
            else:
                urls.extend(get_urls_from_sitemap(sitemap_url))

        # Manual source
        manual_urls = parse_manual_urls(manual_text)
        timeout = int(params.get("request_timeout", 60))
        probe_enabled = bool(params.get("probe_head_for_manual_urls", True))

        for url in manual_urls:
            if url in url_lastmod_map:
                continue  # sitemap version already tracked
            if url in urls:
                continue  # dedupe with already-collected sitemap URL
            urls.append(url)

            if probe_enabled:
                probe = probe_head_lastmod(url, timeout=timeout)
                if probe.get("lastmod"):
                    url_lastmod_map[url] = probe["lastmod"]
                if probe.get("etag"):
                    url_etag_map[url] = probe["etag"]

        return url_lastmod_map, url_etag_map, urls

    def _handle_incremental_sync(
        self, urls: list[str], url_lastmod_map: dict[str, str | None],
        url_etag_map: dict[str, str | None], params: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, tuple[bool, dict | None, set[str]]]:
        """Handle incremental sync logic with manifest."""
        lang = params["lang"]
        incremental_mode = False
        manifest: dict | None = None
        unchanged_urls_set: set[str] = set()

        if not params["manifest_path"]:
            return incremental_mode, manifest, unchanged_urls_set

        yield self.create_text_message(get_message(lang, "incremental_mode"))
        yield self.create_text_message(get_message(lang, "incremental_storage", path=params["manifest_path"]))

        if params["force_full_sync"]:
            yield self.create_text_message(get_message(lang, "force_full_sync"))
            manifest = create_manifest(
                params["sitemap_url"], params["dataset_id"], {
                    "url_filter": params["url_filter"],
                    "exclude_patterns": params["exclude_patterns"],
                    "exclude_urls": params["exclude_urls"],
                },
                manual_urls=params["manual_urls"],
            )
        else:
            manifest = load_manifest(params["manifest_path"])

            if manifest is None:
                yield self.create_text_message(get_message(lang, "manifest_not_found"))
                manifest = create_manifest(
                    params["sitemap_url"], params["dataset_id"], {
                        "url_filter": params["url_filter"],
                        "exclude_patterns": params["exclude_patterns"],
                        "exclude_urls": params["exclude_urls"],
                    },
                    manual_urls=params["manual_urls"],
                )
            else:
                current_params = {
                    "sitemap_url": params["sitemap_url"],
                    "manual_urls": params["manual_urls"],
                    "dataset_id": params["dataset_id"],
                    "url_filter": params["url_filter"],
                    "exclude_patterns": params["exclude_patterns"],
                    "exclude_urls": params["exclude_urls"],
                }

                if not validate_manifest_params(manifest, current_params):
                    yield self.create_text_message(get_message(lang, "manifest_filter_changed"))
                    manifest = create_manifest(
                        params["sitemap_url"], params["dataset_id"], {
                            "url_filter": params["url_filter"],
                            "exclude_patterns": params["exclude_patterns"],
                            "exclude_urls": params["exclude_urls"],
                        },
                        manual_urls=params["manual_urls"],
                    )
                else:
                    incremental_mode = True
                    last_sync = manifest.get("last_sync_completed", "unknown")
                    yield self.create_text_message(get_message(lang, "manifest_loaded", timestamp=last_sync))

                    # Build per-URL payload {url: {lastmod, etag}} for the diff.
                    # Sitemap URLs may have lastmod but no etag; manual URLs (when
                    # probed) have both.
                    current_sitemap_data: dict[str, dict[str, str | None]] = {}
                    if url_lastmod_map or url_etag_map:
                        for url in urls:
                            current_sitemap_data[url] = {
                                "lastmod": url_lastmod_map.get(url),
                                "etag": url_etag_map.get(url),
                            }
                    elif params["sitemap_url"]:
                        sitemap_with_lastmod = get_urls_from_sitemap(params["sitemap_url"], return_lastmod=True)
                        if isinstance(sitemap_with_lastmod, dict):
                            for url in urls:
                                current_sitemap_data[url] = {"lastmod": sitemap_with_lastmod.get(url), "etag": None}
                        else:
                            for url in urls:
                                current_sitemap_data[url] = {"lastmod": None, "etag": None}
                    else:
                        # Manual-only mode without probing: no signals
                        for url in urls:
                            current_sitemap_data[url] = {"lastmod": None, "etag": None}

                    incremental_diff = compute_incremental_diff(manifest, current_sitemap_data)
                    unchanged_urls_set = incremental_diff["unchanged_urls"]



                    # Build sitemap data for diff
                    current_sitemap_data: dict[str, str | None] = {}
                    if url_lastmod_map:
                        for url in urls:
                            current_sitemap_data[url] = url_lastmod_map.get(url)
                    elif params["sitemap_url"]:
                        sitemap_with_lastmod = get_urls_from_sitemap(params["sitemap_url"], return_lastmod=True)
                        if isinstance(sitemap_with_lastmod, dict):
                            for url in urls:
                                current_sitemap_data[url] = sitemap_with_lastmod.get(url)
                        else:
                            for url in urls:
                                current_sitemap_data[url] = None
                    else:
                        # Manual-only mode: no lastmod available
                        for url in urls:
                            current_sitemap_data[url] = None

                    incremental_diff = compute_incremental_diff(manifest, current_sitemap_data)
                    unchanged_urls_set = incremental_diff["unchanged_urls"]

                    yield self.create_text_message(get_message(
                        lang, "incremental_diff",
                        new=len(incremental_diff["new_urls"]),
                        modified=len(incremental_diff["modified_urls"]),
                        removed=len(incremental_diff["removed_urls"]),
                        unchanged=len(unchanged_urls_set)
                    ))

                    if len(unchanged_urls_set) > 0:
                        avg_time = 12
                        urls_to_process = len(urls) - len(unchanged_urls_set)
                        est_min = max(1, (urls_to_process * avg_time) // 60)
                        full_min = max(1, (len(urls) * avg_time) // 60)
                        yield self.create_text_message(get_message(
                            lang, "estimated_time", minutes=est_min, full_minutes=full_min
                        ))

        return incremental_mode, manifest, unchanged_urls_set

    def _handle_cleanup(
        self, dify_client: DifyClient, hash_to_doc: dict, urls: list[str], params: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, tuple[int, int]]:
        """Handle stale document cleanup using CleanupManager."""
        lang = params["lang"]

        if not params["cleanup_removed"] or not hash_to_doc:
            return 0, 0

        yield self.create_text_message(get_message(lang, "checking_stale"))
        sitemap_url_hashes = {generate_url_hash(u) for u in urls}

        cleanup_manager = CleanupManager(dify_client, lang)
        result = cleanup_manager.cleanup_stale_documents(
            hash_to_doc, sitemap_url_hashes, params["max_cleanup_count"], params["dry_run"]
        )

        # Add total_docs to params for message formatting
        params_with_total = {**params, "total_docs": len(hash_to_doc)}
        yield self.create_text_message(cleanup_manager.get_cleanup_message(result, params_with_total))

        return result.get("deleted", 0), result.get("would_delete", 0)

    def _process_urls(
        self, urls: list[str], processor: UrlProcessor, hash_to_doc: dict,
        unchanged_urls_set: set[str], incremental_mode: bool, manifest: dict | None,
        url_lastmod_map: dict, url_etag_map: dict, params: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, tuple[dict, list, dict]]:
        """Process all URLs using UrlProcessor and yield progress messages."""
        lang = params["lang"]
        stats = SyncStats()
        seen_urls: set[str] = set()
        failed_urls: list[str] = []
        failed_reasons: dict[str, int] = {}
        dify_writes_in_chunk = 0
        total_urls = len(urls)

        for i, url in enumerate(urls, 1):
            normalized_url = normalize_url(url)

            # Skip unchanged URLs in incremental mode
            if incremental_mode and normalized_url in unchanged_urls_set:
                stats.manifest_skipped += 1
                stats.processed += 1
                if i % 10 == 0 or i == total_urls:
                    yield self.create_text_message(get_message(
                        lang, "progress", current=i, total=total_urls,
                        action=get_message(lang, "incremental_skipped"),
                        title=url[:50] + "..." if len(url) > 50 else url
                    ))
                continue

            # Process URL using processor
            action, title, result, failure_reason = processor.process_url(
                url, hash_to_doc, params["skip_existing"], params["skip_duplicates"],
                seen_urls, params["dry_run"]
            )

            stats.processed += 1
            stats.update(action, result)

            if action == "failed":
                failure_reason = result.get("reason", "unknown")
                failed_reasons[failure_reason] = failed_reasons.get(failure_reason, 0) + 1
                failed_urls.append(f"{url} ({failure_reason})")

            if action in ["created", "updated"]:
                dify_writes_in_chunk += 1

            # Update manifest
            if manifest is not None and action in ["created", "updated", "would_create", "would_update", "skipped"]:
                url_lastmod = url_lastmod_map.get(url) if url_lastmod_map else None
                url_etag = url_etag_map.get(url) if url_etag_map else None
                doc_id = result.get("doc_id")
                content_hash = result.get("content_hash")
                update_manifest_url(manifest, url, url_lastmod, content_hash, doc_id, etag=url_etag)

            # Yield progress
            yield self.create_text_message(format_progress_message(
                i, total_urls, action, title, failure_reason, result, params["dry_run"], lang
            ))

            # Handle delays
            if not params["dry_run"] and dify_writes_in_chunk >= params["chunk_size"] and i < total_urls:
                yield self.create_text_message(
                    f"⏳ Batch complete ({dify_writes_in_chunk} updates). Waiting {params['chunk_cooldown']}s for Dify indexing...\n"
                )
                time.sleep(params["chunk_cooldown"])
                dify_writes_in_chunk = 0
            elif not params["dry_run"] and i < total_urls and params["max_delay"] > 0:
                delay = random.uniform(params["min_delay"], params["max_delay"])
                time.sleep(delay)

        return stats.to_dict(), failed_urls, failed_reasons

    def _build_json_output(
        self, stats: dict, failed_urls: list, failed_reasons: dict,
        legacy_docs: list, collision_warnings: list, incremental_mode: bool,
        params: dict[str, Any]
    ) -> dict[str, Any]:
        """Build JSON output for the tool response."""
        output: dict[str, Any] = {
            "status": "completed",
            "statistics": stats,
            "failed_urls": failed_urls[:50],
            "failed_reasons": failed_reasons,
            "legacy_docs": legacy_docs[:50],
            "hash_collisions": collision_warnings[:20] if collision_warnings else [],
            "incremental_mode": incremental_mode,
        }
        if params.get("manifest_path"):
            output["manifest_path"] = params["manifest_path"]
        return output

