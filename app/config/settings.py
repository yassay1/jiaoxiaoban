from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_api_base: str = ""
    llm_model_name: str = ""
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "campus_agent"
    postgres_user: str = "campus_agent"
    postgres_password: str = "campus_agent_dev"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # 社区服务
    community_service_base_url: str = "http://localhost:8080/api"
    community_service_api_key: str = ""
    community_service_mode: str = "mock"  # mock | local | real

    # Agent Service
    agent_service_host: str = "0.0.0.0"
    agent_service_port: int = 8000
    agent_service_debug: bool = False
    demo_mode: bool = False

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def postgres_sync_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        base = f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
        if self.redis_password:
            base = f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return base

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_api_base and self.llm_model_name)

    @property
    def debug(self) -> bool:
        return self.agent_service_debug

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False, "extra": "allow"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


