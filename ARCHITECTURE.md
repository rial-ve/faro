# Faro — Architecture

> Engineering design notes for contributors. The user-facing description lives in [README.md](./README.md).

## 1. Product stance

Faro is a **memory companion for people living with Alzheimer's, dementia, or memory loss after a brain injury.** Given a photo of a familiar face, it produces a short spoken sentence identifying that person and their relationship to the user — *"Ese es Rodolfo, tu hijo mayor."*

Three constraints follow from that audience and shape every technical decision below:

- **Privacy.** Family photos, names, and relationships are sensitive data, especially for users whose ability to consent to data sharing may be impaired. Inference runs on the user's device by default; no captured image and no embedding leaves the phone.
- **Latency.** A delayed cue is a useless cue in conversation. No cloud round-trip in the hot path.
- **Offline.** The product must work without connectivity — hospitals, basements, rural settings, in-flight, anywhere.

The **HTTP backend in this repo is a development harness only.** It exists so we can iterate on prompts, evals, and the provider abstractions against a hosted Llama and a hosted face embedder before the same interfaces ship to the phone. It is **not** the long-term inference path.

## 2. Where compute actually runs

The phone is the primary frontend and the only target host for inference.

```
┌──────────────────────────────────────────────────────────┐
│ Phone app (Android first, then iOS)                       │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Camera capture → FaceEmbedder (ArcFace, ONNX Runtime)│ │
│ │                ↓                                      │ │
│ │              PersonStore (local SQLite)               │ │
│ │                ↓                                      │ │
│ │          LLMProvider (Llama 3.2 Q4, ExecuTorch)       │ │
│ │                ↓                                      │ │
│ │              Audio / on-screen prompt                 │ │
│ └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
                          ▲
                          │ same protocols, same prompts, same OpenAPI shapes
                          │ (dev-time only, not production hot path)
                          │
┌──────────────────────────────────────────────────────────┐
│ Backend harness (FastAPI, this repo)                      │
│ • MetaLlamaMobileProvider via llama-cpp-python (Q4 GGUF)  │
│ • InsightFaceEmbedder via insightface / ONNX Runtime      │
│ • PersonStore (JSON file)                                  │
│ • Prompt iteration, eval, debugging                       │
└──────────────────────────────────────────────────────────┘
```

The backend mirrors the phone's interfaces and constraints: same chat template, same context window, same sampling defaults, same stop tokens, same ArcFace model, same cosine threshold. The point is that anything we prove in the harness transfers verbatim to the on-device implementation.

### Other frontends, considered explicitly but deferred

The engine doesn't force a single interaction surface. Once the phone-first frontend is stable, the same on-device backend could power:

- **Smart glasses** (e.g. Meta Ray-Ban or successors) as a camera + audio/HUD peripheral, with the model still running on the paired phone. As of writing, Meta has no general third-party app runtime on Ray-Ban Meta; the Wearables Device Access Toolkit is gated. To revisit when the platform opens up.
- **Stationary devices** at home — a TV-bar form factor near the entryway, for example, that announces visitors.
- **Hearing aids / earbuds** with a microphone-driven trigger.

These are deliberately out of scope for the MVP. They share the engine, so adding one is a frontend project, not an architecture change.

## 3. Model targets

| Stage              | Component       | Model                                | Footprint  | Runtime                |
|--------------------|------------------|--------------------------------------|------------|------------------------|
| Phone target       | Language model  | Llama 3.2 1B Instruct (Q4)           | ~770 MB    | ExecuTorch             |
| Phone target       | Face embedder   | MobileFaceNet (buffalo_s `w600k_mbf`) | 13 MB     | ONNX Runtime Mobile / TFLite |
| Quality fallback   | Language model  | Llama 3.2 3B Instruct (Q4)           | ~1.9 GB    | ExecuTorch             |
| Backend harness    | Language model  | Llama 3.2 1B Instruct (Q4_K_M GGUF)  | 770 MB     | llama-cpp-python       |
| Backend harness    | Face embedder   | MobileFaceNet (default) or buffalo_l (A/B) | 13 MB / 166 MB | ONNX Runtime (CPU) |

We start at **1B Q4** on the LLM side because the gap to "feels instant" is small, the 1B weights fit comfortably in mobile memory and disk budgets, and the export → quantize → deploy pipeline is identical to the 3B path. If 1B fails the eval bar we move to 3B and accept the battery / memory cost.

On the face side we run **MobileFaceNet** (`buffalo_s/w600k_mbf.onnx`, 13 MB, 512-d embedding) as the default. The decision came out of [experiment 003](../experiments/003-mobilefacenet-swap/): MobileFaceNet preserves the same-vs-different-person separation we need while staying mobile-deployable. `buffalo_l` (166 MB, ResNet-50) stays selectable via `FARO_FACE_EMBEDDER=insightface-buffalo_l` for benchmarking, but the prod path is MobileFaceNet on both server and phone — same model on both sides is a hard requirement for the embeddings to be comparable.

