import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class Credentials {
  final String baseUrl;
  final String username;
  final String password;

  const Credentials({
    required this.baseUrl,
    required this.username,
    required this.password,
  });
}

class CredentialsStore {
  static const _storage = FlutterSecureStorage();
  static const _kBaseUrl = 'faro.baseUrl';
  static const _kUsername = 'faro.username';
  static const _kPassword = 'faro.password';

  static Future<Credentials?> load() async {
    final baseUrl = await _storage.read(key: _kBaseUrl);
    final username = await _storage.read(key: _kUsername);
    final password = await _storage.read(key: _kPassword);
    if (baseUrl == null || username == null || password == null) return null;
    return Credentials(
      baseUrl: baseUrl,
      username: username,
      password: password,
    );
  }

  static Future<void> save(Credentials c) async {
    await _storage.write(key: _kBaseUrl, value: c.baseUrl);
    await _storage.write(key: _kUsername, value: c.username);
    await _storage.write(key: _kPassword, value: c.password);
  }

  static Future<void> clear() async {
    await _storage.delete(key: _kBaseUrl);
    await _storage.delete(key: _kUsername);
    await _storage.delete(key: _kPassword);
  }
}
