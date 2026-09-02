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

    auth_token_secret: str = "lessoncanvas-dev-auth-secret-000"
    auth_token_audience: str = "lessoncanvas-dev"
    # ADR-0006 D11: guest tokens are long-lived per-browser workspace keys.
    guest_token_ttl_seconds: int = 30 * 24 * 3600

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
    eval_fault_profile: str = ""
    # F012 D3/D10: the synthetic sample is owned by this designated demo
    # workspace subject. Safe GET endpoints opened with allow_sample_read serve
    # its single active project read-only to any authenticated workspace;
    # writes and streams stay owner-only. The seeding script creates it.
    demo_owner_subject: str = "lessoncanvas-demo-sample-owner"

    model_price_prompt_per_mtok: float = 0.27
    model_price_completion_per_mtok: float = 1.10
    evidence_events_page_default: int = 50
    evidence_events_page_max: int = 200
    evidence_inventory_page_default: int = 50
    evidence_narration_quota_per_workspace: int = 50

    # F011 public-demo guardrails (Spec D2 relaxed set, owner-confirmed 2026-09-01).
    # PostgreSQL is the single rate truth; window boundaries are deterministic.
    rate_window_seconds: int = 60
    rate_general_per_window: int = 240
    rate_expensive_per_window: int = 120
    max_concurrent_generation_runs_per_workspace: int = 2
    max_concurrent_sse_streams_per_workspace: int = 6
    upload_daily_bytes_per_workspace: int = 200 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
