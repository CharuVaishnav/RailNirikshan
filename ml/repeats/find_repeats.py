"""Find problems that keep coming back, by grouping similar observations.

    python find_repeats.py ../routing/sample_points.csv

Uses multilingual sentence embeddings (works for Hindi and English) and HDBSCAN clustering.
In the app, run this per station over the last few months of observations.
"""
import sys

import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import HDBSCAN

df = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else "../routing/sample_points.csv")
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
emb = model.encode(df["text"].tolist(), normalize_embeddings=True)

labels = HDBSCAN(min_cluster_size=2, metric="euclidean").fit_predict(emb)
df["group"] = labels

for g, rows in df[df.group >= 0].groupby("group"):
    print(f"\nRepeated issue #{g} ({len(rows)} times):")
    for t in rows["text"]:
        print("  -", t)
print(f"\n{(labels < 0).sum()} observations did not repeat.")
