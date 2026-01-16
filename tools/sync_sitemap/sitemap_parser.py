"""Sitemap XML parsing utilities.

Extracts URLs and lastmod information from sitemap.xml files.
"""

import xml.etree.ElementTree as ET

import requests


def get_urls_from_sitemap(
    sitemap_url: str, return_lastmod: bool = False
) -> list[str] | dict[str, str | None]:
    """Extract URLs from sitemap.xml or handle single URL.

    Args:
        sitemap_url: URL to sitemap.xml or a single page URL
        return_lastmod: If True, returns dict {url: lastmod} instead of list

    Returns:
        If return_lastmod=False: list of URLs
        If return_lastmod=True: dict mapping URL to lastmod timestamp (or None)
    """
    if not sitemap_url.endswith('.xml'):
        if return_lastmod:
            return {sitemap_url: None}
        return [sitemap_url]

    try:
        response = requests.get(sitemap_url, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'

        if return_lastmod:
            url_data = {}
            for url_elem in root.findall(f'.//{ns}url'):
                loc = url_elem.find(f'{ns}loc')
                lastmod = url_elem.find(f'{ns}lastmod')
                if loc is not None and loc.text:
                    url = loc.text.strip()
                    lastmod_val = lastmod.text.strip() if lastmod is not None and lastmod.text else None
                    url_data[url] = lastmod_val
            return url_data
        else:
            urls = []
            for url_elem in root.findall(f'.//{ns}url'):
                loc = url_elem.find(f'{ns}loc')
                if loc is not None and loc.text:
                    urls.append(loc.text.strip())
            return urls

    except Exception:
        if return_lastmod:
            return {}
        return []

