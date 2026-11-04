from app import create_app, db
from app.models import Admin

app = create_app()

with app.app_context():
    admin = db.session.query(Admin).filter_by(username='admin').first()
    if admin:
        new_password = input('Введите новый пароль для admin: ').strip()
        if len(new_password) < 6:
            print('❌ Пароль слишком короткий (мин. 6 символов)')
        else:
            admin.set_password(new_password)
            db.session.commit()
            print('✅ Пароль обновлён')
    else:
        print('❌ Администратор не найден. Создайте через __init__.py')