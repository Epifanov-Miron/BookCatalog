from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

def init_db():
    with sqlite3.connect('books.db') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                author TEXT,
                genre TEXT,
                description TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                review TEXT,
                rating INTEGER,
                FOREIGN KEY(book_id) REFERENCES books(id)
            )
        ''')

@app.route('/')
def index():
    min_rating = request.args.get('min_rating', type=float)
    
    conn = sqlite3.connect('books.db')
    c = conn.cursor()
    
    query = """
        SELECT 
            b.id, 
            b.title, 
            b.author, 
            b.genre, 
            b.description,
            AVG(r.rating) as avg_rating
        FROM books b
        LEFT JOIN reviews r ON b.id = r.book_id
        GROUP BY b.id
        HAVING avg_rating >= ? OR ? IS NULL
    """
    
    c.execute(query, (min_rating, min_rating))
    books = c.fetchall()
    conn.close()
    
    return render_template('index.html', books=books)

@app.route('/add', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        genre = request.form['genre']
        description = request.form['description']
        with sqlite3.connect('books.db') as conn:
            c = conn.cursor()
            c.execute('INSERT INTO books (title, author, genre, description) VALUES (?, ?, ?, ?)',
                      (title, author, genre, description))
        return redirect(url_for('index'))
    return render_template('add_book.html')

@app.route('/book/<int:book_id>', methods=['GET', 'POST'])
def book_detail(book_id):
    conn = sqlite3.connect('books.db')
    c = conn.cursor()
    if request.method == 'POST':
        review = request.form['review']
        rating = int(request.form['rating'])
        c.execute('INSERT INTO reviews (book_id, review, rating) VALUES (?, ?, ?)',
                  (book_id, review, rating))
        conn.commit()
    c.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = c.fetchone()
    c.execute('SELECT review, rating FROM reviews WHERE book_id = ?', (book_id,))
    reviews = c.fetchall()
    conn.close()
    return render_template('book_detail.html', book=book, reviews=reviews)

@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    if request.method == 'POST':
        author = request.form['author']
        genre = request.form['genre']
        rating = request.form['rating']
        query = '''
            SELECT b.id, b.title, b.author, b.genre, AVG(r.rating) as avg_rating
            FROM books b
            LEFT JOIN reviews r ON b.id = r.book_id
            WHERE (b.author LIKE ? OR ? = '')
              AND (b.genre LIKE ? OR ? = '')
            GROUP BY b.id
            HAVING (avg_rating >= ? OR ? = '')
        '''
        rating_value = float(rating) if rating else 0
        conn = sqlite3.connect('books.db')
        c = conn.cursor()
        c.execute(query, (f'%{author}%', author, f'%{genre}%', genre, rating_value, rating))
        results = c.fetchall()
        conn.close()
    return render_template('search.html', results=results)



if __name__ == '__main__':
    init_db()
    app.run(debug=True)