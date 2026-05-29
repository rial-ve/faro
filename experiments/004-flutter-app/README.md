# Experimento 004 — App Flutter con face embedding on-device

**Estado:** 🟡 En curso
**Periodo:** 2026-05-29 → en curso
**Depende de:** experimento 003 (MobileFaceNet en el servidor)

## Resumen

Llevamos Faro al teléfono. App Flutter que captura un rostro, **calcula el embedding directamente en el dispositivo** con `mobilefacenet.tflite`, envía sólo el vector de 512 floats al servidor, recibe nombre y relación, y los dice en voz alta. La foto nunca sale del teléfono.

El experimento 003 dejó al servidor corriendo el mismo MobileFaceNet que correrá en el teléfono, así que ambos producen embeddings en el mismo espacio vectorial y el match es directo.

## Cartas

- [Test Card](./test-card.md) — la hipótesis y el plan (escrita antes de implementar)
- [Learning Card](./learning-card.md) — observaciones, decisión, siguientes pasos (al cierre)

## Evidencia

_Se irá rellenando a medida que el experimento avance._

### 004.3 — Decisión: monorepo

**Monorepo**, app Flutter en `app-flutter/` dentro de `faro`. Decidido por fiat sin commit propio. Tradeoff considerado: monorepo facilita commits coordinados backend ↔ app durante el desarrollo intenso de 004.4–004.8; el riesgo de arrastrar el toolchain de Flutter al CI del backend Python se mitiga con `paths-ignore` en GitHub Actions cuando exista CI.

### Cerrados

| Punto | Entregable                                                                  | Commit    |
|-------|-----------------------------------------------------------------------------|-----------|
| 004.1 | Test Card publicada + scaffolding del experimento                           | `b3e9fb7` |
| 004.2 | Endpoint `POST /v1/recognize-embedding` + 6 tests con `MockEmbedder` pattern | `813c6d3` |
| 004.4 | Flutter scaffold en `app-flutter/`, credenciales en secure storage, probe `/healthz` + `/v1/models` | `b2aa76c` |
| 004.5 | Captura con `image_picker` (cámara y galería), preview y Info.plist iOS | `f78fb02` |
| 004.6 | Detección de rostro con `google_mlkit_face_detection` + overlay del bounding box | _este commit_ |
