import 'dart:typed_data';
import 'dart:ui' as ui;

class CapturedImage {
  final Uint8List bytes;
  final int width;
  final int height;
  // ML Kit and tflite preprocessing both read from a file path, so we keep
  // image_picker's temp path around alongside the raw bytes.
  final String path;

  const CapturedImage({
    required this.bytes,
    required this.width,
    required this.height,
    required this.path,
  });

  static Future<CapturedImage> fromPickedFile(String path, Uint8List bytes) async {
    final codec = await ui.instantiateImageCodec(bytes);
    final frame = await codec.getNextFrame();
    final img = frame.image;
    return CapturedImage(
      bytes: bytes,
      width: img.width,
      height: img.height,
      path: path,
    );
  }
}
