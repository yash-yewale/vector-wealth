import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Centralized theme configuration for Vector Wealth.
class AppTheme {
  AppTheme._();

  // ─── Brand Palette (Dark) ─────────────────────────────────────────────────
  static const Color _bgPrimary = Color(0xFF080B16);
  static const Color _accentIndigo = Color(0xFF818CF8);
  static const Color _accentEmerald = Color(0xFF34D399);
  static const Color _textPrimary = Color(0xFFF1F5F9);
  static const Color _textSecondary = Color(0xFF94A3B8);

  // ─── Brand Palette (Light) ────────────────────────────────────────────────
  static const Color _lightBg = Color(0xFFF0F0F5);
  static const Color _lightAccent = Color(0xFF6366F1);
  static const Color _lightTextPrimary = Color(0xFF0F172A);
  static const Color _lightTextSecondary = Color(0xFF64748B);

  // ─── Inter TextTheme ──────────────────────────────────────────────────────
  static TextTheme _interTextTheme(Brightness brightness) {
    final base = brightness == Brightness.dark
        ? ThemeData.dark().textTheme
        : ThemeData.light().textTheme;
    return GoogleFonts.interTextTheme(base);
  }

  // ─── Light Theme ──────────────────────────────────────────────────────────
  static ThemeData get light {
    final textTheme = _interTextTheme(Brightness.light);

    final colorScheme = ColorScheme.fromSeed(
      seedColor: _lightAccent,
      brightness: Brightness.light,
      surface: _lightBg,
      onSurface: _lightTextPrimary,
      primary: _lightAccent,
      secondary: _accentEmerald,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      textTheme: textTheme,
      scaffoldBackgroundColor: Colors.transparent,
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: 0,
        backgroundColor: Colors.transparent,
        titleTextStyle: textTheme.headlineSmall?.copyWith(
          color: _lightTextPrimary,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.5,
        ),
        iconTheme: const IconThemeData(color: _lightTextPrimary),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: Colors.white.withValues(alpha: 0.60),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(
            color: const Color(0xFFC8C8D4).withValues(alpha: 0.40),
          ),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        elevation: 0,
        backgroundColor: Colors.white.withValues(alpha: 0.50),
        indicatorColor: _lightAccent.withValues(alpha: 0.15),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return textTheme.labelSmall?.copyWith(
            color: selected ? _lightAccent : _lightTextSecondary,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return IconThemeData(
            color: selected ? _lightAccent : _lightTextSecondary,
            size: 22,
          );
        }),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(
            color: const Color(0xFFC8C8D4).withValues(alpha: 0.40),
          ),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(
            color: const Color(0xFFC8C8D4).withValues(alpha: 0.30),
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: _lightAccent, width: 1.5),
        ),
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.60),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: Colors.white.withValues(alpha: 0.50),
        side: BorderSide(
          color: const Color(0xFFC8C8D4).withValues(alpha: 0.30),
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
        ),
      ),
    );
  }

  // ─── Dark Theme ───────────────────────────────────────────────────────────
  static ThemeData get dark {
    final textTheme = _interTextTheme(Brightness.dark);

    final colorScheme = ColorScheme.fromSeed(
      seedColor: _accentIndigo,
      brightness: Brightness.dark,
      surface: _bgPrimary,
      onSurface: _textPrimary,
      primary: _accentIndigo,
      secondary: _accentEmerald,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      textTheme: textTheme,
      scaffoldBackgroundColor: Colors.transparent,
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: 0,
        backgroundColor: Colors.transparent,
        titleTextStyle: textTheme.headlineSmall?.copyWith(
          color: _textPrimary,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.5,
        ),
        iconTheme: const IconThemeData(color: _textPrimary),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: Colors.white.withValues(alpha: 0.06),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: Colors.white.withValues(alpha: 0.10)),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        elevation: 0,
        backgroundColor: Colors.white.withValues(alpha: 0.06),
        indicatorColor: _accentIndigo.withValues(alpha: 0.20),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return textTheme.labelSmall?.copyWith(
            color: selected ? _accentIndigo : _textSecondary,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return IconThemeData(
            color: selected ? _accentIndigo : _textSecondary,
            size: 22,
          );
        }),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.10)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.08)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: _accentIndigo, width: 1.5),
        ),
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.06),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: Colors.white.withValues(alpha: 0.08),
        side: BorderSide(color: Colors.white.withValues(alpha: 0.10)),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
        ),
      ),
    );
  }
}

/// Utility class for sentiment-based gradient colors.
class SentimentColors {
  SentimentColors._();

  /// Returns a color interpolated across the sentiment range [-1, +1].
  /// Deep red (-1) → Orange (0) → Emerald (+1)
  static Color forValue(double sentiment) {
    final clamped = sentiment.clamp(-1.0, 1.0);
    if (clamped >= 0) {
      // 0..1 → orange to green
      return Color.lerp(
        const Color(0xFFF59E0B), // amber
        const Color(0xFF34D399), // emerald (updated)
        clamped,
      )!;
    } else {
      // -1..0 → red to orange
      return Color.lerp(
        const Color(0xFFF87171), // coral red (updated)
        const Color(0xFFF59E0B), // amber
        clamped + 1.0,
      )!;
    }
  }

  /// Background tint for sentiment values (low alpha).
  static Color backgroundForValue(double sentiment) {
    return forValue(sentiment).withAlpha(30);
  }

  /// Standard sentiment label.
  static String labelForValue(double sentiment) {
    if (sentiment > 0.2) return 'Bullish';
    if (sentiment < -0.2) return 'Bearish';
    return 'Neutral';
  }
}
