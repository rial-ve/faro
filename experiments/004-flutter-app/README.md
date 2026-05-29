# Experimento 004 — App Flutter con face embedding on-device

**Estado:** ✅ Validado con matices
**Periodo:** 2026-05-29
**Depende de:** experimento 003 (MobileFaceNet en el servidor)
**Desbloquea:** experimento 005 (alineación 5-puntos on-device)

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
| 004.6 | Detección de rostro con `google_mlkit_face_detection` + overlay del bounding box | `bf1c8d7` |
| 004.7 | Embedding on-device con `tflite_flutter` (mobilefacenet.tflite, cos(onnx,tflite)=1.000000 vs servidor) | `4aec7f7` |
| 004.8 | POST embedding al endpoint nuevo + render del match + timings de embed/match en pantalla | `2bd04ef` |
| 004.9 | `flutter_tts` en es-ES, espera a que termine antes de habilitar siguiente captura | `aff00bf` |
| 004.10| Smoke offline + SMOKE.md con procedimiento en teléfono. Hallazgo de alineación expuesto (matriz 4 filas) | `d1aeb46` |
| 004.11| Learning Card cerrada con la fila 3 del smoke como ancla del próximo experimento | _esta carta_ |
