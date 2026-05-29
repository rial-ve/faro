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
    # Lowered from 0.5 to 0.45 in experiment 003: MobileFaceNet's
    # same-person similarities sit ~0.5 (vs ~0.6 for buffalo_l), so we
    # need a touch more headroom for real-world variation.
    face_similarity_threshold: float = 0.45

    # Which face embedder runs server-side. Both are insightface packs;
    # `mobilefacenet` (buffalo_s) is the default because it is the only
    # one that will actually deploy on-device — keeping dev and prod on
    # the same model avoids surprises. `insightface-buffalo_l` stays
    # available so experiment 003 can A/B them side by side.
    face_embedder: Literal["insightface-buffalo_l", "mobilefacenet"] = "mobilefacenet"

    # Basic Auth credentials for the carer-side API.
    # Must both be set; if either is empty, admin routes return 503.
    admin_username: str = ""
    admin_password: str = ""


def load() -> Settings:
    return Settings()
