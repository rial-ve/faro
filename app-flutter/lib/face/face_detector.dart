import 'dart:ui';

import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';

import '../capture/captured_image.dart';

class DetectedFace {
  // Bounding box in source-image pixel coordinates.
  final Rect boundingBox;
  const DetectedFace(this.boundingBox);
}

class FaceDetectorRunner {
  final FaceDetector _detector;

  FaceDetectorRunner()
      : _detector = FaceDetector(
          options: FaceDetectorOptions(
            performanceMode: FaceDetectorMode.accurate,
            enableLandmarks: false,
            enableContours: false,
            enableClassification: false,
            enableTracking: false,
            minFaceSize: 0.15,
          ),
        );

  // Returns the largest face by bounding-box area, or null if none.
  Future<DetectedFace?> detectLargest(CapturedImage image) async {
    final input = InputImage.fromFilePath(image.path);
    final faces = await _detector.processImage(input);
    if (faces.isEmpty) return null;
    final largest = faces.reduce((a, b) {
      final aArea = a.boundingBox.width * a.boundingBox.height;
      final bArea = b.boundingBox.width * b.boundingBox.height;
      return aArea >= bArea ? a : b;
    });
    return DetectedFace(largest.boundingBox);
  }

  Future<void> close() => _detector.close();
}
