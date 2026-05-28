from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request

from app.api.chat import router as chat_router
from app.api.enroll import admin_router as enroll_admin_router
from app.api.enroll import public_router as enroll_public_router
from app.api.persons import router as persons_router
from app.api.recognize import router as recognize_router
from app.enrollment.tokens import TokenStore
from app.perception.face import InsightFaceEmbedder
from app.persons.store import PersonStore
from app.providers.base import LLMProvider
from app.providers.meta_llama_mobile import MetaLlamaMobileProvider
from app.providers.mock import MockProvider
from app.security import admin_required
from app.settings import Settings, load


def build_provider(settings: Settings) -> LLMProvider:
    if settings.provider == "mock":
        return MockProvider()
    return MetaLlamaMobileProvider(
        model_path=settings.model_path,
        model_id=settings.model_id,
        quantization=settings.quantization,
        n_ctx=settings.n_ctx,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load()
    app.state.settings = settings
    app.state.provider = build_provider(settings)
    app.state.face_embedder = InsightFaceEmbedder()
    app.state.person_store = PersonStore(settings.persons_db_path)
    app.state.token_store = TokenStore(settings.tokens_db_path)
    yield


app = FastAPI(title="Faro Playground", lifespan=lifespan)

# Carer-side routers — all gated by HTTP Basic Auth.
_admin_deps = [Depends(admin_required)]
app.include_router(chat_router, prefix="/v1", dependencies=_admin_deps)
app.include_router(persons_router, prefix="/v1", dependencies=_admin_deps)
app.include_router(recognize_router, prefix="/v1", dependencies=_admin_deps)
app.include_router(enroll_admin_router, prefix="/v1", dependencies=_admin_deps)

# Public router — anyone with a valid enrollment token URL can use it.
app.include_router(enroll_public_router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models", dependencies=_admin_deps)
async def models(request: Request) -> dict[str, str]:
    p: LLMProvider = request.app.state.provider
    return {
        "provider": p.name,
        "model_id": p.model_id,
        "quantization": p.quantization,
    }
