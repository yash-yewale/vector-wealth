import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../services/api_client.dart';

// ─── Data Models ────────────────────────────────────────────────────────────

class RecommendedStock {
  final String ticker;
  final int quantity;
  final double buyPrice;
  final String reasoning;

  RecommendedStock({
    required this.ticker,
    required this.quantity,
    required this.buyPrice,
    this.reasoning = '',
  });

  Map<String, dynamic> toJson() => {
        'ticker': ticker,
        'quantity': quantity,
        'buyPrice': buyPrice,
        'reasoning': reasoning,
      };

  factory RecommendedStock.fromJson(Map<String, dynamic> json) =>
      RecommendedStock(
        ticker: json['ticker'] ?? '',
        quantity: (json['quantity'] ?? 0) is int
            ? json['quantity']
            : (json['quantity'] as num).toInt(),
        buyPrice: (json['buyPrice'] ?? 0).toDouble(),
        reasoning: json['reasoning'] ?? '',
      );
}

class Holding {
  String ticker;
  double quantity;
  double buyPrice;
  String buyDate;

  // Live data (filled after analysis)
  double? currentPrice;
  double? currentValue;
  double? pnl;
  double? pnlPercent;

  Holding({
    required this.ticker,
    required this.quantity,
    required this.buyPrice,
    this.buyDate = '',
    this.currentPrice,
    this.currentValue,
    this.pnl,
    this.pnlPercent,
  });

  Map<String, dynamic> toJson() => {
        'ticker': ticker,
        'quantity': quantity,
        'buyPrice': buyPrice,
        'buyDate': buyDate,
      };

  factory Holding.fromJson(Map<String, dynamic> json) => Holding(
        ticker: json['ticker'] ?? '',
        quantity: (json['quantity'] ?? 0).toDouble(),
        buyPrice: (json['buyPrice'] ?? 0).toDouble(),
        buyDate: json['buyDate'] ?? '',
      );
}

class Goal {
  final String id;
  String name;
  double targetAmount;
  String targetDate; // ISO date or "2045"
  String riskTolerance; // conservative, moderate, aggressive
  List<Holding> holdings;

  // Computed after analysis
  double? totalInvested;
  double? totalCurrentValue;
  double? totalPnl;
  double? totalPnlPercent;
  double? progress;
  double? yearsLeft;
  String? suggestion;
  List<RecommendedStock> recommendedStocks;

  Goal({
    required this.id,
    required this.name,
    required this.targetAmount,
    required this.targetDate,
    this.riskTolerance = 'moderate',
    List<Holding>? holdings,
    List<RecommendedStock>? recommendedStocks,
  })  : holdings = holdings ?? [],
        recommendedStocks = recommendedStocks ?? [];

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'targetAmount': targetAmount,
        'targetDate': targetDate,
        'riskTolerance': riskTolerance,
        'holdings': holdings.map((h) => h.toJson()).toList(),
      };

  factory Goal.fromJson(Map<String, dynamic> json) => Goal(
        id: json['id'] ?? '',
        name: json['name'] ?? '',
        targetAmount: (json['targetAmount'] ?? 0).toDouble(),
        targetDate: json['targetDate'] ?? '',
        riskTolerance: json['riskTolerance'] ?? 'moderate',
        holdings: (json['holdings'] as List?)
                ?.map((h) => Holding.fromJson(h as Map<String, dynamic>))
                .toList() ??
            [],
      );
}

// ─── Provider ───────────────────────────────────────────────────────────────

class PortfolioProvider extends ChangeNotifier {
  static const _storageKey = 'portfolio_goals';
  List<Goal> _goals = [];
  bool _isLoading = false;
  bool _isAnalyzing = false;
  String? _error;

  String get _baseUrl => ApiClient.instance.baseUrl;

  PortfolioProvider() {
    _loadFromStorage();
  }

  List<Goal> get goals => List.unmodifiable(_goals);
  bool get isLoading => _isLoading;
  bool get isAnalyzing => _isAnalyzing;
  String? get error => _error;
  bool get isEmpty => _goals.isEmpty;
  int get totalHoldings => _goals.fold(0, (sum, g) => sum + g.holdings.length);

  double get totalInvested =>
      _goals.fold(0.0, (sum, g) => sum + (g.totalInvested ?? 0));
  double get totalCurrentValue =>
      _goals.fold(0.0, (sum, g) => sum + (g.totalCurrentValue ?? 0));

  // ─── Persistence (local + backend) ──────────────────────────────────────

