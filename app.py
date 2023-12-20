from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from flask import g
import random

DATABASE = 'database.db'


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a random secret key

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        # Create table
        cursor.execute('''CREATE TABLE IF NOT EXISTS books
                          (id INTEGER PRIMARY KEY, title TEXT, author TEXT)''')

        random_integer = random.randint(1, 10000)
        # Insert sample data
        cursor.execute("INSERT INTO books (title, author) VALUES (?, ?)",
                       (f'Book One {random_integer}', f'Author A {random_integer}'))
        cursor.execute("INSERT INTO books (title, author) VALUES (?, ?)",
                       (f'Book Two {random_integer}', f'Author B {random_integer}'))
        cursor.execute("INSERT INTO books (title, author) VALUES (?, ?)",
                       (f'Book Three {random_integer}', f'Author C {random_integer}'))

        db.commit()

@app.route('/')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    else:
        return "Welcome to the Vulnerable App!"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Vulnerable to A07:2021 – Identification and Authentication Failures
        username = request.form['username']
        password = request.form['password']
        # Insecure authentication check
        if username == 'admin' and password == 'admin':
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            return "Invalid Credentials"
    return render_template('login.html')


# A03:2021 – Injection
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/search', methods=['GET', 'POST'])
def search():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        search_query = request.form['query']
        db = get_db()
        cursor = db.cursor()

        # Vulnerable SQL query
        query = f"SELECT * FROM books WHERE title LIKE '%{search_query}%'"
        cursor.execute(query)
        results = cursor.fetchall()

        if len(results) == 0:
            # XSS RREFLECTION
            return f"no matches found with {search_query}"

        return render_template('search_results.html', results=results)
    
    return render_template('search.html')


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
