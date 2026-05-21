from __future__ import annotations

from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings


KEYWORDS = [
    "about", "product", "solution", "ai", "customer", "case", "integration", "partner", "team", "leadership", "pricing", "blog", "news", "doc",
]


@dataclass
class PageContent:
    url: str
    title: str
    text: str


class CrawlService:
    def __init__(self) -> None:
        self.timeout = httpx.Timeout(settings.request_timeout_seconds)

    def _extract_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())

    async def _fetch_text(self, client: httpx.AsyncClient, url: str) -> str:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        return resp.text

    async def _get_sitemap_urls(self, client: httpx.AsyncClient, base_url: str) -> list[str]:
        sitemap_url = f"{base_url}/sitemap.xml"
        try:
            xml = await self._fetch_text(client, sitemap_url)
        except Exception:
            return []

        soup = BeautifulSoup(xml, "xml")
        urls = [loc.get_text(strip=True) for loc in soup.find_all("loc")]
        filtered = [u for u in urls if any(k in u.lower() for k in KEYWORDS)]
        home = [base_url]
        return (home + filtered)[: settings.max_sitemap_urls]

    async def _discover_links(self, client: httpx.AsyncClient, base_url: str) -> list[str]:
        try:
            html = await self._fetch_text(client, base_url)
        except Exception:
            return [base_url]

        soup = BeautifulSoup(html, "html.parser")
        found: list[str] = [base_url]
        host = urlparse(base_url).netloc

        for a in soup.find_all("a", href=True):
            href = urljoin(base_url, a["href"])
            parsed = urlparse(href)
            if parsed.netloc != host:
                continue
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
            if any(k in normalized.lower() for k in KEYWORDS):
                found.append(normalized)

        deduped = list(dict.fromkeys(found))
        return deduped[: settings.max_pages_to_crawl]

    async def _allowed_by_robots(self, client: httpx.AsyncClient, base_url: str, target_url: str) -> bool:
        robots_url = f"{base_url}/robots.txt"
        parser = robotparser.RobotFileParser()
        try:
            txt = await self._fetch_text(client, robots_url)
            parser.parse(txt.splitlines())
            return parser.can_fetch("CompanyIntelligenceBot/1.0", target_url)
        except Exception:
            return True

    async def crawl(self, base_url: str) -> list[PageContent]:
        async with httpx.AsyncClient(timeout=self.timeout, headers={"User-Agent": "CompanyIntelligenceBot/1.0"}) as client:
            sitemap_urls = await self._get_sitemap_urls(client, base_url)
            discovered = await self._discover_links(client, base_url)
            targets = list(dict.fromkeys(sitemap_urls + discovered))[: settings.max_pages_to_crawl]

            pages: list[PageContent] = []
            for url in targets:
                try:
                    if not await self._allowed_by_robots(client, base_url, url):
                        continue
                    html = await self._fetch_text(client, url)
                    extracted = self._extract_text(html)
                    if len(extracted.strip()) < 120:
                        continue
                    soup = BeautifulSoup(html, "html.parser")
                    title = (soup.title.string if soup.title else "").strip()
                    pages.append(PageContent(url=url, title=title, text=extracted[:10000]))
                except Exception:
                    continue

        return pages


crawl_service = CrawlService()
