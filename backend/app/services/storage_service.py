from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class JsonStorageService:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _slugify(self, value: str) -> str:
        clean = (value or "").replace("https://", "").replace("http://", "").strip().lower()
        clean = clean.split("/")[0]
        clean = re.sub(r"[^a-z0-9.-]", "-", clean)
        clean = re.sub(r"-{2,}", "-", clean).strip("-")
        return clean or "company"

    def save(self, payload: dict, domain: str, company_name: str = "") -> str:
        slug = self._slugify(company_name) if company_name else self._slugify(domain)
        dt_part = datetime.utcnow().strftime("%Y-%m-%d-%H%M%S")
        file_id = f"{slug}-{dt_part}"
        target = self.base_dir / f"{file_id}.json"
        wrapped = {"generated_at": datetime.utcnow().isoformat(), "data": payload}
        target.write_text(json.dumps(wrapped, indent=2), encoding="utf-8")
        logger.info("Stored JSON output file_id=%s path=%s", file_id, target)
        return file_id

    def resolve(self, file_id: str) -> Path:
        return self.base_dir / f"{file_id}.json"

    def list_files(self) -> list[dict]:
        logger.debug("Listing JSON outputs directory=%s", self.base_dir)
        files = sorted(self.base_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        out: list[dict] = []
        for f in files:
            out.append(
                {
                    "id": f.stem,
                    "filename": f.name,
                    "updated_at": datetime.utcfromtimestamp(f.stat().st_mtime).isoformat(),
                }
            )
        return out

    def read(self, file_id: str) -> dict:
        target = self.resolve(file_id)
        if not target.exists():
            logger.warning("Stored JSON not found file_id=%s path=%s", file_id, target)
            raise FileNotFoundError(file_id)
        logger.debug("Reading stored JSON file_id=%s path=%s", file_id, target)
        return json.loads(target.read_text(encoding="utf-8"))


json_storage_service = JsonStorageService(settings.storage_dir)
