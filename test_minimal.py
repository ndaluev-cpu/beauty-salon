"""
Минимальная проверка SQLAlchemy + pg8000 + SSL.
Запуск: python test_minimal.py
"""
import os
import ssl
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL")
print(f"🔌 URL: {DB_URL.split('@')[1] if '@' in DB_URL else DB_URL}\n")

# ⚠️ Явно создаём SSL-контекст — без него pg8000 не подключится к Supabase
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

try:
    engine = create_engine(
        DB_URL,
        echo=True,
        connect_args={'ssl_context': ssl_context}
    )
    print("1️⃣ Engine создан")

    with engine.connect() as conn:
        print("2️⃣ Соединение установлено")

        result = conn.execute(text("SELECT 1"))
        print(f"3️⃣ SELECT 1 вернул: {result.fetchone()}")

        result = conn.execute(text("SELECT version()"))
        print(f"4️⃣ Версия PostgreSQL: {result.fetchone()[0][:60]}")

        result = conn.execute(text("SELECT COUNT(*) FROM categories"))
        print(f"5️⃣ Категорий: {result.fetchone()[0]}")

    print("\n🎉 Всё работает!\n")

except Exception as e:
    print(f"\n❌ ОШИБКА: {type(e).__name__}")
    print(f"   {e}\n")