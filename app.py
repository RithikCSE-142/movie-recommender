from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd
import requests
import sqlite3
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__, static_folder='static')

API_KEY = "aa92a819865e110c56447aed38088de8"

# =========================
# LOAD DATA (SAFE VERSION)
# =========================
movies = pd.read_csv("final_movies.csv")

# TEXT COLUMNS
movies["title"] = movies["title"].fillna("Unknown")
movies["genres"] = movies["genres"].fillna("Unknown")
movies["director"] = movies["director"].fillna("Unknown")
movies["cast"] = movies["cast"].fillna("Unknown")
movies["overview"] = movies["overview"].fillna("No description available")

# NUMERIC COLUMNS (FIXED ERROR HERE)
movies["year"] = pd.to_numeric(movies["year"], errors="coerce").fillna(0)
movies["vote_average"] = pd.to_numeric(movies["vote_average"], errors="coerce").fillna(0)

# =========================
# CREATE TAGS (AI MODEL)
# =========================
movies["tags"] = (
    movies["genres"] + " " +
    movies["director"] + " " +
    movies["cast"] + " " +
    movies["overview"]
)

cv = CountVectorizer(max_features=5000, stop_words="english")
vectors = cv.fit_transform(movies["tags"]).toarray()

similarity = cosine_similarity(vectors)

# =========================
# DATABASE (WATCHLIST)
# =========================
conn = sqlite3.connect("watchlist.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT
)
""")
conn.commit()

# =========================
# GET POSTER
# =========================
def get_poster(title, year=None):
    try:
        url = "https://api.themoviedb.org/3/search/movie"
        params = {
            "api_key": API_KEY,
            "query": title
        }

        if year and year != 0:
            params["year"] = int(year)

        response = requests.get(url, params=params)
        data = response.json()

        if data.get("results"):

            # 🔥 Try to find best match
            for movie in data["results"]:
                if movie.get("poster_path"):
                    return "https://image.tmdb.org/t/p/w500" + movie["poster_path"]

    except:
        pass

    return "/static/default.jpg"

# =========================
# AI RECOMMENDATION
# =========================
def recommend(movie_name):

    import re

    # -------------------------
    # 🔍 Extract year
    # -------------------------
    movie_name = movie_name.lower().strip()

    year_match = re.search(r"(19|20)\d{2}", movie_name)
    year = None

    if year_match:
        year = int(year_match.group())
        movie_name = movie_name.replace(str(year), "").strip()

    # -------------------------
    # 🎬 Normalize
    # -------------------------
    movies["title"] = movies["title"].astype(str).str.lower().str.strip()

    # -------------------------
    # 🔥 Find movie
    # -------------------------
    if year:
        df = movies[
            (movies["title"].str.contains(movie_name, na=False)) &
            (movies["year"] == year)
        ]
    else:
        df = movies[movies["title"].str.contains(movie_name, na=False)]

    if df.empty:
        recs = movies.sort_values(by="vote_average", ascending=False).head(5)

    else:
        selected = df.iloc[0]

        # 🔥 USE ALL GENRES
        selected_genres = set(str(selected["genres"]).split("|"))

        movies["score"] = 0

        # -------------------------
        # 🎯 GENRE MATCH (STRONG)
        # -------------------------
        def genre_score(row):
            movie_genres = set(str(row["genres"]).split("|"))
            return len(selected_genres & movie_genres)

        movies["score"] += movies.apply(genre_score, axis=1) * 3

        # -------------------------
        # 🎭 CAST MATCH
        # -------------------------
        selected_cast = str(selected["cast"]).split(", ")

        def cast_score(row):
            movie_cast = str(row["cast"]).split(", ")
            return len(set(selected_cast) & set(movie_cast))

        movies["score"] += movies.apply(cast_score, axis=1) * 2

        # -------------------------
        # 🎬 DIRECTOR MATCH
        # -------------------------
        movies.loc[
            movies["director"] == selected["director"],
            "score"
        ] += 4

        # -------------------------
        # ⭐ RATING (LOW WEIGHT)
        # -------------------------
        movies["score"] += movies["vote_average"] * 0.3

        # remove same movie
        recs = movies[movies["title"] != selected["title"]]

        recs = recs.sort_values(by="score", ascending=False).head(5)

    # -------------------------
    # 📦 OUTPUT
    # -------------------------
    results = []

    for _, row in recs.iterrows():
        results.append({
            "title": str(row["title"]).title(),
            "poster": get_poster(row["title"], row["year"]),
            "rating": float(row["vote_average"]),
            "year": int(row["year"]),
            "genre": row["genres"].replace("|", " • "),
            "overview": row["overview"],
            "cast": row["cast"],
            "director": row["director"]
        })

    return results

# =========================
# ROUTES
# =========================
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        movie = request.form.get("movie", "").strip()
        return redirect(url_for("results", movie=movie))
    return render_template("index.html")


@app.route("/results")
def results():
    movie_name = request.args.get("movie", "")
    recs = recommend(movie_name)
    selected_movie = recs[0] if recs else None

    return render_template(
        "results.html",
        recs=recs,
        selected=selected_movie,
        search_value=movie_name
    )

# =========================
# WATCHLIST API
# =========================
@app.route("/add_watchlist", methods=["POST"])
def add_watchlist():
    title = request.json.get("title")
    cursor.execute("INSERT INTO watchlist (title) VALUES (?)", (title,))
    conn.commit()
    return jsonify({"status": "added"})


@app.route("/get_watchlist")
def get_watchlist():
    cursor.execute("SELECT title FROM watchlist")
    data = cursor.fetchall()
    return jsonify([i[0] for i in data])

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
