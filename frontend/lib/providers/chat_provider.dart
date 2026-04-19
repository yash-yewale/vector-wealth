import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../services/api_client.dart';

class ChatMessage {
  final String role; // "user" or "assistant"
  final String content;
  final String timestamp;
  final Map<String, dynamic>? data;

  ChatMessage({
    required this.role,
    required this.content,
    this.timestamp = '',
    this.data,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      role: json['role'] ?? '',
      content: json['content'] ?? '',
      timestamp: json['timestamp'] ?? '',
      data: json['data'],
    );
  }

  Map<String, dynamic> toJson() => {
        'role': role,
        'content': content,
        'timestamp': timestamp,
        if (data != null) 'data': data,
      };

  bool get isUser => role == 'user';
  bool get isAssistant => role == 'assistant';
}

class ChatProvider extends ChangeNotifier {
  static const _storageKey = 'chat_history';
  static const _sessionKey = 'chat_session_id';
  static const int _maxPersistedMessages = 50;

  final ApiClient _api = ApiClient.instance;

  final List<ChatMessage> _messages = [];
  bool _isLoading = false;
  String? _error;
  late String _sessionId;
  List<Map<String, dynamic>> Function()? _getPortfolioData;

  ChatProvider({
    List<Map<String, dynamic>> Function()? getPortfolioData,
  })  : _getPortfolioData = getPortfolioData {
    _sessionId = 'session_${DateTime.now().millisecondsSinceEpoch}';
    _loadFromStorage();
  }

  List<ChatMessage> get messages => List.unmodifiable(_messages);
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isEmpty => _messages.isEmpty;

  /// Called by ProxyProvider to update the portfolio data getter
  /// without recreating the provider (preserves chat history).
  void updatePortfolioData(List<Map<String, dynamic>> Function() getter) {
    _getPortfolioData = getter;
  }

  // ─── Persistence ────────────────────────────────────────────────────────

  Future<void> _loadFromStorage() async {
    try {
      final prefs = await SharedPreferences.getInstance();

      // Restore session ID so backend session stays in sync
      final savedSession = prefs.getString(_sessionKey);
      if (savedSession != null && savedSession.isNotEmpty) {
        _sessionId = savedSession;
      } else {
        await prefs.setString(_sessionKey, _sessionId);
      }

      // Restore messages from local first
      final data = prefs.getString(_storageKey);
      if (data != null) {
        final list = jsonDecode(data) as List;
        _messages.clear();
        _messages.addAll(
          list.map((m) => ChatMessage.fromJson(m as Map<String, dynamic>)),
        );
        notifyListeners();
      }

      // If local is empty, try backend
      if (_messages.isEmpty) {
        try {
          final response = await _api.get(
            '/storage/chat/load?session_id=$_sessionId',
            timeout: const Duration(seconds: 5),
          );
          final backendMsgs = response['messages'] as List? ?? [];
          if (backendMsgs.isNotEmpty) {
            _messages.clear();
            _messages.addAll(backendMsgs
                .map((m) => ChatMessage.fromJson(m as Map<String, dynamic>)));
            await _saveLocal();
            notifyListeners();
          }
        } catch (_) {}
      }
    } catch (_) {
      // Silently fail — chat will start fresh
    }
  }

  Future<void> _saveLocal() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_sessionKey, _sessionId);
      final toSave = _messages.length > _maxPersistedMessages
          ? _messages.sublist(_messages.length - _maxPersistedMessages)
          : _messages;
      final data = jsonEncode(toSave.map((m) => m.toJson()).toList());
      await prefs.setString(_storageKey, data);
    } catch (_) {}
  }

  Future<void> _saveToStorage() async {
    await _saveLocal();
    // Also sync to backend
    try {
      await _api.post(
        '/storage/chat/save',
        body: {
          'session_id': _sessionId,
          'messages': _messages.map((m) => m.toJson()).toList(),
        },
        timeout: const Duration(seconds: 5),
      );
    } catch (_) {}
  }

  // ─── Chat ───────────────────────────────────────────────────────────────

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;

    // Add user message immediately
    final userMsg = ChatMessage(
      role: 'user',
      content: text.trim(),
      timestamp: DateTime.now().toIso8601String(),
    );
    _messages.add(userMsg);
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final Map<String, dynamic> payload = {
        'message': text.trim(),
        'session_id': _sessionId,
      };

      // Always include portfolio context if available
      if (_getPortfolioData != null) {
        final portfolio = _getPortfolioData!();
        if (portfolio.isNotEmpty) {
          payload['context_data'] = {'portfolio': portfolio};
        }
      }

      final data = await _api.post('/chat', body: payload);
      final assistantMsg = ChatMessage.fromJson(data);
      _messages.add(assistantMsg);
    } on ApiException catch (e) {
      _error = e.message;
      _messages.add(ChatMessage(
        role: 'assistant',
        content: e.statusCode == 503 ? e.message : 'Sorry, something went wrong: ${e.message}',
        timestamp: DateTime.now().toIso8601String(),
      ));
    } catch (e) {
      _error = 'Connection failed: $e';
      _messages.add(ChatMessage(
        role: 'assistant',
        content:
            'I couldn\'t reach the server. Make sure the backend is running on ${_api.baseUrl}.\nError: $e',
        timestamp: DateTime.now().toIso8601String(),
      ));
    } finally {
      _isLoading = false;
      await _saveToStorage();
      notifyListeners();
    }
  }

  void clearChat() {
    _messages.clear();
    _error = null;
    // New session so the backend starts fresh too
    _sessionId = 'session_${DateTime.now().millisecondsSinceEpoch}';
    _saveToStorage();
    notifyListeners();
  }
}
