from database import db
from flask_login import UserMixin

# Modelos de la base de datos
class User(db.Model, UserMixin):  # Modelo de usuario
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='standard')  # 'moderator' o 'standard'

    def __init__(self, username, email, password, role='standard'):
        self.username = username
        self.email = email
        self.password = password
        self.role = role
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    # Métodos requeridos por Flask-Login
    @property
    def is_active(self):
        return True
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)

class Anime(db.Model):  # Modelo de anime
    __tablename__ = 'animes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Relacionado con el usuario que sube el anime

    # Relaciones con los comentarios
    comments = db.relationship('Comment', backref='anime_reference', lazy=True)

    def __init__(self, title, description, genre, year, image_url):
        self.title = title
        self.description = description
        self.genre = genre
        self.year = year
        self.image_url = image_url

    def __repr__(self):
        return f'<Anime {self.title}>'

class Comment(db.Model):  # Modelo de comentario
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)  # ID del comentario
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Relación con el usuario
    anime_id = db.Column(db.Integer, db.ForeignKey('animes.id'), nullable=False)  # Relación con el anime
    text = db.Column(db.String(500), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # Rating entre 1 y 5
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)  # Relación con el comentario padre

    # Relación con el usuario
    user = db.relationship('User', backref='comments')
    # Relación con las respuestas
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)

    def __init__(self, user_id, anime_id, text, rating, parent_id=None):
        self.user_id = user_id
        self.anime_id = anime_id
        self.text = text
        self.rating = rating
        self.parent_id = parent_id

    def __repr__(self):
        return f'<Comment {self.text[:20]}>'

    # Validación para asegurar que solo los usuarios con rol 'standard' puedan calificar
    @staticmethod
    def validate_rating(user):
        if user.role != 'standard':
            raise ValueError("Solo los usuarios estándar pueden calificar animes")
        if not (1 <= user.rating <= 5):
            raise ValueError("La calificación debe estar entre 1 y 5 estrellas")