# Experimento 002 — Auto-enrolación vía link tokenizado

**Estado:** ✅ Validado
**Periodo:** 2026-05-28

## Resumen

Descentralizamos la enrolación: el cuidador envía un link tokenizado por WhatsApp, cada familiar abre la página, sube o toma una foto y escribe quién es. El servidor calcula el embedding y descarta los bytes de la foto. La persona queda en estado `pending` hasta que el cuidador aprueba. Esto resuelve el problema de cold-start (poblar la base de personas sin que el cuidador tenga que hacerlo todo solo) sin comprometer la privacidad ni la integridad del store.

## Cartas

- [Test Card](./test-card.md) — la hipótesis y el plan (escrita antes de implementar)
- [Learning Card](./learning-card.md) — lo que observamos y aprendimos

## Evidencia

- **Código nuevo:**
  - [`app/enrollment/tokens.py`](../../app/enrollment/tokens.py) — `EnrollmentToken` + `TokenStore` (JSON-backed, mismo patrón que `PersonStore`)
  - [`app/api/enroll.py`](../../app/api/enroll.py) — token CRUD, página HTML, POST de enrolación, endpoint de aprobación
- **Cambios:**
  - [`app/persons/store.py`](../../app/persons/store.py) — campo `status` en `Person`, `find_closest` filtra a `active`
  - [`app/api/persons.py`](../../app/api/persons.py) — `GET /v1/persons?status=pending` para que el cuidador vea pendientes
  - [`app/settings.py`](../../app/settings.py) — `tokens_db_path`
  - [`app/main.py`](../../app/main.py) — carga `TokenStore` en lifespan, monta `enroll_router`
- **Tests:** [`tests/test_enrollment.py`](../../tests/test_enrollment.py) — 13 tests, `MockEmbedder` determinístico para evitar cargar los modelos reales en pytest
- **Smoke test reproducible** documentado en la [Learning Card](./learning-card.md)

## Cómo probarlo manualmente

```bash
# 1. Levanta el servidor
FARO_PROVIDER=meta-llama-mobile \
FARO_MODEL_PATH=models/Llama-3.2-1B-Instruct-Q4_K_M.gguf \
.venv/bin/uvicorn app.main:app --port 8765

# 2. Cuidador crea un token
curl -s -X POST http://127.0.0.1:8765/v1/enrollment-tokens \
  -H 'content-type: application/json' \
  -d '{"label":"familia campos"}'

# 3. Abre la URL devuelta (campo "token") en un navegador móvil:
#    http://127.0.0.1:8765/enroll/<TOKEN>

# 4. El cuidador revisa pendientes
curl -s "http://127.0.0.1:8765/v1/persons?status=pending"

# 5. Aprueba a uno
curl -s -X POST http://127.0.0.1:8765/v1/persons/<PERSON_ID>/approve

# 6. Ahora /v1/recognize lo reconoce
curl -s -X POST http://127.0.0.1:8765/v1/recognize \
  -F 'language=es' -F 'image=@<otra-foto-de-la-misma-persona>.jpg'
```
