# Learning Card — 001 MVP backend

**Periodo:** 2026-05-25 → 2026-05-26
**Estado:** ✅ Validado con matices

## Creíamos que

Llama 3.2 1B Q4 más ArcFace, todo on-device, eran suficientes para construir un asistente de memoria viable hoy: footprint manejable, latencia sub-segundo, reconocimiento fiable, fraseo natural en español.

## Observamos que

### Footprint

| Componente                                | Tamaño     |
|-------------------------------------------|------------|
| Llama 3.2 1B Q4_K_M (`models/`)           | **770 MB** |
| ArcFace `buffalo_l` (`~/.insightface/`, 5 ficheros, solo 2 usados en runtime) | **325 MB** |
| **Combinado**                              | **~1.1 GB** |

Por debajo del target de 1.5 GB. Aceptable para distribución on-first-launch (no para bundle dentro de la APK, pero sí con descarga inicial detrás de un splash).

### Latencia (M-series Mac, CPU, llama-cpp-python)

| Escenario                              | Tiempo          |
|----------------------------------------|-----------------|
| Primera petición (cold)                | ~2.4 s          |
| Petición caliente (warm)               | **300–600 ms**  |
| Solo reconocimiento facial (sin LLM)   | ~280 ms         |

La latencia warm está bastante por debajo del target de 1 s, con margen para perder algo al saltar a hardware móvil.

### Precisión de reconocimiento (ArcFace, 4 fotos de dominio público)

| Pareja                                                | Sim. coseno | Veredicto (umbral 0.5) |
|-------------------------------------------------------|-------------|------------------------|
| Einstein 1921 (enrolada) vs. Einstein 1920            | **+0.5965** | match                  |
| Einstein 1921 (enrolada) vs. Einstein 1921 re-crop    | **+0.5602** | match                  |
| Einstein 1921 (enrolada) vs. Marie Curie (control)    | **+0.0129** | no match               |

Gap real: **~0.55**, muy por encima del target de 0.4. ArcFace separa con margen amplio.

### Calidad del fraseo (Llama 3.2 1B Q4, temperature=0.0)

- **Primer intento** con prompt enmarcado como *"identifica esta persona"* → **rechazo por seguridad**: `"Lo siento, pero no puedo cumplir con esa solicitud."`
- **Reframe** como *"rellena esta plantilla"* + ejemplos few-shot en **turnos alternados user/assistant** → **100% de adherencia al formato** en las pruebas. Salida típica: `"Ese es Albert Einstein, tu abuelo paterno."`
- **Limitación menor:** el 1B siempre escribe `"Ese es"` (masculino), nunca `"Esa es"` (femenino). No infiere género gramatical desde un nombre.

### Hallazgos no planeados

- Wikipedia/Wikimedia requiere un User-Agent reconocible o devuelve 400/429. Lo aprendimos al fallar al descargar fotos de prueba.
- El `<|begin_of_text|>` no debe ir en la plantilla del prompt: tanto `llama-cpp` como ONNX Runtime añaden el BOS automáticamente. Duplicarlo degrada la calidad (warning explícito de llama-cpp).

## Aprendimos que

1. **El 1B Q4 ya es viable para producción.** La apuesta técnica inicial fue correcta. Tenemos margen incluso si la latencia se duplica al pasar a hardware móvil.

2. **El prompt engineering pesa más que el tamaño del modelo a esta escala.** Reencuadrar la tarea como "template-fill" (y no como "identification") fue lo que desbloqueó el caso de uso entero. Es un aprendizaje transferible a cualquier producto sobre LLMs pequeños.

3. **ArcFace nos sobra** para el flujo básico. La separación es amplia. El umbral 0.5 funciona pero está cerca del piso de "misma persona en condiciones reales" — los casos límite (gafas distintas, ángulos extremos, gran diferencia de edad) podrían rozar 0.4.

4. **El 1B no soporta concordancia de género en español** desde un nombre — un 3B probablemente sí. No es razón suficiente para migrar: el coste (footprint, latencia) supera el beneficio para un único matiz lingüístico.

5. **El playground es un proxy fiel mientras estemos en CPU.** La hipótesis de "lo que pasa aquí pasará allá" no la podemos cerrar hasta tener el modelo corriendo en un Snapdragon o Apple Neural Engine real.

## Por lo tanto

### Siguiente experimento

**002 — enrolación multi-foto.** Promediar 3–5 embeddings por persona y medir si robustece los casos límite. Hipótesis: bajará la varianza de la similitud, lo que nos permite subir el umbral con seguridad y reducir falsos positivos sin perder verdaderos positivos.

### Diferido (esperando hardware o capacidad)

- Validación de latencia y batería de Llama 1B Q4 en un Pixel/Snapdragon real
- Exportación a ExecuTorch y medición end-to-end on-device
- Validación cualitativa de Meta Ray-Ban como periférico (peso, audio, latencia BLE, calidad de cámara para rostros) — necesitamos hardware físico. Este será su propio experimento (003+)
- Validación de sesgo por etnia/región — ArcFace fue entrenado con datasets desbalanceados (predominio asiático/caucásico). Para audiencia latinoamericana debe medirse.

### Descartado (por ahora)

- **Migrar a Llama 3.2 3B** por la concordancia de género — el coste no compensa para un único matiz lingüístico.
- **Añadir router de modelos cloud** como fallback — rompería la premisa local-first del producto.
