from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/covers'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

# Проверка расширения файла
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def init_db():
    with sqlite3.connect('books.db') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                author TEXT,
                genre TEXT,
                description TEXT,
                cover TEXT
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

# Обработчик для отображения обложек
@app.route('/covers/<filename>')
def get_cover(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)  # Текущая страница
    per_page = 5  # Количество книг на странице
    min_rating = request.args.get('min_rating', type=float)
    
    conn = sqlite3.connect('books.db')
    c = conn.cursor()
    
    # Общее количество книг (для расчета страниц)
    count_query = "SELECT COUNT(*) FROM books"
    c.execute(count_query)
    total_books = c.fetchone()[0]
    total_pages = (total_books + per_page - 1) // per_page
    
    # Запрос для текущей страницы
    query = """
        SELECT 
            b.id, 
            b.title, 
            b.author, 
            b.genre, 
            b.description,
            b.cover,
            AVG(r.rating) as avg_rating
        FROM books b
        LEFT JOIN reviews r ON b.id = r.book_id
        GROUP BY b.id
        HAVING avg_rating >= ? OR ? IS NULL
        ORDER BY b.id DESC
        LIMIT ? OFFSET ?
    """
    
    offset = (page - 1) * per_page
    c.execute(query, (min_rating, min_rating, per_page, offset))
    books = c.fetchall()
    conn.close()
    
    return render_template(
        'index.html', 
        books=books,
        page=page,
        total_pages=total_pages,
        min_rating=min_rating
    )

@app.route('/add', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        genre = request.form['genre']
        description = request.form['description']
        
        # Обработка обложки
        cover_path = None
        if 'cover' in request.files:
            file = request.files['cover']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cover_path = filename
        
        with sqlite3.connect('books.db') as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO books (title, author, genre, description, cover) 
                VALUES (?, ?, ?, ?, ?)
            ''', (title, author, genre, description, cover_path))
        
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
    
    # Исправил запрос с получением среднего рейтинга в деталях
    query = """
        SELECT 
            b.id,
            b.title,
            b.author,
            b.genre,
            b.description,
            b.cover,
            AVG(r.rating) as avg_rating
        FROM books b
        LEFT JOIN reviews r ON b.id = r.book_id
        WHERE b.id = ?
    """
    c.execute(query, (book_id,))
    book = c.fetchone()
    
    c.execute('SELECT review, rating FROM reviews WHERE book_id = ?', (book_id,))
    reviews = c.fetchall()
    
    conn.close()
    return render_template('book_detail.html', book=book, reviews=reviews)

@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    if request.method == 'POST':
        author = request.form.get('author', '').strip()
        genre = request.form.get('genre', '').strip()
        rating = request.form.get('rating', '').strip()
        
        query = '''
            SELECT 
                b.id, 
                b.title, 
                b.author, 
                b.genre, 
                b.cover,
                AVG(r.rating) as avg_rating
            FROM books b
            LEFT JOIN reviews r ON b.id = r.book_id
            WHERE (b.author LIKE ? OR ? = '')
              AND (b.genre LIKE ? OR ? = '')
            GROUP BY b.id
            HAVING (avg_rating >= ? OR ? = '')
        '''
        
        # используем None для пустого рейтинга вместо 0
        rating_value = float(rating) if rating else None
        
        conn = sqlite3.connect('books.db')
        c = conn.cursor()
        c.execute(query, (
            f'%{author}%', author, 
            f'%{genre}%', genre, 
            rating_value, rating if rating else ''
        ))
        results = c.fetchall()
        conn.close()
    
    return render_template('search.html', results=results)



if __name__ == '__main__':
    init_db()
    app.run(debug=True)