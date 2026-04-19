/// Model for a stock opportunity from the scanner
class Opportunity {
  final String ticker;
  final double sentiment;
  final int newsCount;
  final List<String> headlines;
  final String reasoning;
  final double confidence;
  final String scanType;
  final String scannedAt;
  final double? currentPrice;
  final double? priceChange;
  final double? priceChangePercent;

  const Opportunity({
    required this.ticker,
    required this.sentiment,
    required this.newsCount,
    required this.headlines,
    required this.reasoning,
    required this.confidence,
    required this.scanType,
    required this.scannedAt,
    this.currentPrice,
    this.priceChange,
    this.priceChangePercent,
  });

  factory Opportunity.fromJson(Map<String, dynamic> json) {
    return Opportunity(
      ticker: json['ticker'] as String? ?? '',
      sentiment: (json['sentiment'] as num?)?.toDouble() ?? 0.0,
      newsCount: json['news_count'] as int? ?? 0,
      headlines: (json['headlines'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      reasoning: json['reasoning'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      scanType: json['scan_type'] as String? ?? '',
      scannedAt: json['scanned_at'] as String? ?? '',
      currentPrice: (json['current_price'] is num)
          ? (json['current_price'] as num).toDouble()
          : null,
      priceChange: (json['price_change'] is num)
          ? (json['price_change'] as num).toDouble()
          : null,
      priceChangePercent: (json['price_change_percent'] is num)
          ? (json['price_change_percent'] as num).toDouble()
          : null,
    );
  }

  /// Get confidence as percentage string
  String get confidencePercent => '${(confidence * 100).toStringAsFixed(0)}%';

  /// Get sentiment as formatted string
  String get sentimentFormatted => sentiment >= 0
      ? '+${sentiment.toStringAsFixed(2)}'
      : sentiment.toStringAsFixed(2);

  /// Get scan type display label
  String get scanTypeLabel {
    switch (scanType) {
      case 'pre_market':
        return 'Pre-Market';
      case 'market_hours':
        return 'Live';
      case 'post_market':
        return 'After Hours';
      case 'manual':
        return 'Manual';
      default:
        return scanType;
    }
  }

  /// Get time ago string from scannedAt
  String get timeAgo {
    try {
      final scannedTime = DateTime.parse(scannedAt);
      final now = DateTime.now().toUtc();
      final difference = now.difference(scannedTime);

      if (difference.inMinutes < 1) {
        return 'Just now';
      } else if (difference.inMinutes < 60) {
        return '${difference.inMinutes}m ago';
      } else if (difference.inHours < 24) {
        return '${difference.inHours}h ago';
      } else {
        return '${difference.inDays}d ago';
      }
    } catch (_) {
      return '';
    }
  }
}

/// Response from the opportunities endpoint
class OpportunitiesResponse {
  final List<Opportunity> opportunities;
  final bool isMarketHours;

  const OpportunitiesResponse({
    required this.opportunities,
    required this.isMarketHours,
  });

  factory OpportunitiesResponse.fromJson(Map<String, dynamic> json) {
    final opportunitiesList = (json['opportunities'] as List<dynamic>?)
            ?.map((e) => Opportunity.fromJson(e as Map<String, dynamic>))
            .toList() ??
        [];
    return OpportunitiesResponse(
      opportunities: opportunitiesList,
      isMarketHours: json['is_market_hours'] as bool? ?? false,
    );
  }
}

/// Scanner status response
class ScannerStatus {
  final bool enabled;
  final double sentimentThreshold;
  final int maxCandidates;
  final int topOpportunities;
  final int lookbackHours;
  final bool isMarketHours;
  final bool shouldRunNow;
  final String currentMode;
  final int opportunitiesCount;

  const ScannerStatus({
    required this.enabled,
    required this.sentimentThreshold,
    required this.maxCandidates,
    required this.topOpportunities,
    required this.lookbackHours,
    required this.isMarketHours,
    required this.shouldRunNow,
    required this.currentMode,
    required this.opportunitiesCount,
  });

  factory ScannerStatus.fromJson(Map<String, dynamic> json) {
    return ScannerStatus(
      enabled: json['enabled'] as bool? ?? false,
      sentimentThreshold:
          (json['sentiment_threshold'] as num?)?.toDouble() ?? 0.15,
      maxCandidates: json['max_candidates'] as int? ?? 20,
      topOpportunities: json['top_opportunities'] as int? ?? 5,
      lookbackHours: json['lookback_hours'] as int? ?? 48,
      isMarketHours: json['is_market_hours'] as bool? ?? false,
      shouldRunNow: json['should_run_now'] as bool? ?? false,
      currentMode: json['current_mode'] as String? ?? 'after_hours',
      opportunitiesCount: json['opportunities_count'] as int? ?? 0,
    );
  }

  /// Get mode display label
  String get modeLabel {
    switch (currentMode) {
      case 'pre_market':
        return 'Pre-Market (8:30-9:15 AM)';
      case 'market_hours':
        return 'Market Open (9:15 AM-3:30 PM)';
      case 'post_market':
        return 'After Hours (3:30-5:00 PM)';
      case 'after_hours':
        return 'Closed';
      case 'weekend':
        return 'Weekend';
      default:
        return currentMode;
    }
  }
}
