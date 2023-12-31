from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_from_directory,
    jsonify,
)
from flask_cors import CORS
from werkzeug.utils import secure_filename
from flask import g
import os, requests, random, sqlite3


# A03:2021 – Injection
DATABASE = "database.db"

# A04:2021 – Insecure Design
ALLOWED_EXTENSIONS = set(
    [
        "txt",
        "pdf",
        "png",
        "jpg",
        "jpeg",
        "gif",
        "exe",
        "bat",
        "sh",
        "md",
        "json",
        "yml",
        "yaml",
    ]
)
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
# Misconfigure CORS to allow all domains
CORS(app)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.secret_key = "your_secret_key"  # Change this to a random secret key


def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        # Create table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS books
                          (id INTEGER PRIMARY KEY, title TEXT, author TEXT)"""
        )

        random_integer = random.randint(1, 10000)
        # Insert sample data
        cursor.execute(
            "INSERT INTO books (title, author) VALUES (?, ?)",
            (f"Book One {random_integer}", f"Author A {random_integer}"),
        )
        cursor.execute(
            "INSERT INTO books (title, author) VALUES (?, ?)",
            (f"Book Two {random_integer}", f"Author B {random_integer}"),
        )
        cursor.execute(
            "INSERT INTO books (title, author) VALUES (?, ?)",
            (f"Book Three {random_integer}", f"Author C {random_integer}"),
        )

        db.commit()


@app.route("/")
def home():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    else:
        return "Welcome to the Vulnerable App!"


# Cross-Domain Misconfiguration
@app.route("/api/data")
def public_api():
    return jsonify({"message": "This is public data accessible from any domain"})


# A07:2021 – Identification and Authentication Failures
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        users = ["admin", "user"]
        # Insecure authentication check
        if username in users and password == "admin":
            session["logged_in"] = True
            return redirect(url_for("home"))
        else:
            return "Invalid Credentials"
    return render_template("login.html")


# A03:2021 – Injection
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@app.route("/search", methods=["GET", "POST"])
def search():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        search_query = request.form["query"]
        db = get_db()
        cursor = db.cursor()

        # Vulnerable SQL query
        query = f"SELECT * FROM books WHERE title LIKE '%{search_query}%'"
        cursor.execute(query)
        results = cursor.fetchall()

        if len(results) == 0:
            # XSS RREFLECTION
            return f"no matches found with {search_query}"

        return render_template("search_results.html", results=results)

    return render_template("search.html")


# A04:2021 – Insecure Design
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# route to upload
@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        # Check if the post request has the file part
        if "file" not in request.files:
            return redirect(request.url)
        file = request.files["file"]
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == "":
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            return redirect(url_for("uploaded_file", filename=filename))

    return render_template("upload.html")


# route to display files
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# A01:2021 – Broken Access Control
@app.route("/admin")
def admin_panel():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # Insecure Access Control: All logged-in users can access this page
    return "Admin Panel: Here you can manage the application settings."


# A05:2021 – Security Misconfiguration
@app.route("/error")
def error():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # Intentionally cause an error
    return 1 / 0  # This will cause a ZeroDivisionError


# A08:2021 – Software and Data Integrity Failures
@app.route("/external-config")
def external_config():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # Fetching data from an external source without verifying its integrity
    response = requests.get(
        "https://universalis.app/api/Famfrit/4745?entriesToReturn=10"
    )
    config_data = response.json()

    return render_template("external_config.html", config_data=config_data)


# A10:2021 – Server-Side Request Forgery (SSRF)
@app.route("/fetch-data", methods=["GET", "POST"])
def fetch_data():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        url = request.form["url"]

        # Check if the URL starts with http:// or https://, prepend https:// if not
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # Vulnerable to SSRF: Fetching data from a user-provided URL without validation
        response = requests.get(url)
        return response.text

    return render_template("fetch_data.html")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", debug=True)
