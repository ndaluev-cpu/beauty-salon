import os
print("DB URL prefix:", (os.environ.get("DATABASE_URL") or "")[:30])

from dotenv import load_dotenv
load_dotenv()

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=8000)
