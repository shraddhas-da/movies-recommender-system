import pickle
import urllib.parse
import requests
from requests.adapters import HTTPAdapter, Retry
import streamlit as st

st.set_page_config(page_title="Movie Recommender", layout="wide")

API_KEY = st.secrets["API_KEY"]  # TMDB API key (same one from the original script)
TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"
PROFILE_BASE = "https://image.tmdb.org/t/p/w200"
PLACEHOLDER = "https://via.placeholder.com/500x750.png?text=No+Poster+Available"
PLACEHOLDER_FACE = "https://via.placeholder.com/200x200.png?text=No+Photo"


@st.cache_resource
def get_session():
    """A shared requests Session with automatic retries.

    Windows machines (especially with antivirus doing SSL inspection) can
    intermittently reset connections when several requests fire back-to-back,
    which is exactly what happens on the details page (details + credits +
    external_ids + poster calls, all within a second or two). Retrying with
    backoff absorbs those transient resets instead of failing the page.
    """
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        }
    )
    return session

# Data loading

@st.cache_data
def load_data():
    movies = pickle.load(open("movies.pkl", "rb"))
    similarity = pickle.load(open("similarity.pkl", "rb"))
    movies["title"] = movies["title"].str.strip()
    return movies, similarity


try:
    movies, similarity = load_data()
    movie_list = movies["title"].values
except Exception as e:
    st.error(f"Could not load movies.pkl / similarity.pkl: {e}")
    st.stop()


# Sentiment model is optional -- app still works without it, just skips that section
@st.cache_resource
def load_sentiment_model():
    try:
        vectorizer = pickle.load(open("transform.pkl", "rb"))
        model = pickle.load(open("nlp_model.pkl", "rb"))
        return vectorizer, model, None
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}"


sentiment_vectorizer, sentiment_model, SENTIMENT_LOAD_ERROR = load_sentiment_model()
SENTIMENT_AVAILABLE = sentiment_vectorizer is not None and sentiment_model is not None

# TMDB helpers

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_poster(movie_id, movie_title):
    """ID -> Search -> Placeholder."""
    movie_title = (movie_title or "").strip()
    session = get_session()

    try:
        url = f"{TMDB_BASE}/movie/{movie_id}?api_key={API_KEY}"
        response = session.get(url, timeout=8)
        if response.status_code == 200:
            path = response.json().get("poster_path")
            if path:
                return f"{POSTER_BASE}{path}"
    except Exception:
        pass

    try:
        encoded_title = urllib.parse.quote(movie_title)
        search_url = f"{TMDB_BASE}/search/movie?api_key={API_KEY}&query={encoded_title}"
        search_res = session.get(search_url, timeout=8)
        if search_res.status_code == 200:
            for m in search_res.json().get("results", []):
                path = m.get("poster_path")
                if path:
                    return f"{POSTER_BASE}{path}"
    except Exception:
        pass

    return PLACEHOLDER


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_movie_details(movie_id):
    """Pulls overview/genres/runtime/rating, director+cast, and the IMDB id.

    Returns (details_dict, error_message). error_message is None on success.
    """
    details = {}
    session = get_session()
    try:
        r = session.get(f"{TMDB_BASE}/movie/{movie_id}", params={"api_key": API_KEY}, timeout=8)
        r.raise_for_status()
        d = r.json()
        details.update(
            {
                "title": d.get("title"),
                "release_date": d.get("release_date"),
                "runtime": d.get("runtime"),
                "genres": [g["name"] for g in d.get("genres", [])],
                "overview": d.get("overview"),
                "vote_average": d.get("vote_average"),
                "poster_path": d.get("poster_path"),
            }
        )
    except requests.exceptions.HTTPError as e:
        return None, f"TMDB returned an error: {e} — response body: {r.text[:300]}"
    except requests.exceptions.RequestException as e:
        return None, f"Couldn't reach TMDB: {e}"
    except Exception as e:
        return None, f"Unexpected error: {e}"

    try:
        r = session.get(f"{TMDB_BASE}/movie/{movie_id}/credits", params={"api_key": API_KEY}, timeout=8)
        if r.status_code == 200:
            c = r.json()
            crew = c.get("crew", [])
            directors = [p["name"] for p in crew if p.get("job") == "Director"]
            details["director"] = ", ".join(directors) if directors else "Unknown"
            details["cast"] = c.get("cast", [])[:8]
    except Exception:
        details["director"] = "Unknown"
        details["cast"] = []

    try:
        r = session.get(f"{TMDB_BASE}/movie/{movie_id}/external_ids", params={"api_key": API_KEY}, timeout=8)
        if r.status_code == 200:
            details["imdb_id"] = r.json().get("imdb_id")
    except Exception:
        details["imdb_id"] = None

    return details, None

