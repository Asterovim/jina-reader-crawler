"""Dify API client for knowledge base document operations.

Handles document CRUD, segment fetching, and content hashing for change detection.
"""

import hashlib
import re
import time
from typing import Any

import requests

from .url_processing import extract_url_hash_from_name


class DifyClient:
    """Client for Dify Knowledge Base API with retry support."""

    def __init__(self, config: dict[str, Any]):
        """Initialize the Dify client with configuration.

        Args:
            config: Dictionary containing:
                - dify_api_key: API key for authentication
                - dify_base_url: Base URL for Dify API
                - dataset_id: Knowledge base dataset ID
        """
        self.config = config

    @property
    def headers(self) -> dict[str, str]:
        """Get authorization headers for API requests."""
        return {
            "Authorization": f"Bearer {self.config['dify_api_key']}",
            "Content-Type": "application/json; charset=utf-8"
        }

    def load_existing_documents(self) -> dict[str, dict]:
        """Load all existing documents from the knowledge base.

        Returns:
            Dict mapping document name to {id, name} info
        """
        documents = {}
        page = 1

        while True:
            try:
                response = requests.get(
                    f"{self.config['dify_base_url']}/v1/datasets/{self.config['dataset_id']}/documents",
                    headers=self.headers,
                    params={"page": page, "limit": 100},
                    timeout=30
                )
                if response.status_code != 200:
                    break

                data = response.json()
                for doc in data.get("data", []):
                    documents[doc.get("name", "")] = {
                        "id": doc.get("id"),
                        "name": doc.get("name", "")
                    }

                if not data.get("has_more", False):
                    break
                page += 1
            except Exception:
                break

        return documents

    def build_url_hash_cache(self, existing_docs: dict) -> tuple[dict, list, list]:
        """Build hash → doc cache from document names (no API calls needed).

        Document names include 12-char URL hash: "Title (domain) [abc123def456]"

        Returns:
            tuple: (hash_to_doc, legacy_docs, collision_warnings)
        """
        hash_to_doc = {}
        legacy_docs = []
        collision_warnings = []

        for doc_name, doc_info in existing_docs.items():
            url_hash = extract_url_hash_from_name(doc_name)

            if not url_hash:
                legacy_docs.append(doc_name)
                continue

            # Collision detection: same hash, different names
            if url_hash in hash_to_doc:
                existing_name = hash_to_doc[url_hash]["name"]
                if existing_name != doc_name:
                    collision_warnings.append({
                        "hash": url_hash,
                        "doc1": existing_name,
                        "doc2": doc_name,
                    })
                    continue  # Keep first, skip duplicate

            hash_to_doc[url_hash] = {"id": doc_info["id"], "name": doc_name}

        return hash_to_doc, legacy_docs, collision_warnings

    def create_document(self, doc_name: str, content: str) -> dict:
        """Create document in Dify Knowledge Base with retry logic.

        Args:
            doc_name: Name for the document
            content: Full document content string

        Returns:
            dict with 'success' bool, 'doc_id' if successful, 'error' details if failed
        """
        data = {
            "name": doc_name,
            "text": content,
            "indexing_technique": "high_quality",
            "doc_form": "hierarchical_model",
            "process_rule": {
                "mode": "hierarchical",
                "rules": {
                    "pre_processing_rules": [
                        {"id": "remove_extra_spaces", "enabled": True},
                        {"id": "remove_urls_emails", "enabled": False}
                    ],
                    "segmentation": {"separator": "\\n", "max_tokens": 1024},
                    "parent_mode": "full-doc",
                    "subchunk_segmentation": {
                        "separator": "\\n", "max_tokens": 512, "chunk_overlap": 50
                    }
                }
            }
        }

        return self._execute_with_retry(
            "POST",
            f"/v1/datasets/{self.config['dataset_id']}/document/create-by-text",
            data,
            extract_doc_id=True
        )

    def update_document(self, doc_id: str, doc_name: str, content: str) -> dict:
        """Update existing document using update_by_text API (atomic operation).

        Args:
            doc_id: ID of the document to update
            doc_name: New name for the document
            content: Full document content string

        Returns:
            dict with 'success' bool and 'error' details if failed
        """
        data = {
            "name": doc_name,
            "text": content,
            "doc_form": "hierarchical_model"
        }

        return self._execute_with_retry(
            "POST",
            f"/v1/datasets/{self.config['dataset_id']}/documents/{doc_id}/update_by_text",
            data
        )

    def delete_document(self, doc_id: str) -> bool:
        """Delete document from Dify Knowledge Base with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.delete(
                    f"{self.config['dify_base_url']}/v1/datasets/{self.config['dataset_id']}/documents/{doc_id}",
                    headers=self.headers,
                    timeout=30
                )
                if response.status_code in [200, 204]:
                    return True
                if response.status_code in [429, 500, 502, 503, 504] and attempt < max_retries - 1:
                    time.sleep(1.5)
                    continue
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt < max_retries - 1:
                    time.sleep(1.5)
                    continue
            except Exception:
                pass
            break
        return False

    def get_existing_content_hash(self, doc_id: str) -> str | None:
        """Fetch existing document content and compute hash for comparison.

        Returns MD5 hash of the document's text content, or None if fetch fails.
        """
        try:
            response = requests.get(
                f"{self.config['dify_base_url']}/v1/datasets/{self.config['dataset_id']}/documents/{doc_id}/segments",
                headers=self.headers,
                params={"limit": 100},
                timeout=30
            )
            if response.status_code != 200:
                return None

            data = response.json()
            segments = data.get("data", [])
            if not segments:
                return None

            full_content = "\n".join(seg.get("content", "") for seg in segments)
            return hashlib.md5(full_content.encode('utf-8')).hexdigest()
        except Exception:
            return None

    def extract_last_synced(self, doc_id: str) -> str | None:
        """Extract Last Synced timestamp from document content.

        Fetches the first segment and parses the **Last Synced:** field.
        Returns None if not found or on any error.
        """
        try:
            response = requests.get(
                f"{self.config['dify_base_url']}/v1/datasets/{self.config['dataset_id']}/documents/{doc_id}/segments",
                headers=self.headers,
                params={"limit": 1},
                timeout=30
            )
            if response.status_code != 200:
                return None

            data = response.json()
            segments = data.get("data", [])
            if not segments:
                return None

            content = segments[0].get("content", "")
            match = re.search(
                r'\*\*Last Synced:\*\*\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\s\n\*]*)',
                content
            )
            if match:
                return match.group(1).strip()
        except Exception:
            pass
        return None

    def _execute_with_retry(
        self, method: str, path: str, data: dict, extract_doc_id: bool = False
    ) -> dict:
        """Execute API request with retry logic.

        Args:
            method: HTTP method (POST, etc.)
            path: API path
            data: Request payload
            extract_doc_id: If True, extract doc_id from response

        Returns:
            dict with 'success' bool and additional info
        """
        last_error = "unknown"
        last_status = 0
        max_retries = 3

        for attempt in range(max_retries):
            try:
                url = f"{self.config['dify_base_url']}{path}"
                response = requests.request(
                    method, url, headers=self.headers, json=data, timeout=60
                )
                last_status = response.status_code

                if response.status_code == 200:
                    if extract_doc_id:
                        doc_id = response.json().get("document", {}).get("id")
                        return {"success": True, "doc_id": doc_id}
                    return {"success": True}

                try:
                    error_data = response.json()
                    last_error = error_data.get("message", error_data.get("error", str(error_data)))[:100]
                except Exception:
                    last_error = response.text[:100] if response.text else f"HTTP {response.status_code}"

                if response.status_code in [429, 500, 502, 503, 504] and attempt < max_retries - 1:
                    time.sleep(1.5)
                    continue

            except requests.exceptions.Timeout:
                last_error = "timeout"
                if attempt < max_retries - 1:
                    time.sleep(1.5)
                    continue
            except requests.exceptions.ConnectionError as e:
                last_error = f"connection:{str(e)[:50]}"
                if attempt < max_retries - 1:
                    time.sleep(1.5)
                    continue
            except Exception as e:
                last_error = f"exception:{str(e)[:50]}"
            break

        return {"success": False, "error": last_error, "status": last_status}

