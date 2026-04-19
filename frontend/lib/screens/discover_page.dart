import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../main.dart';
import '../models/opportunity.dart';
import '../providers/analysis_provider.dart';
import '../providers/discover_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_card.dart';

class DiscoverPage extends StatefulWidget {
  final VoidCallback onToggleTheme;

  const DiscoverPage({super.key, required this.onToggleTheme});

  @override
  State<DiscoverPage> createState() => _DiscoverPageState();
}

class _DiscoverPageState extends State<DiscoverPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<DiscoverProvider>().refresh();
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<DiscoverProvider>();
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: const Text('Discover'),
        actions: [
          if (provider.status != null)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Chip(
                label: Text(
                  provider.isMarketHours ? 'Market Open' : 'Market Closed',
                  style: TextStyle(
                    color: provider.isMarketHours
                        ? Colors.green.shade700
                        : Colors.grey.shade600,
                    fontSize: 12,
                  ),
                ),
                backgroundColor: provider.isMarketHours
                    ? const Color(0xFF34D399).withValues(alpha: 0.15)
                    : Colors.grey.withValues(alpha: 0.15),
                side: BorderSide.none,
                padding: EdgeInsets.zero,
              ),
            ),
          ThemeToggleButton(onToggle: widget.onToggleTheme),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => provider.refresh(),
        child: CustomScrollView(
          slivers: [
            // Scanner Status Card
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: _ScannerStatusCard(
                  status: provider.status,
                  isScanning: provider.isScanning,
                  onScan: () => provider.triggerScan(),
                ),
              ),
            ),

            // Error Message
            if (provider.error != null)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Card(
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
                              style:
                                  TextStyle(color: theme.colorScheme.error),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

            // Loading State
            if (provider.isLoading)
              const SliverFillRemaining(
                child: Center(child: CircularProgressIndicator()),
              )
            // Empty State
            else if (provider.opportunities.isEmpty)
              SliverFillRemaining(
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.search_off,
                          size: 64, color: theme.colorScheme.outline),
                      const SizedBox(height: 16),
                      Text(
                        'No opportunities found',
                        style: theme.textTheme.titleMedium?.copyWith(
                          color: theme.colorScheme.outline,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Tap "Scan Now" to find opportunities\nor wait for the next scheduled scan',
                        textAlign: TextAlign.center,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.outline,
                        ),
                      ),
                    ],
                  ),
                ),
              )
            // Opportunities List
            else
              SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                sliver: SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      final opportunity = provider.opportunities[index];
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _OpportunityCard(
                          opportunity: opportunity,
                          rank: index + 1,
                        ),
                      );
                    },
                    childCount: provider.opportunities.length,
                  ),
                ),
              ),

            const SliverToBoxAdapter(child: SizedBox(height: 24)),
          ],
        ),
      ),
    );
  }
}

// ─── Scanner Status Card ─────────────────────────────────────────────────────

class _ScannerStatusCard extends StatelessWidget {
  final ScannerStatus? status;
  final bool isScanning;
  final VoidCallback onScan;

  const _ScannerStatusCard({
    required this.status,
    required this.isScanning,
    required this.onScan,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return GlassCard(
      child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(Icons.radar, color: theme.colorScheme.primary),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Opportunity Scanner',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (status != null)
                        Text(
                          status!.modeLabel,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.outline,
                          ),
                        ),
                    ],
                  ),
                ),
                FilledButton.icon(
                  onPressed: isScanning ? null : onScan,
                  icon: isScanning
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.refresh, size: 18),
                  label: Text(isScanning ? 'Scanning...' : 'Scan Now'),
                ),
              ],
            ),
            if (status != null) ...[
              const SizedBox(height: 12),
              Divider(height: 1, color: Theme.of(context).brightness == Brightness.dark ? Colors.white.withValues(alpha: 0.08) : Colors.black.withValues(alpha: 0.06)),
              const SizedBox(height: 12),
              Wrap(
                spacing: 16,
                runSpacing: 8,
                children: [
                  _StatusChip(
                    icon: Icons.trending_up,
                    label: 'Threshold',
                    value:
                        '>${status!.sentimentThreshold.toStringAsFixed(2)}',
                  ),
                  _StatusChip(
                    icon: Icons.history,
                    label: 'Lookback',
                    value: '${status!.lookbackHours}h',
                  ),
                  _StatusChip(
                    icon: Icons.star,
                    label: 'Top Picks',
                    value: '${status!.topOpportunities}',
                  ),
                ],
              ),
            ],
          ],
        ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _StatusChip({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: theme.colorScheme.outline),
        const SizedBox(width: 4),
        Text(
          '$label: ',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.outline,
          ),
        ),
        Text(
          value,
          style: theme.textTheme.bodySmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}

