import 'package:flutter/material.dart';

import '../api.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _user = TextEditingController(text: 'officer');
  final _pass = TextEditingController();
  final _server = TextEditingController(text: Api.baseUrl);
  bool _busy = false;
  String? _error;

  Future<void> _login() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      Api.baseUrl = _server.text.trim();
      await Api.login(_user.text.trim(), _pass.text);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const HomeScreen()));
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const SizedBox(height: 40),
            Text('RailNirikshan', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold)),
            const Text('Smart inspection and compliance'),
            const SizedBox(height: 32),
            TextField(controller: _user, decoration: const InputDecoration(labelText: 'Username')),
            TextField(controller: _pass, obscureText: true, decoration: const InputDecoration(labelText: 'Password')),
            TextField(controller: _server, decoration: const InputDecoration(labelText: 'Server address')),
            const SizedBox(height: 16),
            if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 8),
            FilledButton(onPressed: _busy ? null : _login, child: Text(_busy ? 'Signing in…' : 'Sign in')),
            const SizedBox(height: 12),
            const Text('Demo users: officer, staff_elec, staff_comm … password demo123',
                style: TextStyle(color: Colors.grey)),
          ],
        ),
      ),
    );
  }
}
