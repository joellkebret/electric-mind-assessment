"""Runtime settings for the portfolio API."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SOLUTION_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = SOLUTION_ROOT.parent / "fixtures"
DEFAULT_DATABASE_PATH = SOLUTION_ROOT / "data" / "portfolio.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=SOLUTION_ROOT / ".env",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
    crm_base_url: str = "http://localhost:4002"
    # CRM timeout mode waits 10s. Keep this well under that for Task 1.
    crm_timeout_seconds: float = 3.0
    api_token: str = "superday-demo-token"

    @property
    def sqlite_file(self) -> Path | None:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            return None
        location = self.database_url.removeprefix(prefix)
        if location == ":memory:":
            return None
        return Path(location)


settings = Settings()
