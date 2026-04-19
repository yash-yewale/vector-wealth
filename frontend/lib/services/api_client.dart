import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Shared HTTP client for the Vector Wealth API.
/// Single source of truth for the backend URL.
class ApiClient {
  ApiClient._();
  static final ApiClient instance = ApiClient._();

  static const Duration _defaultTimeout = Duration(seconds: 120);
  static const int _maxRetries = 1;
  static const Duration _retryDelay = Duration(seconds: 2);

  static const String _prefsKey = 'backend_url';

  static const String _configuredBaseUrl =
      String.fromEnvironment('API_BASE_URL', defaultValue: '');

  /// The resolved backend URL. Call [initialize] first.
  String _resolvedBaseUrl = '';

  /// Whether [initialize] has been called.
  bool _initialized = false;

  String get baseUrl {
    if (_resolvedBaseUrl.isNotEmpty) return _resolvedBaseUrl;
    // Fallback for any early access before initialize()
    if (kIsWeb) return 'http://localhost:8000';
    return 'http://127.0.0.1:8000';
  }

  bool get isInitialized => _initialized;

  /// Whether a custom backend URL has been saved (mobile only).
  bool get hasCustomUrl => _resolvedBaseUrl.isNotEmpty && !kIsWeb;

  /// Initialize the API client. Call once at app startup.
  /// On web: uses localhost.
  /// On mobile: loads saved URL from SharedPreferences.
  Future<void> initialize() async {
    // 1) Compile-time override always wins
    if (_configuredBaseUrl.isNotEmpty) {
      _resolvedBaseUrl = _configuredBaseUrl;
      _initialized = true;
      return;
    }

    // 2) Web: always use localhost
    if (kIsWeb) {
      _resolvedBaseUrl = 'http://localhost:8000';
      _initialized = true;
      return;
    }

    // 3) Mobile: load saved URL from SharedPreferences
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString(_prefsKey);
      if (saved != null && saved.isNotEmpty) {
        _resolvedBaseUrl = saved;
      }
    } catch (_) {
      // SharedPreferences failed — will remain empty
    }

    _initialized = true;
  }

  /// Save a new backend URL (called from Settings page).
  /// [ip] should be just the IP like "192.168.31.78" or full URL.
  Future<void> setBackendUrl(String ip) async {
    final trimmed = ip.trim();
    if (trimmed.isEmpty) return;

    // If user enters just an IP, wrap it
    String url;
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      url = trimmed;
    } else {
      // Only append :8000 if there's no port already specified
      if (trimmed.contains(':')) {
        url = 'http://$trimmed';
      } else {
        url = 'http://$trimmed:8000';
      }
    }

    // Remove trailing slash
    if (url.endsWith('/')) url = url.substring(0, url.length - 1);

    _resolvedBaseUrl = url;

    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefsKey, url);
    } catch (_) {}
  }

  /// Clear the saved backend URL.
  Future<void> clearBackendUrl() async {
    _resolvedBaseUrl = '';
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_prefsKey);
    } catch (_) {}
  }

  /// Test connectivity to the current backend URL.
  /// Returns true if the backend responds successfully.
  Future<bool> testConnection([String? urlOverride]) async {
    final url = urlOverride ?? baseUrl;
    try {
      final response = await http
          .get(Uri.parse('$url/'))
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// POST JSON and return decoded response body.
  Future<Map<String, dynamic>> post(
    String path, {
    Map<String, dynamic>? body,
    Duration? timeout,
  }) async {
    return _withRetry(() async {
      final response = await http
          .post(
            Uri.parse('$baseUrl$path'),
            headers: {'Content-Type': 'application/json'},
            body: body != null ? jsonEncode(body) : null,
          )
          .timeout(timeout ?? _defaultTimeout);
      return _handleResponse(response);
    });
  }

  /// GET and return decoded response body.
  Future<Map<String, dynamic>> get(
    String path, {
    Duration? timeout,
  }) async {
    return _withRetry(() async {
      final response = await http
          .get(Uri.parse('$baseUrl$path'))
          .timeout(timeout ?? _defaultTimeout);
      return _handleResponse(response);
    });
  }

  /// Retry wrapper: tries once, retries on transient failure.
  Future<Map<String, dynamic>> _withRetry(
    Future<Map<String, dynamic>> Function() fn,
  ) async {
    for (int attempt = 0; attempt <= _maxRetries; attempt++) {
      try {
        return await fn();
      } on TimeoutException {
        if (attempt == _maxRetries) rethrow;
        await Future.delayed(_retryDelay);
      } on http.ClientException {
        if (attempt == _maxRetries) rethrow;
        await Future.delayed(_retryDelay);
      }
    }
    throw Exception('Request failed after retries');
  }

  Map<String, dynamic> _handleResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw ApiException(
      statusCode: response.statusCode,
      message: _extractErrorMessage(response),
    );
  }

  String _extractErrorMessage(http.Response response) {
    final body = response.body.trim();
    if (body.isEmpty) return 'API error: ${response.statusCode}';

    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic>) {
        final detail = decoded['detail'];
        if (detail != null && detail.toString().trim().isNotEmpty) {
          return 'API error ${response.statusCode}: ${detail.toString().trim()}';
        }
      }
      return 'API error ${response.statusCode}: $decoded';
    } catch (_) {
      return 'API error ${response.statusCode}: $body';
    }
  }
}

/// Typed API exception.
class ApiException implements Exception {
  final int statusCode;
  final String message;
  const ApiException({required this.statusCode, required this.message});

  @override
  String toString() => message;
}
