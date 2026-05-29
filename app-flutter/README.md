# Faro — Flutter app

Cliente móvil del experimento 004. Reconoce rostros calculando el embedding directamente en el dispositivo con MobileFaceNet (TFLite) y consulta al backend con sólo el vector de 512 floats. La foto nunca sale del teléfono.

## Build

```
flutter pub get
flutter run
```

Necesitas un backend Faro accesible. En el primer arranque la app pide URL, usuario y contraseña; los guarda en el almacén seguro del sistema (Keychain en iOS, EncryptedSharedPreferences en Android).

URLs típicas para el backend en dev:
- **Android emulator:** `http://10.0.2.2:8000` (el emu rutea a localhost del host)
- **iOS simulator:** `http://localhost:8000`
- **Dispositivo físico en LAN:** `http://<ip-de-tu-mac>:8000`

## Layout

```
lib/
├── main.dart                  # Entry + bootstrap (carga credenciales)
├── api/
│   ├── credentials.dart       # flutter_secure_storage wrapper
│   └── api_client.dart        # dio + Basic Auth
├── pages/
│   ├── settings_page.dart     # Primer arranque: URL + usuario + pass
│   └── home_page.dart         # Probe /healthz + /v1/models (cambia en 004.5+)
assets/
└── models/                    # mobilefacenet.tflite (bundleado en 004.7)
```

## Modelo de embedding

`assets/models/mobilefacenet.tflite` (13 MB) sale de convertir el mismo `w600k_mbf.onnx` que corre en el servidor. La conversión y el sanity check se reproducen con:

```
.venv/bin/python scripts/convert_mobilefacenet_to_tflite.py
```

El script falla si el coseno entre ONNX y TFLite cae por debajo de 0.999.

## Estado por punto

- ✅ **004.4** — scaffolding + credenciales + probe del backend
- ✅ **004.5** — cámara + preview
- ✅ **004.6** — detección de rostro con ML Kit
- ✅ **004.7** — embedding on-device con tflite_flutter
- ✅ **004.8** — POST al endpoint `/v1/recognize-embedding`
- ✅ **004.9** — voz con flutter_tts
- ⬜ **004.10** — smoke E2E
