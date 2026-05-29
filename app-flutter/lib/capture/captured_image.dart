import 'dart:typed_data';
import 'dart:ui' as ui;

class CapturedImage {
  final Uint8List bytes;
  final int width;
  final int height;

  const CapturedImage({
    required this.bytes,
    required this.width,
    required this.height,
  });

  static Future<CapturedImage> fromBytes(Uint8List bytes) async {
    final codec = await ui.instantiateImageCodec(bytes);
    final frame = await codec.getNextFrame();
    final img = frame.image;
    return CapturedImage(
      bytes: bytes,
      width: img.width,
      height: img.height,
    );
  }
}
