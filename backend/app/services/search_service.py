from __future__ import annotations

import logging
from typing import Any

import httpx
from duckduckgo_search import DDGS

from app.core.config import settings

logger = logging.getLogger(__name__)


class SearchService:
    def _normalize_domain(self, company_domain: str) -> str:
        clean = company_domain.replace("https://", "").replace("http://", "").strip().lower()
        return clean.split("/")[0]

    def _duckduckgo(self, query: str, max_results: int) -> list[dict[str, Any]]:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in results
        ]

    async def _tavily(self, query: str, max_results: int) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": settings.tavily_api_key, "query": query, "max_results": max_results},
            )
            resp.raise_for_status()
            data = resp.json().get("results", [])
        return [{"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("content", "")} for x in data]

    async def _serper(self, query: str, max_results: int) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            resp = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
                json={"q": query, "num": max_results},
            )
            resp.raise_for_status()
            data = resp.json().get("organic", [])
        return [{"title": x.get("title", ""), "url": x.get("link", ""), "snippet": x.get("snippet", "")} for x in data]

    async def search(self, company_domain: str, company_name: str) -> list[dict[str, Any]]:
        normalized_domain = self._normalize_domain(company_domain)
        queries = [
            f"site:{normalized_domain} about",
            f"site:{normalized_domain} leadership team",
            f"site:{normalized_domain} products platform",
            f"{normalized_domain} company funding investors",
            f"{normalized_domain} enterprise customers case studies",
            f"{company_name} funding investors",
            f"{company_name} leadership team",
            f"{company_name} enterprise customers case studies",
            f"{company_name} partnerships integrations",
        ]

        hits: list[dict[str, Any]] = []
        provider = settings.search_provider.lower()
        logger.info("Search started provider=%s domain=%s", provider or "duckduckgo", normalized_domain)
        for q in queries:
            try:
                if provider == "tavily" and settings.tavily_api_key:
                    res = await self._tavily(q, 4)
                elif provider == "serper" and settings.serper_api_key:
                    res = await self._serper(q, 4)
                else:
                    res = self._duckduckgo(q, 4)
                logger.debug("Search query completed provider=%s results=%s query=%s", provider or "duckduckgo", len(res), q)
                hits.extend(res)
            except Exception:
                logger.exception("Search query failed provider=%s query=%s", provider or "duckduckgo", q)
                continue

        unique = []
        seen = set()
        for h in hits:
            u = h.get("url", "")
            if not u or u in seen:
                continue
            seen.add(u)
            unique.append(h)

        results = unique[:20]
        logger.info("Search completed domain=%s unique_results=%s", normalized_domain, len(results))
        return results


search_service = SearchService()
