import pandas as pd
import ast

# =========================
# LOAD FILES
# =========================
movies = pd.read_csv("tmdb_5000_movies.csv")
credits = pd.read_csv("tmdb_5000_credits.csv")

# =========================
# CLEAN COLUMN NAMES
# =========================
movies.columns = movies.columns.str.strip()
credits.columns = credits.columns.str.strip()

# =========================
# FIX ID COLUMN
# =========================
credits.rename(columns={"movie_id": "id"}, inplace=True)

# =========================
# MERGE DATA
# =========================
movies = movies.merge(credits, on="id")

# =========================
# FIX TITLE COLUMN (IMPORTANT)
# =========================
if "title_x" in movies.columns:
    movies.rename(columns={"title_x": "title"}, inplace=True)

# Remove duplicate title column
if "title_y" in movies.columns:
    movies.drop(columns=["title_y"], inplace=True)

# =========================
# CLEAN GENRES
# =========================
def clean_genres(text):
    try:
        data = ast.literal_eval(text)
        return "|".join([i["name"] for i in data])
    except:
        return "Unknown"

movies["genres"] = movies["genres"].apply(clean_genres)

# =========================
# EXTRACT DIRECTOR
# =========================
def get_director(text):
    try:
        data = ast.literal_eval(text)
        for i in data:
            if i["job"] == "Director":
                return i["name"]
    except:
        pass
    return "Unknown"

movies["director"] = movies["crew"].apply(get_director)

# =========================
# EXTRACT TOP CAST
# =========================
def get_cast(text):
    try:
        data = ast.literal_eval(text)
        names = [i["name"] for i in data[:3]]
        return ", ".join(names)
    except:
        return "Unknown"

movies["cast"] = movies["cast"].apply(get_cast)

# =========================
# EXTRACT YEAR
# =========================
movies["year"] = pd.to_datetime(
    movies["release_date"], errors="coerce"
).dt.year

# =========================
# CLEAN OVERVIEW
# =========================
movies["overview"] = movies["overview"].fillna("No description available")

# =========================
# FINAL DATASET
# =========================
final = movies[
    ["title", "genres", "year", "vote_average", "director", "cast", "overview"]
]

# =========================
# SAVE FILE
# =========================
final.to_csv("final_movies.csv", index=False)

print("✅ final_movies.csv created successfully!")