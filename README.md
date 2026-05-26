# Faro

**Faro es un asistente de memoria para personas con Alzheimer, demencia o pérdida de memoria por una lesión cerebral.** Reconoce el rostro de un ser querido a partir de la cámara del teléfono y le dice al usuario, en una frase corta, quién es y qué relación tiene con él. *"Ese es Rodolfo, tu hijo mayor."*

Dos decisiones de diseño que vienen directamente de la audiencia:

- **Local primero.** Todo corre en el teléfono del usuario, nunca en la nube. Las fotos familiares, los nombres y las relaciones — datos sensibles para cualquiera, y aún más para alguien cuya capacidad de consentir al uso de sus datos puede estar comprometida — nunca salen del dispositivo.
- **Sin conexión.** El modelo funciona sin Internet, así que no falla en un hospital, en un pueblo remoto o en un sótano. La misma restricción hace que la latencia se sienta instantánea.

Los familiares o cuidadores enrolan a los seres queridos una sola vez con una foto, un nombre y una descripción corta; a partir de ese momento, basta con que la cámara apunte a esa persona para que Faro responda. Por dentro: Llama 3.2 1B Instruct (Q4) formula la frase, los embeddings de ArcFace reconocen el rostro, ambos pensados para correr vía ExecuTorch y ONNX Runtime Mobile en el teléfono.

El backend FastAPI de este repo es un entorno de iteración para prompts, modelos y las abstracciones de proveedor — no es el producto.

Para el detalle completo de diseño, ver [ARCHITECTURE.md](./ARCHITECTURE.md).

![Demo del flujo de enrolación y reconocimiento](./docs/demo.gif)

*Demo del flujo: el store empieza vacío, Faro no reconoce a Rodolfo. Tras enrolarlo con `yo3.jpg`, lo identifica de nuevo en esa misma foto y también en una foto distinta (`yo.jpg`) con similitud 0.61.*

## Qué hace hoy

- Aloja Llama 3.2 1B Instruct (Q4_K_M, llama.cpp) tras una interfaz `LLMProvider`.
- Emite los tokens por SSE para que el cliente móvil pueda mostrar la frase de forma incremental.
- Enrola personas a partir de una foto, guardando **solo el embedding del rostro** (nunca la foto).
- Reconoce un rostro en una foto nueva y produce una frase corta en español o inglés vía el LLM.

## Estructura del proyecto

```
faro/
├── ARCHITECTURE.md
├── README.md
├── pyproject.toml
├── app/
│   ├── main.py                       # App FastAPI + lifespan
│   ├── settings.py                   # Variables de entorno FARO_*
│   ├── api/
│   │   ├── chat.py                   # /v1/chat/completions, /v1/chat/stream
│   │   ├── persons.py                # /v1/persons enrolar/listar/eliminar
│   │   └── recognize.py              # /v1/recognize
│   ├── providers/
│   │   ├── base.py                   # Protocolo LLMProvider, ChatMessage, TokenChunk
│   │   ├── meta_llama_mobile.py      # llama-cpp-python, defaults Q4
│   │   └── mock.py
│   ├── perception/
│   │   └── face.py                   # Protocolo FaceEmbedder + InsightFaceEmbedder
│   ├── persons/
│   │   └── store.py                  # Store de personas en JSON + similitud coseno
│   └── prompts/llama3_template.py    # Fuente única de la plantilla de chat
├── tests/                            # pytest, 8 tests
├── scripts/similarity_check.py       # comprobación empírica de precisión
├── models/                           # Pesos GGUF (gitignored, ~770 MB)
├── data/                             # Store de personas en runtime (gitignored)
└── test_data/                        # Fotos para smoke tests (gitignored, se descargan)
```

`models/`, `data/`, `test_data/` y `.venv/` están todos gitignored — se descargan de la red o se generan en runtime, así que no van en control de versiones. Ver `.gitignore` para la lista completa.

## Requisitos

- Python 3.11+
- Un fichero GGUF de Llama 3.2 1B Instruct (usamos Q4_K_M, ~770 MB)
- ~325 MB en disco para los modelos ONNX `buffalo_l` de InsightFace (se descargan automáticamente la primera vez)

## Instalación

```bash
# 1. venv en Python 3.12 (3.11+ vale)
python3.12 -m venv .venv

# 2. instalar el proyecto + extras de LLM y percepción
.venv/bin/pip install -e ".[llama-cpp,perception,dev]"

# 3. descargar los pesos de Llama 3.2 1B Instruct Q4_K_M (~770 MB)
mkdir -p models
curl -L -o models/Llama-3.2-1B-Instruct-Q4_K_M.gguf \
  "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"

# 4. (opcional) descargar las fotos de dominio público que usan
#    scripts/similarity_check.py y la tabla de precisión más abajo.
.venv/bin/python scripts/fetch_test_data.py
```

