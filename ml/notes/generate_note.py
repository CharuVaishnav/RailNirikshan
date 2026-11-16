"""Try the inspection-note prompt against a local LLM in Ollama.

Setup (once, free): install Ollama from ollama.com, then
    ollama pull qwen2.5:3b        # about 2 GB, runs on a normal CPU
    (on a slow laptop try qwen2.5:1.5b)
Run:
    python generate_note.py

When the output is good, set OLLAMA_URL=http://localhost:11434 in backend/.env.
"""
import httpx

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5:3b"

PROMPT = """You are helping a railway inspecting officer write a formal inspection note.
Use ONLY the observations given. Do not add anything that is not in them.
Write a short heading line, then a numbered list with one point per observation,
each point in clear, formal English, ending with the responsible department in brackets.

Location: Jaipur Junction
Inspection type: station
Date: 16 Nov 2026

Observations:
- 2 tube lights not working on FOB near platform 3 (department: Electrical)
- garbage near waiting hall gate, dustbin overflowing (department: Commercial)
- water collecting near platform 1 end after rain, drain blocked (department: Engineering)
"""

if __name__ == "__main__":
    r = httpx.post(f"{OLLAMA_URL}/api/generate", json={"model": MODEL, "prompt": PROMPT, "stream": False}, timeout=180)
    r.raise_for_status()
    print(r.json()["response"])
