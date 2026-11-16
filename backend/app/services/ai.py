"""AI services used by the backend.

Each function has a simple working fallback, so the whole app runs from day one.
Replace the fallbacks with the real models as you build them in the ml/ folder:

  detect_defects   -> YOLOv8 model             (ml/defect_detection)
  route_department -> trained text classifier  (ml/routing)
  generate_note    -> self-hosted LLM via Ollama (ml/notes)
  verify_fix       -> location + image check    (ml/verification)
"""
import math

import httpx

from ..config import settings

# ---------------------------------------------------------------- routing
# Baseline: keyword rules. Week 8 replaces this with a trained classifier.
ROUTING_KEYWORDS: dict[str, list[str]] = {
    "ELEC": ["light", "fan", "bulb", "electric", "wiring", "power", "switch", "socket", "ac ", "lift", "escalator"],
    "ENGG": ["platform surface", "platform edge", "roof", "leak", "waterlog", "drain", "floor", "tile", "wall",
             "crack", "track", "seating", "bench", "building", "toilet", "paint"],
    "COMM": ["clean", "litter", "garbage", "dust", "waiting hall", "drinking water", "ticket", "enquiry", "signage", "announcement board"],
    "MECH": ["coach", "berth", "door", "window", "brake", "pantry car", "bogie"],
    "SNT": ["signal", "display board", "pa system", "public address", "cctv", "communication", "lc gate", "level crossing"],
    "MED": ["food", "hygiene", "first aid", "medical", "pest", "rodent"],
    "SEC": ["security", "rpf", "unauthorised", "trespass", "fire extinguisher"],
}


def route_department(text: str) -> str | None:
    """Return the department code that best matches the observation text."""
    t = f" {text.lower()} "
    scores = {code: sum(1 for kw in kws if kw in t) for code, kws in ROUTING_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


# ------------------------------------------------------- defect detection
_yolo = None


def detect_defects(photo: bytes | None) -> list[dict]:
    """Return a list of {label, confidence, box}. Empty until a YOLO model is configured."""
    global _yolo
    if not photo or not settings.yolo_model_path:
        return []
    try:
        if _yolo is None:
            from ultralytics import YOLO  # installed via ml/requirements.txt

            _yolo = YOLO(settings.yolo_model_path)
        import io

        from PIL import Image

        result = _yolo(Image.open(io.BytesIO(photo)), verbose=False)[0]
        out = []
        for box in result.boxes:
            out.append({
                "label": result.names[int(box.cls)],
                "confidence": round(float(box.conf), 3),
                "box": [round(v, 1) for v in box.xyxy[0].tolist()],
            })
        return out
    except Exception as exc:  # never block an inspection because the model failed
        return [{"label": "model_error", "confidence": 0, "detail": str(exc)}]


# -------------------------------------------------------- note generation
NOTE_PROMPT = """You are helping a railway inspecting officer write a formal inspection note.
Use ONLY the observations given. Do not add anything that is not in them.
Write a short heading line, then a numbered list with one point per observation,
each point in clear, formal English, ending with the responsible department in brackets.

Location: {location}
Inspection type: {kind}
Date: {date}

Observations:
{items}
"""


def generate_note(location: str, kind: str, date: str, observations: list[dict]) -> str:
    """observations: [{"text": ..., "department": ...}]"""
    items = "\n".join(f"- {o['text']} (department: {o.get('department') or 'to be decided'})" for o in observations)
    if settings.ollama_url:
        try:
            resp = httpx.post(
                f"{settings.ollama_url}/api/generate",
                json={"model": settings.ollama_model,
                      "prompt": NOTE_PROMPT.format(location=location, kind=kind, date=date, items=items),
                      "stream": False},
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()["response"].strip()
        except Exception:
            pass  # fall back to the template below
    lines = [f"Inspection note: {kind.replace('_', ' ').title()} inspection at {location} on {date}", ""]
    for i, o in enumerate(observations, start=1):
        lines.append(f"{i}. {o['text'].strip().rstrip('.')}. [{o.get('department') or 'Department to be decided'}]")
    return "\n".join(lines)


# ------------------------------------------------------- fix verification
def distance_m(lat1, lon1, lat2, lon2) -> float:
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def verify_fix(before: dict, after: dict, max_distance_m: float = 100) -> dict:
    """Compare the original observation with the fix update.

    before/after: {"lat", "lon", "defects": [...]}
    Week 8 adds image similarity (ml/verification/verify_fix.py).
    """
    checks: dict = {}
    if None not in (before.get("lat"), before.get("lon"), after.get("lat"), after.get("lon")):
        d = distance_m(before["lat"], before["lon"], after["lat"], after["lon"])
        checks["distance_m"] = round(d, 1)
        checks["same_location"] = d <= max_distance_m
    else:
        checks["same_location"] = None
    before_labels = {x["label"] for x in before.get("defects", [])}
    after_labels = {x["label"] for x in after.get("defects", [])}
    checks["defects_remaining"] = sorted(before_labels & after_labels)
    if checks["same_location"] is False or checks["defects_remaining"]:
        checks["result"] = "doubtful"
    elif checks["same_location"] is None:
        checks["result"] = "needs_review"
    else:
        checks["result"] = "looks_fixed"
    return checks
