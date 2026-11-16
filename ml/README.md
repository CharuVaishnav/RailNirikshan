# RailNirikshan AI / ML

Each folder is one AI feature. Build and test each one here first, then plug it into
`backend/app/services/ai.py`, which already has a working fallback for each.

| Folder | Feature | Week (build plan) | Plugs into |
|---|---|---|---|
| `defect_detection/` | Find defects in inspection photos (YOLOv8) | 5–6 | `detect_defects()` via `YOLO_MODEL_PATH` |
| `speech/` | Hindi/English voice notes to text (faster-whisper) | 7 | new `/transcribe` endpoint |
| `notes/` | AI-written inspection note (Ollama LLM) | 7 | `generate_note()` via `OLLAMA_URL` |
| `routing/` | Send each point to the right department | 8 | replace `route_department()` |
| `verification/` | Check before/after photos | 8 | extend `verify_fix()` |
| `repeats/` | Find problems that keep coming back (optional) | 9 | new dashboard endpoint |

```bash
cd ml
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Everything here is free. Train YOLOv8 on the free GPU in Google Colab or Kaggle (upload the `defect_detection`
folder and your labelled dataset). All other models run on a normal laptop CPU, so no paid AI APIs are needed.
