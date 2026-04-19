import 'package:flutter/material.dart';

import '../models/analysis_result.dart';
import 'glass_card.dart';

class PeerComparisonCard extends StatelessWidget {
  final List<PeerStock> peers;

  const PeerComparisonCard({super.key, required this.peers});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.compare_arrows, color: theme.colorScheme.primary),
              const SizedBox(width: 8),
              Text(
                'Peer Comparison',
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          ...peers.map((peer) => _PeerTile(peer: peer)),
        ],
      ),
    );
  }
}

class _PeerTile extends StatelessWidget {
  final PeerStock peer;

  const _PeerTile({required this.peer});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasPrice = peer.currentPrice != null;
    final isPositive = (peer.priceChange ?? 0) >= 0;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            peer.ticker,
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          if (hasPrice)
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '₹${peer.currentPrice?.toStringAsFixed(2)}',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Text(
                  '${isPositive ? '+' : ''}${peer.priceChangePercent?.toStringAsFixed(2) ?? '0'}%',
                  style: TextStyle(
                    color: isPositive
                        ? const Color(0xFF34D399)
                        : const Color(0xFFF87171),
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            )
          else
            Text(
              '--',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.outline,
              ),
            ),
        ],
      ),
    );
  }
}