# IMDB review scraping + sentiment

@st.cache_data(ttl=3600, show_spinner=False)
def get_movie_reviews(movie_id, max_reviews=10):
    """Fetches reviews from TMDB's own review endpoint.

    Switched from scraping IMDB's reviews page because IMDB sits behind
    bot-detection (Akamai) that returns a ~2KB HTTP 202 interstitial to
    plain `requests` calls instead of the real page -- not reliably
    beatable without heavier tooling like a headless browser. TMDB has a
    stable, official /movie/{id}/reviews endpoint with the same API key
    already in use elsewhere in this app, so this is both simpler and
    more robust, at the cost of a smaller review volume than IMDB has.

    Returns (reviews_list, debug_info_string).
    """
    session = get_session()
    try:
        r = session.get(
            f"{TMDB_BASE}/movie/{movie_id}/reviews",
            params={"api_key": API_KEY, "language": "en-US", "page": 1},
            timeout=8,
        )
    except Exception as e:
        return [], f"Request to TMDB reviews endpoint failed: {e}"

    if r.status_code != 200:
        return [], f"TMDB reviews endpoint returned HTTP {r.status_code}"

    results = r.json().get("results", [])
    reviews = [item["content"] for item in results[:max_reviews] if item.get("content")]

    if not reviews:
        return [], "TMDB has no user reviews on file for this movie."

    return reviews, f"{len(reviews)} review(s) from TMDB"


def predict_sentiment(review_text):
    vec = sentiment_vectorizer.transform([review_text])
    pred = sentiment_model.predict(vec)[0]
    return "Positive" if pred == 1 else "Negative"

# Recommendation logic
def recommend(movie_title):
    movie_index = movies[movies["title"] == movie_title].index[0]
    distances = similarity[movie_index]
    top = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    names, posters, ids = [], [], []
    for i in top:
        m_data = movies.iloc[i[0]]
        names.append(m_data.title)
        ids.append(int(m_data.movie_id))
        posters.append(fetch_poster(m_data.movie_id, m_data.title))
    return names, posters, ids

# Session state / navigation

st.session_state.setdefault("page", "home")
st.session_state.setdefault("recs", None)          # (names, posters, ids) from home search
st.session_state.setdefault("selected_movie_id", None)
st.session_state.setdefault("selected_movie_title", None)


def go_to_details(movie_id, movie_title):
    st.session_state.page = "details"
    st.session_state.selected_movie_id = movie_id
    st.session_state.selected_movie_title = movie_title
    st.rerun()


def go_home():
    st.session_state.page = "home"
    st.rerun()


def render_movie_grid(names, posters, ids, key_prefix):
    """A row of poster cards; clicking 'View Details' opens the details page."""
    cols = st.columns(len(names))
    for idx, col in enumerate(cols):
        with col:
            st.image(posters[idx], use_container_width=True)
            st.caption(f"**{names[idx]}**")
            if st.button("View Details", key=f"{key_prefix}_{ids[idx]}_{idx}"):
                go_to_details(ids[idx], names[idx])

# Home page
def render_home():
    st.title("🎬 Movie Recommendation System")

    selected_movie = st.selectbox("Type or select a movie:", movie_list)

    if st.button("Show Recommendations"):
        with st.spinner("Fetching recommendations..."):
            names, posters, ids = recommend(selected_movie)
            st.session_state.recs = (names, posters, ids)

    if st.session_state.recs:
        names, posters, ids = st.session_state.recs
        st.subheader("Recommended for you")
        render_movie_grid(names, posters, ids, key_prefix="home")


