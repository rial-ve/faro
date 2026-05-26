from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, File, Form, Request, UploadFile
from pydantic import BaseModel

from app.perception.face import FaceEmbedder
from app.persons.store import Match, PersonStore
from app.providers.base import ChatMessage, LLMProvider


router = APIRouter()

Language = Literal["es", "en"]


class MatchPublic(BaseModel):
    """Match shape returned to clients (no embedding)."""

    id: str
    name: str
    description: str
    similarity: float


class RecognizeResponse(BaseModel):
    match: MatchPublic | None
    spoken: str


# Frame as a pure template-fill task (NOT "identification") to avoid the
# 1B model's safety refusals, and feed examples as assistant turns so the
# format is learned in-context.
SYSTEM_PROMPTS: dict[Language, str] = {
    "es": (
        "Eres un formateador. Combinas dos campos (Nombre y Descripción) "
        "en UNA frase usando esta plantilla EXACTA: "
        '"Ese es <Nombre>, <Descripción>." '
        "No inventas información. No añades nada extra. "
        "Solo aplicas la plantilla."
    ),
    "en": (
        "You format two fields (Name and Description) into ONE sentence "
        'using this EXACT template: "That\'s <Name>, <Description>." '
        "Do not invent information. Do not add anything extra. "
        "Only apply the template."
    ),
}

FEW_SHOT: dict[Language, list[tuple[str, str]]] = {
    "es": [
        (
            "Nombre: Juan Pérez. Descripción: tu vecino del quinto.",
            "Ese es Juan Pérez, tu vecino del quinto.",
        ),
        (
            "Nombre: María García. Descripción: tu jefa en la oficina.",
            "Ese es María García, tu jefa en la oficina.",
        ),
    ],
    "en": [
        (
            "Name: Juan Pérez. Description: your fifth-floor neighbor.",
            "That's Juan Pérez, your fifth-floor neighbor.",
        ),
        (
            "Name: Maria Garcia. Description: your boss at the office.",
            "That's Maria Garcia, your boss at the office.",
        ),
    ],
}

UNKNOWN_RESPONSE: dict[Language, str] = {
    "es": "No reconozco a esta persona.",
    "en": "I don't recognize this person.",
}

NO_FACE_RESPONSE: dict[Language, str] = {
    "es": "No veo a ninguna persona en la imagen.",
    "en": "I don't see anyone in the image.",
}


async def _phrase(
    provider: LLMProvider, match: Match, language: Language
) -> str:
    if language == "es":
        final_user = (
            f"Nombre: {match.person.name}. "
            f"Descripción: {match.person.description}."
        )
    else:
        final_user = (
            f"Name: {match.person.name}. "
            f"Description: {match.person.description}."
        )

    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=SYSTEM_PROMPTS[language])
    ]
    for user_ex, assistant_ex in FEW_SHOT[language]:
        messages.append(ChatMessage(role="user", content=user_ex))
        messages.append(ChatMessage(role="assistant", content=assistant_ex))
    messages.append(ChatMessage(role="user", content=final_user))

    result = await provider.generate(
        messages, max_tokens=60, temperature=0.0, stop=["\n"]
    )
    return result.text.strip().strip('"').strip()


def _to_public(match: Match) -> MatchPublic:
    return MatchPublic(
        id=match.person.id,
        name=match.person.name,
        description=match.person.description,
        similarity=match.similarity,
    )


@router.post("/recognize", response_model=RecognizeResponse)
async def recognize(
    request: Request,
    image: UploadFile = File(...),
    language: Language = Form("es"),
) -> RecognizeResponse:
    embedder: FaceEmbedder = request.app.state.face_embedder
    store: PersonStore = request.app.state.person_store
    provider: LLMProvider = request.app.state.provider
    threshold: float = request.app.state.settings.face_similarity_threshold

    image_bytes = await image.read()
    embedding = embedder.embed(image_bytes)
    if embedding is None:
        return RecognizeResponse(match=None, spoken=NO_FACE_RESPONSE[language])

    match = store.find_closest(embedding, threshold=threshold)
    if match is None:
        return RecognizeResponse(match=None, spoken=UNKNOWN_RESPONSE[language])

    spoken = await _phrase(provider, match, language)
    return RecognizeResponse(match=_to_public(match), spoken=spoken)
