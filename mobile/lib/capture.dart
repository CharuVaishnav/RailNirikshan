import 'dart:io';

import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';

/// Takes a photo with the camera (smaller size keeps uploads fast on weak networks).
Future<File?> takePhoto() async {
  final picked = await ImagePicker().pickImage(source: ImageSource.camera, maxWidth: 1600, imageQuality: 80);
  return picked == null ? null : File(picked.path);
}

/// Current GPS position, or null if location is off or permission is denied.
Future<Position?> currentPosition() async {
  if (!await Geolocator.isLocationServiceEnabled()) return null;
  var permission = await Geolocator.checkPermission();
  if (permission == LocationPermission.denied) {
    permission = await Geolocator.requestPermission();
  }
  if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) return null;
  return Geolocator.getCurrentPosition();
}
