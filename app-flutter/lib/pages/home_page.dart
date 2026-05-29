import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../api/models.dart';
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

enum _Stage { idle, detecting, embedding, matching, done, noFace, error }

class _HomePageState extends State<HomePage> {
  final _picker = CapturePicker();
  final _faces = FaceDetectorRunner();
  final _embedder = FaceEmbedder();

  CapturedImage? _image;
  DetectedFace? _face;
  Float32List? _embedding;
  Duration? _embedTime;
  Duration? _matchTime;
  RecognizeResponse? _result;
  _Stage _stage = _Stage.idle;
  String? _errorMessage;
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
        _matchTime = null;
        _result = null;
        _errorMessage = null;
        _stage = _Stage.detecting;
      });

      final face = await _faces.detectLargest(img);
      if (!mounted) return;
      if (face == null) {
        setState(() => _stage = _Stage.noFace);
        return;
      }
      setState(() {
        _face = face;
        _stage = _Stage.embedding;
      });

      final esw = Stopwatch()..start();
      final embedding = await _embedder.embed(img, face);
      esw.stop();
      if (!mounted) return;
      setState(() {
        _embedding = embedding;
        _embedTime = esw.elapsed;
        _stage = _Stage.matching;
      });

      final msw = Stopwatch()..start();
      final response = await widget.client.recognizeEmbedding(embedding);
      msw.stop();
      if (!mounted) return;
      setState(() {
        _result = response;
        _matchTime = msw.elapsed;
        _stage = _Stage.done;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _stage = _Stage.error;
        _errorMessage = '$e';
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  double _norm(Float32List v) {
    var s = 0.0;
    for (final x in v) {
      s += x * x;
    }
    return s == 0 ? 0 : math.sqrt(s);
  }

  Widget _resultPanel() {
    if (_result == null) return const SizedBox.shrink();
    final match = _result!.match;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: match == null
            ? Colors.grey.withValues(alpha: 0.2)
            : Colors.green.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: match == null ? Colors.grey : Colors.green,
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _result!.spoken,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          ),
          if (match != null) ...[
            const SizedBox(height: 6),
            Text(
              'Similitud: ${match.similarity.toStringAsFixed(3)}',
              style: const TextStyle(color: Colors.black54),
            ),
          ],
        ],
      ),
    );
  }

  String _timings() {
    final parts = <String>[];
    if (_embedTime != null) parts.add('embed ${_embedTime!.inMilliseconds} ms');
    if (_matchTime != null) parts.add('match ${_matchTime!.inMilliseconds} ms');
    if (_embedding != null) parts.add('||v||=${_norm(_embedding!).toStringAsFixed(3)}');
    return parts.join(' • ');
  }

  String _statusLine() {
    switch (_stage) {
      case _Stage.idle:
        return 'Toma una foto o elige una de la galería para empezar.';
      case _Stage.detecting:
        return 'Detectando rostro…';
      case _Stage.embedding:
        return 'Calculando embedding on-device…';
      case _Stage.matching:
        return 'Consultando al servidor…';
      case _Stage.noFace:
        return 'No se detectó ningún rostro.';
      case _Stage.done:
        return _timings();
      case _Stage.error:
        return 'Error: ${_errorMessage ?? "desconocido"}';
    }
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
            _resultPanel(),
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
