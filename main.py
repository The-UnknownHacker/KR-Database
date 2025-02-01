from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import mimetypes
from functools import wraps
import secrets

app = Flask(__name__)
app.config.from_object('config.Config')
app.config['TAILWIND_DARK_MODE'] = 'class'

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Categories and upload settings
CATEGORIES = ['Basics','Geethams','Swarajathis','Varnams','Keerthanas','Bhajans','Thillanas','Notes','Archived','Ragam Alapanas','Thyaagaraja Pancharatnas','Other']
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav'}
ALLOWED_PDF_EXTENSIONS = {'pdf'}

# Create upload directories
for category in CATEGORIES:
    category_path = os.path.join(UPLOAD_FOLDER, category)
    if not os.path.exists(category_path):
        os.makedirs(category_path)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_teacher = db.Column(db.Boolean, default=False)
    songs = db.relationship('Song', backref='user', lazy=True)
    notations = db.relationship('Notation', backref='user', lazy=True)

    def get_teacher_status(self):
        return self.is_teacher

class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    composer = db.Column(db.String(200), nullable=False)
    ragam = db.Column(db.String(100), nullable=False)
    talam = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    kalpanaswaram = db.Column(db.Boolean, default=False)
    audio_file = db.Column(db.String(500))
    notation_file = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Notation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class OtherFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))  # To store file extension/type
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper functions
def allowed_audio_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

def allowed_pdf_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_PDF_EXTENSIONS

# Routes
@app.route('/')
def index():
    return redirect(url_for('get_songs'))

@app.route('/songs')
@app.route('/songs/<category>')
@login_required
def get_songs(category=None):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
        
    if category:
        if category not in CATEGORIES:
            flash('Invalid category')
            return redirect(url_for('get_songs'))
        songs = Song.query.filter_by(category=category).all()
        return render_template('songs/category.html', songs=songs, category=category)
    
    # Show folders view for both teachers and students
    return render_template('songs/folders.html', categories=CATEGORIES)

@app.route('/songs/create', methods=['GET', 'POST'])
@login_required
def create_song():
    if not current_user.get_teacher_status():
        flash('Unauthorized access')
        return redirect(url_for('get_songs'))
        
    if request.method == 'POST':
        category = request.form.get('category')
        if category not in CATEGORIES:
            flash('Invalid category')
            return redirect(url_for('get_songs'))
            
        audio_file = request.files.get('audio_file')
        audio_path = None
        if audio_file and audio_file.filename and allowed_audio_file(audio_file.filename):
            audio_filename = secure_filename(audio_file.filename)
            audio_path = os.path.join(category, audio_filename)
            audio_file.save(os.path.join(UPLOAD_FOLDER, audio_path))
            
        song = Song(
            name=request.form['name'],
            composer=request.form['composer'],
            ragam=request.form['ragam'],
            talam=request.form['talam'],
            category=category,
            kalpanaswaram='kalpanaswaram' in request.form,
            audio_file=f'/static/uploads/{audio_path}' if audio_path else None,
            created_by=current_user.id
        )
        
        db.session.add(song)
        db.session.commit()
        flash('Song added successfully')
        return redirect(url_for('get_songs', category=category))
            
    return render_template('songs/create.html', categories=CATEGORIES)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('get_songs'))
        
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('get_songs'))
        flash('Invalid username or password')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check if username or email already exists
        if User.query.filter_by(username=request.form['username']).first():
            flash('Username already exists')
            return render_template('auth/register.html')
            
        if User.query.filter_by(email=request.form['email']).first():
            flash('Email already exists')
            return render_template('auth/register.html')
            
        user = User(
            username=request.form['username'],
            email=request.form['email'],
            is_teacher=False  # Explicitly set to False for new users
        )
        user.password_hash = generate_password_hash(request.form['password'])
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except:
            db.session.rollback()
            flash('An error occurred. Please try again.')
            
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/songs/<category>/<int:song_id>/add-notation', methods=['GET', 'POST'])
@login_required
def add_notation(category, song_id):
    if not current_user.get_teacher_status():
        flash('Unauthorized access')
        return redirect(url_for('get_songs'))
        
    song = Song.query.get_or_404(song_id)
    if song.category != category:
        return redirect(url_for('get_songs'))
        
    if request.method == 'POST':
        notation_file = request.files.get('notation_file')
        if notation_file and notation_file.filename and allowed_pdf_file(notation_file.filename):
            notation_filename = secure_filename(notation_file.filename)
            notation_path = os.path.join(category, notation_filename)
            notation_file.save(os.path.join(UPLOAD_FOLDER, notation_path))
            
            song.notation_file = f'/static/uploads/{notation_path}'
            db.session.commit()
            flash('Notation added successfully')
            return redirect(url_for('get_songs', category=category))
            
    return render_template('songs/add_notation.html', song=song, category=category)

