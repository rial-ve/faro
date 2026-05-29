import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../capture/capture_picker.dart';
import '../capture/captured_image.dart';
import '../face/embedder.dart';
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
  final _embedder = FaceEmbedder();

  CapturedImage? _image;
  DetectedFace? _face;
  Float32List? _embedding;
  Duration? _embedTime;
  bool _processing = false;
  String? _backendStatus;
  String? _stageError;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _probeBackend();
  }

  @override
  void dispose() {
    _faces.close();
    _embedder.close();
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
        _embedding = null;
        _embedTime = null;
        _stageError = null;
        _processing = true;
      });

      final face = await _faces.detectLargest(img);
      if (!mounted) return;
      if (face == null) {
        setState(() {
          _face = null;
          _processing = false;
        });
        return;
      }
      setState(() => _face = face);

      final sw = Stopwatch()..start();
      final embedding = await _embedder.embed(img, face);
      sw.stop();
      if (!mounted) return;
      setState(() {
        _embedding = embedding;
        _embedTime = sw.elapsed;
        _processing = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _processing = false;
        _stageError = '$e';
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _statusLine() {
    if (_image == null) return 'Toma una foto o elige una de la galería para empezar.';
    if (_stageError != null) return 'Error: $_stageError';
    if (_processing) {
      if (_face == null) return 'Detectando rostro…';
      return 'Calculando embedding on-device…';
    }
    if (_face == null) return 'No se detectó ningún rostro.';
    if (_embedding == null) return 'Rostro detectado, embedding pendiente.';
    final ms = _embedTime!.inMilliseconds;
    return 'Embedding 512-d • L2 ${_norm(_embedding!).toStringAsFixed(3)} • $ms ms';
  }

  double _norm(Float32List v) {
    var s = 0.0;
    for (final x in v) {
      s += x * x;
    }
    return s == 0 ? 0 : math.sqrt(s);
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

