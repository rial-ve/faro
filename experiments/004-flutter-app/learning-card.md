# Learning Card — 004 Flutter app con embedding on-device

**Periodo:** 2026-05-29
**Estado:** ✅ Validado con matices

## Creíamos que

Podíamos llevar Faro al teléfono con una app Flutter que calculase el embedding facial directamente en el dispositivo (con el mismo MobileFaceNet que el servidor ya corría desde el experimento 003), y enviase sólo el vector de 512 floats al backend. La foto nunca dejaría el teléfono.

Criterios fijados en la [Test Card](./test-card.md):

- Tap → voz < 2 s
- Similitud para misma persona ~0.5 en el rango que mide el servidor con `mobilefacenet`
- Embedding on-device < 100 ms en teléfono moderno
- Smoke E2E: persona enrolada vía 002 reconocida desde la app con similitud > 0.4

## Observamos que

### La arquitectura cierra

Las once piezas del pipeline encajan y compilan:

- Endpoint nuevo `POST /v1/recognize-embedding` con tests verdes (`813c6d3`).
- App Flutter (`b2aa76c`) con credenciales en almacén seguro y probe autenticado del backend.
- Captura con `image_picker`, detección con `google_mlkit_face_detection`, embedding on-device con `tflite_flutter`, POST + render del match, voz con `flutter_tts`.
- Flujo de estado: `idle → detecting → embedding → matching → speaking → done`, visible en pantalla con tiempos por etapa.

### La conversión ONNX → TFLite es bit-perfecta

`scripts/convert_mobilefacenet_to_tflite.py` corre el `w600k_mbf.onnx` por `onnx2tf` y, sobre un input aleatorio, mide:

```
cosine(onnx, tflite) = 1.000000
```

El modelo bundleado (`app-flutter/assets/models/mobilefacenet.tflite`, 13 MB) produce, palabra por palabra, lo mismo que el ONNX del servidor para el mismo tensor de entrada. **El modelo no es el problema.**

### El preprocesado, sí

El smoke offline (`scripts/smoke_recognize_embedding.py`) emula el path on-device en Python — mismo `.tflite`, mismo crop simple por bbox + 1.1× padding, misma normalización — y reporta sobre `(yo.jpg, yo2.jpg)`:

| Pareja                                    | cosine  | veredicto    |
|-------------------------------------------|---------|--------------|
| server enroll vs server recognize         | +0.6064 | MATCH ✅     |
| phone enroll vs phone recognize           | +0.3926 | no match ❌  |
| **server enroll vs phone recognize**      | **+0.2737** | **no match ❌** |
| server recog. vs phone recognize          | +0.5610 | MATCH (misma foto, delta de alineación) |

La fila 3 es la **forma realmente desplegada**: alguien se enroló desde el form web del experimento 002 (cuyo embedding usa el pipeline del servidor) y luego es identificado desde la app Flutter (cuyo embedding usa el pipeline del teléfono). El threshold por defecto es 0.45 (ajustado en `b14c56d`); 0.27 cae por debajo. La app diría "no reconozco a esta persona" sobre alguien que sí está en el `persons.json`.

La fila 4 aísla la causa: misma foto, distinto preprocesado, **0.44 puntos de similitud cuesta** la diferencia entre alinear con 5 landmarks (lo que hace el servidor vía `norm_crop` de InsightFace, usando ojos, nariz y comisuras) y no alinear (lo que hace hoy el teléfono, bounding box → crop cuadrado).

### Qué no medimos

- **Latencia real en dispositivo.** No hay teléfono físico en el loop de Claude. El embed time del Stopwatch del Mac M-series ronda los 50–100 ms; en CPU del teléfono se mantendrá del mismo orden, pero el número honesto sale del dispositivo. Anotado como acción en `SMOKE.md` parte B.
- **APK / IPA release size.** No hubo `flutter build`, ni hay keystore Android ni perfil de provisioning iOS configurados. Estimación gruesa: ~30–40 MB en release con `mobilefacenet.tflite` (13 MB) + ML Kit (10–15 MB nativo) + Flutter runtime.
- **Tap → voz total con cronómetro.** Idem: depende del teléfono.

## Aprendimos que

