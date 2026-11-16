import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Talks to the FastAPI backend.
/// 10.0.2.2 is how the Android emulator reaches your laptop's localhost.
/// On a real phone, use your laptop's Wi-Fi IP address, e.g. http://192.168.1.20:8000
class Api {
  static String baseUrl = 'http://10.0.2.2:8000';
  static String? _token;
  static String? role;
  static String? fullName;

  static Future<void> loadSession() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('token');
    role = prefs.getString('role');
    fullName = prefs.getString('fullName');
    baseUrl = prefs.getString('baseUrl') ?? baseUrl;
  }

  static bool get loggedIn => _token != null;

  static Map<String, String> get _headers => {
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  static Future<void> login(String username, String password) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'username': username, 'password': password}),
    );
    final data = _decode(res);
    _token = data['access_token'];
    role = data['role'];
    fullName = data['full_name'];
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('token', _token!);
    await prefs.setString('role', role!);
    await prefs.setString('fullName', fullName!);
    await prefs.setString('baseUrl', baseUrl);
  }

  static Future<void> logout() async {
    _token = null;
    role = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
    await prefs.remove('role');
  }

  static dynamic _decode(http.Response res) {
    final body = res.body.isEmpty ? {} : jsonDecode(utf8.decode(res.bodyBytes));
    if (res.statusCode >= 400) {
      throw ApiError(body is Map && body['detail'] != null ? body['detail'].toString() : 'Error ${res.statusCode}');
    }
    return body;
  }

  static Future<dynamic> get(String path) async =>
      _decode(await http.get(Uri.parse('$baseUrl$path'), headers: _headers));

  static Future<dynamic> postJson(String path, [Map<String, dynamic>? body]) async => _decode(await http.post(
        Uri.parse('$baseUrl$path'),
        headers: {..._headers, 'Content-Type': 'application/json'},
        body: jsonEncode(body ?? {}),
      ));

  static Future<dynamic> putJson(String path, Map<String, dynamic> body) async => _decode(await http.put(
        Uri.parse('$baseUrl$path'),
        headers: {..._headers, 'Content-Type': 'application/json'},
        body: jsonEncode(body),
      ));

  /// Multipart form with an optional photo (used for observations and fixes).
  static Future<dynamic> postForm(String path, Map<String, String> fields, {File? photo}) async {
    final req = http.MultipartRequest('POST', Uri.parse('$baseUrl$path'))
      ..headers.addAll(_headers)
      ..fields.addAll(fields);
    if (photo != null) {
      req.files.add(await http.MultipartFile.fromPath('photo', photo.path));
    }
    final streamed = await req.send();
    return _decode(await http.Response.fromStream(streamed));
  }

  static String photoUrl(String key) => '$baseUrl/inspections/photos/$key';
  static Map<String, String> get imageHeaders => _headers;
}

class ApiError implements Exception {
  final String message;
  ApiError(this.message);
  @override
  String toString() => message;
}
