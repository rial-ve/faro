import 'package:image_picker/image_picker.dart';

import 'captured_image.dart';

class CapturePicker {
  final ImagePicker _picker = ImagePicker();

  Future<CapturedImage?> takePhoto() => _pick(ImageSource.camera);
  Future<CapturedImage?> pickFromGallery() => _pick(ImageSource.gallery);

  Future<CapturedImage?> _pick(ImageSource source) async {
    final picked = await _picker.pickImage(
      source: source,
      preferredCameraDevice: CameraDevice.rear,
      maxWidth: 1024,
      imageQuality: 90,
    );
    if (picked == null) return null;
    final bytes = await picked.readAsBytes();
    return CapturedImage.fromBytes(bytes);
  }
}
