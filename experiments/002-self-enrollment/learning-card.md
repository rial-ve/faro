# Learning Card — 002 self-enrollment

**Periodo:** 2026-05-28
**Estado:** ✅ Validado

## Creíamos que

Podíamos descentralizar la enrolación: el cuidador envía un link tokenizado por WhatsApp, cada familiar abre la página, sube o toma una foto, escribe quién es, y el sistema computa el embedding y descarta la foto. Las personas auto-enroladas quedan en estado `pending` hasta que el cuidador aprueba.

## Observamos que

### El flujo entero cierra end-to-end

Smoke test con foto real (`yo2.jpg` enrolada, `yo3.jpg` para reconocer después):

| Paso                                                         | Resultado                                                       |
|--------------------------------------------------------------|-----------------------------------------------------------------|
| Carer crea token                                             | `id=438968ce2b16`, `token=HcdAl76v9...` (32 chars url-safe)     |
| GET `/enroll/{token}` (familiar abre el link)                | 200, HTML con formulario y aviso de privacidad                  |
| POST con `yo2.jpg` + nombre + descripción                    | persona creada con `status=pending`                             |
| Recognize con `yo3.jpg` ANTES de aprobar                     | `match: null` — el gating funciona                              |
| Carer aprueba                                                | `status=active`                                                 |
| Recognize con `yo3.jpg` DESPUÉS de aprobar                   | match, similitud **0.9811**, frase *"Ese es Rodolfo Campos, tu hijo mayor."* |

### La promesa de privacidad se sostiene en código

En `app/api/enroll.py`, los bytes de la imagen viven en una variable local que sale de scope al volver de la función. Se calcula el embedding una vez y se `del image_bytes` explícitamente como señal de intención. **El `image_bytes` no se escribe a disco en ningún punto del código**, solo el embedding entra en `data/persons.json`.

### El gating por status es robusto

`find_closest` filtra a `status == "active"` antes del cálculo de similitud. Una persona en `pending` es invisible al reconocimiento aunque tenga una similitud de 0.99. Verificado en el smoke test (paso 5) y en `tests/test_enrollment.py::test_recognize_does_not_match_pending_person`.

### Tests automatizados cubren los flujos sin necesidad de modelos reales

Escribimos un `MockEmbedder` determinístico (mismo input → mismo embedding) que evita cargar los 325 MB de InsightFace en cada sesión de pytest. La suite completa pasa en **<1 s**: 13 tests nuevos + 8 anteriores = 21 verdes.

### Limitaciones conocidas

- **El token viaja en la URL** (`/enroll/{token}`). Eso significa que puede aparecer en logs del servidor, historial del navegador y headers `Referer` si la página enlaza a otro sitio. Para una enrolación familiar de bajo riesgo es aceptable; para escenarios de mayor sensibilidad habría que pasarlo por POST o por cookie.
- **No hay rate-limiting.** Cualquiera con un token válido puede spamear pendientes. Para MVP, mitigado por el paso de aprobación humana del cuidador. Antes de exponer públicamente, hay que añadir un límite por token (p.ej. 10 enrolaciones por hora).
- **No hay revisión visual del rostro.** El cuidador aprueba viendo solo el nombre + descripción. Sin la foto (que ya descartamos), no puede verificar visualmente que ese embedding corresponde a esa persona. Es una consecuencia directa de la promesa de privacidad. Mitigación: el cuidador puede pedir al familiar que confirme por WhatsApp que lo envió.
- **El umbral 0.5 sigue siendo el mismo que en 001.** No hemos vuelto a medir si la auto-enrolación (donde no controlas la calidad de la foto subida) baja la precisión efectiva.

## Aprendimos que

1. **El patrón de protocolos (`LLMProvider`, `FaceEmbedder`) se extendió sin fricción.** Añadir `TokenStore` con el mismo patrón JSON-en-disco que `PersonStore` tomó ~40 líneas. La consistencia interna del proyecto está pagando rendimientos.

2. **El estado `pending` resuelve dos problemas a la vez:** integridad de datos (filtra el spam) y consentimiento del cuidador (siempre hay una revisión humana antes de que algo afecte al reconocimiento). No es solo un detalle de UX, es parte de la arquitectura de confianza.

3. **El `MockEmbedder` como hash determinístico fue clave** para tener tests rápidos y hermetic. Misma técnica que `MockProvider`. Vale la pena formalizar el patrón "mock por hash de contenido" para cualquier proveedor que dependa de modelos pesados.

4. **HTML server-renderizado sin framework JS es suficiente** para esta página. ~50 líneas de HTML+CSS, mobile-first, funciona con `<input type="file" accept="image/*">` para activar cámara o galería nativamente. No necesitamos React/Next para un formulario de una pantalla.

5. **El smoke test cualitativo (vs. los tests automatizados con MockEmbedder) sigue siendo necesario.** Los tests verifican el wiring; el smoke verifica que la cadena InsightFace → embedding → LLM → frase final realmente produce el output esperado con datos reales. Ambos cuestan poco y atrapan clases de error distintas.

## Por lo tanto

### Siguiente experimento (003)

**Enrolación multi-foto.** Permitir al familiar subir 2–5 fotos en la misma sesión y promediar los embeddings antes de guardar. Hipótesis: baja la varianza de la similitud frente al rostro real en distintas condiciones (gafas, luz, ángulo), permitiendo subir el umbral con seguridad. Esto era el siguiente paso ya identificado en la Learning Card 001 y la auto-enrolación es el frontend natural donde implementarlo (la persona se hace 3 selfies fácil).

### Diferido

- **Rate-limiting** por token. Sencillo (token bucket en memoria), pero solo lo necesitamos cuando expongamos el servicio fuera de localhost.
- **Vista previa segura para el cuidador.** Si decidimos que el cuidador necesita ver la cara para aprobar, podemos almacenar un thumbnail de baja resolución cifrado en reposo y borrarlo al aprobar/rechazar. Rompe la promesa actual de "la foto no se guarda" — solo lo activaríamos si user research lo justifica.
- **Token en cookie / POST en vez de URL.** Solo si surge un escenario más sensible.
- **Notificación al cuidador** cuando llega un pending (Telegram? email?). Útil para el producto real, no para el MVP local.

### Descartado

- **Auto-aprobación.** Tentador para reducir fricción del cuidador, pero rompe el control de calidad que justifica todo el patrón pending/active.
- **Persistir un hash de la imagen original** "por si necesitamos verificar después". Cualquier persistencia de la imagen contradice la promesa de privacidad del producto.
