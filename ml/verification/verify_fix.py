"""Compare a 'before' and 'after' photo of the same spot.

    python verify_fix.py before.jpg after.jpg

A perceptual hash tells us whether the two photos show the same scene (taken from roughly
the same place). Combined with the GPS distance and re-running the defect detector on the
after-photo (both already in the backend), this decides if a fix looks genuine.
"""
import sys

import imagehash
from PIL import Image


def scene_similarity(before_path: str, after_path: str) -> float:
    """1.0 = identical scene, around 0.5 or below = unrelated photos."""
    a = imagehash.phash(Image.open(before_path))
    b = imagehash.phash(Image.open(after_path))
    return 1 - (a - b) / len(a.hash) ** 2


if __name__ == "__main__":
    s = scene_similarity(sys.argv[1], sys.argv[2])
    verdict = "same scene" if s >= 0.7 else "possibly a different place - flag for review"
    print(f"similarity = {s:.2f} -> {verdict}")
    # Tune the 0.7 threshold on real before/after pairs collected during the pilot.
