import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;

import '../api.dart';
import 'inspection_screen.dart';

const inspectionTypes = {'station': 'Station', 'lc_gate': 'LC gate', 'coach': 'Coach'};

class NewInspectionScreen extends StatefulWidget {
  const NewInspectionScreen({super.key});

  @override
  State<NewInspectionScreen> createState() => _NewInspectionScreenState();
}

class _NewInspectionScreenState extends State<NewInspectionScreen> {
  List<dynamic> _locations = [];
  int? _locationId;
  String _type = 'station';
  List<dynamic> _items = [];
  final Map<String, bool> _answers = {};
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    Api.get('/locations').then((v) => setState(() => _locations = v));
    _loadChecklist();
  }

  Future<void> _loadChecklist() async {
    final raw = await rootBundle.loadString('assets/checklists/$_type.json');
    setState(() {
      _items = jsonDecode(raw)['items'];
      _answers.clear();
      for (final item in _items) {
        _answers[item['id']] = true;
      }
    });
  }

  Future<void> _start() async {
    if (_locationId == null) return;
    setState(() => _busy = true);
    try {
      final insp = await Api.postJson('/inspections', {
        'location_id': _locationId,
        'inspection_type': _type,
        'checklist': _answers,
      });
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => InspectionScreen(inspectionId: insp['id'])),
      );
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New inspection')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          DropdownButtonFormField<int>(
            decoration: const InputDecoration(labelText: 'Location'),
            value: _locationId,
            items: [
              for (final l in _locations) DropdownMenuItem(value: l['id'] as int, child: Text(l['name'])),
            ],
            onChanged: (v) => setState(() => _locationId = v),
          ),
          DropdownButtonFormField<String>(
            decoration: const InputDecoration(labelText: 'Inspection type'),
            value: _type,
            items: [
              for (final e in inspectionTypes.entries) DropdownMenuItem(value: e.key, child: Text(e.value)),
            ],
            onChanged: (v) {
              _type = v!;
              _loadChecklist();
            },
          ),
          const SizedBox(height: 16),
          const Text('Checklist (untick anything that is not OK)', style: TextStyle(fontWeight: FontWeight.bold)),
          for (final item in _items)
            CheckboxListTile(
              value: _answers[item['id']] ?? true,
              title: Text(item['label']),
              onChanged: (v) => setState(() => _answers[item['id']] = v ?? false),
            ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _busy || _locationId == null ? null : _start,
            child: const Text('Start inspection'),
          ),
        ],
      ),
    );
  }
}
