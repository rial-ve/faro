# Test Card — 004 Flutter app con face embedding on-device

## Hipótesis

**Creemos que** podemos llevar Faro al teléfono — la única superficie donde un asistente de memoria tiene sentido — construyendo una **app Flutter** que reconozca rostros **calculando el embedding directamente en el dispositivo** y consultando al servidor sólo con el vector de 512 floats. La foto nunca sale del teléfono.

Esto es posible hoy porque el experimento 003 ya dejó al servidor corriendo MobileFaceNet (`w600k_mbf.onnx`, 13 MB). Si el mismo modelo, convertido a TFLite y cargado con `tflite_flutter`, produce embeddings en el **mismo espacio vectorial** que produce el servidor con su ONNX, el flujo cierra: el teléfono extrae el vector, el servidor encuentra la persona, el teléfono dice en voz alta quién es.

La decisión arquitectónica de **Flutter** sobre nativo (Kotlin/Swift), React Native o KMP la tomamos por dos razones: audiencia multiplataforma (RIAL incluye iOS y Android sin segmentar), y velocidad de iteración con un único codebase mientras el producto sigue siendo prototipo.

La decisión de **embedding on-device desde la primera versión** la tomamos por tres razones: (1) coherencia con el discurso de privacidad ya construido en el experimento 002 — la foto no se envía a ningún servidor; (2) latencia perceptual — un round-trip de imagen sobre red móvil es del orden de 1-3 s, un round-trip de 512 floats es despreciable; (3) capacidad de funcionar parcialmente offline.

## Verificación

**Para verificarlo**, ejecutaremos 11 puntos. Cada uno es un commit, en orden:

| Punto  | Entregable                                                                            |
|--------|----------------------------------------------------------------------------------------|
| 004.1  | Esta Test Card + scaffolding del experimento                                          |
| 004.2  | `POST /v1/recognize-embedding` en el backend (JSON con `{embedding, language}`) + tests con `MockEmbedder` |
| 004.3  | Decisión: monorepo (`/app-flutter` dentro de `faro`) vs repo Flutter separado         |
| 004.4  | Scaffold Flutter, credenciales en `flutter_secure_storage`, `GET /healthz` autenticado funcionando |
| 004.5  | Cámara y preview (`image_picker` como primer paso, antes de pasar a `camera` si hace falta) |
| 004.6  | Detección de rostro con `google_mlkit_face_detection` — bounding box + alineación básica |
| 004.7  | Embedding on-device con `tflite_flutter` cargando `mobilefacenet.tflite` (convertido desde el mismo ONNX que usa el servidor) |
| 004.8  | POST del vector al endpoint nuevo + render del resultado en pantalla                  |
| 004.9  | Text-to-speech con `flutter_tts` en español                                           |
| 004.10 | Smoke end-to-end: enrolar a alguien vía web form (002), reconocer desde la app Flutter, comparar similitud teléfono-vs-servidor sobre el mismo rostro |
| 004.11 | Learning Card                                                                          |

Decisiones pendientes que se resolverán antes de implementar:

- **Monorepo vs repo separado** (004.3). Tradeoff principal: monorepo facilita commits coordinados backend ↔ app durante el desarrollo intenso; repo separado evita arrastrar el toolchain de Flutter al CI del backend Python.
- **Distribución** (a decidir antes del 004.10). Tradeoff principal: tiendas (App Store / Play Store) dan instalación a un click pero meten meses de review y políticas; TestFlight / sideload da iteración rápida en círculo RIAL pero excluye a usuarios finales.

## Mediciones

**Mediremos:**

| Métrica                                                          | Cómo                                                                 |
|------------------------------------------------------------------|----------------------------------------------------------------------|
| Latencia tap → voz hablando                                      | Cronómetro de pantalla sobre 10 ejecuciones, dispositivo real, WiFi  |
| Latencia desglosada: detección, embedding, red, TTS              | `Stopwatch` instrumentado en cada paso                               |
| Similitud teléfono ↔ servidor sobre la misma persona             | Embedding del teléfono comparado contra embedding del servidor sobre la misma foto; coseno |
| Similitud teléfono para misma persona en distintas fotos         | Misma fixture Einstein del 003, ahora corrida en el teléfono         |
| Footprint del `.tflite` en bundle                                | `ls -lh` en el `assets/` de Flutter                                  |
| Tamaño del APK release y del IPA release                         | `flutter build apk --release` / `flutter build ipa`                  |
| Tests del backend tras el endpoint nuevo                         | `pytest` debe seguir verde, ahora con cobertura del nuevo endpoint    |

## Criterio de éxito

**Tendremos razón si:**

- **Flujo tap → voz < 2 s** sobre WiFi razonable en dispositivo moderno (iPhone reciente o Android gama media-alta). Sub-segundo es ideal; arriba de 2 s rompe la sensación de "el teléfono te dice quién es esa persona".
- **Similitud para misma persona ~0.5**, en el rango que el servidor mide hoy con `mobilefacenet` (003 reportó 0.5024 y 0.5164). Aceptamos variación de hasta ±0.10 por diferencias de preprocessing entre TFLite/ONNX y por la cámara real introduciendo iluminación distinta.
- **Embedding on-device < 100 ms** en teléfono moderno con GPU delegate. El servidor mide 252 ms en CPU; el dispositivo debería bajar por delegate y por ser ARM optimizado.
- **El embedding se ejecuta sin internet.** Sólo el POST del vector y el TTS requieren red.
- **Smoke E2E**: una persona enrolada vía la página web del 002, fotografiada en vivo desde la app Flutter, se reconoce con similitud > 0.4 y el teléfono dice su nombre y relación en voz alta.
- **Backend sigue verde** (los 27 tests del 001+002+003 más los nuevos del 004.2).

## Criterio de invalidación

**Lo descartamos si:**

- **Latencia tap → voz > 4 s** en condiciones normales. El producto pierde su razón de ser; quien tiene Alzheimer ya olvidó por qué levantó el teléfono.
- **Similitud para misma persona < 0.3** entre teléfono y servidor sobre la misma foto. Significa que la conversión ONNX → TFLite o el preprocessing en Flutter desalinearon los espacios vectoriales y obligaría a re-enrolar a todo el mundo desde el teléfono (y hacer el servidor incapaz de aceptar enrolaciones del 002).
- **APK / IPA release > 100 MB**. Excluye a usuarios con poco almacenamiento y dispara fricción de descarga sobre datos móviles.
- **`tflite_flutter` no carga el `.tflite` convertido** o produce resultados inconsistentes entre run y run en el mismo dispositivo. Implicaría rehacer el camino con `onnxruntime` para Flutter, lo cual existe pero está peor documentado.

Si 004 falla por embedding on-device, la rama alternativa es servir el embedding desde el backend desde el teléfono (subiendo la imagen al servidor) y validar al menos UX, voz y flujo en un experimento 005 sobre ese fallback.
