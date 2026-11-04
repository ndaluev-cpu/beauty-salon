# app/__init__.py
from flask import Flask, flash, redirect, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.exc import InterfaceError, OperationalError

from config import Config

# ─────────────────────────────────────────────────────────────
#  Глобальные расширения (объявляются на уровне модуля!)
# ─────────────────────────────────────────────────────────────
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'admin.login'
login_manager.login_message = 'Войдите в админку'
login_manager.login_message_category = 'warning'


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    # Импорт моделей — чтобы SQLAlchemy знал о них
    from app import models

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.Admin, int(user_id))

    # Регистрация blueprint'ов
    from app import routes, admin
    app.register_blueprint(routes.bp)
    app.register_blueprint(admin.bp)

    # ─────────────────────────────────────────────────────────
    #  Глобальный перехват обрыва соединения с БД
    # ─────────────────────────────────────────────────────────
    @app.errorhandler(InterfaceError)
    @app.errorhandler(OperationalError)
    def handle_db_disconnect(e):
        db.session.rollback()
        try:
            db.engine.dispose()
        except Exception:
            pass
        app.logger.warning(f'DB disconnect: {e}')
        flash('Соединение с БД прервалось, попробуйте ещё раз.', 'warning')
        return redirect(request.referrer or '/admin/')

    # Проверка подключения при старте
    with app.app_context():
        try:
            db.session.execute(db.text('SELECT 1'))
            print('✅ Подключение к Supabase: OK')
        except Exception as e:
            print(f'⚠️  Ошибка подключения к БД: {e}')

    return app