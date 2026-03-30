# # import streamlit as st
# # import pickle
# # import pandas as pd
# # import requests
# #
# # import requests
# #
# # def fetch_poster(movie_id):
# #     url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key=8265bd1679663a7ea12ac168da84d2e8"
# #     try:
# #         response = requests.get(url, timeout=10)   # timeout prevents hanging
# #         response.raise_for_status()                # raises error if status != 200
# #         data = response.json()
# #         poster_path = data.get('poster_path')
# #         if poster_path:
# #             return "https://image.tmdb.org/t/p/w500" + poster_path
# #         return None
# #     except requests.exceptions.RequestException as e:
# #         print("Error fetching poster:", e)
# #         return None
# #
# # def recommend(movie):
# #     movie_index = movies[movies['title']==movie].index[0]
# #     distances = similarity[movie_index]
# #     movies_list=sorted(list(enumerate(distances)), reverse=True, key=lambda x:x[1])[1:6]
# #
# #     recommended_movies = []
# #     recommended_movies_posters=[]
# #
# #     for i in movies_list:
# #         movie_id= movies.iloc[i[0]].movie_id
# #         recommended_movies.append(movies.iloc[i[0]].title)
# #         # Fetch poster from api
# #         recommended_movies_posters.append(fetch_poster(movie_id))
# #     return recommended_movies, recommended_movies_posters
# #
# # similarity = pickle.load(open('similarity.pkl', 'rb'))
# # movies_list = pickle.load(open('movies.pkl', 'rb'))
# # movies_list = movies_list['title']
# # movies= pd.DataFrame(movies_list)
# #
# # st.title("Movie Recommendation System")
# #
# # selected_movie_name = st.selectbox('Select Movie to recommend', movies_list)
# #
# # if st.button('Recommend'):
# #     recommended_movie_names, recommended_movie_posters = recommend(selected_movie_name)
# #     col1, col2, col3, col4, col5 = st.columns(5)
# #
# #     with col1:
# #         st.text(recommended_movie_names[0])
# #         st.image(recommended_movie_posters[0])
# #
# #     with col2:
# #         st.text(recommended_movie_names[1])
# #         st.image(recommended_movie_posters[1])
# #
# #     with col3:
# #         st.text(recommended_movie_names[2])
# #         st.image(recommended_movie_posters[2])
# #
# #     with col4:
# #         st.text(recommended_movie_names[3])
# #         st.image(recommended_movie_posters[3])
# #
# #     with col5:
# #         st.text(recommended_movie_names[4])
# #         st.image(recommended_movie_posters[4])
#
# import streamlit as st
# import pickle
# import pandas as pd
# import requests
#
# # --- Configuration & Setup ---
# st.set_page_config(page_title="Movie Recommender", layout="wide")
#
#
# def fetch_poster(movie_id):
#     url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key=8265bd1679663a7ea12ac168da84d2e8"
#     try:
#         response = requests.get(url, timeout=10)
#         response.raise_for_status()
#         data = response.json()
#         poster_path = data.get('poster_path')
#         if poster_path:
#             return "https://image.tmdb.org/t/p/w500" + poster_path
#         return "https://via.placeholder.com/500x750?text=No+Poster+Found"
#     except Exception:
#         return "https://via.placeholder.com/500x750?text=Error+Loading"
#
#
# def recommend(movie):
#     # Locate the index of the selected movie
#     movie_index = movies[movies['title'] == movie].index[0]
#     distances = similarity[movie_index]
#
#     # Get top 5 similar movies (excluding the movie itself)
#     movies_list_indices = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]
#
#     recommended_movies = []
#     recommended_movies_posters = []
#
#     for i in movies_list_indices:
#         # Get metadata using the index
#         current_movie = movies.iloc[i[0]]
#         movie_id = current_movie.movie_id
#
#         recommended_movies.append(current_movie.title)
#         # Fetch poster from TMDB API
#         recommended_movies_posters.append(fetch_poster(movie_id))
#
#     return recommended_movies, recommended_movies_posters
#
#
# # --- Data Loading ---
# # Ensure these files are in the same directory as your script
# try:
#     movies = pickle.load(open('movies.pkl', 'rb'))
#     similarity = pickle.load(open('similarity.pkl', 'rb'))
#     # Extract titles for the dropdown menu
#     movie_list_titles = movies['title'].values
# except FileNotFoundError:
#     st.error("Pickle files (movies.pkl/similarity.pkl) not found. Please check your file paths.")
#     st.stop()
#
# # --- UI Layout ---
# st.title("🎬 Movie Recommendation System")
#
# selected_movie_name = st.selectbox(
#     'Which movie did you enjoy?',
#     movie_list_titles
# )
#
# if st.button('Show Recommendations'):
#     with st.spinner('Fetching recommendations and posters...'):
#         names, posters = recommend(selected_movie_name)
#
#         # Create 5 columns for the recommendations
#         cols = st.columns(5)
#
#         for index in range(5):
#             with cols[index]:
#                 st.text(names[index])
#                 st.image(posters[index])
import streamlit as st
import pickle
import pandas as pd
import requests
import urllib.parse  # Added for safe URL encoding

# 1. Page Configuration
st.set_page_config(page_title="Movie Recommender", layout="wide")

API_KEY = "8265bd1679663a7ea12ac168da84d2e8"


def fetch_poster(movie_id, movie_title):
    """Fetches poster with enhanced error handling and search fallback."""
    # Clean the title (remove trailing spaces)
    movie_title = movie_title.strip()

    # Attempt 1: Fetch by ID
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            poster_path = data.get('poster_path')
            if poster_path:
                return "https://image.tmdb.org/t/p/w500" + poster_path
    except:
        pass

    # Attempt 2: Fallback Search by Title (Safe Encoding)
    try:
        encoded_title = urllib.parse.quote(movie_title)
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={encoded_title}"
        search_response = requests.get(search_url, timeout=5)
        if search_response.status_code == 200:
            search_data = search_response.json()
            if search_data.get('results'):
                # Loop through results to find the first one with a poster
                for result in search_data['results']:
                    poster_path = result.get('poster_path')
                    if poster_path:
                        return "https://image.tmdb.org/t/p/w500" + poster_path
    except:
        pass

    # Final Fallback: Professional Placeholder
    return "https://via.placeholder.com/500x750?text=Poster+Not+Found"


def recommend(movie):
    movie_index = movies[movies['title'] == movie].index[0]
    distances = similarity[movie_index]
    movies_list_indices = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    recommended_movie_names = []
    recommended_movie_posters = []

    for i in movies_list_indices:
        movie_data = movies.iloc[i[0]]
        title = movie_data.title
        m_id = movie_data.movie_id

        recommended_movie_names.append(title)
        recommended_movie_posters.append(fetch_poster(m_id, title))

    return recommended_movie_names, recommended_movie_posters


# --- Load Data ---
try:
    movies = pickle.load(open('movies.pkl', 'rb'))
    similarity = pickle.load(open('similarity.pkl', 'rb'))
    # Clean the titles in the dataframe to prevent search issues
    movies['title'] = movies['title'].str.strip()
    movie_list = movies['title'].values
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# --- UI ---
st.title("🎬 Movie Recommendation System")

selected_movie = st.selectbox('Type or select a movie:', movie_list)

if st.button('Show Recommendations'):
    with st.spinner('Scanning TMDB database...'):
        names, posters = recommend(selected_movie)

        cols = st.columns(5)
        for i in range(5):
            with cols[i]:
                st.write(f"**{names[i]}**")
                # use_container_width ensures all posters are uniform
                st.image(posters[i], use_container_width=True)