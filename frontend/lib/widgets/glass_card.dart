import 'dart:ui';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

/// A premium frosted-glass card used throughout the app.
///
/// Adapts blur intensity and fill opacity based on the current
/// [Brightness] (dark vs light) and skips the expensive
/// [BackdropFilter] on web when performance is a concern.
class GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final double borderRadius;
  final VoidCallback? onTap;

  /// If true, skip the blur even on non-web platforms (for nested glass).
  final bool skipBlur;

  const GlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.borderRadius = 20,
    this.onTap,
    this.skipBlur = false,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final useBlur = !skipBlur && !kIsWeb; // skip blur on web for perf

    final fillColor = isDark
        ? Colors.white.withValues(alpha: 0.06)
        : Colors.white.withValues(alpha: 0.60);
    final borderColor = isDark
        ? Colors.white.withValues(alpha: 0.10)
        : const Color(0xFFC8C8D4).withValues(alpha: 0.40);
    final blurSigma = isDark ? 24.0 : 16.0;

    final shape = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(borderRadius),
      side: BorderSide(color: borderColor, width: 1),
    );

    Widget card = Container(
      decoration: ShapeDecoration(
        shape: shape,
        color: useBlur ? fillColor : fillColor.withValues(alpha: isDark ? 0.12 : 0.75),
      ),
      child: Padding(
        padding: padding,
        child: child,
      ),
    );

    if (useBlur) {
      card = ClipRRect(
        borderRadius: BorderRadius.circular(borderRadius),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: blurSigma, sigmaY: blurSigma),
          child: card,
        ),
      );
    }

    if (onTap != null) {
      card = InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(borderRadius),
        child: card,
      );
    }

    return card;
  }
}
