import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/analysis_result.dart';
import '../services/api_client.dart';

class AnalysisProvider extends ChangeNotifier {
  final ApiClient _api = ApiClient.instance;

  bool isLoading = false;
  String? error;
  AnalysisResult? result;

  /// Last 10 analyzed tickers (most recent first, no duplicates).
  final List<String> _recentTickers = [];
  List<String> get recentTickers => List.unmodifiable(_recentTickers);

  Future<void> analyzeTicker(String ticker) async {
    final cleanTicker = ticker.trim().toUpperCase();
    if (cleanTicker.isEmpty) {
      error = 'Please enter a stock ticker.';
      result = null;
      notifyListeners();
      return;
    }

    isLoading = true;
    error = null;
    notifyListeners();

    try {
      final parsed = await _api.post(
        '/analyze',
        body: {'ticker': cleanTicker},
      );
      result = AnalysisResult.fromJson(parsed);

      // Track recent tickers
      _recentTickers.remove(cleanTicker);
      _recentTickers.insert(0, cleanTicker);
      if (_recentTickers.length > 10) {
        _recentTickers.removeLast();
      }
    } on TimeoutException {
      error = 'Request timed out. The backend may still be processing.';
      result = null;
    } on ApiException catch (e) {
      error = e.message;
      result = null;
    } catch (e) {
      error = 'Failed to connect: $e';
      result = null;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }
}
