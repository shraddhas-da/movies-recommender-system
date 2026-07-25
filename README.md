# Movie Recommender + Details + Sentiment Analysis

## Files
- `app.py` - the full Streamlit app (home page, clickable details page, sentiment section)
- `train_sentiment_model.py` - trains a sentiment classifier from scratch (run once)
- `requirements.txt` - dependencies
- `movies.pkl`, `similarity.pkl` - **your existing files, not included here.** Put them in this same folder.

## Setup

```bash
pip install -r requirements.txt

# Train the sentiment model (only needs to be run once; downloads NLTK's
# movie_reviews corpus and saves transform.pkl + nlp_model.pkl)
python train_sentiment_model.py

# Run the app
streamlit run app.py
```

Make sure `movies.pkl`, `similarity.pkl`, `transform.pkl`, and `nlp_model.pkl` all sit next to `app.py`.

## How it works

**Home page**
- Pick a movie, hit "Show Recommendations" - 5 poster cards appear.
- Each card has a "View Details" button under the poster (Streamlit can't make
  `st.image` itself clickable, so the button is the click target) that opens
  the details page for that movie.

**Details page**
- Fetches live from TMDB (same API key as your original script): title,
  release date, genres, runtime, rating, overview, director, and up to 8
  cast members with photos - laid out like your reference screenshots.
- Shows a fresh row of recommendations for *this* movie — clicking one of
  those drills further in, so you can browse movie → similar movie →
  similar movie indefinitely.
- **Sentiment Analysis**: fetches up to 10 user reviews for the movie from
  TMDB's own review API (the same API key already used elsewhere in the app),
  runs each through the trained model, and shows each review tagged
  Positive/Negative plus an overall positive-review percentage.

## Notes / things worth knowing

1. **Sentiment model quality**: `train_sentiment_model.py` trains on NLTK's
   built-in `movie_reviews` corpus (~2,000 labeled reviews) so the whole
   pipeline works with zero external downloads. It's noticeably smaller than
   the classic 50k-review IMDB Kaggle dataset, so accuracy is decent (~80%
   in testing) but not state-of-the-art. If you already have a larger
   labeled CSV, swap the "Build dataset" section in that script to load it -
   everything downstream (vectorize → train → save) stays the same.

2. **Review volume**: TMDB's review endpoint (`get_movie_reviews`) is used
   instead of scraping IMDB, because IMDB sits behind bot-detection (Akamai)
   that returns a small interstitial page to plain HTTP requests rather than
   real content - not reliably beatable without heavier tooling like a
   headless browser. TMDB's official API is stable and requires no scraping,
   but has fewer user reviews per title than IMDB does, so some movies may
   show only a handful of reviews (or none).

3. **API key**: left inline exactly as in your original script for
   simplicity. If you ever deploy this publicly, move it into
   `st.secrets["TMDB_API_KEY"]` instead of hardcoding it.

4. **Caching**: TMDB calls and IMDB scraping are cached (`st.cache_data`)
   for an hour so repeatedly clicking around the same movie doesn't re-hit
   either site every time.
