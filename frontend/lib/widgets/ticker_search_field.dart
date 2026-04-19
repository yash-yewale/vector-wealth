import 'package:flutter/material.dart';

import 'glass_card.dart';

/// Popular Indian stock tickers for autocomplete suggestions.
const List<String> popularTickers = [
  'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
  'HINDUNILVR', 'SBIN', 'BHARTIARTL', 'BAJFINANCE', 'WIPRO',
  'ITC', 'LT', 'AXISBANK', 'KOTAKBANK', 'HCLTECH',
  'TATAMOTORS', 'MARUTI', 'SUNPHARMA', 'TITAN', 'ASIANPAINT',
  'ULTRACEMCO', 'NESTLEIND', 'TECHM', 'POWERGRID', 'NTPC',
  'TATASTEEL', 'ONGC', 'JSWSTEEL', 'ADANIENT', 'ADANIPORTS',
  'BAJAJFINSV', 'DRREDDY', 'CIPLA', 'DIVISLAB', 'MRF',
  'COALINDIA', 'GRASIM', 'BPCL', 'EICHERMOT', 'HEROMOTOCO',
  'HINDALCO', 'VEDL', 'DLF', 'GODREJCP', 'TATAPOWER',
  'ZOMATO', 'NYKAA', 'PAYTM', 'DELHIVERY', 'PIDILITIND',
];

class TickerSearchField extends StatelessWidget {
  final TextEditingController controller;
  final bool isLoading;
  final VoidCallback onAnalyze;
  final List<String> recentTickers;
  final ValueChanged<String>? onRecentTap;

  const TickerSearchField({
    super.key,
    required this.controller,
    required this.isLoading,
    required this.onAnalyze,
    this.recentTickers = const [],
    this.onRecentTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Stock Analysis',
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          Autocomplete<String>(
            optionsBuilder: (textEditingValue) {
              final query = textEditingValue.text.trim().toUpperCase();
              if (query.isEmpty) return const Iterable<String>.empty();
              return popularTickers
                  .where((t) => t.contains(query))
                  .take(6);
            },
            onSelected: (selection) {
              controller.text = selection;
              onAnalyze();
            },
            fieldViewBuilder: (context, textController, focusNode, onSubmit) {
              // Sync with external controller
              textController.text = controller.text;
              textController.addListener(() {
                if (controller.text != textController.text) {
                  controller.text = textController.text;
                }
              });
              return TextField(
                controller: textController,
                focusNode: focusNode,
                textCapitalization: TextCapitalization.characters,
                onSubmitted: (_) => onAnalyze(),
                decoration: InputDecoration(
                  labelText: 'Enter Stock Ticker',
                  hintText: 'e.g. HDFCBANK, MRF, TCS',
                  prefixIcon: const Icon(Icons.search),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                  filled: true,
                ),
              );
            },
            optionsViewBuilder: (context, onSelected, options) {
              return Align(
                alignment: Alignment.topLeft,
                child: Material(
                  elevation: 0,
                  color: isDark
                      ? const Color(0xFF0F1322).withValues(alpha: 0.95)
                      : Colors.white.withValues(alpha: 0.95),
                  borderRadius: BorderRadius.circular(14),
                  child: Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: isDark
                            ? Colors.white.withValues(alpha: 0.10)
                            : const Color(0xFFC8C8D4).withValues(alpha: 0.40),
                      ),
                    ),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(
                        maxHeight: 240,
                        maxWidth: 300,
                      ),
                      child: ListView.builder(
                        padding: EdgeInsets.zero,
                        shrinkWrap: true,
                        itemCount: options.length,
                        itemBuilder: (context, index) {
                          final option = options.elementAt(index);
                          return ListTile(
                            dense: true,
                            leading: Icon(
                              Icons.show_chart,
                              size: 18,
                              color: theme.colorScheme.primary,
                            ),
                            title: Text(
                              option,
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            onTap: () => onSelected(option),
                          );
                        },
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 12),

          // Recent tickers chips
          if (recentTickers.isNotEmpty) ...[
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: recentTickers.map((ticker) {
                return ActionChip(
                  avatar: Icon(
                    Icons.history,
                    size: 14,
                    color: theme.colorScheme.primary,
                  ),
                  label: Text(
                    ticker,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  onPressed: () => onRecentTap?.call(ticker),
                  visualDensity: VisualDensity.compact,
                );
              }).toList(),
            ),
            const SizedBox(height: 12),
          ],

          FilledButton.icon(
            onPressed: isLoading ? null : onAnalyze,
            icon: isLoading
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.analytics),
            label: Text(isLoading ? 'Analyzing...' : 'Deep Analysis'),
          ),
        ],
      ),
    );
  }
}
