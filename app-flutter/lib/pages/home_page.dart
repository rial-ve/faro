import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../capture/capture_picker.dart';
import '../capture/captured_image.dart';
import '../face/face_detector.dart';
import '../face/face_overlay.dart';

class HomePage extends StatefulWidget {
  final ApiClient client;
  final VoidCallback onResetCredentials;
  const HomePage({
    super.key,
    required this.client,
    required this.onResetCredentials,
  });

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final _picker = CapturePicker();
  final _faces = FaceDetectorRunner();

  CapturedImage? _image;
  DetectedFace? _face;
  bool _detecting = false;
  String? _backendStatus;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _probeBackend();
  }

  @override
  void dispose() {
    _faces.close();
    super.dispose();
  }

  Future<void> _probeBackend() async {
    try {
      final ok = await widget.client.healthz();
      await widget.client.models();
      setState(() => _backendStatus = ok ? null : 'Backend respondió, pero no como esperaba');
    } catch (e) {
      setState(() => _backendStatus = 'Backend inalcanzable: $e');
    }
  }

  Future<void> _take(Future<CapturedImage?> Function() source) async {
    setState(() => _busy = true);
    try {
      final img = await source();
      if (img == null) return;
      setState(() {
        _image = img;
        _face = null;
        _detecting = true;
      });
      final face = await _faces.detectLargest(img);
      if (!mounted) return;
      setState(() {
        _face = face;
        _detecting = false;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
      setState(() => _detecting = false);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _statusLine() {
    if (_image == null) return 'Toma una foto o elige una de la galería para empezar.';
    if (_detecting) return 'Detectando rostro…';
    if (_face == null) return 'No se detectó ningún rostro.';
    return 'Rostro detectado: '
        '${_face!.boundingBox.width.toInt()} × ${_face!.boundingBox.height.toInt()} px';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Faro'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            tooltip: 'Cambiar credenciales',
            onPressed: widget.onResetCredentials,
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_backendStatus != null)
              Container(
                padding: const EdgeInsets.all(8),
                color: Colors.orange.withValues(alpha: 0.2),
                child: Text(_backendStatus!),
              ),
            const SizedBox(height: 12),
            Expanded(
              child: Center(
                child: _image == null
                    ? const Text(
                        'Toma una foto o elige una de la galería para empezar.',
                        textAlign: TextAlign.center,
                      )
                    : FaceOverlay(image: _image!, face: _face),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              _statusLine(),
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: _busy ? null : () => _take(_picker.takePhoto),
                    icon: const Icon(Icons.camera_alt),
                    label: const Text('Tomar foto'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _busy ? null : () => _take(_picker.pickFromGallery),
                    icon: const Icon(Icons.photo_library),
                    label: const Text('Galería'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
