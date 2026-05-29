# Test Card — 003 MobileFaceNet swap

## Hipótesis

**Creemos que** un modelo de embedding facial de la familia **MobileFaceNet** (~5–15 MB, derivado del paradigma ArcFace pero diseñado para móvil) preserva calidad de reconocimiento suficiente para distinguir a personas conocidas en un contexto familiar — y nos abre la puerta a correr el embedding **directamente en el teléfono**.

Esto es prerrequisito del experimento 004 (app Flutter): el teléfono y el servidor deben producir embeddings en el **mismo espacio vectorial**, lo cual hoy no ocurre porque el servidor usa `buffalo_l` (ResNet-50, 166 MB), que no es desplegable en un móvil.

## Verificación

**Para verificarlo:**

- Implementaremos `MobileFaceNetEmbedder` como segunda implementación del Protocol `FaceEmbedder`, **dejando viva** la `InsightFaceEmbedder` existente para poder comparar.
- Añadiremos un setting `FARO_FACE_EMBEDDER` que alterna entre `insightface-buffalo_l` y `mobilefacenet`. Permite A/B local sin tocar código.
- Extenderemos `scripts/similarity_check.py` para correr **ambos modelos sobre las mismas fotos** y emitir las dos tablas lado a lado, con el delta entre ellas.
- Las fotos son las cuatro que ya usa el experimento 001: tres Einstein de épocas distintas (1920, 1921, 1921 re-crop) + Marie Curie como control negativo. Mismos datos, distinto modelo: el efecto es puro.
- Decidiremos si el umbral 0.5 sigue siendo el adecuado o si MobileFaceNet desplaza la distribución y requiere ajuste.
- Si el modelo pasa el criterio de éxito, cambiamos el default a `mobilefacenet`, documentamos que los `persons.json` existentes quedan **incompatibles** (los embeddings viven en otro espacio vectorial), y dejamos `insightface-buffalo_l` como opción reactivable.

## Mediciones

**Mediremos:**

| Métrica                                                | Cómo                                                       |
|--------------------------------------------------------|------------------------------------------------------------|
| Footprint en disco del modelo                          | `ls -lh` del fichero ONNX                                  |
| Latencia de embedding por rostro                       | `time` sobre 10 ejecuciones, calentado, en CPU             |
| Similitud coseno misma persona (3 pares Einstein)      | `scripts/similarity_check.py` extendido                    |
| Similitud coseno persona distinta (Einstein vs Curie)  | mismo script                                               |
| Gap de separación (mín. misma vs máx. distinta)        | calculado del anterior                                     |
| Dimensión del embedding                                | propiedad del modelo (192 o 512 típicamente)               |
| Modelo concreto elegido y su procedencia               | documentado en la Learning Card (autor, repo, commit SHA del fichero, licencia) |

## Criterio de éxito

**Tendremos razón si**, con el modelo MobileFaceNet elegido:

- **Similitud para la misma persona ≥ 0.4** en al menos 2 de los 3 pares (Einstein 1921 vs 1920, 1921 vs 1921-recrop). Margen claro sobre cualquier umbral razonable.
- **Similitud para persona distinta < 0.2** (Einstein vs Curie). Lo ideal es < 0.1, en línea con lo que mide buffalo_l hoy (0.0129).
- **Gap de separación > 0.2** entre el mínimo de misma persona y el máximo de persona distinta. Suficiente para sostener un umbral con seguridad.
- **Footprint del modelo < 20 MB**. Razonable para bundlear en una APK/IPA.
- **Latencia de embedding < 100 ms** por rostro en CPU (Mac M-series). Si esto vale en CPU del servidor, en el teléfono con GPU delegate de TFLite estará en el rango de 30–50 ms.

## Criterio de invalidación

**Lo descartamos si:**

- La similitud misma persona cae bajo 0.3 en alguno de los pares (forzaría umbral inseguro).
- El gap entre misma y distinta cae bajo 0.15 (riesgo serio de falsos positivos).
- El footprint pasa de 25 MB (problemas de distribución en móvil).
- La latencia pasa de 500 ms en CPU (mal augurio para móvil real).

Si MobileFaceNet falla, las opciones inmediatas son: probar otra variante de la misma familia, o aceptar un modelo algo más grande de la categoría "EdgeFace" o "ArcFace mobile" hasta 30 MB.
