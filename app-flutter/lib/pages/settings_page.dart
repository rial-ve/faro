import 'package:flutter/material.dart';

import '../api/credentials.dart';

class SettingsPage extends StatefulWidget {
  final void Function(Credentials) onSaved;
  const SettingsPage({super.key, required this.onSaved});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final _baseUrl = TextEditingController(text: 'http://10.0.2.2:8000');
  final _user = TextEditingController(text: 'carer');
  final _pass = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _baseUrl.dispose();
    _user.dispose();
    _pass.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    final c = Credentials(
      baseUrl: _baseUrl.text.trim(),
      username: _user.text.trim(),
      password: _pass.text,
    );
    try {
      await CredentialsStore.save(c);
      widget.onSaved(c);
    } catch (e) {
      setState(() {
        _busy = false;
        _error = 'No se pudo guardar: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Conectar a Faro')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Datos del servidor del cuidador. Se guardan cifrados en el '
              'almacén seguro del sistema (Keychain en iOS, EncryptedSharedPreferences en Android).',
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _baseUrl,
              decoration: const InputDecoration(
                labelText: 'URL del backend',
                hintText: 'http://10.0.2.2:8000 (Android emu) o http://localhost:8000 (iOS sim)',
              ),
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _user,
              decoration: const InputDecoration(labelText: 'Usuario'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _pass,
              decoration: const InputDecoration(labelText: 'Contraseña'),
              obscureText: true,
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _busy ? null : _save,
              child: Text(_busy ? 'Guardando…' : 'Guardar'),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: const TextStyle(color: Colors.red)),
            ],
          ],
        ),
      ),
    );
  }
}
