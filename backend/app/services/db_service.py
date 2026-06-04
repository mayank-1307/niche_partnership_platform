from __future__ import annotations

import asyncio
import logging
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings

logger = logging.getLogger(__name__)


def _strip_json_null_bytes(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [_strip_json_null_bytes(item) for item in value]
    if isinstance(value, tuple):
        return [_strip_json_null_bytes(item) for item in value]
    if isinstance(value, dict):
        return {
            _strip_json_null_bytes(key) if isinstance(key, str) else key: _strip_json_null_bytes(item)
            for key, item in value.items()
        }
    return value


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

    def _ensure_schema_sync(self) -> None:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS evaluation_reports (
                        id BIGSERIAL PRIMARY KEY,
                        profile_id INTEGER NOT NULL REFERENCES company_profiles(id) ON DELETE CASCADE,
                        evaluation_type TEXT NOT NULL CHECK (evaluation_type IN ('decision_intelligence', 'scoring')),
                        report_json JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_evaluation_reports_profile_id
                    ON evaluation_reports (profile_id)
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_evaluation_reports_type
                    ON evaluation_reports (evaluation_type)
                    """
                )
                conn.commit()

    async def connect(self) -> None:
        if not self.enabled:
            logger.warning("Database integration is disabled; DATABASE_URL is empty")
            return
        await asyncio.to_thread(self._verify_connection)
        await asyncio.to_thread(self._ensure_schema_sync)
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
        safe_company_name = company_name.replace("\x00", "")
        safe_username = username.replace("\x00", "")
        safe_artefact = _strip_json_null_bytes(artefact)
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO company_profiles (company_name, username, artefact)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (safe_company_name, safe_username, psycopg.types.json.Jsonb(safe_artefact)),
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

    def _list_company_profiles_sync(self, search: str = "", limit: int = 5) -> list[dict[str, Any]]:
        logger.debug("Fetching company profile list search=%s limit=%s", search, limit)
        search_term = search.strip()
        like_pattern = f"%{search_term}%"
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                if search_term:
                    cur.execute(
                        """
                        SELECT id, company_name, username, created_at
                        FROM company_profiles
                        WHERE company_name ILIKE %s
                           OR COALESCE(artefact->>'website', '') ILIKE %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (like_pattern, like_pattern, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, company_name, username, created_at
                        FROM company_profiles
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    async def list_company_profiles(self, search: str = "", limit: int = 5) -> list[dict[str, Any]]:
        self._require_ready()
        return await asyncio.to_thread(self._list_company_profiles_sync, search, limit)

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

    def _save_evaluation_report_sync(
        self,
        *,
        profile_id: int,
        evaluation_type: str,
        report_json: dict[str, Any],
    ) -> int:
        logger.debug(
            "Saving evaluation report profile_id=%s evaluation_type=%s",
            profile_id,
            evaluation_type,
        )
        safe_report_json = _strip_json_null_bytes(report_json)
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO evaluation_reports (profile_id, evaluation_type, report_json)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (profile_id, evaluation_type, psycopg.types.json.Jsonb(safe_report_json)),
                )
                row = cur.fetchone()
                conn.commit()
        if not row:
            raise RuntimeError("Failed to save evaluation report.")
        return int(row[0])

    async def save_evaluation_report(
        self,
        *,
        profile_id: int,
        evaluation_type: str,
        report_json: dict[str, Any],
    ) -> int:
        self._require_ready()
        return await asyncio.to_thread(
            self._save_evaluation_report_sync,
            profile_id=profile_id,
            evaluation_type=evaluation_type,
            report_json=report_json,
        )


company_profile_db = CompanyProfileDatabase()
