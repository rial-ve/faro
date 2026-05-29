import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

import 'credentials.dart';
import 'models.dart';

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

  // Liveness — does NOT require auth on the server, but we send the header
  // anyway so a 200 here proves the URL is reachable.
  Future<bool> healthz() async {
    final r = await _dio.get('/healthz');
    return r.statusCode == 200 && r.data['status'] == 'ok';
  }

  // Authenticated probe: succeeds only if the credentials are valid.
  Future<Map<String, String>> models() async {
    final r = await _dio.get('/v1/models');
    return Map<String, String>.from(r.data as Map);
  }

  // Send a pre-computed 512-d embedding for matching against the carer's
  // PersonStore. Backend reply is the same shape as /v1/recognize: a
  // {match, spoken} envelope.
  Future<RecognizeResponse> recognizeEmbedding(
    Float32List embedding, {
    String language = 'es',
  }) async {
    final r = await _dio.post(
      '/v1/recognize-embedding',
      data: {
        'embedding': embedding.toList(),
        'language': language,
      },
    );
    return RecognizeResponse.fromJson(r.data as Map<String, dynamic>);
  }
}
