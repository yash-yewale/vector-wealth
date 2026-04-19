import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Tracks sentiment trend history per ticker using SharedPreferences.
class TrendProvider extends ChangeNotifier {
  static const _storageKey = 'sentiment_trends';
  Map<String, List<Map<String, dynamic>>> _trends = {};

  TrendProvider() {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_storageKey);
    if (raw != null) {
      try {
        final decoded = jsonDecode(raw) as Map<String, dynamic>;
        _trends = decoded.map((key, value) =>
            MapEntry(key, (value as List).cast<Map<String, dynamic>>()));
      } catch (_) {}
    }
    notifyListeners();
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_storageKey, jsonEncode(_trends));
  }

  /// Record an analysis result for trend tracking.
  Future<void> recordAnalysis({
    required String ticker,
    required double sentiment,
    required String recommendation,
  }) async {
    final upper = ticker.toUpperCase();
    _trends.putIfAbsent(upper, () => []);
    _trends[upper]!.add({
      'date': DateTime.now().toIso8601String().substring(0, 10),
      'sentiment': sentiment,
      'recommendation': recommendation,
    });
    // Keep last 20 entries per ticker
    if (_trends[upper]!.length > 20) {
      _trends[upper] = _trends[upper]!.sublist(_trends[upper]!.length - 20);
    }
    notifyListeners();
    await _save();
  }

  /// Get trend data for a ticker. Returns list of {date, sentiment, recommendation}.
  List<Map<String, dynamic>> getTrend(String ticker) {
    return _trends[ticker.toUpperCase()] ?? [];
  }

  /// Returns true if there's enough data to show a trend chart (≥2 points).
  bool hasTrend(String ticker) {
    return getTrend(ticker).length >= 2;
  }
}
