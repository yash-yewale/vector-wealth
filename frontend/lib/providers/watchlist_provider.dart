import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Persistent watchlist provider — stores favorite tickers using SharedPreferences.
class WatchlistProvider extends ChangeNotifier {
  static const _storageKey = 'watchlist_tickers';
  List<String> _tickers = [];

  List<String> get tickers => List.unmodifiable(_tickers);

  WatchlistProvider() {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    _tickers = prefs.getStringList(_storageKey) ?? [];
    notifyListeners();
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(_storageKey, _tickers);
  }

  bool isWatched(String ticker) =>
      _tickers.contains(ticker.toUpperCase());

  Future<void> toggle(String ticker) async {
    final upper = ticker.toUpperCase();
    if (_tickers.contains(upper)) {
      _tickers.remove(upper);
    } else {
      _tickers.insert(0, upper);
      if (_tickers.length > 20) _tickers.removeLast();
    }
    notifyListeners();
    await _save();
  }
}
