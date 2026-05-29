import 'package:flutter/material.dart';

import '../capture/captured_image.dart';
import 'face_detector.dart';

// Draws [face]'s bounding box on top of [image], scaling from the original
// image pixel space to whatever size the widget is laid out at.
class FaceOverlay extends StatelessWidget {
  final CapturedImage image;
  final DetectedFace? face;
  const FaceOverlay({super.key, required this.image, required this.face});

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: image.width / image.height,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final scaleX = constraints.maxWidth / image.width;
          final scaleY = constraints.maxHeight / image.height;
          final scale = scaleX < scaleY ? scaleX : scaleY;
          return Stack(
            fit: StackFit.expand,
            children: [
              Image.memory(image.bytes, fit: BoxFit.contain),
              if (face != null)
                Positioned.fromRect(
                  rect: Rect.fromLTWH(
                    face!.boundingBox.left * scale,
                    face!.boundingBox.top * scale,
                    face!.boundingBox.width * scale,
                    face!.boundingBox.height * scale,
                  ),
                  child: Container(
                    decoration: BoxDecoration(
                      border: Border.all(
                        color: Colors.greenAccent,
                        width: 3,
                      ),
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}
