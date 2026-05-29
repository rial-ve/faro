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

- Modelo elegido y su procedencia: _pendiente (punto 003.2)_
- Código de `MobileFaceNetEmbedder`: _pendiente (003.3)_
- Setting `FARO_FACE_EMBEDDER`: _pendiente (003.4)_
- Datos comparativos de precisión: _pendiente (003.5)_
- Decisión final + commit: _pendiente (003.6–003.7)_
