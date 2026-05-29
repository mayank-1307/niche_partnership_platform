from __future__ import annotations

import asyncio
import logging
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings

logger = logging.getLogger(__name__)


class CompanyProfileDatabase:
    def __init__(self) -> None:
        self._ready = False

    @property
    def enabled(self) -> bool:
        return bool(settings.database_url.strip())

    def _verify_connection(self) -> None:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

    async def connect(self) -> None:
        if not self.enabled:
            logger.warning("Database integration is disabled; DATABASE_URL is empty")
            return
        await asyncio.to_thread(self._verify_connection)
        self._ready = True
        logger.info("Database connection verified")

    async def disconnect(self) -> None:
        self._ready = False

    def _require_ready(self) -> None:
        if not self.enabled:
            raise RuntimeError("Database integration is disabled. Set DATABASE_URL to enable it.")
        if not self._ready:
            raise RuntimeError("Database is not ready.")

    def _save_company_profile_sync(self, *, company_name: str, artefact: dict[str, Any], username: str) -> int:
        logger.debug("Saving company profile company_name=%s username=%s", company_name, username)
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO company_profiles (company_name, username, artefact)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (company_name, username, psycopg.types.json.Jsonb(artefact)),
                )
                row = cur.fetchone()
                conn.commit()
        if not row:
            raise RuntimeError("Failed to save company profile.")
        return int(row[0])

    async def save_company_profile(self, *, company_name: str, artefact: dict[str, Any], username: str = "") -> int:
        self._require_ready()
        return await asyncio.to_thread(
            self._save_company_profile_sync,
            company_name=company_name,
            artefact=artefact,
            username=username,
        )

    def _list_company_profiles_sync(self) -> list[dict[str, Any]]:
        logger.debug("Fetching company profile list")
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, company_name, username, created_at
                    FROM company_profiles
                    ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    async def list_company_profiles(self) -> list[dict[str, Any]]:
        self._require_ready()
        return await asyncio.to_thread(self._list_company_profiles_sync)

    def _get_company_profile_sync(self, profile_id: int) -> dict[str, Any] | None:
        logger.debug("Fetching company profile profile_id=%s", profile_id)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, company_name, username, artefact, created_at
                    FROM company_profiles
                    WHERE id = %s
                    """,
                    (profile_id,),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    async def get_company_profile(self, profile_id: int) -> dict[str, Any] | None:
        self._require_ready()
        return await asyncio.to_thread(self._get_company_profile_sync, profile_id)


company_profile_db = CompanyProfileDatabase()
