import 'package:flutter/material.dart';

import '../models/analysis_result.dart';
import 'glass_card.dart';

class DriversCard extends StatelessWidget {
  final AnalysisResult result;

  const DriversCard({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasPositive = result.positiveDrivers.isNotEmpty;
    final hasNegative = result.negativeDrivers.isNotEmpty;

    if (!hasPositive && !hasNegative) return const SizedBox.shrink();

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Key Drivers',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          if (hasPositive) ...[
            Row(
              children: [
                const Icon(Icons.trending_up,
                    color: Color(0xFF34D399), size: 18),
                const SizedBox(width: 8),
                Text(
                  'Positive',
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: const Color(0xFF34D399),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ...result.positiveDrivers.take(3).map(
                  (driver) => Padding(
                    padding: const EdgeInsets.only(left: 26, bottom: 4),
                    child:
                        Text('• $driver', style: theme.textTheme.bodySmall),
                  ),
                ),
          ],
          if (hasPositive && hasNegative) const SizedBox(height: 12),
          if (hasNegative) ...[
            Row(
              children: [
                const Icon(Icons.trending_down,
                    color: Color(0xFFF87171), size: 18),
                const SizedBox(width: 8),
                Text(
                  'Negative',
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: const Color(0xFFF87171),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ...result.negativeDrivers.take(3).map(
                  (driver) => Padding(
                    padding: const EdgeInsets.only(left: 26, bottom: 4),
                    child:
                        Text('• $driver', style: theme.textTheme.bodySmall),
                  ),
                ),
          ],
        ],
      ),
    );
  }
}
