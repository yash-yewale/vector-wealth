import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;

import '../services/api_client.dart';

/// Settings page — configure backend connection for mobile devices.
class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final _ipController = TextEditingController();
  bool _testing = false;
  bool? _connected;

  @override
  void initState() {
    super.initState();
    final url = ApiClient.instance.baseUrl;
    // Extract just the IP:port from the URL for display
    final uri = Uri.tryParse(url);
    if (uri != null && uri.host.isNotEmpty) {
      if (uri.port != 80 && uri.port != 443) {
        _ipController.text = '${uri.host}:${uri.port}';
      } else {
        _ipController.text = uri.host;
      }
    }
    _testConnection();
  }

  @override
  void dispose() {
    _ipController.dispose();
    super.dispose();
  }

  Future<void> _testConnection([String? urlOverride]) async {
    setState(() {
      _testing = true;
      _connected = null;
    });
    final result = await ApiClient.instance.testConnection(urlOverride);
    if (mounted) {
      setState(() {
        _testing = false;
        _connected = result;
      });
    }
  }

  Future<void> _save() async {
    final input = _ipController.text.trim();
    if (input.isEmpty) return;

    // Build the test URL
    String testUrl;
    if (input.startsWith('http://') || input.startsWith('https://')) {
      testUrl = input;
    } else {
      // If user entered ip:port or just ip
      testUrl = 'http://$input';
      if (!input.contains(':')) {
        testUrl = 'http://$input:8000';
      }
    }
    if (testUrl.endsWith('/')) testUrl = testUrl.substring(0, testUrl.length - 1);

    // Test first
    setState(() {
      _testing = true;
      _connected = null;
    });
    final ok = await ApiClient.instance.testConnection(testUrl);
    if (!mounted) return;

    if (ok) {
      await ApiClient.instance.setBackendUrl(input);
      setState(() {
        _testing = false;
        _connected = true;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✅ Connected! Backend URL saved.'),
            backgroundColor: Color(0xFF2DD4BF),
          ),
        );
      }
    } else {
      setState(() {
        _testing = false;
        _connected = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('❌ Could not reach backend at that address.'),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cardColor = isDark
        ? Colors.white.withValues(alpha: 0.06)
        : Colors.white.withValues(alpha: 0.8);

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: const Text('Settings'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // ─── Connection Status ──────────────────────────────────
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: cardColor,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.08)
                    : Colors.black.withValues(alpha: 0.06),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.wifi_rounded,
                      size: 20,
                      color: isDark ? Colors.white70 : Colors.black54,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Backend Connection',
                      style: Theme.of(context)
                          .textTheme
                          .titleMedium
                          ?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    const Spacer(),
                    _buildStatusBadge(),
                  ],
                ),
                const SizedBox(height: 16),
                Text(
                  'Current: ${ApiClient.instance.baseUrl}',
                  style: TextStyle(
                    fontFamily: 'monospace',
                    fontSize: 13,
                    color: isDark ? Colors.white60 : Colors.black45,
                  ),
                ),
                if (kIsWeb) ...[
                  const SizedBox(height: 12),
                  Text(
                    'Running in browser — using localhost automatically.',
                    style: TextStyle(
                      fontSize: 13,
                      color: isDark ? Colors.white38 : Colors.black38,
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 20),

          // ─── IP Configuration (mobile only) ─────────────────────
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: cardColor,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.08)
                    : Colors.black.withValues(alpha: 0.06),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.settings_ethernet_rounded,
                      size: 20,
                      color: isDark ? Colors.white70 : Colors.black54,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Backend IP Address',
                      style: Theme.of(context)
                          .textTheme
                          .titleMedium
                          ?.copyWith(fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  'Enter your PC\'s local IP address. Find it by running ipconfig in a terminal on your PC.',
                  style: TextStyle(
                    fontSize: 13,
                    color: isDark ? Colors.white38 : Colors.black38,
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _ipController,
                  keyboardType: TextInputType.url,
                  decoration: InputDecoration(
                    hintText: '192.168.1.100:8000',
                    prefixText: 'http://',
                    filled: true,
                    fillColor: isDark
                        ? Colors.white.withValues(alpha: 0.05)
                        : Colors.grey.withValues(alpha: 0.1),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide.none,
                    ),
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 14,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: _testing ? null : _save,
                        icon: _testing
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(Icons.check_rounded, size: 18),
                        label: Text(_testing ? 'Testing...' : 'Save & Test'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    OutlinedButton(
                      onPressed: _testing ? null : () => _testConnection(),
                      child: const Text('Test'),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // ─── Help ────────────────────────────────────────────────
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: isDark
                  ? const Color(0xFF818CF8).withValues(alpha: 0.08)
                  : const Color(0xFF818CF8).withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: const Color(0xFF818CF8).withValues(alpha: 0.15),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.help_outline_rounded,
                      size: 20,
                      color: Color(0xFF818CF8),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'How to find your PC\'s IP',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                            color: const Color(0xFF818CF8),
                          ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                _buildStep('1', 'Open a terminal on your PC'),
                _buildStep(
                    '2', 'Run: ipconfig (Windows) or ifconfig (Mac/Linux)'),
                _buildStep('3', 'Find "IPv4 Address" under your WiFi adapter'),
                _buildStep('4', 'Enter that IP above (e.g., 192.168.1.100)'),
                const SizedBox(height: 12),
                Text(
                  'Both your phone and PC must be on the same WiFi network.',
                  style: TextStyle(
                    fontSize: 12,
                    fontStyle: FontStyle.italic,
                    color: isDark ? Colors.white38 : Colors.black38,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusBadge() {
    if (_testing) {
      return const SizedBox(
        width: 16,
        height: 16,
        child: CircularProgressIndicator(strokeWidth: 2),
      );
    }
    if (_connected == null) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.grey.withValues(alpha: 0.2),
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Text('Unknown', style: TextStyle(fontSize: 12)),
      );
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: _connected!
            ? const Color(0xFF2DD4BF).withValues(alpha: 0.2)
            : Colors.redAccent.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        _connected! ? 'Connected' : 'Disconnected',
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: _connected! ? const Color(0xFF2DD4BF) : Colors.redAccent,
        ),
      ),
    );
  }

  Widget _buildStep(String number, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 22,
            height: 22,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: const Color(0xFF818CF8).withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              number,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: Color(0xFF818CF8),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }
}
