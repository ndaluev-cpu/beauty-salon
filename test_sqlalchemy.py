"""
Проверка: SQLAlchemy подключается к Supabase через наш Config.
Запуск: python test_sqlalchemy.py
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from sqlalchemy import text

app = Flask(__name__)
app.config.from_object(Config)

# ⚠️ ВАЖНО: отключаем prepared statements для psycopg2
# Supabase Session Pooler (PgBouncer) их не поддерживает
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 5,
    'max_overflow': 2,
    'pool_recycle': 300,
    'pool_pre_ping': True,
    'connect_args': {
        'prepare_threshold': None,
        'options': '-c statement_timeout=30000',  # 30 сек таймаут на запрос
    },
}

db = SQLAlchemy(app)

with app.app_context():
    print("🔌 Проверяю подключение через SQLAlchemy...\n")
    try:
        result = db.session.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print(f"✅ SQLAlchemy подключён к PostgreSQL")
        print(f"   {version[:70]}")

        result = db.session.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name;
        """))
        tables = [r[0] for r in result.fetchall()]
        print(f"\n📊 Таблиц: {len(tables)}")
        for t in tables:
            print(f"   • {t}")

        result = db.session.execute(text("SELECT COUNT(*) FROM categories;"))
        print(f"\n🏷️  Категорий: {result.fetchone()[0]}")

        result = db.session.execute(text("SELECT COUNT(*) FROM admins;"))
        print(f"👤 Админов: {result.fetchone()[0]}")

        print("\n🎉 SQLAlchemy работает с Supabase!\n")

    except Exception as e:
        print(f"❌ ОШИБКА: {type(e).__name__}: {e}")