import 'dart:io';

import 'package:flutter/material.dart';

import '../api.dart';
import '../capture.dart';

/// Add observations (text + photo + GPS), let AI draft the note, then approve.
class InspectionScreen extends StatefulWidget {
  final int inspectionId;
  const InspectionScreen({super.key, required this.inspectionId});

  @override
  State<InspectionScreen> createState() => _InspectionScreenState();
}

class _InspectionScreenState extends State<InspectionScreen> {
  Map<String, dynamic>? _insp;
  final _text = TextEditingController();
  final _note = TextEditingController();
  File? _photo;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final insp = await Api.get('/inspections/${widget.inspectionId}');
    setState(() {
      _insp = insp;
      _note.text = insp['note_text'] ?? '';
    });
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addObservation() => _run(() async {
        if (_text.text.trim().isEmpty) throw ApiError('Write or speak the observation first');
        final pos = await currentPosition();
        await Api.postForm('/inspections/${widget.inspectionId}/observations', {
          'text': _text.text.trim(),
          if (pos != null) 'latitude': '${pos.latitude}',
          if (pos != null) 'longitude': '${pos.longitude}',
        }, photo: _photo);
        _text.clear();
        _photo = null;
      });

  @override
  Widget build(BuildContext context) {
    final insp = _insp;
    if (insp == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    final draft = insp['status'] == 'draft';
    final observations = insp['observations'] as List;

    return Scaffold(
      appBar: AppBar(title: Text(insp['location']['name'])),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Observations (${observations.length})', style: Theme.of(context).textTheme.titleMedium),
          for (final o in observations)
            Card(
              child: ListTile(
                leading: o['photo_key'] != null
                    ? Image.network(Api.photoUrl(o['photo_key']), headers: Api.imageHeaders, width: 56, fit: BoxFit.cover)
                    : const Icon(Icons.notes),
                title: Text(o['text']),
                subtitle: Text([
                  'Dept: ${o['suggested_department']?['name'] ?? 'not decided'}',
                  if ((o['ai_defects'] as List).isNotEmpty)
                    'AI found: ${(o['ai_defects'] as List).map((d) => d['label']).join(', ')}',
                ].join('\n')),
              ),
            ),
          if (draft) ...[
            const Divider(height: 32),
            TextField(
              controller: _text,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'New observation',
                hintText: 'e.g. Two lights not working on platform 3',
                // TODO (week 7): add a microphone button that records audio and sends it for Whisper transcription.
              ),
            ),
            Row(children: [
              TextButton.icon(
                icon: const Icon(Icons.photo_camera),
                label: Text(_photo == null ? 'Add photo' : 'Retake photo'),
                onPressed: () async {
                  final p = await takePhoto();
                  if (p != null) setState(() => _photo = p);
                },
              ),
              if (_photo != null) Image.file(_photo!, width: 48, height: 48, fit: BoxFit.cover),
              const Spacer(),
              FilledButton(onPressed: _busy ? null : _addObservation, child: const Text('Add')),
            ]),
            const Divider(height: 32),
            OutlinedButton.icon(
              icon: const Icon(Icons.auto_awesome),
              label: const Text('Generate inspection note with AI'),
              onPressed: _busy || observations.isEmpty
                  ? null
                  : () => _run(() => Api.postJson('/inspections/${widget.inspectionId}/generate-note')),
            ),
          ],
          if (_note.text.isNotEmpty || !draft) ...[
            const SizedBox(height: 12),
            TextField(
              controller: _note,
              maxLines: null,
              readOnly: !draft,
              decoration: const InputDecoration(labelText: 'Inspection note', border: OutlineInputBorder()),
            ),
          ],
          if (draft && _note.text.isNotEmpty) ...[
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _busy
                  ? null
                  : () => _run(() async {
                        // Save the officer's edits to the AI draft, then approve.
                        await Api.putJson('/inspections/${widget.inspectionId}/note', {'note_text': _note.text});
                        await Api.postJson('/inspections/${widget.inspectionId}/approve');
                      }),
              child: const Text('Approve and send to departments'),
            ),
          ],
          if (!draft) const Padding(padding: EdgeInsets.only(top: 12), child: Text('Approved. Tasks sent to departments.')),
        ],
      ),
    );
  }
}
