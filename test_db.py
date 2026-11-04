import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    print("❌ DATABASE_URL не задан в .env")
    exit(1)

# Скрываем пароль при выводе
safe_url = DB_URL
if '@' in DB_URL and ':' in DB_URL.split('@')[0]:
    parts = DB_URL.split('@')
    user_part = parts[0].rsplit(':', 1)[0]
    safe_url = f"{user_part}:****@{parts[1]}"

print(f"🔌 Подключаюсь к: {safe_url}\n")

try:
    conn = psycopg2.connect(DB_URL, connect_timeout=15)
    cur = conn.cursor()

    cur.execute("SELECT version();")
    print(f"✅ PostgreSQL: {cur.fetchone()[0][:70]}")

    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' ORDER BY table_name;
    """)
    tables = [r[0] for r in cur.fetchall()]
    print(f"\n📊 Таблиц: {len(tables)}")
    for t in tables:
        print(f"   • {t}")

    cur.execute("SELECT COUNT(*) FROM categories;")
    print(f"\n🏷️  Категорий: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM admins;")
    print(f"👤 Админов: {cur.fetchone()[0]}")

    cur.close()
    conn.close()
    print("\n🎉 Всё работает!\n")

except Exception as e:
    print(f"\n❌ ОШИБКА: {type(e).__name__}")
    print(f"   {e}\n")
    print("💡 Проверьте:")
    print("   • Пароль в .env — точный?")
    print("   • Username = postgres.fimottqatxdxjelbpnzg ?")
    print("   • Проект Supabase не на паузе?")