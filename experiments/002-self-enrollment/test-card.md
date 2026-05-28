# Test Card — 002 self-enrollment

## Hipótesis

**Creemos que** podemos descentralizar la enrolación de personas sin sacrificar privacidad ni integridad de los datos. En lugar de obligar al cuidador a enrolar manualmente a cada familiar, el cuidador envía por WhatsApp un link tokenizado, y cada familiar abre la página, sube o toma una foto, escribe quién es y qué relación tiene, y el sistema:

- Computa el embedding en el servidor y **descarta los bytes de la foto** inmediatamente.
- Guarda la persona en estado **`pending`** (no visible aún para el flujo de reconocimiento).
- El cuidador revisa, aprueba o rechaza desde su propia interfaz.

## Verificación

**Para verificarlo:**

- Añadiremos un campo `status: "pending" | "active"` al modelo `Person`. `find_closest` filtrará a `active` para que las pendientes no contaminen el reconocimiento.
- Crearemos un `EnrollmentToken` con su `TokenStore` (JSON, mismo patrón que `PersonStore`). El cuidador genera tokens por API; cada token puede revocarse.
- Añadiremos una página web simple servida por FastAPI en `GET /enroll/{token}`. Mobile-first, sin framework JS, un `<input type="file" accept="image/*">` que en móvil ofrece "tomar foto" o "elegir de la galería".
- `POST /enroll/{token}` recibe multipart (`name`, `description`, `image`), valida el token, computa el embedding, crea la persona en `pending`, y devuelve una pantalla de confirmación.
- Añadiremos endpoints de cuidador: `GET /v1/persons?status=pending`, `POST /v1/persons/{id}/approve`. El `DELETE /v1/persons/{id}` existente cubre el "rechazar".
- El mensaje de privacidad será explícito en la página: "Tu foto se procesa una vez para extraer un vector matemático y luego se descarta. No se guarda en ningún servidor."

## Mediciones

**Mediremos:**

| Métrica                                                | Cómo                                                       |
|--------------------------------------------------------|------------------------------------------------------------|
| El token gatea correctamente                           | Test: GET/POST con token inválido → 404                    |
| La persona auto-enrolada queda en `pending`            | Test: tras POST /enroll, list pending la incluye           |
| Reconocimiento no la encuentra antes de aprobar        | Test: recognize con su foto → no match                     |
| Aprobación activa a la persona                         | Test: POST /approve → status=active → recognize la encuentra |
| Los bytes de la foto no persisten                      | Inspección de código + assert en test que `image` no se escribe a disco |
| El formulario funciona en móvil                        | Smoke test manual: abrir en navegador móvil y enrolar      |

## Criterio de éxito

**Tendremos razón si:**

- La suite de tests cubre token CRUD, self-enroll → pending, aprobación → active, y reconocimiento gateado por status, y pasa al 100%.
- El smoke test con `yo2.jpg` enrolada vía la página web es reconocible después de aprobar, con similitud > 0.5.
- El código nunca llama a `write_bytes` ni `save()` con los bytes de la imagen subida; solo se calcula el embedding y se descarta.
- La página HTML se renderiza correctamente en un navegador móvil moderno (Chrome Android / Safari iOS) — verificable porque solo usa HTML5 estándar (`<input type="file" accept="image/*">`).
- Los tests existentes (los 8 del experimento 001) siguen pasando sin cambios.
