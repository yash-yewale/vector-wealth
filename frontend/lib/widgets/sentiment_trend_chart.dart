import 'dart:math';
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'glass_card.dart';

/// Custom sparkline chart widget showing sentiment trend over time.
class SentimentTrendChart extends StatelessWidget {
  final List<Map<String, dynamic>> data;
  final String ticker;

  const SentimentTrendChart({
    super.key,
    required this.data,
    required this.ticker,
  });

  @override
  Widget build(BuildContext context) {
    if (data.length < 2) return const SizedBox.shrink();

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.trending_up, size: 20,
                  color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 8),
              Text(
                'Sentiment History',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const Spacer(),
              Text(
                '${data.length} analyses',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.outline,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 80,
            child: CustomPaint(
              size: Size.infinite,
              painter: _SparklinePainter(
                data: data,
                isDark: Theme.of(context).brightness == Brightness.dark,
              ),
            ),
          ),
          const SizedBox(height: 8),
          // Date labels
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                _formatDate(data.first['date'] ?? ''),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.outline,
                      fontSize: 10,
                    ),
              ),
              Text(
                _formatDate(data.last['date'] ?? ''),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.outline,
                      fontSize: 10,
                    ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _formatDate(String iso) {
    if (iso.length < 10) return iso;
    final parts = iso.split('-');
    if (parts.length >= 3) return '${parts[2]}/${parts[1]}';
    return iso;
  }
}

class _SparklinePainter extends CustomPainter {
  final List<Map<String, dynamic>> data;
  final bool isDark;

  _SparklinePainter({required this.data, required this.isDark});

  @override
  void paint(Canvas canvas, Size size) {
    if (data.length < 2) return;

    final values = data
        .map((d) => (d['sentiment'] as num?)?.toDouble() ?? 0.0)
        .toList();

    final minVal = values.reduce(min) - 0.1;
    final maxVal = values.reduce(max) + 0.1;
    final range = maxVal - minVal;

    final points = <Offset>[];
    for (var i = 0; i < values.length; i++) {
      final x = (i / (values.length - 1)) * size.width;
      final y = size.height - ((values[i] - minVal) / range) * size.height;
      points.add(Offset(x, y));
    }

    // Draw gradient fill
    final fillPath = Path()..moveTo(points.first.dx, size.height);
    for (final p in points) {
      fillPath.lineTo(p.dx, p.dy);
    }
    fillPath.lineTo(points.last.dx, size.height);
    fillPath.close();

    final lastVal = values.last;
    final lineColor = SentimentColors.forValue(lastVal);

    final fillPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [lineColor.withAlpha(60), lineColor.withAlpha(3)],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));
    canvas.drawPath(fillPath, fillPaint);

    // Draw zero line
    if (minVal < 0 && maxVal > 0) {
      final zeroY = size.height - ((0 - minVal) / range) * size.height;
      final zeroPaint = Paint()
        ..color = (isDark ? Colors.white.withAlpha(15) : Colors.black.withAlpha(10))
        ..strokeWidth = 1;
      canvas.drawLine(
          Offset(0, zeroY), Offset(size.width, zeroY), zeroPaint);
    }

    // Draw line
    final linePaint = Paint()
      ..color = lineColor
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final linePath = Path()..moveTo(points.first.dx, points.first.dy);
    for (var i = 1; i < points.length; i++) {
      linePath.lineTo(points[i].dx, points[i].dy);
    }
    canvas.drawPath(linePath, linePaint);

    // Draw dots
    final dotPaint = Paint()..color = lineColor;
    for (var i = 0; i < points.length; i++) {
      final dotColor = SentimentColors.forValue(values[i]);
      dotPaint.color = dotColor;
      canvas.drawCircle(points[i], i == points.length - 1 ? 4.0 : 2.5,
          dotPaint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
