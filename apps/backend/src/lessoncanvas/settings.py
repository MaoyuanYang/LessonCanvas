from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LESSONCANVAS_", env_file=".env")

    database_url: str = (
        "postgresql+psycopg://lessoncanvas:lessoncanvas_dev_only@localhost:5432/lessoncanvas"
    )
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "lessoncanvas"
    s3_secret_key: str = "lessoncanvas_dev_only"
    s3_bucket_sources: str = "lessoncanvas-sources"
    s3_bucket_artifacts: str = "lessoncanvas-artifacts"

    clerk_jwks_url: str = ""
    clerk_issuer: str = ""
    clerk_audience: str = ""
    clerk_secret_key: str = ""
    clerk_api_base: str = "https://api.clerk.com"
    auth_dev_secret: str = "lessoncanvas-dev-auth-secret-000"
    auth_dev_audience: str = "lessoncanvas-dev"

    max_projects_per_workspace: int = 5
    max_planning_runs_per_workspace: int = 50
    cors_allowed_origins: list[str] = ["http://localhost:3000"]
    tasks_eager: bool = False

    model_adapter: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    max_model_calls_per_run: int = 20
    max_model_calls_per_deck_run: int = 20
    deck_max_slides: int = 16
    deck_max_stage_slides: int = 2
    max_model_calls_per_exercise_run: int = 20
    exercise_min_items_per_lesson: int = 6
    exercise_max_items_per_lesson: int = 15
    exercise_min_categories_per_lesson: int = 3
    exercise_max_categories_per_lesson: int = 4
    checkpoint_backend: str = "postgres"


@lru_cache
def get_settings() -> Settings:
    return Settings()