## Levantar el servidor

```bash
FARO_PROVIDER=meta-llama-mobile \
FARO_MODEL_PATH=models/Llama-3.2-1B-Instruct-Q4_K_M.gguf \
.venv/bin/uvicorn app.main:app --port 8765
```

La primera llamada a `/v1/recognize` o `/v1/persons` dispara la descarga única de los modelos de InsightFace (~325 MB en `~/.insightface/`). Los arranques siguientes son instantáneos.

Si el puerto 8765 está ocupado:
```bash
kill $(lsof -nP -iTCP:8765 -sTCP:LISTEN -t) 2>/dev/null
```

### Configuración

Todas las opciones son variables de entorno con prefijo `FARO_`:

| Variable                            | Default                                  | Notas                                  |
|-------------------------------------|------------------------------------------|----------------------------------------|
| `FARO_PROVIDER`                     | `mock`                                   | `mock` o `meta-llama-mobile`           |
| `FARO_MODEL_PATH`                   | `""`                                     | Ruta al fichero GGUF                   |
| `FARO_MODEL_ID`                     | `meta-llama/Llama-3.2-1B-Instruct`       | Lo reporta `/v1/models`                |
| `FARO_QUANTIZATION`                 | `Q4_K_M`                                 | Lo reporta `/v1/models`                |
| `FARO_N_CTX`                        | `4096`                                   | Ventana de contexto                    |
| `FARO_PERSONS_DB_PATH`              | `data/persons.json`                      | Dónde viven las personas enroladas     |
| `FARO_FACE_SIMILARITY_THRESHOLD`    | `0.5`                                    | Umbral de similitud coseno             |

## API

| Método | Ruta                    | Función                                                |
|--------|-------------------------|--------------------------------------------------------|
| GET    | `/healthz`              | Liveness                                               |
| GET    | `/v1/models`            | Proveedor activo, id de modelo, cuantización           |
| POST   | `/v1/chat/completions`  | Completion de chat puntual                             |
| POST   | `/v1/chat/stream`       | Stream de tokens por SSE                               |
| POST   | `/v1/persons`           | Enrolar una persona (multipart: `name`, `description`, `image`) |
| GET    | `/v1/persons`           | Listar personas enroladas                              |
| DELETE | `/v1/persons/{id}`      | Eliminar una persona                                   |
| POST   | `/v1/recognize`         | Reconocer un rostro en una imagen (multipart: `image`, `language`) |
| GET    | `/openapi.json`         | Esquema OpenAPI 3.1 (fuente para codegen del cliente)  |
| GET    | `/docs`                 | Swagger UI                                             |

### Ejemplos

Completion de chat:
```bash
curl -s -X POST http://127.0.0.1:8765/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "messages": [
      {"role": "system", "content": "Responde en una sola frase corta."},
      {"role": "user",   "content": "¿Cuál es la capital de Japón?"}
    ],
    "max_tokens": 64,
    "temperature": 0.2
  }'
```

Streaming (SSE):
```bash
curl -sN -X POST http://127.0.0.1:8765/v1/chat/stream \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"Enumera tres razones para correr un LLM localmente."}],"max_tokens":120}' \
  | sed -u -n 's/^data: //p' \
  | jq -j '.delta, (if .done then "\n[done: \(.stop_reason)]\n" else "" end)'
```

Enrolar una persona:
```bash
curl -s -X POST http://127.0.0.1:8765/v1/persons \
  -F "name=Rodolfo Campos" \
  -F "description=tu hijo mayor" \
  -F "image=@/ruta/a/foto.jpg"
```

Reconocer un rostro:
```bash
curl -s -X POST http://127.0.0.1:8765/v1/recognize \
  -F "language=es" \
  -F "image=@/ruta/a/foto.jpg" | jq
```

Una respuesta exitosa:
```json
{
  "match": {
    "id": "171c25a5d3ff",
    "name": "Albert Einstein",
    "description": "tu abuelo paterno",
    "similarity": 0.5965
  },
  "spoken": "Ese es Albert Einstein, tu abuelo paterno."
}
```

Si no se detecta ningún rostro: `match: null, spoken: "No veo a ninguna persona en la imagen."`
Si se detecta un rostro pero no hace match con nadie enrolado: `match: null, spoken: "No reconozco a esta persona."`

## Privacidad: qué se guarda

**Las fotos nunca se escriben a disco.** Cuando llamas a `POST /v1/persons` o `POST /v1/recognize`:

1. Los bytes de la imagen viven en memoria solo durante la petición HTTP.
2. Se calcula un embedding de ArcFace (512 floats).
3. Solo el embedding y los campos estructurados (`id`, `name`, `description`) se persisten en `data/persons.json`. Los bytes de la imagen se descartan.