@app.route('/notations')
@app.route('/notations/<category>')
@login_required
def get_notations(category=None):
    if category:
        if category not in CATEGORIES:
            flash('Invalid category')
            return redirect(url_for('get_notations'))
        notations = Notation.query.filter_by(category=category).all()
        return render_template('notations/category.html', notations=notations, category=category)
    
    return render_template('notations/folders.html', categories=CATEGORIES)

@app.route('/notations/<category>/upload', methods=['GET', 'POST'])
@login_required
def upload_notation(category):
    if not current_user.get_teacher_status():
        flash('Unauthorized access')
        return redirect(url_for('get_notations'))
        
    if category not in CATEGORIES:
        flash('Invalid category')
        return redirect(url_for('get_notations'))
        
    if request.method == 'POST':
        notation_file = request.files.get('notation_file')
        if notation_file and notation_file.filename and allowed_pdf_file(notation_file.filename):
            notation_filename = secure_filename(notation_file.filename)
            notation_path = os.path.join(category, notation_filename)
            notation_file.save(os.path.join(UPLOAD_FOLDER, notation_path))
            
            notation = Notation(
                title=request.form['title'],
                category=category,
                file_path=f'/static/uploads/{notation_path}',
                created_by=current_user.id
            )
            
            db.session.add(notation)
            db.session.commit()
            flash('Notation uploaded successfully')
            return redirect(url_for('get_notations', category=category))
            
    return render_template('notations/upload.html', category=category)

@app.route('/songs/<int:song_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_song(song_id):
    if not current_user.get_teacher_status():
        flash('Unauthorized access')
        return redirect(url_for('get_songs'))
        
    song = Song.query.get_or_404(song_id)
    if request.method == 'POST':
        song.name = request.form['name']
        song.composer = request.form['composer']
        song.ragam = request.form['ragam']
        song.talam = request.form['talam']
        song.category = request.form['category']
        song.kalpanaswaram = 'kalpanaswaram' in request.form
        
        audio_file = request.files.get('audio_file')
        if audio_file and audio_file.filename and allowed_audio_file(audio_file.filename):
            audio_filename = secure_filename(audio_file.filename)
            audio_path = os.path.join(song.category, audio_filename)
            audio_file.save(os.path.join(UPLOAD_FOLDER, audio_path))
            song.audio_file = f'/static/uploads/{audio_path}'
            
        db.session.commit()
        flash('Song updated successfully')
        return redirect(url_for('get_songs', category=song.category))
        
    return render_template('songs/edit.html', song=song, categories=CATEGORIES)

@app.route('/files')
@app.route('/files/<category>')
@login_required
def get_files(category=None):
    if category:
        if category not in CATEGORIES:
            flash('Invalid category')
            return redirect(url_for('get_files'))
        files = OtherFile.query.filter_by(category=category).all()
        return render_template('files/category.html', files=files, category=category)
    return render_template('files/folders.html', categories=CATEGORIES)

@app.route('/files/<category>/upload', methods=['GET', 'POST'])
@login_required
def upload_file(category):
    if not current_user.get_teacher_status():
        flash('Unauthorized access')
        return redirect(url_for('get_files'))
        
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(category, filename)
            file.save(os.path.join(UPLOAD_FOLDER, file_path))
            
            other_file = OtherFile(
                title=request.form['title'],
                description=request.form.get('description', ''),
                category=category,
                file_path=f'/static/uploads/{file_path}',
                file_type=filename.rsplit('.', 1)[1].lower(),
                created_by=current_user.id
            )
            
            db.session.add(other_file)
            db.session.commit()
            flash('File uploaded successfully')
            return redirect(url_for('get_files', category=category))
            
    return render_template('files/upload.html', category=category)

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'status': 'error', 'message': 'No API key provided'}), 401
            
        if api_key != app.config['API_KEY']:
            return jsonify({'status': 'error', 'message': 'Invalid API key'}), 401
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/songs')
@require_api_key
def api_get_songs():
    """API endpoint to get all songs with their details"""
    songs = Song.query.all()
    songs_list = []
    
    for song in songs:
        songs_list.append({
            'id': song.id,
            'name': song.name,
            'composer': song.composer,
            'ragam': song.ragam,
            'talam': song.talam,
            'category': song.category,
            'has_kalpanaswaram': song.kalpanaswaram,
            'has_audio': bool(song.audio_file),
            'has_notation': bool(song.notation_file),
            'created_at': song.created_at.isoformat()
        })
    
    return jsonify({
        'status': 'success',
        'songs': songs_list
    })