# Details page
def render_details():
    movie_id = st.session_state.selected_movie_id
    movie_title = st.session_state.selected_movie_title

    if st.button("← Back to search"):
        go_home()

    with st.spinner("Loading movie details..."):
        details, error = fetch_movie_details(movie_id)

    if details is None:
        st.error(f"Couldn't load details for this movie from TMDB right now.\n\n{error}")
        st.caption(f"(movie_id used: {movie_id})")
        return

    poster_url = f"{POSTER_BASE}{details['poster_path']}" if details.get("poster_path") else PLACEHOLDER

    col1, col2 = st.columns([1, 3])
    with col1:
        st.image(poster_url, use_container_width=True)
    with col2:
        st.title(details.get("title") or movie_title)
        meta_bits = []
        if details.get("release_date"):
            meta_bits.append(details["release_date"])
        if details.get("genres"):
            meta_bits.append(" ".join(details["genres"]))
        if details.get("runtime"):
            meta_bits.append(f"{details['runtime']} mins")
        st.caption("   ".join(meta_bits))

        if details.get("vote_average") is not None:
            st.subheader(f"User Rating - {details['vote_average']}")

        st.markdown("### Overview")
        st.write(details.get("overview") or "No overview available.")

        st.markdown("### Director")
        st.write(details.get("director", "Unknown"))

    # Starcast
    cast = details.get("cast") or []
    if cast:
        st.markdown("---")
        st.markdown("### Starcast")
        cast_cols = st.columns(len(cast))
        for i, person in enumerate(cast):
            with cast_cols[i]:
                photo = f"{PROFILE_BASE}{person['profile_path']}" if person.get("profile_path") else PLACEHOLDER_FACE
                st.image(photo, use_container_width=True)
                st.caption(f"**{person.get('name', '')}**\n\n{person.get('character', '')}")

    #  Recommendations from this movie 
    st.markdown("---")
    st.markdown("### Recommendations")
    if movie_title in movies["title"].values:
        rec_names, rec_posters, rec_ids = recommend(movie_title)
        render_movie_grid(rec_names, rec_posters, rec_ids, key_prefix="det")
    else:
        st.info("This title isn't in the local recommendation dataset, so similar-movie suggestions aren't available.")

    # Sentiment analysis
    st.markdown("---")
    st.markdown("### 🎭 Review Sentiment Analysis")

    if not SENTIMENT_AVAILABLE:
        st.warning(
            "Sentiment model not found. Run `python train_sentiment_model.py` once to generate "
            "`transform.pkl` and `nlp_model.pkl`, then restart the app."
        )
        st.caption(f"Debug: {SENTIMENT_LOAD_ERROR}")
        return

    with st.spinner("Fetching and analyzing reviews..."):
        reviews, debug_info = get_movie_reviews(movie_id, max_reviews=10)

    if not reviews:
        st.warning(
            "No reviews were available for this movie to analyze right now."
        )
        st.caption(f"Debug: {debug_info}")
        return

    pos_count = 0
    for rev in reviews:
        sentiment = predict_sentiment(rev)
        pos_count += sentiment == "Positive"
        color = "#1DB954" if sentiment == "Positive" else "#E63946"
        snippet = rev if len(rev) <= 600 else rev[:600] + "..."
        st.markdown(
            f"<div style='border-left:4px solid {color}; padding:8px 12px; "
            f"margin-bottom:10px; background-color:#f7f7f7; border-radius:4px;'>"
            f"<b style='color:{color}'>{sentiment}</b><br>{snippet}</div>",
            unsafe_allow_html=True,
        )

    st.info(f"{pos_count} of {len(reviews)} sampled reviews were Positive "
            f"({pos_count / len(reviews) * 100:.0f}%).")

# Router

if st.session_state.page == "home":
    render_home()
else:
    render_details()
