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

### Cerrados

| Punto | Entregable                                                                  | Commit    |
|-------|-----------------------------------------------------------------------------|-----------|
| 004.1 | Test Card publicada + scaffolding del experimento                           | _este commit_ |
