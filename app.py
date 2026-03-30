import streamlit as st
import pickle
import pandas as pd
import requests
import urllib.parse

st.set_page_config(page_title="Movie Recommender", layout="wide")

API_KEY = "8265bd1679663a7ea12ac168da84d2e8"


def fetch_poster(movie_id, movie_title):
    """The most robust poster fetcher: ID -> Search -> Placeholder."""
    movie_title = movie_title.strip()

    # 1. Try Fetching by ID
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            path = response.json().get('poster_path')
            if path:
                return f"https://image.tmdb.org/t/p/w500{path}"
    except:
        pass

    # 2. Try Search by Title (Handling common names like 'The Signal')
    try:
        encoded_title = urllib.parse.quote(movie_title)
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={encoded_title}"
        search_res = requests.get(search_url, timeout=5)
        if search_res.status_code == 200:
            results = search_res.json().get('results', [])
            for movie in results:
                path = movie.get('poster_path')
                if path:
                    return f"https://image.tmdb.org/t/p/w500{path}"
    except:
        pass

    # 3. Final Fallback: If TMDB has absolutely no image, use a valid URL placeholder
    # This prevents the "Broken Icon" from ever appearing.
    return "https://via.placeholder.com/500x750.png?text=No+Poster+Available"


def recommend(movie):
    movie_index = movies[movies['title'] == movie].index[0]
    distances = similarity[movie_index]
    movies_list_indices = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    recommended_names = []
    recommended_posters = []

    for i in movies_list_indices:
        m_data = movies.iloc[i[0]]
        recommended_names.append(m_data.title)
        # Pass ID and Title to the enhanced fetcher
        recommended_posters.append(fetch_poster(m_data.movie_id, m_data.title))

    return recommended_names, recommended_posters


# --- Load Data ---
try:
    movies = pickle.load(open('movies.pkl', 'rb'))
    similarity = pickle.load(open('similarity.pkl', 'rb'))
    movies['title'] = movies['title'].str.strip()
    movie_list = movies['title'].values
except Exception as e:
    st.error(f"File Error: {e}")
    st.stop()

# --- UI ---
st.title("🎬 Movie Recommendation System")

selected_movie = st.selectbox('Type or select a movie:', movie_list)

if st.button('Show Recommendations'):
    with st.spinner('Fetching recommendations...'):
        names, posters = recommend(selected_movie)

        cols = st.columns(5)
        for i in range(5):
            with cols[i]:
                st.write(f"**{names[i]}**")
                # use_container_width=True is the updated version of use_column_width
                st.image(posters[i], use_container_width=True)