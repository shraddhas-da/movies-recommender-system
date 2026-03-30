# 🎬 Movie Recommender System

A content-based movie recommendation system built with **Streamlit**, **Pandas**, and **Scikit-Learn**. This app suggests five similar movies based on a user's selection using a cosine similarity matrix.

---

## 🚀 Features
* **Search Functionality:** Select or type a movie from a database of 5,000+ titles.
* **Poster Fetching:** Real-time poster retrieval using the **TMDB API**.
* **Smart Fallback:** If a poster isn't found via ID, the system automatically searches by title or provides a professional placeholder.
* **Interactive UI:** A clean, responsive dashboard built with Streamlit.

---

## 🛠️ Installation & Setup

### 1. Clone the Repository
Ensure you have [Git LFS](https://git-lfs.github.com/) installed so the large `.pkl` files download correctly:

```bash
git clone [https://github.com/shraddhas-da/movies-recommender-system.git](https://github.com/shraddhas-da/movies-recommender-system.git)
cd movies-recommender-system
git lfs pull

# Create the environment
python -m venv .venv

# Activate on Windows:
.venv\Scripts\activate

# Activate on Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt

streamlit run app.py
