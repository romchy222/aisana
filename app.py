# Импорт необходимых библиотек
import os
import logging
from flask import Flask
from flask_cors import CORS
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)


# Базовый класс для моделей базы данных
class Base(DeclarativeBase):
    pass


# Import db from models to avoid circular imports
from models import db


def create_app():
    """Функция создания и настройки Flask приложения"""
    # Создание экземпляра Flask приложения
    app = Flask(__name__)
    
    # Установка секретного ключа для сессий с проверкой переменной окружения
    session_secret = os.environ.get("SESSION_SECRET")
    if not session_secret:
        # In development, use a warning and fallback
        if os.environ.get("FLASK_ENV") == "development":
            app.logger.warning("SESSION_SECRET not set, using development fallback")
            session_secret = "dev-secret-key-change-in-production"
        else:
            # In production, this is critical
            raise ValueError("SESSION_SECRET environment variable is required for production deployment")
    
    app.secret_key = session_secret
    
    # Настройка ProxyFix для работы за прокси (нужно для Replit deployments)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Настройка базы данных с улучшенной обработкой ошибок
    try:
        from config import DatabaseConfig
        database_url = DatabaseConfig.get_database_url()
        
        # Логирование информации о БД (скрываем пароли)
        if database_url:
            safe_url = database_url
            if "@" in safe_url:
                parts = safe_url.split("@")
                if ":" in parts[0]:
                    user_pass = parts[0].split(":")
                    safe_url = f"{user_pass[0]}:***@{parts[1]}"
            logging.info(f"Using database: {safe_url}")
        else:
            logging.error("No database URL configured")
            raise ValueError("Database configuration is required - check DATABASE_URL or PostgreSQL environment variables")
        
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        # Настройки движка базы данных в зависимости от типа БД
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = DatabaseConfig.get_engine_options()
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        
    except Exception as e:
        logging.error(f"Database configuration error: {e}")
        raise

    # Инициализация базы данных с приложением
    db.init_app(app)

    # Настройка CORS (разрешение кросс-доменных запросов)
    CORS(
        app,
        origins=[
            "https://7a0463a0-cbab-40ed-8964-1461cf93cb8a-00-tv6bvx5wqo3s.pike.replit.dev",
            "https://*.replit.dev",  # Разрешить все поддомены replit.dev
            "http://localhost:*",  # Для локальной разработки
            "https://localhost:*"  # Для локальной разработки с HTTPS
        ],
        supports_credentials=True)

    # Настройка системы локализации
    from localization import localization, localize_filter
    app.jinja_env.filters['localize'] = localize_filter
    app.jinja_env.globals['get_language'] = localization.get_current_language
    app.jinja_env.globals['get_locale'] = localization.get_current_language
    app.jinja_env.globals['_'] = localization.get_text

    # Импорт модулей с маршрутами (blueprints)
    from views import main_bp
    from admin import admin_bp
    from auth import auth_bp
    from feedback_api import feedback_bp

    # Регистрация модулей маршрутов
    app.register_blueprint(main_bp)  # Основные страницы
    app.register_blueprint(admin_bp, url_prefix='/admin')  # Админ панель
    app.register_blueprint(auth_bp, url_prefix='/auth')  # Аутентификация
    app.register_blueprint(feedback_bp)  # API обратной связи для ML

    # Database initialization will be handled in views.py startup endpoint

    # Immediate lightweight initialization for deployment readiness  
    with app.app_context():
        try:
            # Only import models to register them with SQLAlchemy
            import models
            logging.info("Models imported successfully")
            
            # Try basic database initialization but don't fail if it doesn't work
            try:
                db.create_all()
                logging.info("Database tables created during startup")
            except Exception as db_e:
                logging.warning(f"Database initialization deferred: {db_e}")
                
        except Exception as e:
            logging.error(f"Model import failed: {e}")
            # Continue anyway - health check endpoint will still work

    return app


# Создание экземпляра приложения
app = create_app()

# Запуск приложения в режиме разработки
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
