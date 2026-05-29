# Smoke E2E — experimento 004

Dos pruebas, una offline (la que cualquiera puede correr ya), otra en teléfono real (requiere build + dispositivo).

## A — Smoke offline (sin teléfono)

Emula el path on-device del teléfono en Python:

```
.venv/bin/python scripts/smoke_recognize_embedding.py [enroll_image] [recognize_image]
```

Por defecto compara `test_data/yo.jpg` (enroll) contra `test_data/yo2.jpg` (recognize). Imprime cuatro similitudes y aplica el threshold 0.45.

### Resultados sobre (yo.jpg, yo2.jpg) — 2026-05-29

| Pareja                                  | cosine  | veredicto    | qué significa                                            |
|-----------------------------------------|---------|--------------|----------------------------------------------------------|
| server enroll vs server recognize       | +0.6064 | MATCH ✅     | baseline. Misma persona, ambos lados con alineación 5-pt |
| phone enroll vs phone recognize         | +0.3926 | no match ❌  | el path on-device consigo mismo todavía cae abajo de 0.45 |
| **server enroll vs phone recognize**    | **+0.2737** | **no match ❌** | **configuración real: enrolación web (002) + recognición desde Flutter (004)** |
| server recog. vs phone recognize        | +0.5610 | MATCH       | misma foto, distinto preprocesado: aísla el delta puro de alineación |

### Lectura

- La conversión ONNX → TFLite es **fiel** (cos(onnx, tflite) = 1.000000 en el sanity check de `scripts/convert_mobilefacenet_to_tflite.py`). El modelo on-device produce, palabra por palabra, lo mismo que el servidor para el mismo tensor de entrada.
- Lo que no es fiel es el **preprocesado**. El servidor usa `norm_crop` con 5 landmarks (ojos, nariz, comisuras) para alinear la cara a una pose canónica antes del modelo. El teléfono hoy usa la bounding box de ML Kit y hace un crop cuadrado con 1.1× padding, **sin alinear**.
- El delta de alineación sobre la misma foto cuesta ~0.45 puntos de similitud (fila 4: el servidor saca 1.0 contra sí mismo en su propio crop, mientras que server-vs-phone sobre la misma foto saca 0.5610).
- La consecuencia práctica está en la fila 3: una persona enrolada por el familiar vía la página de 002 **no se reconoce desde la app**.

### Camino correcto

ML Kit Face Detection puede emitir landmarks (`enableLandmarks: true` o `enableContours: true`). Habilitarlos y replicar el `norm_crop` de InsightFace en Dart cierra la brecha. El embedding TFLite ya está demostrado equivalente al ONNX; sólo falta darle el mismo input.

Esta es la siguiente bala — corresponde al experimento 005 (alineación on-device), no a una sub-fase del 004.

## B — Smoke en teléfono (con dispositivo)

Para correr en hardware real:

1. **Backend levantado.**

   ```
   FARO_ADMIN_USERNAME=carer FARO_ADMIN_PASSWORD=tu-pass \
     uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

   El `--host 0.0.0.0` es para que el teléfono te pueda alcanzar en la LAN. Anota la IP de la Mac (`ipconfig getifaddr en0`).

2. **Enrolar a alguien vía el form web 002.**

   - Como cuidador, generar un token: `POST /v1/enrollment-tokens`.
   - Abrir `http://<ip>:8000/enroll/<token>` desde un navegador.
   - Subir una foto, escribir nombre y descripción, enviar.
   - Aprobar la persona: `POST /v1/persons/{id}/approve`.

3. **Build de la app.**

   ```
   cd app-flutter && flutter run
   ```

   Con un iPhone enchufado o un emulator Android. En primer arranque, ingresar:
   - URL: `http://<ip>:8000`
   - Usuario / contraseña: las mismas del backend.

4. **Capturar a esa persona desde la app.**

   - Tomar foto desde la app.
   - Observar pantalla:
     - Verdor del marco de detección.
     - Status: `embed XXX ms · match YYY ms · ||v||=1.000`.
     - Panel de resultado con la frase hablada por el LLM.
     - Voz en español saliendo del altavoz.

5. **Anotar números en la Learning Card.**

   | Medida                          | Valor del teléfono |
   |---------------------------------|--------------------|
   | Embed (ms)                      |                    |
   | Match (ms, round-trip al server)|                    |
   | TTS hasta primera palabra (ms)  | (estimar a oído)   |
   | Similitud reportada             |                    |
   | Tap → voz total (cronómetro)    |                    |

   Si la similitud queda < 0.45 (esperable mientras no haya alineación, según el smoke A), la app dirá "no reconozco a esta persona". Anótalo igual y compara contra el endpoint de imagen para tener punto de control.

6. **Comparar contra `/v1/recognize`.**

   Subir la misma foto desde el form / curl al endpoint multipart:

   ```
   curl -u carer:tu-pass -F image=@foto.jpg -F language=es \
     http://<ip>:8000/v1/recognize
   ```

   Si éste sí reconoce y la app no, el delta es 100% alineación.
