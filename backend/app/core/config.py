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

    jwt_secret: str = "dev-only-secret-change-me-0123456789"
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

    # M1-2 任务与生成工作流
    build_mode: str = "real"  # real | mock（mock 用于无 LLM/无网络环境）
    generation_concurrency: int = 2
    modification_concurrency: int = 4
    task_timeout_seconds: int = 1200
    max_requirement_length: int = 8000
    mock_delay_seconds: float = 0.05

    # LLM 适配（OpenAI 兼容协议；留空/ mock 则使用内置 mock 执行器）
    llm_model: str = "mock"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_reasoning_effort: str = "high"
    llm_thinking_enabled: bool = True

    # 生成 Agent（ReAct 工具循环）
    agent_max_iterations: int = 50

    # 异步素材编排：图片来源均通过白名单适配器访问，密钥不暴露给模型。
    asset_request_timeout_seconds: int = 8
    asset_iconify_enabled: bool = True
    asset_iconify_api_url: str = "https://api.iconify.design"
    asset_pexels_api_key: str = ""
    asset_pexels_api_url: str = "https://api.pexels.com/v1"

    # 命令执行模式：shell=本机终端语义（无沙箱，本地开发默认）；
    # sandbox=白名单受限执行（生产/受限环境）
    command_mode: str = "shell"

    # 首页项目截图（无头浏览器）
    backend_url: str = "http://127.0.0.1:8000"
    screenshot_timeout_seconds: int = 45
    screenshot_virtual_time_budget_ms: int = 3000

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
