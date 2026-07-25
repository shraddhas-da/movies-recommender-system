"""
train_sentiment_model.py
-------------------------
Trains a simple, self-contained sentiment classifier from scratch and saves
it as two pickle files that app.py loads at runtime:

    transform.pkl   -> the fitted CountVectorizer
    nlp_model.pkl   -> the fitted classifier (Logistic Regression)

Why NLTK's movie_reviews corpus?
It's ~2000 labeled (pos/neg) full movie reviews that ships via NLTK's own
downloader, so this script has zero dependency on hunting down an external
CSV (like the 50k-review IMDB Kaggle dataset). Quality is lower than the
50k-review dataset, but it's reliable to obtain anywhere and good enough to
label live-scraped IMDB reviews as Positive/Negative for this project.

If you already have a larger labeled reviews CSV (columns like `review`,
`sentiment`), swap the "Build dataset" section below to load that instead
-- the rest of the script (vectorize -> train -> save) stays the same.

Run once, before starting the app:
    python train_sentiment_model.py
"""

import random
import pickle

import nltk
from nltk.corpus import movie_reviews
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

print("Checking / downloading NLTK 'movie_reviews' corpus...")
nltk.download("movie_reviews")

docs, labels = [], []
for category in movie_reviews.categories():          # 'pos' / 'neg'
    for fileid in movie_reviews.fileids(category):
        docs.append(movie_reviews.raw(fileid))
        labels.append(1 if category == "pos" else 0)

combined = list(zip(docs, labels))
random.seed(42)
random.shuffle(combined)
docs, labels = zip(*combined)

print(f"Loaded {len(docs)} labeled reviews "
      f"({sum(labels)} positive / {len(labels) - sum(labels)} negative).")

X_train, X_test, y_train, y_test = train_test_split(
    docs, labels, test_size=0.2, random_state=42, stratify=labels
)
vectorizer = CountVectorizer(max_features=5000, stop_words="english", ngram_range=(1, 2))
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)


model = LogisticRegression(max_iter=1000)
model.fit(X_train_vec, y_train)

preds = model.predict(X_test_vec)
print("\nTest accuracy:", round(accuracy_score(y_test, preds), 4))
print(classification_report(y_test, preds, target_names=["neg", "pos"]))


pickle.dump(vectorizer, open("transform.pkl", "wb"))
pickle.dump(model, open("nlp_model.pkl", "wb"))
print("\nSaved transform.pkl and nlp_model.pkl in the current folder.")
print("Place them next to app.py, movies.pkl, and similarity.pkl, then run:")
print("    streamlit run app.py")
