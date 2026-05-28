from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FARO_", env_file=".env", extra="ignore"
    )

    provider: Literal["mock", "meta-llama-mobile"] = "mock"
    model_path: str = ""
    model_id: str = "meta-llama/Llama-3.2-1B-Instruct"
    quantization: str = "Q4_K_M"
    n_ctx: int = 4096

    persons_db_path: str = "data/persons.json"
    tokens_db_path: str = "data/tokens.json"
    face_similarity_threshold: float = 0.5

    # Basic Auth credentials for the carer-side API.
    # Must both be set; if either is empty, admin routes return 503.
    admin_username: str = ""
    admin_password: str = ""


def load() -> Settings:
    return Settings()
