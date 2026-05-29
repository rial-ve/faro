# Experimento 003 — Migración del face embedder a MobileFaceNet

**Estado:** ✅ Validado
**Periodo:** 2026-05-29
**Desbloquea:** experimento 004 (app Flutter con embedding on-device)

## Resumen

Probamos si un modelo de embedding facial de la familia MobileFaceNet (~5–15 MB) preserva calidad suficiente para nuestro caso de uso, a cambio de poder correrlo en un teléfono. Hoy el servidor usa `buffalo_l` (166 MB, ResNet-50), que no es desplegable on-device.

El experimento mantiene `InsightFaceEmbedder` viva en paralelo durante toda la fase de validación, alterna por setting, y mide los dos lado a lado sobre el mismo fixture.

## Cartas

- [Test Card](./test-card.md) — la hipótesis y el plan (escrita antes de implementar)
- [Learning Card](./learning-card.md) — observaciones, decisión, siguientes pasos

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

### Cerrados

| Punto | Entregable                                                                  | Commit    |
|-------|-----------------------------------------------------------------------------|-----------|
| 003.3 | `MobileFaceNetEmbedder` implementado en `app/perception/face.py`            | `115cc85` |
| 003.4 | Setting `FARO_FACE_EMBEDDER` + `build_face_embedder()` + tests              | `9120c06` |
| 003.4b| Default flipeado a `mobilefacenet`                                          | `cafbfe2` |
| 003.5 | Script comparativo A/B con datos validando los criterios                    | `46d7ff4` |
| 003.6 | Threshold default 0.5 → 0.45 + README + ARCHITECTURE actualizados           | `b14c56d` |
| 003.7 | Learning Card cerrada                                                       | _esta carta_ |
