import 'dart:math' as math;
import 'dart:typed_data';

import 'package:image/image.dart' as img;
import 'package:tflite_flutter/tflite_flutter.dart';

import '../capture/captured_image.dart';
import 'face_detector.dart';

const _modelAsset = 'assets/models/mobilefacenet.tflite';
const _inputSize = 112;
const _embeddingDim = 512;

class FaceEmbedder {
  Interpreter? _interpreter;

  Future<void> _ensureLoaded() async {
    _interpreter ??= await Interpreter.fromAsset(_modelAsset);
  }

  // Crop a square around [face] in [image], resize to 112x112, run
  // MobileFaceNet, return a 512-d L2-normalized embedding in the same
  // vector space as the server's mobilefacenet (experiment 003).
  Future<Float32List> embed(CapturedImage image, DetectedFace face) async {
    await _ensureLoaded();

    final decoded = img.decodeImage(image.bytes);
    if (decoded == null) {
      throw StateError('Could not decode image bytes');
    }

    final crop = _squareCrop(decoded, face);
    final resized = img.copyResize(
      crop,
      width: _inputSize,
      height: _inputSize,
      interpolation: img.Interpolation.linear,
    );

    final input = _toNHWCNested(resized);
    final output = List.generate(
      1,
      (_) => List<double>.filled(_embeddingDim, 0.0),
    );

    _interpreter!.run(input, output);

    return _l2Normalize(Float32List.fromList(output[0]));
  }

  img.Image _squareCrop(img.Image src, DetectedFace face) {
    final box = face.boundingBox;
    final cx = box.left + box.width / 2;
    final cy = box.top + box.height / 2;
    // 1.1x padding around the detected box, snapped to a square so the
    // resize to 112x112 doesn't squash a non-square crop.
    final side = math.max(box.width, box.height) * 1.1;
    final half = side / 2;

    var left = (cx - half).toInt();
    var top = (cy - half).toInt();
    var width = side.toInt();
    var height = side.toInt();

    if (left < 0) {
      width += left;
      left = 0;
    }
    if (top < 0) {
      height += top;
      top = 0;
    }
    if (left + width > src.width) width = src.width - left;
    if (top + height > src.height) height = src.height - top;

    return img.copyCrop(src, x: left, y: top, width: width, height: height);
  }

  // NHWC RGB, normalized to [-1, 1] via (pixel - 127.5) / 127.5 — the same
  // normalization insightface's blobFromImages applies before feeding the
  // server's ONNX (input_mean=input_std=127.5, swapRB=True).
  List<List<List<List<double>>>> _toNHWCNested(img.Image src) {
    return [
      List.generate(_inputSize, (y) {
        return List.generate(_inputSize, (x) {
          final p = src.getPixel(x, y);
          return [
            (p.r - 127.5) / 127.5,
            (p.g - 127.5) / 127.5,
            (p.b - 127.5) / 127.5,
          ];
        });
      }),
    ];
  }

  Float32List _l2Normalize(Float32List v) {
    var sumSq = 0.0;
    for (final x in v) {
      sumSq += x * x;
    }
    final norm = math.sqrt(sumSq) + 1e-12;
    final out = Float32List(v.length);
    for (var i = 0; i < v.length; i++) {
      out[i] = v[i] / norm;
    }
    return out;
  }

  Future<void> close() async {
    _interpreter?.close();
    _interpreter = null;
  }
}
