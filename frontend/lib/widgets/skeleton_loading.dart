import 'package:flutter/material.dart';

import 'glass_card.dart';

/// Skeleton loading placeholder that pulses to indicate loading.
class SkeletonCard extends StatelessWidget {
  final double height;

  const SkeletonCard({super.key, this.height = 120});

  @override
  Widget build(BuildContext context) {
    return _ShimmerWrapper(
      child: GlassCard(
        child: SizedBox(height: height),
      ),
    );
  }
}

/// Shows a column of skeleton cards to represent the analysis layout.
class AnalysisSkeleton extends StatelessWidget {
  const AnalysisSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: [
        SizedBox(height: 16),
        SkeletonCard(height: 140), // Price card
        SizedBox(height: 12),
        SkeletonCard(height: 100), // AI summary
        SizedBox(height: 12),
        SkeletonCard(height: 160), // Sentiment card
        SizedBox(height: 12),
        SkeletonCard(height: 120), // Drivers card
      ],
    );
  }
}

/// Shimmer animation wrapper.
class _ShimmerWrapper extends StatefulWidget {
  final Widget child;

  const _ShimmerWrapper({required this.child});

  @override
  State<_ShimmerWrapper> createState() => _ShimmerWrapperState();
}

class _ShimmerWrapperState extends State<_ShimmerWrapper>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    )..repeat();
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
      animation: _controller,
      builder: (context, child) {
        return ShaderMask(
          shaderCallback: (bounds) {
            return LinearGradient(
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
              colors: isDark
                  ? [
                      Colors.white.withAlpha(5),
                      Colors.white.withAlpha(20),
                      Colors.white.withAlpha(5),
                    ]
                  : [
                      Colors.grey.shade300.withAlpha(80),
                      Colors.grey.shade100.withAlpha(80),
                      Colors.grey.shade300.withAlpha(80),
                    ],
              stops: [
                (_controller.value - 0.3).clamp(0.0, 1.0),
                _controller.value,
                (_controller.value + 0.3).clamp(0.0, 1.0),
              ],
            ).createShader(bounds);
          },
          blendMode: BlendMode.srcATop,
          child: child,
        );
      },
      child: widget.child,
    );
  }
}
