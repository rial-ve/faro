# Experimento 001 — MVP backend

**Estado:** ✅ Validado con matices
**Periodo:** 2026-05-25 → 2026-05-26
**Nota:** documentación retroactiva. Este es el primer experimento del proyecto y sirve también como plantilla para los siguientes. A partir del 002, las tarjetas se escriben antes de ejecutar.

## Resumen

Probamos si un asistente de memoria local-first es construible hoy con tecnología abierta: Llama 3.2 1B Instruct (Q4) para la generación de la frase hablada, ArcFace (`buffalo_l`, ONNX) para el reconocimiento facial, ambos servidos por un backend FastAPI que actúa como banco de pruebas del futuro frontend móvil.

## Cartas

- [Test Card](./test-card.md) — la hipótesis y el plan
- [Learning Card](./learning-card.md) — lo que observamos y aprendimos

## Evidencia

- **Código:** commits [`cc616e0`](https://github.com/rial-ve/faro/commit/cc616e0) (backend + perception) y [`444a121`](https://github.com/rial-ve/faro/commit/444a121) (demo grabado)
- **Demo del flujo:** [`docs/demo.gif`](../../docs/demo.gif)
- **Datos de precisión:** tabla en el [README principal](../../README.md#precisión), reproducible con [`scripts/similarity_check.py`](../../scripts/similarity_check.py)
- **Diseño técnico:** [ARCHITECTURE.md](../../ARCHITECTURE.md)
