import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../main.dart';
import '../screens/settings_page.dart';

import '../providers/analysis_provider.dart';
import '../providers/trend_provider.dart';
import '../providers/watchlist_provider.dart';
import '../widgets/ai_summary_card.dart';
import '../widgets/drivers_card.dart';
import '../widgets/news_card.dart';
import '../widgets/peer_comparison_card.dart';
import '../widgets/price_card.dart';
import '../widgets/sentiment_card.dart';
import '../widgets/sentiment_trend_chart.dart';
import '../widgets/skeleton_loading.dart';
import '../widgets/ticker_search_field.dart';

class DashboardPage extends StatefulWidget {
  final VoidCallback onToggleTheme;

  const DashboardPage({super.key, required this.onToggleTheme});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  final TextEditingController _tickerController = TextEditingController();

  @override
  void dispose() {
    _tickerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AnalysisProvider>();
    final result = provider.result;
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: const Text('Vector Wealth'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_rounded),
            tooltip: 'Settings',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const SettingsPage()),
              );
            },
          ),
          ThemeToggleButton(onToggle: widget.onToggleTheme),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          if (_tickerController.text.trim().isNotEmpty) {
            await provider.analyzeTicker(_tickerController.text);
          }
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Watchlist quick access
              Consumer<WatchlistProvider>(
                builder: (context, watchlist, _) {
                  if (watchlist.tickers.isEmpty) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.star,
                                size: 16, color: Color(0xFFFBBF24)),
                            const SizedBox(width: 4),
                            Text('Watchlist',
                                style: theme.textTheme.bodySmall
                                    ?.copyWith(fontWeight: FontWeight.w600)),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Wrap(
                          spacing: 8,
                          runSpacing: 4,
                          children: watchlist.tickers.take(8).map((t) {
                            return ActionChip(
                              avatar: const Icon(Icons.star,
                                  size: 14, color: Color(0xFFFBBF24)),
                              label:
                                  Text(t, style: const TextStyle(fontSize: 12)),
                              onPressed: () {
                                _tickerController.text = t;
                                provider.analyzeTicker(t);
                              },
                            );
                          }).toList(),
                        ),
                      ],
                    ),
                  );
                },
              ),

              // Search Card with autocomplete
              TickerSearchField(
                controller: _tickerController,
                isLoading: provider.isLoading,
                onAnalyze: () => provider.analyzeTicker(_tickerController.text),
                recentTickers: provider.recentTickers,
                onRecentTap: (ticker) {
                  _tickerController.text = ticker;
                  provider.analyzeTicker(ticker);
                },
              ),

              if (provider.error != null) ...[
                const SizedBox(height: 12),
                Card(
                  color: theme.colorScheme.errorContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Icon(Icons.error_outline,
                            color: theme.colorScheme.error),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            provider.error!,
                            style: TextStyle(color: theme.colorScheme.error),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],

              // Skeleton loading
              if (provider.isLoading) const AnalysisSkeleton(),

              // Results with staggered entry
              if (result != null && !provider.isLoading)
                _AnimatedResults(result: result),
            ],
          ),
        ),
      ),
    );
  }
}

/// Staggered animation wrapper that fades + slides each result card in.
class _AnimatedResults extends StatefulWidget {
  final dynamic result;

  const _AnimatedResults({required this.result});

  @override
  State<_AnimatedResults> createState() => _AnimatedResultsState();
}

class _AnimatedResultsState extends State<_AnimatedResults>
    with TickerProviderStateMixin {
  late List<AnimationController> _controllers;
  late List<Animation<double>> _fadeAnims;
  late List<Animation<Offset>> _slideAnims;
  bool _recorded = false;

  static const _cardCount = 7;
  static const _staggerDelay = Duration(milliseconds: 80);
  static const _animDuration = Duration(milliseconds: 500);

  void _recordOnce(TrendProvider trend, dynamic result) {
    if (_recorded) return;
    _recorded = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      trend.recordAnalysis(
        ticker: result.ticker,
        sentiment: result.sentiment,
        recommendation: result.recommendation,
      );
    });
  }

  @override
  void initState() {
    super.initState();
    _controllers = List.generate(
      _cardCount,
      (i) => AnimationController(duration: _animDuration, vsync: this),
    );
    _fadeAnims = _controllers
        .map((c) => Tween<double>(begin: 0, end: 1).animate(CurvedAnimation(
              parent: c,
              curve: Curves.easeOut,
            )))
        .toList();
    _slideAnims = _controllers
        .map((c) =>
            Tween<Offset>(begin: const Offset(0, 0.15), end: Offset.zero)
                .animate(CurvedAnimation(
              parent: c,
              curve: Curves.easeOutCubic,
            )))
        .toList();

    _startAnimations();
  }

  Future<void> _startAnimations() async {
    for (int i = 0; i < _cardCount; i++) {
      if (!mounted) return;
      await Future.delayed(_staggerDelay);
      if (mounted) _controllers[i].forward();
    }
  }

  @override
  void dispose() {
    for (final c in _controllers) {
      c.dispose();
    }
    super.dispose();
  }

  Widget _animated(int index, Widget child) {
    if (index >= _cardCount) return child;
    return FadeTransition(
      opacity: _fadeAnims[index],
      child: SlideTransition(
        position: _slideAnims[index],
        child: child,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final result = widget.result;
    int idx = 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 16),
        _animated(idx++, PriceCard(result: result)),
        const SizedBox(height: 16),
        if (result.aiSummary != null && result.aiSummary!.isNotEmpty) ...[
          _animated(idx++, AiSummaryCard(summary: result.aiSummary!)),
          const SizedBox(height: 16),
        ],
        _animated(idx++, SentimentCard(result: result)),
        const SizedBox(height: 16),
        // Sentiment trend chart
        Consumer<TrendProvider>(
          builder: (context, trend, _) {
            // Auto-record this analysis
            _recordOnce(trend, result);
            if (!trend.hasTrend(result.ticker)) return const SizedBox.shrink();
            return _animated(
              idx++,
              SentimentTrendChart(
                data: trend.getTrend(result.ticker),
                ticker: result.ticker,
              ),
            );
          },
        ),
        if (result.peers != null && result.peers!.isNotEmpty) ...[
          _animated(idx++, PeerComparisonCard(peers: result.peers!)),
          const SizedBox(height: 16),
        ],
        _animated(idx++, DriversCard(result: result)),
        const SizedBox(height: 16),
        _animated(idx++, NewsCard(result: result)),
      ],
    );
  }
}
