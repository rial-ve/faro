# Test Card — 001 MVP backend

> Esta tarjeta fue formalizada después de la ejecución, ya que es el primer experimento del proyecto. Representa la hipótesis implícita con la que se arrancó. A partir del 002 las tarjetas se escriben antes.

## Hipótesis

**Creemos que** un asistente de memoria local-first es técnicamente viable hoy:

- Llama 3.2 1B Instruct cuantizado a 4 bits tiene footprint y latencia suficientes para correr en un teléfono moderno y producir una frase corta en menos de un segundo.
- ArcFace puede reconocer un rostro conocido a partir de una sola foto de enrolación con precisión suficiente para uso real.
- Ambas piezas componen un flujo end-to-end (cámara → embedding → match → frase hablada) sin sacrificar la garantía de que nada sale del dispositivo.

## Verificación

**Para verificarlo:**

- Construiremos un backend FastAPI con abstracciones `LLMProvider` y `FaceEmbedder` que mirroreen los contratos que tendrá el cliente móvil.
- Cargaremos Llama 3.2 1B Q4_K_M vía `llama-cpp-python` (mismo formato cuantizado que correrá en el teléfono vía ExecuTorch).
- Cargaremos ArcFace `buffalo_l` vía `insightface` sobre ONNX Runtime (mismo formato que correrá vía ONNX Runtime Mobile).
- Implementaremos los endpoints `/v1/persons` (enrolación) y `/v1/recognize` (reconocimiento), donde el segundo devuelve la frase generada por el LLM.
- Probaremos con fotos públicas: tres de Albert Einstein de épocas distintas más una de Marie Curie como control negativo.

## Mediciones

**Mediremos:**

| Métrica                                | Cómo                                                       |
|----------------------------------------|------------------------------------------------------------|
| Footprint en disco del LLM             | `ls -lh models/*.gguf`                                     |
| Footprint en disco del face embedder   | `du -sh ~/.insightface/models/`                            |
| Latencia cold (primera petición)       | `time curl /v1/recognize` justo después del arranque       |
| Latencia warm                          | `time curl /v1/recognize` con el servidor caliente         |
| Separación de similitud coseno         | `scripts/similarity_check.py` (3 Einstein + 1 Curie)       |
| Calidad del fraseo en español          | Inspección manual de respuestas con distintos prompts      |

## Criterio de éxito

**Tendremos razón si:**

- Footprint combinado (LLM + face embedder) **< 1.5 GB** — target razonable para distribución on-first-launch en una APK/IPA.
- Latencia warm end-to-end **< 1 segundo** en CPU.
- Similitud para la misma persona **> 0.5**; similitud para personas distintas **< 0.2**.
- El LLM produce la frase con el formato esperado (`"<verbo> <nombre>, <descripción>."`) en **el 80% o más** de los intentos.