// ─── Opportunity Card ────────────────────────────────────────────────────────

class _OpportunityCard extends StatelessWidget {
  final Opportunity opportunity;
  final int rank;

  const _OpportunityCard({
    required this.opportunity,
    required this.rank,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return GlassCard(
      onTap: () => _navigateToAnalyze(context, opportunity.ticker),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Row
          Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: _getRankColor(rank),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Center(
                  child: Text(
                    '#$rank',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          opportunity.ticker,
                          style: theme.textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        if (opportunity.currentPrice != null) ...[
                          const SizedBox(width: 8),
                          Text(
                            '₹${opportunity.currentPrice!.toStringAsFixed(2)}',
                            style: theme.textTheme.titleMedium?.copyWith(
                              color: theme.colorScheme.secondary,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ],
                    ),
                    Row(
                      children: [
                        Icon(Icons.trending_up,
                            size: 14,
                            color: SentimentColors.forValue(
                                opportunity.sentiment)),
                        const SizedBox(width: 4),
                        Text(
                          opportunity.sentimentFormatted,
                          style: TextStyle(
                            color: SentimentColors.forValue(
                                opportunity.sentiment),
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        if (opportunity.priceChangePercent != null) ...[
                          const SizedBox(width: 8),
                          Text(
                            '(${opportunity.priceChangePercent! >= 0 ? '+' : ''}${opportunity.priceChangePercent!.toStringAsFixed(2)}%)',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: (opportunity.priceChangePercent ?? 0) >= 0
                                  ? SentimentColors.forValue(1)
                                  : SentimentColors.forValue(-1),
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                        const SizedBox(width: 12),
                        Icon(Icons.article_outlined,
                            size: 14, color: theme.colorScheme.outline),
                        const SizedBox(width: 4),
                        Text(
                          '${opportunity.newsCount} articles',
                          style: theme.textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: SentimentColors.forValue(1).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: SentimentColors.forValue(1).withValues(alpha: 0.30)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.thumb_up,
                        color: SentimentColors.forValue(1), size: 14),
                    const SizedBox(width: 4),
                    Text(
                      'BUY',
                      style: TextStyle(
                        color: SentimentColors.forValue(1),
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),
          Divider(height: 1, color: Theme.of(context).brightness == Brightness.dark ? Colors.white.withValues(alpha: 0.08) : Colors.black.withValues(alpha: 0.06)),
          const SizedBox(height: 12),

          // AI Reasoning
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.auto_awesome,
                  size: 16, color: theme.colorScheme.primary),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  opportunity.reasoning,
                  style: theme.textTheme.bodyMedium,
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          if (opportunity.headlines.isNotEmpty) ...[
            Text(
              'Latest Headlines:',
              style: theme.textTheme.labelSmall?.copyWith(
                color: theme.colorScheme.outline,
              ),
            ),
            const SizedBox(height: 4),
            ...opportunity.headlines.take(2).map(
                  (headline) => Padding(
                    padding: const EdgeInsets.only(bottom: 2),
                    child: Text(
                      '• $headline',
                      style: theme.textTheme.bodySmall,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ),
          ],

          const SizedBox(height: 12),

          Row(
            children: [
              _InfoChip(
                icon: Icons.schedule,
                label: opportunity.timeAgo,
              ),
              const SizedBox(width: 8),
              _InfoChip(
                icon: Icons.verified,
                label: 'Confidence: ${opportunity.confidencePercent}',
              ),
              const Spacer(),
              TextButton.icon(
                onPressed: () =>
                    _navigateToAnalyze(context, opportunity.ticker),
                icon: const Icon(Icons.analytics, size: 16),
                label: const Text('Deep Analyze'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Color _getRankColor(int rank) {
    switch (rank) {
      case 1:
        return Colors.amber.shade700;
      case 2:
        return Colors.grey.shade500;
      case 3:
        return Colors.brown.shade400;
      default:
        return Colors.indigo.shade400;
    }
  }

  void _navigateToAnalyze(BuildContext context, String ticker) {
    final navState =
        context.findAncestorStateOfType<MainNavigationPageState>();
    navState?.switchToAnalyzeTab();
    context.read<AnalysisProvider>().analyzeTicker(ticker);
  }
}

class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String label;

  const _InfoChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: theme.colorScheme.outline),
          const SizedBox(width: 4),
          Text(label, style: theme.textTheme.labelSmall),
        ],
      ),
    );
  }
}
