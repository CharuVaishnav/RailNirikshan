"""Transcribe an officer's voice note (Hindi, English or mixed) with faster-whisper on a normal CPU.

    python transcribe.py note.m4a
    python transcribe.py note.m4a --language hi --model medium

"small" is quick on a laptop CPU; "medium" is more accurate for Hindi but slower. Free, runs offline.
"""
import argparse

from faster_whisper import WhisperModel


def transcribe(path: str, model_name: str = "small", language: str | None = None) -> str:
    model = WhisperModel(model_name, device="cpu", compute_type="int8")  # int8 = small and fast on CPU
    segments, info = model.transcribe(path, language=language, vad_filter=True)
    return " ".join(seg.text.strip() for seg in segments)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("audio")
    p.add_argument("--model", default="small")
    p.add_argument("--language", default=None, help="hi or en; leave empty to auto-detect")
    a = p.parse_args()
    print(transcribe(a.audio, a.model, a.language))
