import os
from dotenv import load_dotenv

# Загружаем переменные из .env (должен лежать в корне проекта)
load_dotenv()


class Config:
    """Базовая конфигурация приложения."""

    # --- Flask ---
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-me'

    # --- База данных (Supabase Session Pooler) ---
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Пул соединений — важно для Supabase Session Pooler
    # (у бесплатного тарифа ограничение одновременных соединений)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'max_overflow': 2,
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }

    # --- Email (уведомления о заявках) ---
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    ORDER_EMAIL = os.environ.get('ORDER_EMAIL', 'orders@example.ru')

    # --- Telegram (опционально) ---
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')


# Ранняя проверка: если DATABASE_URL не задан — падаем сразу с понятным сообщением
if not Config.SQLALCHEMY_DATABASE_URI:
    raise RuntimeError(
        "❌ DATABASE_URL не задан в .env!\n"
        "   Убедитесь, что файл .env лежит в корне проекта рядом с config.py\n"
        "   и содержит строку вида:\n"
        "   DATABASE_URL=postgresql://postgres.fimottqatxdxjelbpnzg:ПАРОЛЬ@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
    )