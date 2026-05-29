# Experimento 003 — Migración del face embedder a MobileFaceNet

**Estado:** 🟡 en curso
**Periodo:** 2026-05-29 → _en progreso_
**Bloqueante para:** experimento 004 (app Flutter con embedding on-device)

## Resumen

Probamos si un modelo de embedding facial de la familia MobileFaceNet (~5–15 MB) preserva calidad suficiente para nuestro caso de uso, a cambio de poder correrlo en un teléfono. Hoy el servidor usa `buffalo_l` (166 MB, ResNet-50), que no es desplegable on-device.

El experimento mantiene `InsightFaceEmbedder` viva en paralelo durante toda la fase de validación, alterna por setting, y mide los dos lado a lado sobre el mismo fixture.

## Cartas

- [Test Card](./test-card.md) — la hipótesis y el plan (escrita antes de implementar)
- Learning Card — _pendiente_

## Evidencia

_Se irá rellenando a medida que el experimento avance:_

### 003.2 — Modelo elegido ✅

**MobileFaceNet de InsightFace `buffalo_s`**, fichero `w600k_mbf.onnx`.

- **Fuente:** [`deepinsight/insightface`](https://github.com/deepinsight/insightface), distribuido como parte del paquete `buffalo_s`
- **Arquitectura:** MobileFaceNet
- **Entrenamiento:** Webface600k (el mismo dataset que `buffalo_l`, lo que minimiza variables entre los dos en la comparación)
- **Tamaño:** 13.0 MB
- **Dimensión de embedding:** 512-d (idéntica a `buffalo_l`, no requiere cambios en `Person.embedding` ni en `Match`)
- **Input shape:** 1×3×112×112, normalización 127.5/127.5 (idéntico al pipeline actual)
- **Licencia:** MIT (la del proyecto InsightFace)
- **SHA-256 del fichero:** `9cc6e4a75f0e2bf0b1aed94578f144d15175f357bdc05e815e5c4a02b319eb4f`
- **Detector emparejado en buffalo_s:** `det_500m.onnx` (2.4 MB)
- **Footprint combinado detección + reconocimiento:** **15.4 MB** (frente a ~182 MB de buffalo_l, una reducción de **12×**)

Razón de elegir esta variante sobre otras MobileFaceNet del ecosistema: mismo autor, mismo dataset y misma API de carga que `buffalo_l`, lo que hace la comparación A/B una variable única (arquitectura) en vez de varias confundidas.

### Pendientes

- Código de `MobileFaceNetEmbedder`: _pendiente (003.3)_
- Setting `FARO_FACE_EMBEDDER`: _pendiente (003.4)_
- Datos comparativos de precisión: _pendiente (003.5)_
- Decisión final + commit: _pendiente (003.6–003.7)_
