"""Sync Sitemap Tool - Dify plugin for synchronizing sitemap content to knowledge base.

This package provides modular components for:
- Sitemap XML parsing and URL extraction
- Content fetching via Jina Reader API
- Document management via Dify Knowledge Base API
- Incremental sync with manifest-based change detection
- URL normalization and hash-based document matching
"""

from .tool import SyncSitemapTool

__all__ = ["SyncSitemapTool"]

