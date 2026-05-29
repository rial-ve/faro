import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../capture/capture_picker.dart';
import '../capture/captured_image.dart';

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
  CapturedImage? _image;
  String? _backendStatus;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _probeBackend();
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
      setState(() => _image = img);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo capturar: $e')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
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
                    : Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          ConstrainedBox(
                            constraints: const BoxConstraints(maxHeight: 360),
                            child: Image.memory(_image!.bytes),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            '${_image!.width} × ${_image!.height}',
                            style: const TextStyle(color: Colors.grey),
                          ),
                        ],
                      ),
              ),
            ),
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
