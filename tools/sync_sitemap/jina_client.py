"""Jina Reader API client for fetching web page content.

Handles content fetching with retry logic, SSE streaming, and cached snapshot detection.
"""

import json
import time
from typing import Any

import requests


class JinaClient:
    """Client for Jina Reader API with streaming and retry support."""

    def __init__(self, config: dict[str, Any]):
        """Initialize the Jina client with configuration.

        Args:
            config: Dictionary containing:
                - jina_api_key: Optional API key for authentication
                - eu_compliance: If True, use EU endpoint
                - css_selector: CSS selector for content removal
                - no_cache: If True, bypass cache
                - wait_for_selector: CSS selector to wait for
                - return_format: Response format (markdown, html, text, etc.)
                - request_timeout: Timeout in seconds
                - retry_count: Number of retries
                - streaming_mode: If True, use SSE streaming
        """
        self.config = config

    def fetch(self, url: str) -> dict | None:
        """Fetch URL content using Jina Reader API with full retry logic.

        Returns dict with content on success, or dict with error info on failure.
        """
        cfg = self.config
        jina_url = "https://eu-r-beta.jina.ai/" if cfg.get("eu_compliance") else "https://r.jina.ai/"

        # Get return_format - only use if explicitly set and valid
        return_format = cfg.get("return_format", "")
        valid_formats = ("markdown", "html", "text", "screenshot", "pageshot")

        # Check if streaming mode is enabled
        streaming_mode = cfg.get("streaming_mode", False)

        # Set Accept header based on streaming mode
        accept_header = "text/event-stream" if streaming_mode else "application/json"

        # Build headers
        headers = {
            "Accept": accept_header,
            "Content-Type": "application/json",
            "X-Timeout": str(cfg.get("request_timeout", 60)),
            "X-Retain-Images": "none",
            "X-Engine": "browser"
        }

        # Only add X-Return-Format header if a valid format is explicitly specified
        if return_format and return_format in valid_formats:
            headers["X-Return-Format"] = return_format

        if cfg.get("jina_api_key"):
            headers["Authorization"] = f"Bearer {cfg['jina_api_key']}"
        if cfg.get("css_selector"):
            headers["X-Remove-Selector"] = cfg["css_selector"]
        if cfg.get("no_cache"):
            headers["X-No-Cache"] = "true"
        if cfg.get("wait_for_selector"):
            headers["X-Wait-For-Selector"] = cfg["wait_for_selector"]

        retry_count = cfg.get("retry_count", 2)
        timeout = cfg.get("request_timeout", 60) + (60 if streaming_mode else 0)
        last_error = ""

        for attempt in range(retry_count + 1):
            try:
                response = requests.post(jina_url, headers=headers, json={"url": url}, timeout=timeout)

                if response.status_code >= 400:
                    last_error = f"http_{response.status_code}"
                    if attempt < retry_count:
                        time.sleep(1)
                        continue
                    return {"_error": last_error, "_error_detail": f"HTTP {response.status_code}"}

                if streaming_mode:
                    response.encoding = 'utf-8'
                    data = self._parse_sse_response(response.text)
                    if not data:
                        last_error = "sse_parse_failed"
                        if attempt < retry_count:
                            time.sleep(1)
                            continue
                        return {"_error": last_error, "_error_detail": "SSE response parsing failed"}
                    content_data = data
                else:
                    try:
                        data = response.json()
                    except Exception as e:
                        last_error = "json_parse_failed"
                        if attempt < retry_count:
                            time.sleep(1)
                            continue
                        return {"_error": last_error, "_error_detail": str(e)[:50]}

                    # Check for cached snapshot warning and retry with X-No-Cache
                    warning = data.get("warning", "")
                    if "cached snapshot" in warning.lower() and not cfg.get("no_cache"):
                        retry_headers = headers.copy()
                        retry_headers["X-No-Cache"] = "true"
                        try:
                            response = requests.post(jina_url, headers=retry_headers, json={"url": url}, timeout=timeout)
                            data = response.json()
                        except Exception:
                            pass

                    content_data = data.get("data", {})

                return {
                    "title": content_data.get("title", ""),
                    "content": content_data.get("content", ""),
                    "url": content_data.get("url", url),
                    "description": content_data.get("description", "")
                }

            except requests.exceptions.Timeout:
                last_error = "timeout"
                if attempt < retry_count:
                    time.sleep(1)
                    continue
                return {"_error": last_error, "_error_detail": f"Timeout after {timeout}s"}
            except requests.exceptions.ConnectionError as e:
                last_error = "connection_error"
                if attempt < retry_count:
                    time.sleep(1)
                    continue
                return {"_error": last_error, "_error_detail": str(e)[:50]}
            except Exception as e:
                last_error = "unknown_error"
                if attempt < retry_count:
                    time.sleep(1)
                    continue
                return {"_error": last_error, "_error_detail": str(e)[:50]}

        return {"_error": last_error or "max_retries", "_error_detail": "Max retries exceeded"}

    def _parse_sse_response(self, response_text: str) -> dict | None:
        """Parse SSE (Server-Sent Events) response and return the last chunk.

        Jina Reader's streaming mode returns progressive chunks where each
        chunk contains more complete information. The last chunk is the final result.
        """
        if not response_text:
            return None

        last_data = None
        lines = response_text.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('data:'):
                json_str = line[5:].strip()
                if not json_str:
                    continue
                try:
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict):
                        last_data = parsed
                except json.JSONDecodeError:
                    continue

        return last_data

