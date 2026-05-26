from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.perception.face import FaceEmbedder
from app.persons.store import Person, PersonStore


router = APIRouter()


def _store(request: Request) -> PersonStore:
    return request.app.state.person_store


def _embedder(request: Request) -> FaceEmbedder:
    return request.app.state.face_embedder


@router.get("/persons", response_model=list[Person])
async def list_persons(request: Request) -> list[Person]:
    return _store(request).list()


@router.post("/persons", response_model=Person, status_code=201)
async def enroll_person(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...),
) -> Person:
    image_bytes = await image.read()
    embedding = _embedder(request).embed(image_bytes)
    if embedding is None:
        raise HTTPException(status_code=422, detail="No face detected in image")
    return _store(request).add(name=name, description=description, embedding=embedding)


@router.delete("/persons/{person_id}", status_code=204)
async def delete_person(person_id: str, request: Request) -> None:
    if not _store(request).delete(person_id):
        raise HTTPException(status_code=404, detail="Person not found")