1. **La validación del path on-device se hace en dos etapas independientes, y eso importa.** El experimento 003 dejó al servidor corriendo el mismo modelo que iba a correr en el teléfono. Eso resolvió la parte del modelo — `cos(onnx, tflite) = 1.000000` es la prueba — pero dejó una segunda variable suelta: el preprocesado. Asumir "mismo modelo → mismo embedding" fue ingenuo. Lo correcto: **mismo modelo AND mismo preprocesado → mismo embedding**.

2. **La alineación 5-puntos no es decorativa.** ArcFace y derivados se entrenan sobre rostros warpeados a posiciones canónicas. Sin ese warp, la red sigue dando un vector razonable, pero rotado lo suficiente como para perder ~0.44 de coseno sobre la misma foto. La métrica que importa no es "¿el modelo corre?", sino "¿produce vectores en la misma región de la esfera que el modelo de referencia?". Hoy no lo hace.

3. **Documentar el path de despliegue por separado del path técnico paga.** El smoke matrix tiene cuatro filas; la fila 3 es la única que importa para el producto. Sin la fila 3 explícita, hubiéramos podido reportar "cos(server, phone) = 0.56 sobre la misma foto, validado" y declarar éxito mientras la cosa estaba rota en la práctica. Para futuros experimentos: **siempre incluir la fila del despliegue real, aunque no sea la más bonita.**

4. **El gap encontrado es relativamente barato de cerrar.** ML Kit acepta `enableLandmarks: true` y devuelve, entre otros, posiciones de ojos y boca. Implementar la transformación afín (o similar) que InsightFace hace en `norm_crop` es ~50–80 líneas de Dart con `image` package. No es un rediseño; es la siguiente bala.

5. **Conviene separar arquitectura validada de criterio de éxito validado.** La arquitectura del 004 (Flutter + on-device embedding + endpoint nuevo + voz) funciona como sistema. El criterio del 004 (smoke E2E con similitud > 0.4 sobre persona enrolada vía 002) no se cumple. Las dos cosas son verdaderas a la vez. El estado "validado con matices" cubre exactamente esa diferencia.

## Por lo tanto

### Habilitado

- **Toda la arquitectura cliente-servidor del path on-device** queda en pie. El endpoint nuevo, el cliente HTTP, el TFLite cargando, ML Kit detectando, el TTS hablando — todo encajado, todo en `main` (último commit del 004.x: `d1aeb46`).
- **Conversión reproducible.** Cualquier swap futuro del modelo de embedding se valida con el mismo gate (`cosine ≥ 0.999`) antes de bundlear.
- **Smoke offline replicable.** Cualquiera puede correr `scripts/smoke_recognize_embedding.py` con un par de fotos y obtener la matriz 4 filas en segundos.

### Tareas pendientes (heredadas a 005 y siguientes)

- **Experimento 005 — alineación on-device 5-puntos.** Habilitar landmarks en `FaceDetectorOptions`, implementar `norm_crop` (transformación de similitud usando puntos canónicos como los de InsightFace `arcface_dst`) en `lib/face/embedder.dart`. Re-correr el smoke y demostrar fila 3 ≥ 0.5.
- **Medir en hardware real.** Tap → voz cronometrado en un iPhone reciente y un Android medio-alto, anotado en una nueva tabla de la learning card del 005.
- **Distribución.** TestFlight + sideload Android al círculo RIAL antes de pensar en App Store / Play Store. La decisión se toma en 005 una vez la alineación esté en su sitio.
- **Test del path on-device en CI.** El smoke offline corre sin servidor y sin teléfono; es el candidato natural para gatear regresiones cuando exista CI en el repo.

### Descartado (con razón)

- **Implementar la alineación dentro del experimento 004.** Habría reabierto el alcance del experimento después de haberlo cerrado con datos. La regla del proyecto es: una hipótesis por carta. La hipótesis "Flutter + embedding on-device + voz" se midió contra los hechos; el aprendizaje "el preprocesado pesa" merece su propia carta.
- **Mover el threshold de 0.45 hacia abajo para que la fila 3 pase.** Tentación fácil que rompería la separación de personas distintas. La distancia entre la fila 3 (0.27) y un par de personas distintas (que con buffalo_l mide 0.0129; con mobilefacenet rondaría 0.06) deja apenas 0.21 de margen, ya estrecho. Bajarlo más es renunciar al filtro.
