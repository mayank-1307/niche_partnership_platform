from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.services.db_service import company_profile_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    await company_profile_db.connect()
    try:
        yield
    finally:
        await company_profile_db.disconnect()


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

origins = [x.strip() for x in settings.backend_cors_origins.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
