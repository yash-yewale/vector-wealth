import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/opportunity.dart';
import '../services/api_client.dart';

class DiscoverProvider extends ChangeNotifier {
  final ApiClient _api = ApiClient.instance;

  bool isLoading = false;
  bool isScanning = false;
  String? error;
  List<Opportunity> opportunities = [];
  bool isMarketHours = false;
  ScannerStatus? status;

  /// Fetch current opportunities.
  Future<void> fetchOpportunities() async {
    isLoading = true;
    error = null;
    notifyListeners();

    try {
      final parsed = await _api.get(
        '/opportunities',
        timeout: const Duration(seconds: 60),
      );
      final result = OpportunitiesResponse.fromJson(parsed);
      opportunities = result.opportunities;
      isMarketHours = result.isMarketHours;
    } on TimeoutException {
      error = 'Request timed out. Please try again.';
    } on ApiException catch (e) {
      error = e.message;
    } catch (e) {
      error = 'Failed to connect: $e';
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  /// Fetch scanner status.
  Future<void> fetchStatus() async {
    try {
      final parsed = await _api.get(
        '/opportunities/status',
        timeout: const Duration(seconds: 60),
      );
      status = ScannerStatus.fromJson(parsed);
      isMarketHours = status?.isMarketHours ?? false;
      notifyListeners();
    } catch (_) {
      // Silent fail for status — not critical
    }
  }

  /// Trigger a manual scan.
  Future<void> triggerScan() async {
    isScanning = true;
    error = null;
    notifyListeners();

    try {
      await _api.post('/opportunities/scan');
      await fetchOpportunities();
    } on TimeoutException {
      error = 'Scan timed out. Please try again.';
    } on ApiException catch (e) {
      error = e.message;
    } catch (e) {
      error = 'Failed to scan: $e';
    } finally {
      isScanning = false;
      notifyListeners();
    }
  }

  /// Refresh both opportunities and status.
  Future<void> refresh() async {
    await Future.wait([
      fetchOpportunities(),
      fetchStatus(),
    ]);
  }
}
