"""Extensions Flask instanciées une seule fois et initialisées via l'app factory."""
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
csrf = CSRFProtect()
migrate = Migrate()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Connecte-toi pour accéder à ton tableau de bord."
login_manager.login_message_category = "error"

limiter = Limiter(
    get_remote_address,
    default_limits=[],
    storage_uri="memory://",
    strategy="fixed-window",
)
