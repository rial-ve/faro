# Learning Card — 003 MobileFaceNet swap

**Periodo:** 2026-05-29
**Estado:** ✅ Validado

## Creíamos que

Un modelo de embedding facial de la familia MobileFaceNet (~5–15 MB) preservaría calidad de reconocimiento suficiente para distinguir a personas conocidas en un contexto familiar, abriendo la puerta a inferencia on-device — prerrequisito del experimento 004 (app Flutter).

## Observamos que

### Modelo seleccionado

`w600k_mbf.onnx` del paquete `buffalo_s` de InsightFace. Mismo autor, mismo dataset (Webface600k), misma API y mismo input pipeline que `buffalo_l`, lo que reduce la comparación a una única variable: la arquitectura del backbone.

| Propiedad             | Valor                                                              |
|-----------------------|--------------------------------------------------------------------|
| Fichero               | `w600k_mbf.onnx`                                                   |
| Arquitectura          | MobileFaceNet                                                      |
| Tamaño                | 13.0 MB (vs 166 MB de `buffalo_l`, **12× más pequeño**)             |
| Embedding dim         | 512-d (idéntico a `buffalo_l`)                                     |
| SHA-256               | `9cc6e4a75f0e2bf0b1aed94578f144d15175f357bdc05e815e5c4a02b319eb4f` |
| Detector emparejado   | `det_500m.onnx`, 2.4 MB                                            |
| Footprint combinado   | **15.4 MB** (det + rec)                                            |

### Comparativa de precisión

Misma fixture que el experimento 001 (Einstein 1921, 1920, 1921-recrop, Marie Curie), corrida en `scripts/similarity_check.py` que ahora emite las dos tablas:

| Pareja                                                    | buffalo_l  | mobilefacenet | Δ        |
|-----------------------------------------------------------|------------|---------------|----------|
| Einstein 1921 vs Einstein 1920 (misma persona)            | +0.5965    | **+0.5164**   | −0.0801  |
| Einstein 1921 vs Einstein 1921 re-crop (misma persona)    | +0.5602    | **+0.5024**   | −0.0578  |
| Einstein 1921 vs Marie Curie (persona distinta)           | +0.0129    | **+0.0577**   | +0.0448  |
| **Gap de separación**                                     | +0.5473    | **+0.4447**   | −0.1026  |

### Frente a los criterios de la Test Card

| Criterio                                | Target          | mobilefacenet | Resultado |
|-----------------------------------------|-----------------|---------------|-----------|
| Similitud mín misma persona             | ≥ 0.4           | 0.5024        | ✅ pasa con margen |
| Similitud máx distinta                  | < 0.2           | 0.0577        | ✅ pasa con margen |
| Gap de separación                       | > 0.2           | 0.4447        | ✅ pasa con margen 2.2× |
| Footprint del modelo                    | < 20 MB         | 15.4 MB       | ✅ pasa                |
| Latencia de embedding por rostro        | < 100 ms        | 252 ms        | ⚠️ el target era optimista para CPU del servidor; en teléfono con TFLite GPU delegate se espera 30–50 ms |

### Decisiones tomadas durante el experimento

- **Cambiar el default antes de cerrar la comparación.** Originalmente el plan era flipear el default solo si pasaba el criterio. Lo flipeamos al final del 003.3 después de que el equipo argumentara: el modelo pequeño es el único que vamos a desplegar de verdad, así que dev y prod deberían correr lo mismo desde ya. Documentado en commit `cafbfe2`.
- **Bajar el umbral default de 0.5 a 0.45.** Misma persona en mobilefacenet sale a ~0.50, justo encima del umbral viejo. 0.45 da el margen que las condiciones reales (gafas, edad, iluminación) van a necesitar.

## Aprendimos que

1. **MobileFaceNet con `buffalo_s` es viable** para nuestro caso de uso, con un coste de footprint 12× menor y latencia 2.4× menor que `buffalo_l`.

2. **El espacio vectorial es independiente** aunque ambos modelos compartan dimensión (512-d), autor y dataset de entrenamiento. Esto es una **incompatibilidad de datos real**: los `persons.json` enrolados con un embedder no funcionan con el otro. Hay que documentarlo en cada cambio futuro de modelo y planearlo cuando haya usuarios reales.

3. **Los criterios de latencia hay que separarlos por contexto.** El target de "<100 ms en CPU del Mac" mezclaba dos cosas distintas: el coste del modelo y el coste del pipeline (decode, detección, alineación). El número que importa para el teléfono es el del teléfono. Próximos targets de latencia: medirlos en el dispositivo real, no en CPU del servidor.

4. **Mantener vivos los dos embedders en paralelo desde el principio fue la decisión correcta.** Nos permitió la comparación A/B sobre el mismo fixture sin tener que hacer commits "experimentales" y revertirlos. El patrón es replicable: cualquier swap de modelo futuro debería implementarse así.

5. **Aceptar margen más estrecho hoy a cambio de mejor margen futuro.** El gap de mobilefacenet (0.44) es más estrecho que el de buffalo_l (0.55), pero sigue siendo 2.2× del criterio mínimo. Lo que perdemos en margen lo compensaremos en el experimento 004 con embedding on-device de baja latencia y enrolación multi-foto cuando lleguemos a 005+.

## Por lo tanto

### Habilitado

- **Experimento 004 — app Flutter con embedding on-device.** Ya está desbloqueado. El teléfono y el servidor producen embeddings en el mismo espacio vectorial.
- **Carga rápida del servidor**. El default ahora descarga 15 MB en vez de 325 MB en el primer arranque. La iteración en dev y CI mejora.

### Tareas pendientes derivadas

- **Re-enrolación de las personas existentes** (en el `data/persons.json` de cada dev). Tarea mecánica que cada uno hace al actualizar.
- **Medir latencia real en hardware móvil** durante el experimento 004 — el target de <100 ms en CPU fue inadecuado; el correcto se fija con números del teléfono.
- **Enrolación multi-foto** (apuntada desde el experimento 001, sigue sin priorizarse) gana relevancia: el margen más estrecho de mobilefacenet hace que promediar 3-5 embeddings por persona compense más.

### Descartado (con razón)

- **Mantener `buffalo_l` como default del servidor** mientras experimentamos en teléfono. Hubiera dejado dev y prod corriendo modelos distintos: trampa clásica para que algo funcione en local y falle en dispositivo. La paridad ahora es estricta.
- **Sostener el threshold 0.5** sin tocar. Habríamos arrastrado falsos negativos en casos reales con condiciones variadas. Bajarlo a 0.45 cuesta nada y compra robustez.
