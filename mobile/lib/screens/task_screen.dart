import 'dart:io';

import 'package:flutter/material.dart';

import '../api.dart';
import '../capture.dart';

/// Staff view of one compliance task: see the issue, fix it, upload an after-photo.
class TaskScreen extends StatefulWidget {
  final Map<String, dynamic> task;
  const TaskScreen({super.key, required this.task});

  @override
  State<TaskScreen> createState() => _TaskScreenState();
}

class _TaskScreenState extends State<TaskScreen> {
  final _remark = TextEditingController();
  File? _photo;
  bool _busy = false;

  Future<void> _submit() async {
    setState(() => _busy = true);
    try {
      final pos = await currentPosition();
      final updated = await Api.postForm('/tasks/${widget.task['id']}/fix', {
        'remark': _remark.text.trim(),
        if (pos != null) 'latitude': '${pos.latitude}',
        if (pos != null) 'longitude': '${pos.longitude}',
      }, photo: _photo);
      final check = (updated['updates'] as List).last['verification']?['result'] ?? 'submitted';
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Fix submitted. AI check: $check')));
      Navigator.of(context).pop();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final obs = widget.task['observation'];
    final canFix = widget.task['status'] == 'open';
    return Scaffold(
      appBar: AppBar(title: Text('Task #${widget.task['id']}')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(obs['text'], style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Text('Deadline: ${widget.task['deadline'].toString().substring(0, 10)} · Status: ${widget.task['status']}'),
          if (obs['photo_key'] != null) ...[
            const SizedBox(height: 12),
            const Text('Before'),
            Image.network(Api.photoUrl(obs['photo_key']), headers: Api.imageHeaders, height: 200, fit: BoxFit.cover),
          ],
          if (canFix) ...[
            const Divider(height: 32),
            TextField(controller: _remark, decoration: const InputDecoration(labelText: 'What was done?')),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              icon: const Icon(Icons.photo_camera),
              label: Text(_photo == null ? 'Take after-photo' : 'Retake after-photo'),
              onPressed: () async {
                final p = await takePhoto();
                if (p != null) setState(() => _photo = p);
              },
            ),
            if (_photo != null) Image.file(_photo!, height: 200, fit: BoxFit.cover),
            const SizedBox(height: 12),
            FilledButton(onPressed: _busy ? null : _submit, child: const Text('Submit fix')),
          ],
        ],
      ),
    );
  }
}
