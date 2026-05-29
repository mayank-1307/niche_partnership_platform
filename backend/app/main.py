from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.services.db_service import company_profile_db

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting application lifespan")
    await company_profile_db.connect()
    try:
        yield
    finally:
        logger.info("Shutting down application lifespan")
        await company_profile_db.disconnect()


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

# CORS is intentionally env-driven so local and deployed frontends can share this API.
origins = [x.strip() for x in settings.backend_cors_origins.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
