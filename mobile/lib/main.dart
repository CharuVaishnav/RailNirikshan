import 'package:flutter/material.dart';

import 'api.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';

const navy = Color(0xFF1B2A4A);
const railRed = Color(0xFFB7312C);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Api.loadSession();
  runApp(const RailNirikshanApp());
}

class RailNirikshanApp extends StatelessWidget {
  const RailNirikshanApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RailNirikshan',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: navy, primary: navy, secondary: railRed),
        appBarTheme: const AppBarTheme(backgroundColor: navy, foregroundColor: Colors.white),
        useMaterial3: true,
      ),
      home: Api.loggedIn ? const HomeScreen() : const LoginScreen(),
    );
  }
}
