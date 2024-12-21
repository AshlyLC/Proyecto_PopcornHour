import os
from flask import current_app, Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from models import User, Anime, Comment
from database import db
from flask_login import login_user, logout_user, current_user

# Crear un Blueprint para las rutas
routes = Blueprint('routes', __name__)

# Ruta principal: lista de animes
@routes.route('/')
def index():
    # Obtener todos los animes de la base de datos
    animes = Anime.query.all()
    anime_ratings = {}
    for anime in animes:
        # Obtener todos los comentarios del anime
        comments = Comment.query.filter_by(anime_id=anime.id).all()
        # Calcular el promedio de calificación
        ratings = [comment.rating for comment in comments if comment.rating > 0]
        average_rating = sum(ratings) / len(ratings) if ratings else 0
        anime_ratings[anime.id] = average_rating
    # Renderizar la plantilla index.html con los animes y sus calificaciones
    return render_template('index.html', animes=animes, anime_ratings=anime_ratings)

# Ruta de registro
@routes.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        # Obtener los datos del formulario
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        account_type = request.form['account_type']  # 'standard' o 'moderator'

        # Verificar si las contraseñas coinciden
        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('routes.registro'))

        # Verificar si el correo ya existe
        if User.query.filter_by(email=email).first():
            flash('El correo electrónico ya está registrado.', 'danger')
            return redirect(url_for('routes.registro'))

        # Crear un nuevo usuario con contraseña hasheada
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password, role=account_type)
        db.session.add(new_user)
        db.session.commit()

        flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('routes.login'))
    return render_template('registro.html')

