import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'providers/analysis_provider.dart';
import 'providers/chat_provider.dart';
import 'providers/discover_provider.dart';
import 'providers/portfolio_provider.dart';
import 'providers/trend_provider.dart';
import 'providers/watchlist_provider.dart';
import 'screens/chat_page.dart';
import 'screens/dashboard_page.dart';
import 'screens/discover_page.dart';
import 'screens/portfolio_page.dart';
import 'screens/settings_page.dart';
import 'services/api_client.dart';
import 'theme/app_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ApiClient.instance.initialize();
  runApp(const VectorWealthApp());
}

class VectorWealthApp extends StatefulWidget {
  const VectorWealthApp({super.key});

  @override
  State<VectorWealthApp> createState() => _VectorWealthAppState();
}

class _VectorWealthAppState extends State<VectorWealthApp> {
  ThemeMode _themeMode = ThemeMode.dark;

  void _toggleTheme() {
    setState(() {
      _themeMode =
          _themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AnalysisProvider()),
        ChangeNotifierProvider(create: (_) => DiscoverProvider()),
        ChangeNotifierProvider(create: (_) => PortfolioProvider()),
        ChangeNotifierProxyProvider<PortfolioProvider, ChatProvider>(
          create: (_) => ChatProvider(),
          update: (_, portfolio, chat) {
            chat!.updatePortfolioData(
              () => portfolio.goals.map((g) => g.toJson()).toList(),
            );
            return chat;
          },
        ),
        ChangeNotifierProvider(create: (_) => WatchlistProvider()),
        ChangeNotifierProvider(create: (_) => TrendProvider()),
      ],
      child: MaterialApp(
        title: 'Vector Wealth',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light,
        darkTheme: AppTheme.dark,
        themeMode: _themeMode,
        home: MainNavigationPage(onToggleTheme: _toggleTheme),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Reusable theme toggle widget for AppBar actions
// ─────────────────────────────────────────────────────────────────────────────

class ThemeToggleButton extends StatelessWidget {
  final VoidCallback onToggle;

  const ThemeToggleButton({super.key, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return IconButton(
      icon: Icon(isDark ? Icons.light_mode_rounded : Icons.dark_mode_rounded),
      tooltip: isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode',
      onPressed: onToggle,
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN NAVIGATION WITH BOTTOM NAV BAR
// ─────────────────────────────────────────────────────────────────────────────

class MainNavigationPage extends StatefulWidget {
  final VoidCallback onToggleTheme;

  const MainNavigationPage({super.key, required this.onToggleTheme});

  @override
  State<MainNavigationPage> createState() => MainNavigationPageState();
}

class MainNavigationPageState extends State<MainNavigationPage> {
  int _currentIndex = 0;

  void switchToAnalyzeTab() {
    setState(() {
      _currentIndex = 0;
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final pages = <Widget>[
      DashboardPage(onToggleTheme: widget.onToggleTheme),
      DiscoverPage(onToggleTheme: widget.onToggleTheme),
      PortfolioPage(onToggleTheme: widget.onToggleTheme),
      ChatPage(onToggleTheme: widget.onToggleTheme),
    ];

    return Scaffold(
      backgroundColor:
          isDark ? const Color(0xFF080B16) : const Color(0xFFF0F0F5),
      body: Stack(
        children: [
          // Gradient background layer (dark mode only)
          if (isDark) ...[
            const Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    center: Alignment(-0.6, -0.5),
                    radius: 1.2,
                    colors: [
                      Color(0x14818CF8), // indigo blob @ 8%
                      Color(0x00080B16),
                    ],
                  ),
                ),
              ),
            ),
            const Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    center: Alignment(0.7, 0.8),
                    radius: 1.0,
                    colors: [
                      Color(0x0D2DD4BF), // teal blob @ 5%
                      Color(0x00080B16),
                    ],
                  ),
                ),
              ),
            ),
          ],
          // Page content layer
          IndexedStack(
            index: _currentIndex,
            children: pages,
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          setState(() {
            _currentIndex = index;
          });
          if (index == 1) {
            context.read<DiscoverProvider>().refresh();
          } else if (index == 2) {
            final prov = context.read<PortfolioProvider>();
            if (!prov.isEmpty && !prov.isAnalyzing) {
              prov.analyzePortfolio();
            }
          }
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.analytics_outlined),
            selectedIcon: Icon(Icons.analytics),
            label: 'Analyze',
          ),
          NavigationDestination(
            icon: Icon(Icons.explore_outlined),
            selectedIcon: Icon(Icons.explore),
            label: 'Discover',
          ),
          NavigationDestination(
            icon: Icon(Icons.account_balance_wallet_outlined),
            selectedIcon: Icon(Icons.account_balance_wallet),
            label: 'Portfolio',
          ),
          NavigationDestination(
            icon: Icon(Icons.auto_awesome_outlined),
            selectedIcon: Icon(Icons.auto_awesome),
            label: 'Chat',
          ),
        ],
      ),
    );
  }
}
