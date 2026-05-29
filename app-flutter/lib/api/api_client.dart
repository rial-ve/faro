import 'dart:convert';

import 'package:dio/dio.dart';

import 'credentials.dart';

class ApiClient {
  final Credentials creds;
  late final Dio _dio;

  ApiClient(this.creds) {
    final basic = base64Encode(utf8.encode('${creds.username}:${creds.password}'));
    _dio = Dio(BaseOptions(
      baseUrl: creds.baseUrl,
      headers: {'Authorization': 'Basic $basic'},
      connectTimeout: const Duration(seconds: 5),
      receiveTimeout: const Duration(seconds: 10),
    ));
  }

  /// Liveness — does NOT require auth on the server, but we send the header
  /// anyway so a 200 here proves the URL is reachable.
  Future<bool> healthz() async {
    final r = await _dio.get('/healthz');
    return r.statusCode == 200 && r.data['status'] == 'ok';
  }

  /// Authenticated probe: succeeds only if the credentials are valid.
  Future<Map<String, String>> models() async {
    final r = await _dio.get('/v1/models');
    return Map<String, String>.from(r.data as Map);
  }
}
