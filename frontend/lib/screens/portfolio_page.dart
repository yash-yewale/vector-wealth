import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../main.dart';
import '../providers/portfolio_provider.dart';

class PortfolioPage extends StatelessWidget {
  final VoidCallback onToggleTheme;

  const PortfolioPage({super.key, required this.onToggleTheme});

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(
            title: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(colors: [
                      Theme.of(context).colorScheme.primary,
                      Theme.of(context).colorScheme.tertiary,
                    ]),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.account_balance_wallet,
                      color: Colors.white, size: 18),
                ),
                const SizedBox(width: 10),
                const Text('Portfolio'),
              ],
            ),
            actions: [
              Consumer<PortfolioProvider>(
                builder: (context, prov, _) => prov.isAnalyzing
                    ? const Padding(
                        padding: EdgeInsets.all(12),
                        child: SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2)),
                      )
                    : const SizedBox.shrink(),
              ),
              ThemeToggleButton(onToggle: onToggleTheme),
            ],
          ),
          floatingActionButton: SafeArea(
            child: FloatingActionButton.extended(
              onPressed: () => _showAddGoalDialog(context),
              icon: const Icon(Icons.add),
              label: const Text('New Goal'),
            ),
          ),
          floatingActionButtonLocation: FloatingActionButtonLocation.endDocked,
          body: Consumer<PortfolioProvider>(
            builder: (context, prov, _) {
              if (prov.isLoading) {
                return const Center(child: CircularProgressIndicator());
              }
              if (prov.isEmpty) {
                return _EmptyState(onAdd: () => _showAddGoalDialog(context));
              }
              return _GoalsList(goals: prov.goals);
            },
          ),
        ),
        Consumer<PortfolioProvider>(
          builder: (context, prov, _) => prov.isAnalyzing
              ? Container(
                  color: Colors.black.withValues(alpha: 0.3),
                  child: const Center(
                    child: CircularProgressIndicator(),
                  ),
                )
              : const SizedBox.shrink(),
        ),
      ],
    );
  }

  void _showAddGoalDialog(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const _AddGoalSheet(),
    );
  }
}

// ─── Empty State ────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  final VoidCallback onAdd;
  const _EmptyState({required this.onAdd});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [
                  theme.colorScheme.primary.withAlpha(30),
                  theme.colorScheme.tertiary.withAlpha(30),
                ]),
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.flag_outlined,
                  size: 48, color: theme.colorScheme.primary),
            ),
            const SizedBox(height: 20),
            Text('Set Your Financial Goals',
                style: theme.textTheme.headlineSmall
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(
              'Create goals like retirement, car, or education.\nAssign stocks and get goal-specific AI suggestions.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium
                  ?.copyWith(color: theme.colorScheme.outline),
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: onAdd,
              icon: const Icon(Icons.add),
              label: const Text('Create First Goal'),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Goals List ─────────────────────────────────────────────────────────────

class _GoalsList extends StatelessWidget {
  final List<Goal> goals;
  const _GoalsList({required this.goals});

  @override
  Widget build(BuildContext context) {
    final prov = context.read<PortfolioProvider>();
    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 100),
      itemCount: goals.length,
      itemBuilder: (context, index) =>
          _GoalCard(goal: goals[index], onAnalyze: prov.analyzePortfolio),
    );
  }
}

// ─── Goal Card ──────────────────────────────────────────────────────────────

class _GoalCard extends StatefulWidget {
  final Goal goal;
  final VoidCallback onAnalyze;
  const _GoalCard({required this.goal, required this.onAnalyze});

  @override
  State<_GoalCard> createState() => _GoalCardState();
}