  Future<void> _loadFromStorage() async {
    _isLoading = true;
    notifyListeners();
    try {
      // Try local first
      final prefs = await SharedPreferences.getInstance();
      final data = prefs.getString(_storageKey);
      if (data != null && data.isNotEmpty) {
        final list = jsonDecode(data) as List;
        _goals =
            list.map((g) => Goal.fromJson(g as Map<String, dynamic>)).toList();
      }

      // Also try to load from backend (more reliable than browser localStorage)
      if (_goals.isEmpty) {
        try {
          final response = await http
              .get(
                  Uri.parse('$_baseUrl/storage/portfolio/load?user_id=default'))
              .timeout(const Duration(seconds: 5));
          if (response.statusCode == 200) {
            final body = jsonDecode(response.body);
            final backendGoals = body['goals'] as List? ?? [];
            if (backendGoals.isNotEmpty) {
              _goals = backendGoals
                  .map((g) => Goal.fromJson(g as Map<String, dynamic>))
                  .toList();
              // Sync back to local
              await _saveLocal();
            }
          }
        } catch (_) {
          // Backend not reachable — local data is fine
        }
      }
    } catch (e) {
      _error = 'Failed to load portfolio: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> _saveLocal() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final data = jsonEncode(_goals.map((g) => g.toJson()).toList());
      await prefs.setString(_storageKey, data);
    } catch (e) {
      _error = 'Failed to save locally: $e';
    }
  }

  Future<void> _saveToStorage() async {
    await _saveLocal();
    // Also save to backend for durability
    _syncToBackend();
  }

  Future<void> _syncToBackend() async {
    try {
      await http
          .post(
            Uri.parse('$_baseUrl/storage/portfolio/save'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'user_id': 'default',
              'goals': _goals.map((g) => g.toJson()).toList(),
            }),
          )
          .timeout(const Duration(seconds: 5));
    } catch (_) {
      // Silently fail — local storage is primary
    }
  }

  // ─── Goal CRUD ──────────────────────────────────────────────────────────

  Future<void> addGoal(Goal goal) async {
    _goals.add(goal);
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> updateGoal(String goalId, Goal updated) async {
    final idx = _goals.indexWhere((g) => g.id == goalId);
    if (idx >= 0) {
      _goals[idx] = updated;
      await _saveToStorage();
      notifyListeners();
    }
  }

  Future<void> deleteGoal(String goalId) async {
    _goals.removeWhere((g) => g.id == goalId);
    await _saveToStorage();
    notifyListeners();
  }

  // ─── Holding CRUD ───────────────────────────────────────────────────────

  Future<void> addHolding(String goalId, Holding holding) async {
    final goal = _goals.firstWhere((g) => g.id == goalId,
        orElse: () => throw Exception('Goal not found'));
    goal.holdings.add(holding);
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> removeHolding(String goalId, int holdingIndex) async {
    final goal = _goals.firstWhere((g) => g.id == goalId,
        orElse: () => throw Exception('Goal not found'));
    if (holdingIndex >= 0 && holdingIndex < goal.holdings.length) {
      goal.holdings.removeAt(holdingIndex);
      await _saveToStorage();
      notifyListeners();
    }
  }

  // ─── Analysis ───────────────────────────────────────────────────────────

  Future<void> analyzePortfolio() async {
    if (_goals.isEmpty) return;
    _isAnalyzing = true;
    _error = null;
    notifyListeners();

    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/portfolio/analyze'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'goals': _goals.map((g) => g.toJson()).toList(),
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final analyzedGoals = data['goals'] as List;

        for (final ag in analyzedGoals) {
          final goalId = ag['goalId'];
          final goal = _goals.firstWhere((g) => g.id == goalId,
              orElse: () => _goals.first);

          goal.totalInvested = (ag['totalInvested'] ?? 0).toDouble();
          goal.totalCurrentValue = (ag['totalCurrentValue'] ?? 0).toDouble();
          goal.totalPnl = (ag['totalPnl'] ?? 0).toDouble();
          goal.totalPnlPercent = (ag['totalPnlPercent'] ?? 0).toDouble();
          goal.progress = (ag['progress'] ?? 0).toDouble();
          goal.yearsLeft = (ag['yearsLeft'] ?? 0).toDouble();

          // Update holding prices
          final analyzedHoldings = ag['holdings'] as List? ?? [];
          for (int i = 0;
              i < analyzedHoldings.length && i < goal.holdings.length;
              i++) {
            final ah = analyzedHoldings[i];
            goal.holdings[i].currentPrice =
                (ah['currentPrice'] ?? 0).toDouble();
            goal.holdings[i].currentValue =
                (ah['currentValue'] ?? 0).toDouble();
            goal.holdings[i].pnl = (ah['pnl'] ?? 0).toDouble();
            goal.holdings[i].pnlPercent = (ah['pnlPercent'] ?? 0).toDouble();
          }
        }
      } else {
        _error = 'Analysis failed (${response.statusCode})';
      }
    } catch (e) {
      _error = 'Connection failed: $e';
    } finally {
      _isAnalyzing = false;
      notifyListeners();
    }
  }

  Future<void> fetchSuggestion(String goalId) async {
    final goal = _goals.firstWhere((g) => g.id == goalId,
        orElse: () => throw Exception('Goal not found'));

    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/portfolio/suggest'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'goal': goal.toJson()}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        goal.suggestion = data['suggestion'] ?? '';
        final stocks = data['recommended_stocks'] as List? ?? [];
        goal.recommendedStocks = stocks
            .map((s) => RecommendedStock.fromJson(s as Map<String, dynamic>))
            .toList();
        notifyListeners();
      }
    } catch (e) {
      goal.suggestion = 'Could not fetch suggestions: $e';
      goal.recommendedStocks = [];
      notifyListeners();
    }
  }
}
