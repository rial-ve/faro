import 'dart:async';

import 'package:flutter_tts/flutter_tts.dart';

class Speaker {
  final FlutterTts _tts = FlutterTts();
  bool _ready = false;

  Future<void> _ensureReady() async {
    if (_ready) return;
    await _tts.setLanguage('es-ES');
    await _tts.setSpeechRate(0.5);
    await _tts.setPitch(1.0);
    await _tts.awaitSpeakCompletion(true);
    _ready = true;
  }

  Future<void> speak(String text) async {
    if (text.isEmpty) return;
    await _ensureReady();
    await _tts.stop();
    await _tts.speak(text);
  }

  Future<void> stop() async {
    if (!_ready) return;
    await _tts.stop();
  }

  Future<void> close() async {
    if (!_ready) return;
    await _tts.stop();
  }
}
