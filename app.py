from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

# ===== MySQL Logging Imports =====
import time
from functools import wraps
import mysql.connector

app = Flask(__name__)
DB_PATH = "db/books_writable.db"

# ---- MongoDB Setup ----
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB = os.getenv("MONGO_DB", "book_reviews_db")
MONGO_REVIEWS_COLLECTION = os.getenv("MONGO_REVIEWS_COLLECTION", "reviews")

reviews_col = None

try:
    print("Connecting to MongoDB at:", MONGO_URI)
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    mongo_client.server_info()  # test the connection
    mongo_db = mongo_client[MONGO_DB]
    reviews_col = mongo_db[MONGO_REVIEWS_COLLECTION]
    print("Connected to MongoDB successfully!")
except Exception as e:
    print("MongoDB connection failed:", e)
    reviews_col = None

# ===== MySQL Logging Helpers =====
import time
from functools import wraps
import mysql.connector

def _get_mysql_conn():
    """Create a short-lived MySQL connection for logging."""
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DB", "books"),
            autocommit=True,
        )
        return conn
    except Exception as e:
        print("▲ MySQL logging connection failed:", e)
        return None

def write_log(function_name: str, status: str,
              execution_time_ms=None,
              error_message=None):
    """Insert a log row; fail silently if MySQL not available."""
    conn = _get_mysql_conn()
    if not conn:
        return
    cur = None
    try:
        cur = conn.cursor()
        # Ensure table exists (only if not already created)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                function_name VARCHAR(128),
                status ENUM('success','error') NOT NULL,
                execution_time_ms INT NULL,
                error_message VARCHAR(255) NULL
            )
        """)
        cur.execute(
            """
            INSERT INTO logs (function_name, status, execution_time_ms, error_message)
            VALUES (%s, %s, %s, %s)
            """,
            (function_name, status, execution_time_ms, error_message),
        )
    except Exception as e:
        print("▲ MySQL write_log failed:", e)
    finally:
        try:
            if cur: cur.close()
            conn.close()
        except Exception:
            pass
def log_timed(fn):
    """Logs success with execution time; logs error (no time) for HTTP >=400 or exceptions."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        t1 = time.perf_counter()
        try:
            rv = fn(*args, **kwargs)

            # --- figure out the HTTP status code ---
            try:
                from flask import Response
                if isinstance(rv, Response):
                    status_code = rv.status_code
                elif isinstance(rv, tuple) and len(rv) >= 2:
                    status_code = rv[1]
                else:
                    status_code = 200
            except Exception:
                status_code = 200

            # --- log based on status ---
            if int(status_code) >= 400:
                # error: skip execution_time_ms as required
                write_log(fn.__name__, "error", None, f"HTTP {status_code}")
            else:
                exec_ms = int((time.perf_counter() - t1) * 1000)
                write_log(fn.__name__, "success", exec_ms, None)

            return rv
        except Exception as e:
            # real exception = error, no execution_time_ms
            write_log(fn.__name__, "error", None, str(e)[:240])
            raise
    return wrapper

# SQLite Helper Function ------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn



# Flask Routes -------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/books")
@log_timed
def get_books():
    conn = get_db()
    books = conn.execute("SELECT * FROM Books ORDER BY book_id DESC").fetchall()
    conn.close()
    return jsonify([dict(b) for b in books])


@app.route("/api/add_book", methods=["POST"])
@log_timed
def add_book():
    data = request.get_json()
    title = data.get("title")
    author = data.get("author")
    year = data.get("publication_year")
    image = data.get("image_url")

    if not title or not author:
        return jsonify({"error": "Title and author are required"}), 400

    conn = get_db()
    conn.execute(
        "INSERT INTO Books (title, author, publication_year, image_url) VALUES (?, ?, ?, ?)",
        (title, author, year, image)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Book added successfully"})


@app.route("/api/search")
@log_timed
def search_books():
    q = request.args.get("q", "").lower()
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM Books WHERE LOWER(title) LIKE ? OR LOWER(author) LIKE ?",
        (f"%{q}%", f"%{q}%")
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ======== MongoDB Review Endpoints =============


@app.route("/api/reviews", methods=["GET"])
@log_timed
def get_reviews():
    if reviews_col is None:
        return jsonify({"error": "MongoDB connection failed"}), 500

    book_id = request.args.get("book_id")
    query = {}
    if book_id:
        query["book_id"] = book_id

    try:
        docs = list(reviews_col.find(query).sort("created_at", -1))
        reviews = []
        for d in docs:
            reviews.append({
                "id": str(d.get("_id")),
                "book_id": d.get("book_id"),
                "reviewer": d.get("reviewer"),
                "review_text": d.get("review_text"),
                "rating": d.get("rating"),
                "created_at": d.get("created_at").isoformat() if d.get("created_at") else None
            })
        return jsonify(reviews)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch reviews: {e}"}), 500


@app.route("/api/add_review", methods=["POST"])
@log_timed
def add_review():
    if reviews_col is None:
        return jsonify({"error": "MongoDB connection failed"}), 500

    data = request.get_json() or {}
    review = {
        "book_id": str(data.get("book_id") or "").strip(),
        "reviewer": data.get("reviewer") or "Anonymous",
        "review_text": data.get("review_text") or "",
        "rating": int(data.get("rating") or 0),
        "created_at": datetime.utcnow()
    }

    if not review["book_id"] or not review["review_text"]:
        return jsonify({"error": "Book ID and review text are required"}), 400

    try:
        result = reviews_col.insert_one(review)
        return jsonify({"message": "Review added successfully", "id": str(result.inserted_id)})
    except Exception as e:
        print("Error inserting review:", e)
        return jsonify({"error": f"Failed to add review: {e}"}), 500

# ---------- Run Flask App ----------

if __name__ == "__main__":
    app.run(debug=True, port=5001)