class _GoalCardState extends State<_GoalCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final g = widget.goal;
    final progress = g.progress ?? 0;
    final progressColor = progress > 60
        ? Colors.green
        : progress > 30
            ? Colors.orange
            : theme.colorScheme.primary;

    final riskIcon = {
          'conservative': '🛡️',
          'moderate': '⚖️',
          'aggressive': '🚀',
        }[g.riskTolerance] ??
        '⚖️';

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: isDark ? 0 : 1,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: isDark ? Colors.white.withAlpha(15) : Colors.black12,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => setState(() => _expanded = !_expanded),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(g.name,
                                style: theme.textTheme.titleMedium
                                    ?.copyWith(fontWeight: FontWeight.bold)),
                            const SizedBox(width: 6),
                            Text(riskIcon,
                                style: const TextStyle(fontSize: 16)),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Target: ₹${_formatAmount(g.targetAmount)} · '
                          '${g.targetDate.length >= 4 ? g.targetDate.substring(0, 4) : g.targetDate} · '
                          '${g.riskTolerance[0].toUpperCase()}${g.riskTolerance.substring(1)}',
                          style: theme.textTheme.bodySmall
                              ?.copyWith(color: theme.colorScheme.outline),
                        ),
                      ],
                    ),
                  ),
                  PopupMenuButton<String>(
                    onSelected: (val) => _handleMenu(val, context),
                    itemBuilder: (_) => [
                      const PopupMenuItem(
                          value: 'add', child: Text('Add Holding')),
                      const PopupMenuItem(
                          value: 'suggest', child: Text('Get Suggestions')),
                      const PopupMenuItem(
                          value: 'delete',
                          child: Text('Delete Goal',
                              style: TextStyle(color: Colors.red))),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Progress bar
              Row(
                children: [
                  Expanded(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(
                        value: (progress / 100).clamp(0.0, 1.0),
                        minHeight: 8,
                        backgroundColor: progressColor.withAlpha(30),
                        valueColor:
                            AlwaysStoppedAnimation<Color>(progressColor),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text('${progress.toStringAsFixed(1)}%',
                      style: theme.textTheme.bodySmall
                          ?.copyWith(fontWeight: FontWeight.w600)),
                ],
              ),
              const SizedBox(height: 8),

              // P&L summary
              if (g.totalCurrentValue != null)
                Row(
                  children: [
                    _PnlChip(
                        label: 'Invested',
                        value: '₹${_formatAmount(g.totalInvested ?? 0)}'),
                    const SizedBox(width: 8),
                    _PnlChip(
                        label: 'Current',
                        value: '₹${_formatAmount(g.totalCurrentValue ?? 0)}'),
                    const SizedBox(width: 8),
                    _PnlChip(
                      label: 'P&L',
                      value:
                          '${(g.totalPnl ?? 0) >= 0 ? "+" : ""}₹${_formatAmount(g.totalPnl ?? 0)}',
                      color: (g.totalPnl ?? 0) >= 0
                          ? Colors.green
                          : Colors.redAccent,
                    ),
                  ],
                ),

              // Holdings count
              const SizedBox(height: 8),
              Row(
                children: [
                  Icon(Icons.inventory_2_outlined,
                      size: 14, color: theme.colorScheme.outline),
                  const SizedBox(width: 4),
                  Text('${g.holdings.length} holdings',
                      style: theme.textTheme.bodySmall
                          ?.copyWith(color: theme.colorScheme.outline)),
                  const Spacer(),
                  Icon(_expanded ? Icons.expand_less : Icons.expand_more,
                      size: 18, color: theme.colorScheme.outline),
                ],
              ),

              // Expanded: Holdings list + Suggestion
              if (_expanded) ...[
                const Divider(height: 20),
                ...g.holdings.asMap().entries.map(
                      (entry) => _HoldingRow(
                        holding: entry.value,
                        onDelete: () {
                          context
                              .read<PortfolioProvider>()
                              .removeHolding(g.id, entry.key);
                        },
                      ),
                    ),
                if (g.holdings.isEmpty)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    child: Center(
                      child: Text('No holdings yet. Tap ⋮ → Add Holding.',
                          style: theme.textTheme.bodySmall
                              ?.copyWith(color: theme.colorScheme.outline)),
                    ),
                  ),
                if (g.suggestion != null && g.suggestion!.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primary.withAlpha(12),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                          color: theme.colorScheme.primary.withAlpha(30)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.auto_awesome,
                                size: 14, color: theme.colorScheme.primary),
                            const SizedBox(width: 6),
                            Text('AI Suggestion',
                                style: theme.textTheme.labelSmall?.copyWith(
                                    fontWeight: FontWeight.w600,
                                    color: theme.colorScheme.primary)),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(g.suggestion!,
                            style: theme.textTheme.bodySmall
                                ?.copyWith(height: 1.45)),
                      ],
                    ),
                  ),
                ],
                // Recommended stocks with Add buttons
                if (g.recommendedStocks.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Icon(Icons.trending_up,
                          size: 14, color: theme.colorScheme.tertiary),
                      const SizedBox(width: 6),
                      Text('Recommended Stocks',
                          style: theme.textTheme.labelSmall?.copyWith(
                              fontWeight: FontWeight.w600,
                              color: theme.colorScheme.tertiary)),
                    ],
                  ),
                  const SizedBox(height: 6),
                  ...g.recommendedStocks.map((stock) => _RecommendedStockCard(
                        stock: stock,
                        goalId: g.id,
                      )),
                ],
              ],
            ],
          ),
        ),
      ),
    );
  }

  void _handleMenu(String action, BuildContext context) {
    switch (action) {
      case 'add':
        showModalBottomSheet(
          context: context,
          isScrollControlled: true,
          backgroundColor: Colors.transparent,
          builder: (_) => _AddHoldingSheet(goalId: widget.goal.id),
        );
      case 'suggest':
        context.read<PortfolioProvider>().fetchSuggestion(widget.goal.id);
      case 'delete':
        _confirmDelete(context);
    }
  }

  void _confirmDelete(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Goal?'),
        content: Text(
            'This will remove "${widget.goal.name}" and all its holdings.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          FilledButton(
            onPressed: () {
              context.read<PortfolioProvider>().deleteGoal(widget.goal.id);
              Navigator.pop(ctx);
            },
            style: FilledButton.styleFrom(backgroundColor: Colors.redAccent),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }
}

