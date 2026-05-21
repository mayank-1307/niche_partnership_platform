from __future__ import annotations

from urllib.parse import urlparse


def normalize_domain(domain: str) -> str:
    value = domain.strip()
    if not value:
        raise ValueError("Domain is required")
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    parsed = urlparse(value)
    if not parsed.netloc:
        raise ValueError("Invalid domain")
    return f"{parsed.scheme}://{parsed.netloc}"


def to_company_name(url: str) -> str:
    host = urlparse(url).netloc.replace("www.", "")
    base = host.split(".")[0]
    return base.replace("-", " ").replace("_", " ").title()
