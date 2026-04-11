from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail

db       = SQLAlchemy()
jwt      = JWTManager()
socketio = SocketIO(cors_allowed_origins="*")
limiter  = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)
mail     = Mail()