Los embeddings son un resumen de baja dimensión y con pérdida del rostro. Reconstruir la foto original a partir de un embedding no es viable de forma casual; técnicas avanzadas de ML adversarial pueden producir una *aproximación* del rostro, pero requieren un esfuerzo deliberado y caen fuera del modelo de amenaza habitual.

### Borrar datos

- Una persona: `DELETE /v1/persons/{id}`
- Todas las personas enroladas: `rm data/persons.json` (se recrea vacío al siguiente arranque)
- Modelos de visión cacheados (InsightFace): `rm -rf ~/.insightface/`

## Precisión

Medida empírica con tres fotos distintas de Albert Einstein (dominio público) y una de Marie Curie como control negativo:

| Pareja                                                   | Sim. coseno | Veredicto (umbral 0.5) |
|----------------------------------------------------------|-------------|------------------------|
| Einstein 1921 (enrolada) vs. Einstein 1920               | **+0.5965** | match                  |
| Einstein 1921 (enrolada) vs. Einstein 1921 re-crop       | **+0.5602** | match                  |
| Einstein 1921 (enrolada) vs. Marie Curie                 | **+0.0129** | no match               |

Para reproducirlo:
```bash
.venv/bin/python scripts/fetch_test_data.py   # si aún no las has descargado
.venv/bin/python scripts/similarity_check.py
```

La misma persona en fotos distintas se sitúa cómodamente sobre el umbral de 0.5; una persona distinta se queda cerca de cero. La separación es amplia.

**Casos donde el umbral puede fallar:**
- Diferencia grande de edad entre la foto de enrolación y la de reconocimiento
- Gafas en una foto y no en la otra
- Iluminación o ángulos extremos (perfil vs. frontal)
- Rostros muy pequeños, borrosos o parcialmente tapados

Si los casos límite dan falsos negativos, baja el umbral:
```bash
FARO_FACE_SIMILARITY_THRESHOLD=0.4 .venv/bin/uvicorn app.main:app --port 8765
```

**Mejora futura de robustez** (no implementada): enrolar varias fotos por persona y promediar los embeddings. Unas 20 líneas en `PersonStore`. Aporta mucha más tolerancia a pose, iluminación y edad sin tener que tocar el umbral.

## Hacia dónde va: el teléfono primero

Este backend es un sustituto temporal. El producto real corre en el teléfono:

- `LLMProvider` se reimplementará en Kotlin/Swift como `ExecuTorchLlamaProvider`, cargando los mismos pesos de Llama 3.2 a través de ExecuTorch.
- `FaceEmbedder` se reimplementará en el teléfono vía ONNX Runtime Mobile cargando los mismos modelos ONNX de ArcFace que ya usamos aquí.
- `PersonStore` pasará a SQLite local en el dispositivo.

Mismos protocolos, misma plantilla de prompts, mismas formas de OpenAPI — el playground se mantiene como un proxy fiel del frontend móvil.

**Otros frontends posibles a futuro.** El motor que corre en el teléfono no fuerza un único formato de interfaz. Una app móvil tradicional es el primer frente; gafas inteligentes (con la cámara y un audio o HUD discreto como salida), un dispositivo doméstico, o una integración con audífonos son formas adicionales que comparten exactamente el mismo backend on-device. Cada una se considerará cuando el frente móvil esté estable.

## Tests

```bash
.venv/bin/pytest -q
```

Ocho tests cubren el contrato del proveedor de LLM, la plantilla de chat y la superficie HTTP usando `MockProvider`. El camino de reconocimiento facial se ejercita a mano con `scripts/similarity_check.py` — automatizarlo bajo pytest requeriría cargar los ~325 MB de modelos de InsightFace en cada sesión, cosa que aún no hemos hecho.

## Limitaciones conocidas

- Solo se considera un rostro por imagen — el más grande por área del bounding box. No hay manejo de fotos de grupo.
- El modelo 1B de Llama es sensible al fraseo del prompt; el flujo de reconocimiento usa ejemplos few-shot en turnos alternados de usuario/asistente y replantea la tarea como rellenado de plantilla en vez de identificación, lo que esquiva un patrón de rechazo por seguridad que encontramos durante el desarrollo. Pasar al modelo 3B relajaría esta restricción.
- Arranque en frío: la primera llamada a `/v1/recognize` después del arranque del servidor paga ~1 s por la carga de InsightFace, más ~1 s por la carga del Llama Q4. Las llamadas siguientes responden en pocos cientos de ms.
- El fraseo en español siempre abre con `Ese es` porque coincide con nuestros ejemplos few-shot. Gramaticalmente a veces debería ser `Esa es`. Un modelo 1B no es lo bastante fiable para inferir el género a partir del nombre; uno 3B sí.
- Sin autenticación, sin rate limiting, sin multi-tenancy. Esto es un entorno de desarrollo para un único usuario.