**Data caveat from the swap:** embeddings from `buffalo_l` and `mobilefacenet` live in independent vector spaces despite having the same 512-d shape. Switching `FARO_FACE_EMBEDDER` makes any previously-enrolled `data/persons.json` un-matchable; people must be re-enrolled.

## 4. Two on-device abstractions

The harness and the phone implementations depend on the same two protocols.

### `LLMProvider`

```python
class LLMProvider(Protocol):
    name: str
    model_id: str
    quantization: str

    async def generate(self, messages, *, max_tokens, temperature, stop) -> GenerationResult: ...
    def stream(self, messages, *, max_tokens, temperature, stop) -> AsyncIterator[TokenChunk]: ...
```

Implementations:

- **`MetaLlamaMobileProvider`** (this repo, Python) — wraps `llama-cpp-python` with a Q4 GGUF. **Intentionally not a multi-vendor router.** It mirrors phone constraints exactly so the harness stays a faithful proxy: same prompt template, context window, sampling defaults, stop tokens. Not a generic "call any model" wrapper.
- **`MockProvider`** (this repo) — deterministic, dependency-free responses for unit tests and CI.
- **`ExecuTorchLlamaProvider`** (future, on the phone, Kotlin/Swift) — same protocol, ExecuTorch runtime, same weights.

### `FaceEmbedder`

```python
class FaceEmbedder(Protocol):
    name: str
    def embed(self, image_bytes: bytes) -> np.ndarray | None: ...   # 512-d L2-normalized, or None
```

Implementations:

- **`MobileFaceNetEmbedder`** (this repo, Python — default) — wraps `insightface` `buffalo_s` running on ONNX Runtime CPU. Returns the largest detected face's 512-d embedding. Selected by [experiment 003](../experiments/003-mobilefacenet-swap/) as the model that runs on both server and phone.
- **`InsightFaceEmbedder`** (this repo, Python) — same Protocol, wraps `insightface` `buffalo_l` (ResNet-50, 166 MB). Kept as a server-only alternative for benchmarking; selectable via `FARO_FACE_EMBEDDER=insightface-buffalo_l`.
- Future on-device implementation in Kotlin/Swift over ONNX Runtime Mobile (or TFLite, post-conversion) loads the same `w600k_mbf.onnx` we already use here.

The provider abstractions are **the** architectural contract. Anything that needs to vary between server and device is hidden behind them; anything that should stay the same (prompts, thresholds, schemas) sits above them.

### What the abstractions are *not*

- Not multi-vendor routers (no OpenAI / cloud face APIs / etc. fallbacks). Adding those would let the harness drift from on-device reality, which would defeat the harness's only purpose.
- Not feature-flag layers for end-user model selection. Model choice is a deployment decision, not a runtime one.

## 5. Person store

Enrolled people live in a tiny store keyed by id, with `(name, description, embedding)` per row. Implementations:

- **JSON file** (this repo) — `data/persons.json`, linear-scan cosine similarity, thread-safe writes. Adequate up to several thousand entries, vastly more than a real user will ever enrol.
- **SQLite** (future, on-device) — same shape, same cosine-similarity match, durable storage.

Matching is L2-normalized cosine similarity with a configurable threshold (default 0.5). Empirically validated: same-person-different-photo lands at ~0.55–0.60, different-person near 0.01 (see `scripts/similarity_check.py` and the README accuracy table).

## 6. Backend API surface

Minimal. Only what we need to iterate the prompts and the perception pipeline. Routes split into two trust tiers:

**Carer-side** (gated by HTTP Basic Auth via the `admin_required` dependency in `app/security.py`):

| Method | Path                              | Purpose                                              |
|--------|-----------------------------------|------------------------------------------------------|
| GET    | `/v1/models`                      | Active provider, model id, quantization              |
| POST   | `/v1/chat/completions`            | One-shot chat completion                             |
| POST   | `/v1/chat/stream`                 | SSE token stream                                     |
| POST   | `/v1/persons`                     | Direct enrolment by the carer                        |
| GET    | `/v1/persons`                     | List enrolled people (filterable by `status`)        |
| DELETE | `/v1/persons/{id}`                | Remove or reject a person                            |
| POST   | `/v1/persons/{id}/approve`        | Promote a pending person to `active`                 |
| POST   | `/v1/recognize`                   | Image → match + LLM-phrased spoken response          |
| POST   | `/v1/enrollment-tokens`           | Create a shareable enrolment token                   |
| GET    | `/v1/enrollment-tokens`           | List active tokens                                   |
| DELETE | `/v1/enrollment-tokens/{id}`      | Revoke a token                                       |

**Public** (intentionally open — these are what an invited family member touches via a WhatsApp link):

| Method | Path                    | Purpose                                                          |
|--------|-------------------------|------------------------------------------------------------------|
| GET    | `/healthz`              | Liveness                                                         |
| GET    | `/enroll/{token}`       | Self-enrolment HTML form. Token validates the request.           |
| POST   | `/enroll/{token}`       | Submit photo + name + description. Photo bytes never persisted.  |

