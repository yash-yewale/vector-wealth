class NewsReference {
  final String date;
  final String title;

  NewsReference({required this.date, required this.title});

  factory NewsReference.fromJson(Map<String, dynamic> json) {
    return NewsReference(
      date: (json['date'] ?? '').toString(),
      title: (json['title'] ?? '').toString(),
    );
  }
}

class PeerStock {
  final String ticker;
  final double? currentPrice;
  final double? priceChange;
  final double? priceChangePercent;

  PeerStock({
    required this.ticker,
    this.currentPrice,
    this.priceChange,
    this.priceChangePercent,
  });

  factory PeerStock.fromJson(Map<String, dynamic> json) {
    return PeerStock(
      ticker: (json['ticker'] ?? '').toString(),
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
}

class AnalysisResult {
  final String ticker;
  final double sentiment;
  final double nowSentiment;
  final double patternSentiment;
  final double confidence;
  final int recentNewsCount;
  final int patternNewsCount;
  final String latestNewsDate;
  final bool staleData;
  final String staleReason;
  final String explanation;
  final List<String> positiveDrivers;
  final List<String> negativeDrivers;
  final String recommendation;
  final List<NewsReference> newsReferences;
  // New enhanced fields
  final double? currentPrice;
  final double? priceChange;
  final double? priceChangePercent;
  final String? aiSummary;
  final List<PeerStock>? peers;

  AnalysisResult({
    required this.ticker,
    required this.sentiment,
    required this.nowSentiment,
    required this.patternSentiment,
    required this.confidence,
    required this.recentNewsCount,
    required this.patternNewsCount,
    required this.latestNewsDate,
    required this.staleData,
    required this.staleReason,
    required this.explanation,
    required this.positiveDrivers,
    required this.negativeDrivers,
    required this.recommendation,
    required this.newsReferences,
    this.currentPrice,
    this.priceChange,
    this.priceChangePercent,
    this.aiSummary,
    this.peers,
  });

  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    final refs = (json['news_references'] as List<dynamic>? ?? [])
        .map((item) => NewsReference.fromJson(item as Map<String, dynamic>))
        .toList();
    final positiveDrivers = (json['positive_drivers'] as List<dynamic>? ?? [])
        .map((item) => item.toString())
        .toList();
    final negativeDrivers = (json['negative_drivers'] as List<dynamic>? ?? [])
        .map((item) => item.toString())
        .toList();
    final peers = (json['peers'] as List<dynamic>?)
        ?.map((item) => PeerStock.fromJson(item as Map<String, dynamic>))
        .toList();

    return AnalysisResult(
      ticker: (json['ticker'] ?? '').toString(),
      sentiment: (json['sentiment'] is num)
          ? (json['sentiment'] as num).toDouble()
          : double.tryParse((json['sentiment'] ?? '0').toString()) ?? 0,
      nowSentiment: (json['now_sentiment'] is num)
          ? (json['now_sentiment'] as num).toDouble()
          : double.tryParse((json['now_sentiment'] ?? '0').toString()) ?? 0,
      patternSentiment: (json['pattern_sentiment'] is num)
          ? (json['pattern_sentiment'] as num).toDouble()
          : double.tryParse((json['pattern_sentiment'] ?? '0').toString()) ?? 0,
      confidence: (json['confidence'] is num)
          ? (json['confidence'] as num).toDouble()
          : double.tryParse((json['confidence'] ?? '0').toString()) ?? 0,
      recentNewsCount: (json['recent_news_count'] is num)
          ? (json['recent_news_count'] as num).toInt()
          : int.tryParse((json['recent_news_count'] ?? '0').toString()) ?? 0,
      patternNewsCount: (json['pattern_news_count'] is num)
          ? (json['pattern_news_count'] as num).toInt()
          : int.tryParse((json['pattern_news_count'] ?? '0').toString()) ?? 0,
      latestNewsDate: (json['latest_news_date'] ?? '').toString(),
      staleData: json['stale_data'] == true,
      staleReason: (json['stale_reason'] ?? '').toString(),
      explanation: (json['explanation'] ?? '').toString(),
      positiveDrivers: positiveDrivers,
      negativeDrivers: negativeDrivers,
      recommendation: (json['recommendation'] ?? 'HOLD').toString(),
      newsReferences: refs,
      // New enhanced fields
      currentPrice: (json['current_price'] is num)
          ? (json['current_price'] as num).toDouble()
          : null,
      priceChange: (json['price_change'] is num)
          ? (json['price_change'] as num).toDouble()
          : null,
      priceChangePercent: (json['price_change_percent'] is num)
          ? (json['price_change_percent'] as num).toDouble()
          : null,
      aiSummary: json['ai_summary']?.toString(),
      peers: peers,
    );
  }
}
