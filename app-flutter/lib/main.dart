import 'package:flutter/material.dart';

import 'api/api_client.dart';
import 'api/credentials.dart';
import 'pages/home_page.dart';
import 'pages/settings_page.dart';

void main() {
  runApp(const FaroApp());
}

class FaroApp extends StatelessWidget {
  const FaroApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Faro',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.amber),
        useMaterial3: true,
      ),
      home: const Bootstrap(),
    );
  }
}

class Bootstrap extends StatefulWidget {
  const Bootstrap({super.key});

  @override
  State<Bootstrap> createState() => _BootstrapState();
}

class _BootstrapState extends State<Bootstrap> {
  Credentials? _creds;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final c = await CredentialsStore.load();
    setState(() {
      _creds = c;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (_creds == null) {
      return SettingsPage(onSaved: (c) => setState(() => _creds = c));
    }
    return HomePage(client: ApiClient(_creds!), onResetCredentials: () {
      setState(() => _creds = null);
    });
  }
}