The token in the URL is the authorisation for the public flow; it does not interact with Basic Auth. The two mechanisms are intentionally separate so the public form stays single-click from WhatsApp.

OpenAPI 3.1 is the source of truth. The mobile client will codegen request/response types from `/openapi.json` so the on-device frontend and the harness stay in lockstep on shapes.

### Security model

- Admin credentials come from `FARO_ADMIN_USERNAME` and `FARO_ADMIN_PASSWORD`. If either is empty, all carer routes return **503 Service Unavailable** (fail-closed) — we never silently fall through to "no auth".
- Credentials are compared with `secrets.compare_digest` to avoid timing side channels.
- One shared admin secret per deployment. No per-user identity yet. The day this needs to support multiple carers (e.g. a clinic), the single `admin_required` dependency is the only swap-out point — replace with OIDC and the rest of the architecture is unaffected.
- This is enough security for a localhost / private-network deployment. Any public exposure **must** terminate TLS in front of uvicorn (Caddy / Nginx + Let's Encrypt). Basic Auth over plain HTTP is trivially sniffable.

## 7. Stack

- **Language:** Python 3.11+
- **Web:** FastAPI + Uvicorn
- **LLM (harness):** `llama-cpp-python` over a Q4_K_M GGUF. We dropped the planned `transformers` backend — Q4 via llama.cpp is closer to what the phone will run and the iteration loop is faster.
- **Face (harness):** `insightface` over ONNX Runtime (CPU).
- **Schema:** Pydantic v2, exported via FastAPI's OpenAPI.
- **Config:** `pydantic-settings`, env-driven (`FARO_*`).
- **Testing:** `pytest` + `httpx.AsyncClient`, `MockProvider` for hermetic tests.

We chose Python because the Llama / ExecuTorch tooling is Python-native, and the harness will also host evals and quantization experiments that are cleanest in Python.

## 8. Prompt-engineering decisions

Two non-obvious decisions came out of working with the 1B model:

1. **The recognition prompt is framed as a template-fill task, not as "identification."** Asking a 1B Llama to "identify a person" triggers safety refusals ("Lo siento, pero no puedo cumplir con esa solicitud"). Reframing as "combine two fields using this exact template" sidesteps it entirely.
2. **Few-shot examples are passed as alternating user/assistant turns, not as a single system block.** At this model size, in-context examples in dialogue form lock onto the output format reliably at `temperature=0.0`; the same examples crammed into a system prompt are ignored about half the time.

Both decisions are encoded in `app/api/recognize.py`. Moving to a 3B model would likely relax both constraints; we'll re-test when we do.

## 9. Repo layout

```
faro/
├── ARCHITECTURE.md
├── README.md
├── pyproject.toml
├── app/
│   ├── main.py                       # FastAPI app + lifespan
│   ├── settings.py                   # FARO_* env vars
│   ├── api/
│   │   ├── chat.py
│   │   ├── persons.py
│   │   └── recognize.py
│   ├── providers/
│   │   ├── base.py                   # LLMProvider Protocol + types
│   │   ├── meta_llama_mobile.py
│   │   └── mock.py
│   ├── perception/
│   │   └── face.py                   # FaceEmbedder Protocol + InsightFaceEmbedder
│   ├── persons/
│   │   └── store.py                  # Person + Match + PersonStore
│   └── prompts/llama3_template.py
├── tests/
├── scripts/
│   ├── fetch_test_data.py
│   └── similarity_check.py
├── models/                           # Llama GGUF (gitignored)
├── data/                             # PersonStore JSON (gitignored)
└── test_data/                        # smoke-test photos (gitignored)
```

## 10. Out of scope for the MVP

- On-device deployment itself (will live in a separate mobile repo).
- Authentication, multi-tenancy, rate limiting.
- Cloud fallback when on-device inference fails (would re-introduce the very thing this stance rejects).
- RAG, tool use, multimodal LLM input. Revisit after the basic recognition loop ships on-device.
- Multiple faces per image, group photos.
- Gender-aware grammar in Spanish (`Ese` vs. `Esa`) — needs a model larger than 1B to dispatch from a name.

## 11. Open questions

1. **Eval set.** We need a small, fixed eval set (recognition correctness + spoken-cue quality) before we can pick between 1B and 3B with confidence.
2. **Multi-photo enrollment.** Averaging several embeddings per person should make recognition robust across age / lighting / glasses variation without lowering the similarity threshold. Roughly 20 lines in `PersonStore`. Worth doing before user testing.
3. **Model distribution to the phone.** Bundled in the APK/IPA, or downloaded on first launch with a progress UI? The full Llama 1B Q4 is ~770 MB; the ArcFace ONNX is another ~170 MB. Probably the latter, but it changes onboarding UX.
4. **Mobile face-embedder choice.** `buffalo_l` is overkill on a phone. MobileFaceNet or a smaller ArcFace variant is likely the right swap. Run an A/B against `buffalo_l` numbers from the harness before committing.
