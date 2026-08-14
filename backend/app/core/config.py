from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
REPO_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AI_LINGMA_",
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI灵码平台"
    environment: str = "dev"
    debug: bool = True

    # 运行时数据目录（workspaces/versions/publish/db）
    storage_dir: Path = REPO_DIR / "storage"
    # 留空则使用 storage_dir/app.db
    database_url: str = ""

    jwt_secret: str = "dev-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    register_enabled: bool = False

    admin_username: str = "admin"
    admin_password: str = "admin123"
    admin_email: str = "admin@example.com"

    default_user_quota: int = 20
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @property
    def database_url_default(self) -> str:
        return f"sqlite:///{(self.storage_dir / 'app.db').as_posix()}"

    @property
    def workspace_dir(self) -> Path:
        return self.storage_dir / "workspaces"

    @property
    def versions_dir(self) -> Path:
        return self.storage_dir / "versions"

    @property
    def publish_dir(self) -> Path:
        return self.storage_dir / "publish"


@lru_cache
def get_settings() -> Settings:
    return Settings()