@app.route('/api/songs/<int:song_id>')
@require_api_key
def api_get_song(song_id):
    """API endpoint to get details of a specific song"""
    song = Song.query.get_or_404(song_id)
    
    song_data = {
        'id': song.id,
        'name': song.name,
        'composer': song.composer,
        'ragam': song.ragam,
        'talam': song.talam,
        'category': song.category,
        'has_kalpanaswaram': song.kalpanaswaram,
        'has_audio': bool(song.audio_file),
        'has_notation': bool(song.notation_file),
        'created_at': song.created_at.isoformat()
    }
    
    return jsonify({
        'status': 'success',
        'song': song_data
    })

@app.route('/api/songs/<int:song_id>/audio')
@require_api_key
def api_get_song_audio(song_id):
    """API endpoint to get the audio file for a song"""
    song = Song.query.get_or_404(song_id)
    
    if not song.audio_file:
        return jsonify({
            'status': 'error',
            'message': 'No audio file available for this song'
        }), 404
    
    file_path = os.path.join(app.root_path, 'static', song.audio_file.lstrip('/static/'))
    
    if not os.path.exists(file_path):
        return jsonify({
            'status': 'error',
            'message': 'Audio file not found'
        }), 404
    
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = 'application/octet-stream'
    
    return send_file(
        file_path,
        mimetype=mime_type,
        as_attachment=False,
        download_name=os.path.basename(file_path)
    )

@app.route('/api/songs/<int:song_id>/notation')
@require_api_key
def api_get_song_notation(song_id):
    """API endpoint to get the notation file for a song"""
    song = Song.query.get_or_404(song_id)
    
    if not song.notation_file:
        return jsonify({
            'status': 'error',
            'message': 'No notation file available for this song'
        }), 404
    
    file_path = os.path.join(app.root_path, 'static', song.notation_file.lstrip('/static/'))
    
    if not os.path.exists(file_path):
        return jsonify({
            'status': 'error',
            'message': 'Notation file not found'
        }), 404
    
    return send_file(
        file_path,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=os.path.basename(file_path)
    )

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.username == 'admin':
            flash('Unauthorized access')
            return redirect(url_for('get_songs'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    users = User.query.all()
    return render_template('admin/dashboard.html', users=users)

@app.route('/admin/toggle-teacher/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_teacher_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.username != 'admin':  # Prevent modifying admin's status
        user.is_teacher = not user.is_teacher
        db.session.commit()
        flash(f"Teacher status updated for {user.username}")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/create-user', methods=['POST'])
@login_required
@admin_required
def create_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    is_teacher = 'is_teacher' in request.form
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists')
        return redirect(url_for('admin_dashboard'))
        
    if User.query.filter_by(email=email).first():
        flash('Email already exists')
        return redirect(url_for('admin_dashboard'))
        
    user = User(
        username=username,
        email=email,
        is_teacher=is_teacher
    )
    user.password_hash = generate_password_hash(password)
    
    try:
        db.session.add(user)
        db.session.commit()
        flash('User created successfully')
    except:
        db.session.rollback()
        flash('An error occurred. Please try again.')
        
    return redirect(url_for('admin_dashboard'))

def create_admin():
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                is_teacher=True
            )
            admin.password_hash = generate_password_hash('admin')
            db.session.add(admin)
            db.session.commit()

    

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin()  # Create admin user if it doesn't exist
    app.run(debug=True)