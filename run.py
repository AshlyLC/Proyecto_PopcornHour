from flask import Flask, session
from database import db
from routes import routes
from flask_login import LoginManager
from datetime import timedelta
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
app.secret_key = 'supersecretkey123'  # Clave secreta para la sesión

login_manager = LoginManager()
login_manager.init_app(app)

app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)  # Mantener la sesión activa por 7 días

from models import User 

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Cieguito7@localhost/pmovie'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    Session = sessionmaker(bind=db.engine)
    session = scoped_session(Session)

@login_manager.user_loader
def load_user(user_id):
    return session.get(User, int(user_id))

app.register_blueprint(routes)

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=30)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
