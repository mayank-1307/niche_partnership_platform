from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR.parent / ".env"), extra="ignore")

    app_name: str = "Company Intelligence Extractor"
    app_version: str = "1.0.0"

    openai_api_key: str = ""
    openai_model: str = "gpt-5-mini"

    mistral_api_key: str = ""
    mistral_model: str = "mistral-large-latest"
    mistral_base_url: str = "https://api.mistral.ai/v1"

    search_provider: str = "duckduckgo"
    tavily_api_key: str = ""
    serper_api_key: str = ""

    backend_cors_origins: str = "http://localhost:5173"

    request_timeout_seconds: int = 25
    max_pages_to_crawl: int = 12
    max_sitemap_urls: int = 40

    storage_dir: Path = BASE_DIR / "storage"


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