// ─── Recommended Stock Card ─────────────────────────────────────────────────

class _RecommendedStockCard extends StatelessWidget {
  final RecommendedStock stock;
  final String goalId;
  const _RecommendedStockCard({required this.stock, required this.goalId});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: isDark ? Colors.green.withAlpha(15) : Colors.green.withAlpha(10),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.green.withAlpha(40)),
      ),
      child: Row(
        children: [
          // Ticker badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.green.withAlpha(25),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              stock.ticker,
              style: theme.textTheme.labelSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: Colors.green.shade700,
              ),
            ),
          ),
          const SizedBox(width: 10),
          // Details
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${stock.quantity} qty × ₹${stock.buyPrice.toStringAsFixed(0)}',
                  style: theme.textTheme.bodySmall
                      ?.copyWith(fontWeight: FontWeight.w600),
                ),
                if (stock.reasoning.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    stock.reasoning,
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontSize: 11,
                      color: theme.colorScheme.outline,
                      height: 1.3,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          // Add button
          SizedBox(
            height: 32,
            child: FilledButton.tonalIcon(
              onPressed: () {
                final holding = Holding(
                  ticker: stock.ticker,
                  quantity: stock.quantity.toDouble(),
                  buyPrice: stock.buyPrice,
                  buyDate: DateTime.now().toIso8601String().split('T').first,
                );
                context.read<PortfolioProvider>().addHolding(goalId, holding);
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('${stock.ticker} added to holdings'),
                    duration: const Duration(seconds: 2),
                  ),
                );
              },
              icon: const Icon(Icons.add, size: 16),
              label: const Text('Add', style: TextStyle(fontSize: 12)),
              style: FilledButton.styleFrom(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 0),
                backgroundColor: Colors.green.withAlpha(30),
                foregroundColor: Colors.green.shade700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Holding Row ────────────────────────────────────────────────────────────

class _HoldingRow extends StatelessWidget {
  final Holding holding;
  final VoidCallback onDelete;
  const _HoldingRow({required this.holding, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final pnl = holding.pnl ?? 0;
    final pnlPct = holding.pnlPercent ?? 0;
    final isPositive = pnl >= 0;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          // Ticker badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: theme.colorScheme.primary.withAlpha(18),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(holding.ticker,
                style: theme.textTheme.labelSmall
                    ?.copyWith(fontWeight: FontWeight.bold)),
          ),
          const SizedBox(width: 8),
          // Qty × Price
          Expanded(
            child: Text(
              '${holding.quantity.toStringAsFixed(0)} × ₹${holding.buyPrice.toStringAsFixed(0)}',
              style: theme.textTheme.bodySmall,
            ),
          ),
          // P&L
          if (holding.currentPrice != null)
            Text(
              '${isPositive ? "+" : ""}₹${pnl.toStringAsFixed(0)} '
              '(${isPositive ? "+" : ""}${pnlPct.toStringAsFixed(1)}%)',
              style: theme.textTheme.bodySmall?.copyWith(
                color: isPositive ? Colors.green : Colors.redAccent,
                fontWeight: FontWeight.w600,
              ),
            ),
          const SizedBox(width: 4),
          InkWell(
            onTap: onDelete,
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.all(4),
              child:
                  Icon(Icons.close, size: 14, color: theme.colorScheme.outline),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── P&L Chip ───────────────────────────────────────────────────────────────

class _PnlChip extends StatelessWidget {
  final String label;
  final String value;
  final Color? color;
  const _PnlChip({required this.label, required this.value, this.color});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: theme.textTheme.labelSmall
                  ?.copyWith(color: theme.colorScheme.outline, fontSize: 10)),
          Text(value,
              style: theme.textTheme.bodySmall?.copyWith(
                  fontWeight: FontWeight.w600, color: color, fontSize: 12)),
        ],
      ),
    );
  }
}

