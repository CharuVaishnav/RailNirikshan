import 'package:flutter/material.dart';

import '../api.dart';
import 'inspection_screen.dart';
import 'login_screen.dart';
import 'new_inspection_screen.dart';
import 'task_screen.dart';

/// Officers see their inspections. Staff see the compliance tasks for their department.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<List<dynamic>> _items;
  bool get _isStaff => Api.role == 'staff';

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    setState(() {
      _items = Api.get(_isStaff ? '/tasks' : '/inspections').then((v) => v as List<dynamic>);
    });
  }

  Future<void> _logout() async {
    await Api.logout();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const LoginScreen()));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_isStaff ? 'My department tasks' : 'My inspections'),
        actions: [IconButton(onPressed: _logout, icon: const Icon(Icons.logout))],
      ),
      floatingActionButton: _isStaff
          ? null
          : FloatingActionButton.extended(
              icon: const Icon(Icons.add),
              label: const Text('New inspection'),
              onPressed: () async {
                await Navigator.of(context).push(MaterialPageRoute(builder: (_) => const NewInspectionScreen()));
                _reload();
              },
            ),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<List<dynamic>>(
          future: _items,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) return ListView(children: [Padding(padding: const EdgeInsets.all(24), child: Text('${snap.error}'))]);
            final items = snap.data!;
            if (items.isEmpty) {
              return ListView(children: const [Padding(padding: EdgeInsets.all(24), child: Text('Nothing here yet.'))]);
            }
            return ListView.separated(
              itemCount: items.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, i) => _isStaff ? _taskTile(items[i]) : _inspectionTile(items[i]),
            );
          },
        ),
      ),
    );
  }

  Widget _inspectionTile(dynamic insp) => ListTile(
        title: Text('${insp['location']['name']} · ${insp['inspection_type']}'),
        subtitle: Text('${(insp['observations'] as List).length} observations · ${insp['status']}'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () async {
          await Navigator.of(context).push(MaterialPageRoute(builder: (_) => InspectionScreen(inspectionId: insp['id'])));
          _reload();
        },
      );

  Widget _taskTile(dynamic task) => ListTile(
        title: Text(task['observation']['text']),
        subtitle: Text('Due ${task['deadline'].toString().substring(0, 10)} · ${task['status']}'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () async {
          await Navigator.of(context).push(MaterialPageRoute(builder: (_) => TaskScreen(task: task)));
          _reload();
        },
      );
}
