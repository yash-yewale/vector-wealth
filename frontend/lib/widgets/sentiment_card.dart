import 'package:flutter/material.dart';

import '../models/analysis_result.dart';
import '../theme/app_theme.dart';
import 'glass_card.dart';

class SentimentCard extends StatelessWidget {
  final AnalysisResult result;

  const SentimentCard({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Sentiment Analysis',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          SentimentGauge(value: result.sentiment),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: MetricChip(
                  label: 'Now',
                  value: result.nowSentiment.toStringAsFixed(2),
                  color: SentimentColors.forValue(result.nowSentiment),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: MetricChip(
                  label: 'Pattern',
                  value: result.patternSentiment.toStringAsFixed(2),
                  color: SentimentColors.forValue(result.patternSentiment),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: MetricChip(
                  label: 'Confidence',
                  value:
                      '${(result.confidence * 100).toStringAsFixed(0)}%',
                  color: theme.colorScheme.primary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Recent: ${result.recentNewsCount} articles • Total: ${result.patternNewsCount} articles',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.outline,
            ),
          ),
          if (result.latestNewsDate.isNotEmpty)
            Text(
              'Latest news: ${result.latestNewsDate}',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.outline,
              ),
            ),
          if (result.explanation.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              result.explanation,
              style: theme.textTheme.bodySmall?.copyWith(
                fontStyle: FontStyle.italic,
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Animated arc-based sentiment gauge.
class SentimentGauge extends StatefulWidget {
  final double value;

  const SentimentGauge({super.key, required this.value});

  @override
  State<SentimentGauge> createState() => _SentimentGaugeState();
}

class _SentimentGaugeState extends State<SentimentGauge>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
    _animation = Tween<double>(begin: 0.0, end: widget.value).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
    );
    _controller.forward();
  }

  @override
  void didUpdateWidget(SentimentGauge oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.value != widget.value) {
      _animation = Tween<double>(
        begin: _animation.value,
        end: widget.value,
      ).animate(
        CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
      );
      _controller
        ..reset()
        ..forward();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        final animValue = _animation.value;
        final normalized = ((animValue + 1) / 2).clamp(0.0, 1.0);
        final color = SentimentColors.forValue(animValue);

        return Row(
          children: [
            SizedBox(
              width: 64,
              height: 64,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  SizedBox(
                    width: 64,
                    height: 64,
                    child: CircularProgressIndicator(
                      value: normalized,
                      strokeWidth: 6,
                      strokeCap: StrokeCap.round,
                      backgroundColor: isDark
                          ? Colors.white.withValues(alpha: 0.08)
                          : Colors.black.withValues(alpha: 0.06),
                      valueColor: AlwaysStoppedAnimation(color),
                    ),
                  ),
                  Text(
                    animValue.toStringAsFixed(2),
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                      color: color,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 16),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Overall Sentiment',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
                const SizedBox(height: 2),
                Text(
                  SentimentColors.labelForValue(animValue),
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.w600,
                    fontSize: 15,
                  ),
                ),
              ],
            ),
          ],
        );
      },
    );
  }
}

class MetricChip extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const MetricChip({
    super.key,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withAlpha(25),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withAlpha(40)),
      ),
      child: Column(
        children: [
          Text(
            value,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}