# Ruta de inicio de sesión
@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Obtener los datos del formulario
        email = request.form['email']
        password = request.form['password']
        # Verificar si el usuario existe
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            # Guardar datos del usuario en la sesión y recordar la sesión
            login_user(user, remember=True)
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('routes.inicio'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')

    return render_template('login.html')

# Ruta para cerrar sesión
@routes.route('/logout')
def logout():
    # Limpiar la sesión del usuario
    logout_user()
    session.clear()
    flash('Sesión cerrada exitosamente.', 'success')
    return redirect(url_for('routes.index'))

# Ruta para agregar un anime (solo para moderadores)
@routes.route('/add_anime', methods=['GET', 'POST'])
def add_anime():
    # Verificar si el usuario está autenticado y es moderador
    if session.get('role') != 'moderator':  # Verifica si es moderador
        flash('No tienes permisos para agregar animes.', 'danger')
        return redirect(url_for('routes.inicio'))
    image_url = None
    if request.method == 'POST':
        # Obtener los datos del formulario
        title = request.form['title']
        description = request.form['description']
        genre = request.form['genre']
        year = request.form['year']
        # Verificar si se subió una imagen
        if 'image' in request.files:  
            image = request.files['image']
            if image:
                filename = secure_filename(image.filename)
                image_path = os.path.join(current_app.root_path, 'static', 'images', filename)
                image.save(image_path)
                image_url = url_for('static', filename=f'images/{filename}')
        # Guardar el anime
        new_anime = Anime(title=title, description=description, genre=genre, year=year, image_url=image_url)
        db.session.add(new_anime)
        db.session.commit()
        flash(f'Anime "{title}" agregado exitosamente.', 'success')
        return redirect(url_for('routes.inicio'))
    return render_template('add_anime.html')

# Dashboard para mostrar los animes y opciones
@routes.route('/inicio')
def inicio():
    if not current_user.is_authenticated:
        flash('Debes iniciar sesión primero.', 'warning')
        return redirect(url_for('routes.login'))
    # Obtener todos los animes de la base de datos
    animes = Anime.query.all()
    anime_ratings = {}
    for anime in animes:
        comments = Comment.query.filter_by(anime_id=anime.id).all()
        # Calcular el promedio de calificación
        ratings = [comment.rating for comment in comments if comment.rating > 0]
        average_rating = sum(ratings) / len(ratings) if ratings else 0
        anime_ratings[anime.id] = average_rating
    # Renderizar la plantilla inicio.html con los animes y sus calificaciones
    return render_template('inicio.html', animes=animes, anime_ratings=anime_ratings, username=session['username'], role=session['role'])

# Ruta para ver detalles de un anime
@routes.route('/anime/<int:anime_id>', methods=['GET', 'POST'])
def anime_detail(anime_id):
    # Obtener el anime por ID
    anime = Anime.query.get_or_404(anime_id)
    # Obtener los comentarios principales del anime
    comments = Comment.query.filter_by(anime_id=anime.id, parent_id=None).all() 
    # Calcular el promedio de calificación
    ratings = [comment.rating for comment in comments if comment.rating > 0]
    average_rating = sum(ratings) / len(ratings) if ratings else 0
    if 'user_id' in session:
        user_role = session.get('role')
        if user_role == 'standard' and request.method == 'POST':
            # Obtener los datos del formulario
            comment_text = request.form['comment']
            rating = request.form.get('rating')  # Puede ser None si es una respuesta
            parent_id = request.form.get('parent_id')  # ID del comentario padre, si es una respuesta
            # Validar que la calificación sea un número y esté entre 1 y 5, si se proporciona
            if rating:
                try:
                    rating = int(rating)
                    if not (1 <= rating <= 5):
                        flash('La calificación debe estar entre 1 y 5 estrellas.', 'danger')
                        return redirect(url_for('routes.anime_detail', anime_id=anime.id))
                except ValueError:
                    flash('La calificación debe ser un número entero entre 1 y 5.', 'danger')
                    return redirect(url_for('routes.anime_detail', anime_id=anime.id))
            # Guardar el comentario y calificación en la base de datos
            new_comment = Comment(anime_id=anime.id, user_id=session['user_id'], text=comment_text, rating=rating or 0, parent_id=parent_id)
            db.session.add(new_comment)
            db.session.commit()
            flash('Comentario y calificación agregados exitosamente.', 'success')
            # Redirigir a la misma página para evitar reenvío de formulario
            return redirect(url_for('routes.anime_detail', anime_id=anime.id))
    # Renderizar la plantilla anime_details.html con el anime, comentarios y calificaciones
    return render_template('anime_details.html', anime=anime, comments=comments, average_rating=average_rating, user_id=session.get('user_id'))

# Ruta para eliminar un anime (solo para moderadores)
@routes.route('/delete_anime/<int:anime_id>', methods=['POST'])
def delete_anime(anime_id):
    if 'user_id' not in session or session.get('role') != 'moderator':
        flash('No tienes permisos para eliminar animes.', 'danger')
        return redirect(url_for('routes.inicio'))
    # Obtener el anime por ID y eliminarlo
    anime = Anime.query.get_or_404(anime_id)
    db.session.delete(anime)
    db.session.commit()
    flash(f'Anime "{anime.title}" eliminado exitosamente.', 'success')
    return redirect(url_for('routes.inicio'))

# Ruta para editar un anime (solo para moderadores)
@routes.route('/edit_anime/<int:anime_id>', methods=['GET', 'POST'])
def edit_anime(anime_id):
    # Verificar si el usuario está autenticado y es moderador
    if session.get('role') != 'moderator':
        flash('No tienes permisos para editar animes.', 'danger')
        return redirect(url_for('routes.inicio'))
    
    # Obtener el anime por ID
    anime = Anime.query.get_or_404(anime_id)
    
    if request.method == 'POST':
        # Obtener los datos del formulario
        anime.title = request.form['title']
        anime.description = request.form['description']
        anime.genre = request.form['genre']
        anime.year = request.form['year']
        
        # Verificar si se subió una nueva imagen
        if 'image' in request.files:
            image = request.files['image']
            if image:
                filename = secure_filename(image.filename)
                image_path = os.path.join(current_app.root_path, 'static', 'images', filename)
                image.save(image_path)
                anime.image_url = url_for('static', filename=f'images/{filename}')
        
        # Guardar los cambios en la base de datos
        db.session.commit()
        flash(f'Anime "{anime.title}" actualizado exitosamente.', 'success')
        return redirect(url_for('routes.inicio'))
    
    # Renderizar la plantilla edit_anime.html con los datos del anime
    return render_template('edit_anime.html', anime=anime)