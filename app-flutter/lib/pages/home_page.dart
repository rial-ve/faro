import 'package:flutter/material.dart';

import '../api/api_client.dart';

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
  String _healthz = '…';
  String _models = '…';

  @override
  void initState() {
    super.initState();
    _probe();
  }

  Future<void> _probe() async {
    setState(() {
      _healthz = '…';
      _models = '…';
    });
    try {
      final ok = await widget.client.healthz();
      setState(() => _healthz = ok ? 'ok' : 'unexpected');
    } catch (e) {
      setState(() => _healthz = 'error: $e');
    }
    try {
      final m = await widget.client.models();
      setState(() => _models = '${m['provider']} / ${m['model_id']} / ${m['quantization']}');
    } catch (e) {
      setState(() => _models = 'error: $e');
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
            _Row(label: 'GET /healthz', value: _healthz),
            const SizedBox(height: 8),
            _Row(label: 'GET /v1/models', value: _models),
            const SizedBox(height: 24),
            OutlinedButton(
              onPressed: _probe,
              child: const Text('Reintentar'),
            ),
            const Spacer(),
            const Text(
              '004.4 — wiring básico. La cámara, la detección, el embedding '
              'on-device y la voz llegan en los puntos siguientes.',
              style: TextStyle(color: Colors.grey),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  final String label;
  final String value;
  const _Row({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(width: 140, child: Text(label, style: const TextStyle(fontWeight: FontWeight.w600))),
        Expanded(child: Text(value)),
      ],
    );
  }
}
