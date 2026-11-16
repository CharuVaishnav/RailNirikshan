"""Department routing: train a baseline text classifier and report accuracy.

    python train_baseline.py                      # uses sample_points.csv (demo data)
    python train_baseline.py real_points.csv      # use anonymised points from NWR

The sample file is tiny and made up, only to show the pipeline. Replace it with real,
anonymised inspection points (and officers' corrections from the app) for real results.
Target: accuracy >= 90% on real data.
"""
import sys
import pickle

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import cross_val_predict
from sklearn.pipeline import make_pipeline

path = sys.argv[1] if len(sys.argv) > 1 else "sample_points.csv"
df = pd.read_csv(path)

model = make_pipeline(
    TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, analyzer="word"),
    LogisticRegression(max_iter=1000, class_weight="balanced"),
)

# Cross-validation gives a fair accuracy estimate even on small data.
folds = min(5, df["department"].value_counts().min())
pred = cross_val_predict(model, df["text"], df["department"], cv=folds)
print(classification_report(df["department"], pred, zero_division=0))

model.fit(df["text"], df["department"])
with open("routing_model.pkl", "wb") as f:
    pickle.dump(model, f)
print("Saved routing_model.pkl")

# Next step (week 8): compare with
#  - a multilingual transformer (e.g. fine-tuned on Hindi + English points), and
#  - the LLM in zero-shot mode ("Which department handles: ...?")
# and pick the best for backend/app/services/ai.py route_department().
