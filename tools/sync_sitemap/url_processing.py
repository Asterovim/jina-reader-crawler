"""URL processing utilities for sitemap synchronization.

Handles URL normalization, hashing for duplicate detection, and document naming.
"""

import hashlib
import re
import unicodedata
from urllib.parse import unquote, urlparse

# 12 hex chars = 48 bits = ~281 trillion unique values
# Collision probability (Birthday Paradox): negligible for any realistic KB size
URL_HASH_LENGTH = 12


def normalize_url(url: str) -> str:
    """Normalize URL for comparison (handle http/https, www/non-www, encoding, Unicode).

    This is critical for French URLs with accented characters like:
    - connaitre vs connaître vs conna%C3%AEtre
    - L'Examen vs L%27Examen

    Normalization steps:
    1. Strip whitespace
    2. Decode percent-encoded characters (e.g., %C3%AE -> î)
    3. Normalize Unicode to NFC form (canonical composition)
    4. Lowercase for case-insensitive comparison
    5. Remove protocol (http/https)
    6. Remove www. prefix
    7. Remove trailing slash
    """
    if not url:
        return ""

    url = url.strip()

    # Decode percent-encoded characters (handles %C3%AE -> î, %27 -> ', etc.)
    # This is safe because we're just using for comparison, not making requests
    try:
        url = unquote(url)
    except Exception:
        pass  # Keep original if decode fails

    # Normalize Unicode to NFC (Canonical Composition)
    # This ensures é (single char) == e + combining accent (two chars)
    # Critical for French: "connaître" should match regardless of composition
    try:
        url = unicodedata.normalize('NFC', url)
    except Exception:
        pass  # Keep original if normalization fails

    # Lowercase for case-insensitive comparison
    url = url.lower()

    # Remove protocol
    url = re.sub(r'^https?://', '', url)

    # Remove www. prefix
    url = re.sub(r'^www\.', '', url)

    # Remove trailing slash
    url = url.rstrip('/')

    return url


def generate_url_hash(url: str) -> str:
    """Generate 12-char URL hash for duplicate detection.

    Embedded in document names for O(1) lookup without API calls.
    """
    normalized = normalize_url(url)
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:URL_HASH_LENGTH]


def extract_url_hash_from_name(doc_name: str) -> str | None:
    """Extract 12-character URL hash from document name.

    Expected format: "Title (domain) [abc123def456]"
    Returns None for documents without valid hash suffix.
    """
    match = re.search(r'\[([a-f0-9]{12})\]$', doc_name)
    return match.group(1) if match else None


def generate_doc_name(url: str, title: str) -> str:
    """Generate document name with URL hash for duplicate detection.

    Format: "Title (domain) [hash]" or "domain_path [hash]"
    The hash enables O(1) lookup without segment API calls.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    url_hash = generate_url_hash(url)

    if title:
        # Shorter title (80 chars) to fit hash within reasonable name length
        safe_title = title[:80] if len(title) > 80 else title
        return f"{safe_title} ({domain}) [{url_hash}]"
    path = parsed.path.strip("/").replace("/", "_") or "index"
    return f"{domain}_{path} [{url_hash}]"


def truncate_title(title: str, max_length: int = 60) -> str:
    """Truncate title to max_length characters with ellipsis."""
    if len(title) <= max_length:
        return title
    return title[:max_length - 3] + "..."


def get_url_path(url: str) -> str:
    """Extract path from URL for display when title is unavailable."""
    parsed = urlparse(url)
    path = parsed.path or "/"
    if parsed.query:
        path += f"?{parsed.query[:30]}"  # Include query params, truncated
    return path[:60] if len(path) > 60 else path


def parse_manual_urls(text: str) -> list[str]:
    """Parse a newline/comma-separated URL list from a textarea field.

    Rules:
    - Split on newlines and commas
    - Strip whitespace per entry
    - Drop empty lines and comments (lines starting with #)
    - Keep only http:// or https:// URLs
    - Dedupe while preserving first-seen order

    Args:
        text: Raw text from the `manual_urls` tool parameter.

    Returns:
        Ordered list of unique URLs.
    """
    if not text:
        return []

    candidates: list[str] = []
    for line in text.replace(",", "\n").splitlines():
        url = line.strip()
        if not url or url.startswith("#"):
            continue
        if not (url.startswith("http://") or url.startswith("https://")):
            continue
        candidates.append(url)

    seen: set[str] = set()
    unique: list[str] = []
    for url in candidates:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique

