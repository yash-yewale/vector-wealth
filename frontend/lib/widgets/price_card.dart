import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/analysis_result.dart';
import '../providers/watchlist_provider.dart';
import '../theme/app_theme.dart';
import 'glass_card.dart';

class PriceCard extends StatelessWidget {
  final AnalysisResult result;

  const PriceCard({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasPrice = result.currentPrice != null;
    final isPositive = (result.priceChange ?? 0) >= 0;

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      result.ticker,
                      style: theme.textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    if (hasPrice) ...[
                      const SizedBox(height: 4),
                      Text(
                        '₹${result.currentPrice!.toStringAsFixed(2)}',
                        style: theme.textTheme.headlineMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          Icon(
                            isPositive
                                ? Icons.arrow_upward
                                : Icons.arrow_downward,
                            size: 16,
                            color: isPositive
                                ? SentimentColors.forValue(1)
                                : SentimentColors.forValue(-1),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '${isPositive ? '+' : ''}${result.priceChange?.toStringAsFixed(2) ?? '0'} '
                            '(${isPositive ? '+' : ''}${result.priceChangePercent?.toStringAsFixed(2) ?? '0'}%)',
                            style: TextStyle(
                              color: isPositive
                                  ? SentimentColors.forValue(1)
                                  : SentimentColors.forValue(-1),
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ] else ...[
                      const SizedBox(height: 4),
                      Text(
                        'Price unavailable',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.outline,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              Column(
                children: [
                  Consumer<WatchlistProvider>(
                    builder: (context, watchlist, _) {
                      final isWatched = watchlist.isWatched(result.ticker);
                      return IconButton(
                        icon: Icon(
                          isWatched ? Icons.star : Icons.star_border,
                          color: isWatched ? const Color(0xFFFBBF24) : theme.colorScheme.outline,
                        ),
                        tooltip: isWatched ? 'Remove from Watchlist' : 'Add to Watchlist',
                        onPressed: () => watchlist.toggle(result.ticker),
                      );
                    },
                  ),
                  DecisionBadge(decision: result.recommendation),
                ],
              ),
            ],
          ),
          if (result.staleData) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFBBF24).withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFFBBF24).withValues(alpha: 0.25)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline,
                      size: 18, color: Color(0xFFFBBF24)),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      result.staleReason.isNotEmpty
                          ? result.staleReason
                          : 'Limited recent data available',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: const Color(0xFFFBBF24),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class DecisionBadge extends StatelessWidget {
  final String decision;

  const DecisionBadge({super.key, required this.decision});

  @override
  Widget build(BuildContext context) {
    Color color;
    IconData icon;
    switch (decision.toUpperCase()) {
      case 'BUY':
        color = SentimentColors.forValue(1);
        icon = Icons.thumb_up;
        break;
      case 'SELL':
        color = SentimentColors.forValue(-1);
        icon = Icons.thumb_down;
        break;
      default:
        color = SentimentColors.forValue(0);
        icon = Icons.pause_circle;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.30)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 8),
          Text(
            decision.toUpperCase(),
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
