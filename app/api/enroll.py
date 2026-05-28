from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.enrollment.tokens import EnrollmentToken, TokenStore
from app.perception.face import FaceEmbedder
from app.persons.store import Person, PersonStore


router = APIRouter()


# ---------------------------------------------------------------------------
# Carer-side: token CRUD (lives under /v1/...)
# ---------------------------------------------------------------------------


class CreateTokenRequest(BaseModel):
    label: str = ""


def _token_store(request: Request) -> TokenStore:
    return request.app.state.token_store


def _person_store(request: Request) -> PersonStore:
    return request.app.state.person_store


def _embedder(request: Request) -> FaceEmbedder:
    return request.app.state.face_embedder


@router.post("/v1/enrollment-tokens", response_model=EnrollmentToken, status_code=201)
async def create_token(body: CreateTokenRequest, request: Request) -> EnrollmentToken:
    return _token_store(request).create(label=body.label)


@router.get("/v1/enrollment-tokens", response_model=list[EnrollmentToken])
async def list_tokens(request: Request) -> list[EnrollmentToken]:
    return _token_store(request).list()


@router.delete("/v1/enrollment-tokens/{token_id}", status_code=204)
async def revoke_token(token_id: str, request: Request) -> None:
    if not _token_store(request).revoke(token_id):
        raise HTTPException(status_code=404, detail="Token not found")


# ---------------------------------------------------------------------------
# Carer-side: approve a pending person
# ---------------------------------------------------------------------------


@router.post("/v1/persons/{person_id}/approve", response_model=Person)
async def approve_person(person_id: str, request: Request) -> Person:
    updated = _person_store(request).set_status(person_id, "active")
    if updated is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return updated


# ---------------------------------------------------------------------------
# Public self-enrollment via tokenized URL
# ---------------------------------------------------------------------------


def _page(body: str, title: str = "Faro · Enrolar") -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --fg: #1a1a1a; --bg: #fafafa; --accent: #4a6fa5; --muted: #666; --border: #ddd; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: -apple-system, system-ui, sans-serif; color: var(--fg); background: var(--bg); line-height: 1.5; }}
  main {{ max-width: 480px; margin: 0 auto; padding: 24px 20px 48px; }}
  h1 {{ font-size: 22px; margin: 0 0 8px; }}
  p.lead {{ color: var(--muted); margin: 0 0 24px; font-size: 15px; }}
  label {{ display: block; margin: 18px 0 6px; font-weight: 600; font-size: 14px; }}
  input[type=text], textarea, input[type=file] {{
    width: 100%; padding: 12px; font-size: 16px; border: 1px solid var(--border);
    border-radius: 8px; background: #fff; font-family: inherit;
  }}
  textarea {{ resize: vertical; min-height: 70px; }}
  button {{
    margin-top: 24px; width: 100%; padding: 14px; font-size: 16px; font-weight: 600;
    background: var(--accent); color: #fff; border: 0; border-radius: 8px; cursor: pointer;
  }}
  .privacy {{
    margin-top: 32px; padding: 14px 16px; background: #eef3fa;
    border-left: 3px solid var(--accent); border-radius: 4px; font-size: 13px; color: #333;
  }}
  .ok {{ padding: 20px; background: #e8f5e8; border-radius: 8px; }}
  .err {{ padding: 20px; background: #fdecea; border-radius: 8px; color: #8a1f12; }}
</style>
</head>
<body><main>{body}</main></body>
</html>"""
    return HTMLResponse(content=html)


def _form_body(token: str, error: str | None = None) -> str:
    err_block = f'<div class="err">{error}</div>' if error else ""
    return f"""
<h1>Ayúdanos a recordarte</h1>
<p class="lead">Sube o toma una foto, escribe quién eres y qué relación tienes. Listo.</p>
{err_block}
<form method="post" action="/enroll/{token}" enctype="multipart/form-data">
  <label for="name">Tu nombre</label>
  <input type="text" id="name" name="name" required maxlength="80" autocomplete="name">

  <label for="description">Quién eres en una frase</label>
  <textarea id="description" name="description" required maxlength="160"
            placeholder="ej.: tu hijo mayor"></textarea>

  <label for="image">Tu foto</label>
  <input type="file" id="image" name="image" accept="image/*" required>

  <button type="submit">Enviar</button>
</form>
<div class="privacy">
  <strong>Tu foto no se guarda.</strong> El sistema la procesa una sola vez para
  extraer un vector matemático que representa los rasgos de tu rostro, y
  después la descarta. Lo único que se almacena es ese vector y la descripción
  que escribes.
</div>
"""


@router.get("/enroll/{token}", response_class=HTMLResponse)
async def enrollment_form(token: str, request: Request) -> HTMLResponse:
    if not _token_store(request).is_valid(token):
        return _page("<h1>Enlace inválido</h1><p>El enlace ha expirado o ya no es válido.</p>", title="Faro")
    return _page(_form_body(token))


@router.post("/enroll/{token}", response_class=HTMLResponse)
async def enrollment_submit(
    token: str,
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...),
) -> HTMLResponse:
    if not _token_store(request).is_valid(token):
        return _page("<h1>Enlace inválido</h1><p>El enlace ha expirado o ya no es válido.</p>", title="Faro")

    image_bytes = await image.read()
    embedding = _embedder(request).embed(image_bytes)
    # NOTE: image_bytes goes out of scope when this function returns; it is
    # never written to disk. Only the embedding survives.
    del image_bytes

    if embedding is None:
        return _page(_form_body(token, error="No detectamos ningún rostro en la imagen. Probá con otra foto."))

    _person_store(request).add(
        name=name.strip(),
        description=description.strip(),
        embedding=embedding,
        status="pending",
    )
    return _page(
        '<div class="ok"><h1>¡Listo!</h1>'
        "<p>Recibimos tu información. La persona que cuida de tu familiar la revisará y aprobará pronto.</p>"
        "<p>Ya puedes cerrar esta ventana.</p></div>"
    )