// ─── Add Goal Sheet ─────────────────────────────────────────────────────────

class _AddGoalSheet extends StatefulWidget {
  const _AddGoalSheet();

  @override
  State<_AddGoalSheet> createState() => _AddGoalSheetState();
}

class _AddGoalSheetState extends State<_AddGoalSheet> {
  final _nameCtrl = TextEditingController();
  final _amountCtrl = TextEditingController();
  final _yearCtrl = TextEditingController();
  String _risk = 'moderate';

  @override
  void dispose() {
    _nameCtrl.dispose();
    _amountCtrl.dispose();
    _yearCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bottom = MediaQuery.of(context).viewInsets.bottom;

    return Container(
      padding: EdgeInsets.fromLTRB(20, 16, 20, 16 + bottom),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                  color: theme.colorScheme.outline.withAlpha(60),
                  borderRadius: BorderRadius.circular(2)),
            ),
          ),
          const SizedBox(height: 16),
          Text('New Financial Goal',
              style: theme.textTheme.titleMedium
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          TextField(
            controller: _nameCtrl,
            decoration: const InputDecoration(
              labelText: 'Goal name',
              hintText: 'e.g. Retirement Fund, New Car',
              prefixIcon: Icon(Icons.flag_outlined),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _amountCtrl,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            decoration: const InputDecoration(
              labelText: 'Target amount (₹)',
              hintText: 'e.g. 10000000',
              prefixIcon: Icon(Icons.currency_rupee),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _yearCtrl,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            decoration: const InputDecoration(
              labelText: 'Target year',
              hintText: 'e.g. 2045',
              prefixIcon: Icon(Icons.calendar_today),
            ),
          ),
          const SizedBox(height: 14),
          Text('Risk Tolerance',
              style: theme.textTheme.bodySmall
                  ?.copyWith(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Row(
            children: [
              _riskChip('conservative', '🛡️ Conservative'),
              const SizedBox(width: 8),
              _riskChip('moderate', '⚖️ Moderate'),
              const SizedBox(width: 8),
              _riskChip('aggressive', '🚀 Aggressive'),
            ],
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _submit,
              child: const Text('Create Goal'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _riskChip(String value, String label) {
    final selected = _risk == value;
    return Expanded(
      child: ChoiceChip(
        label: Text(label, style: const TextStyle(fontSize: 11)),
        selected: selected,
        onSelected: (_) => setState(() => _risk = value),
        showCheckmark: false,
        padding: EdgeInsets.zero,
        labelPadding: const EdgeInsets.symmetric(horizontal: 2),
      ),
    );
  }

  void _submit() {
    final name = _nameCtrl.text.trim();
    final amount = double.tryParse(_amountCtrl.text.trim()) ?? 0;
    final year = _yearCtrl.text.trim();

    if (name.isEmpty || amount <= 0 || year.length != 4) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in all fields correctly')),
      );
      return;
    }

    final goal = Goal(
      id: 'goal_${DateTime.now().millisecondsSinceEpoch}',
      name: name,
      targetAmount: amount,
      targetDate: '$year-01-01',
      riskTolerance: _risk,
    );

    context.read<PortfolioProvider>().addGoal(goal);
    Navigator.pop(context);
  }
}

// ─── Add Holding Sheet ──────────────────────────────────────────────────────

class _AddHoldingSheet extends StatefulWidget {
  final String goalId;
  const _AddHoldingSheet({required this.goalId});

  @override
  State<_AddHoldingSheet> createState() => _AddHoldingSheetState();
}

class _AddHoldingSheetState extends State<_AddHoldingSheet> {
  final _tickerCtrl = TextEditingController();
  final _qtyCtrl = TextEditingController();
  final _priceCtrl = TextEditingController();

  @override
  void dispose() {
    _tickerCtrl.dispose();
    _qtyCtrl.dispose();
    _priceCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bottom = MediaQuery.of(context).viewInsets.bottom;

    return Container(
      padding: EdgeInsets.fromLTRB(20, 16, 20, 16 + bottom),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                  color: theme.colorScheme.outline.withAlpha(60),
                  borderRadius: BorderRadius.circular(2)),
            ),
          ),
          const SizedBox(height: 16),
          Text('Add Holding',
              style: theme.textTheme.titleMedium
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          TextField(
            controller: _tickerCtrl,
            textCapitalization: TextCapitalization.characters,
            decoration: const InputDecoration(
              labelText: 'Stock ticker',
              hintText: 'e.g. TCS, RELIANCE, INFY',
              prefixIcon: Icon(Icons.show_chart),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _qtyCtrl,
                  keyboardType: TextInputType.number,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  decoration: const InputDecoration(
                    labelText: 'Quantity',
                    hintText: 'e.g. 50',
                    prefixIcon: Icon(Icons.numbers),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextField(
                  controller: _priceCtrl,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(
                    labelText: 'Buy price (₹)',
                    hintText: 'e.g. 3200',
                    prefixIcon: Icon(Icons.currency_rupee),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _submit,
              child: const Text('Add Holding'),
            ),
          ),
        ],
      ),
    );
  }

  void _submit() {
    final ticker = _tickerCtrl.text.trim().toUpperCase();
    final qty = double.tryParse(_qtyCtrl.text.trim()) ?? 0;
    final price = double.tryParse(_priceCtrl.text.trim()) ?? 0;

    if (ticker.isEmpty || qty <= 0 || price <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in all fields correctly')),
      );
      return;
    }

    final holding = Holding(
      ticker: ticker,
      quantity: qty,
      buyPrice: price,
      buyDate: DateTime.now().toIso8601String().split('T').first,
    );

    context.read<PortfolioProvider>().addHolding(widget.goalId, holding);
    Navigator.pop(context);
  }
}

// ─── Helpers ────────────────────────────────────────────────────────────────

String _formatAmount(double amount) {
  if (amount >= 10000000) return '${(amount / 10000000).toStringAsFixed(2)} Cr';
  if (amount >= 100000) return '${(amount / 100000).toStringAsFixed(2)} L';
  if (amount >= 1000) return '${(amount / 1000).toStringAsFixed(1)}K';
  return amount.toStringAsFixed(0);
}
