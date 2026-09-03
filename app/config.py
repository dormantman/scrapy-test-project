from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://books:books@localhost:5432/books"
    scraper_base_url: str = "https://books.toscrape.com/catalogue/page-1.html"
    scraper_concurrency: int = 10
    scraper_retries: int = 3
    scraper_backoff: float = 0.5
    scraper_timeout: float = 20.0
    scraper_commit_every: int = 100


settings = Settings()
