# app/admin.py
import os
import uuid

from flask import (
    Blueprint, render_template, redirect, url_for, request,
    flash, jsonify, current_app
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy.exc import InterfaceError, OperationalError

from app import db
from app.models import Admin, Category, Master, Service, Order, OrderItem

bp = Blueprint('admin', __name__, url_prefix='/admin')


# ─────────────────────────────────────────────────────────────
#  Утилиты
# ─────────────────────────────────────────────────────────────

def _commit_with_retry(max_attempts=2):
    """
    Коммит с одной повторной попыткой при обрыве соединения
    (pg8000 → InterfaceError / OperationalError из-за ТСПУ/VPN/Session Pooler).
    """
    for attempt in range(1, max_attempts + 1):
        try:
            db.session.commit()
            return True
        except (InterfaceError, OperationalError) as e:
            db.session.rollback()
            if attempt >= max_attempts:
                current_app.logger.error(
                    f'DB commit failed after {attempt} attempts: {e}'
                )
                raise
            try:
                db.engine.dispose()
            except Exception:
                pass
            current_app.logger.warning(
                f'Обрыв соединения с БД (попытка {attempt}), повтор...'
            )


def _slugify(name: str) -> str:
    """Простой slug без внешних зависимостей (транслит для кириллицы)."""
    translit = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    }
    s = name.lower().strip()
    out = []
    for ch in s:
        if ch in translit:
            out.append(translit[ch])
        elif ch.isalnum():
            out.append(ch)
        elif ch in (' ', '-', '_'):
            out.append('-')
    slug = ''.join(out)
    while '--' in slug:
        slug = slug.replace('--', '-')
    return slug.strip('-') or f'cat-{uuid.uuid4().hex[:6]}'


def _save_upload(file_storage, subdir: str):
    """
    Сохраняет загруженный файл в static/images/<subdir>/.
    Возвращает ТОЛЬКО имя файла (без пути) — шаблоны добавляют
    'images/<subdir>/' + имя сами.
    """
    if not file_storage or not file_storage.filename:
        return None
    filename = secure_filename(file_storage.filename)
    if not filename:
        return None
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
        return None
    unique = f'{uuid.uuid4().hex}{ext}'
    upload_dir = os.path.join(
        current_app.root_path, 'static', 'images', subdir
    )
    os.makedirs(upload_dir, exist_ok=True)
    file_storage.save(os.path.join(upload_dir, unique))
    return unique  # ← только имя файла


def _parse_int(value, default=None):
    """Целое число из строки. Пусто/None/мусор → default."""
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_int_money(value, default=None):
    """
    Парсит цену в ЦЕЛОЕ число (в БД price/old_price — Integer).
    Принимает '5000', '5000.0', '5 000', '5000,00' → 5000.
    Пустое/None → default.
    """
    if value is None or value == '':
        return default
    try:
        s = str(value).strip().replace(' ', '').replace(',', '.')
        return int(round(float(s)))
    except (TypeError, ValueError):
        return default


# ─────────────────────────────────────────────────────────────
#  Аутентификация
# ─────────────────────────────────────────────────────────────

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            login_user(admin)
            flash('Добро пожаловать!', 'success')
            next_url = request.args.get('next') or url_for('admin.dashboard')
            return redirect(next_url)
        flash('Неверный логин или пароль', 'danger')

    return render_template('admin/login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из админки', 'info')
    return redirect(url_for('admin.login'))


# ─────────────────────────────────────────────────────────────
#  Дашборд
# ─────────────────────────────────────────────────────────────

@bp.route('/')
@login_required
def dashboard():
    stats = {
        'services': Service.query.count(),
        'categories': Category.query.count(),
        'masters': Master.query.count(),
        'orders': Order.query.count(),
        'new_orders': Order.query.filter_by(status='new').count(),
    }
    recent_orders = (
        Order.query.order_by(Order.created_at.desc()).limit(5).all()
    )
    return render_template(
        'admin/dashboard.html', stats=stats, recent_orders=recent_orders
    )


# ─────────────────────────────────────────────────────────────
#  Услуги
# ─────────────────────────────────────────────────────────────

@bp.route('/services')
@login_required
def services():
    q = request.args.get('q', '').strip()
    cat_id = _parse_int(request.args.get('category'))
    query = Service.query
    if q:
        query = query.filter(Service.name.ilike(f'%{q}%'))
    if cat_id:
        query = query.filter(Service.category_id == cat_id)
    items = query.order_by(Service.sort_order, Service.id).all()
    categories = Category.query.order_by(Category.sort_order, Category.name).all()
    masters = Master.query.order_by(Master.sort_order, Master.name).all()
    return render_template(
        'admin/products.html',
        services=items,
        categories=categories,
        masters=masters,
        q=q,
        cat_id=cat_id,
    )


@bp.route('/services/add', methods=['GET', 'POST'])
@login_required
def services_add():
    # GET — просто редирект на список (форма в модалке на /admin/services)
    if request.method == 'GET':
        return redirect(url_for('admin.services'))

    name = request.form.get('name', '').strip()
    if not name:
        flash('Название обязательно', 'danger')
        return redirect(url_for('admin.services'))

    price = _parse_int_money(request.form.get('price'))
    if price is None:
        flash('Цена обязательна', 'danger')
        return redirect(url_for('admin.services'))

    image = _save_upload(request.files.get('image'), 'services')
    service = Service(
        name=name,
        description=request.form.get('description', '').strip() or None,
        price=price,
        old_price=_parse_int_money(request.form.get('old_price')),
        duration=_parse_int(request.form.get('duration')),
        category_id=_parse_int(request.form.get('category_id')),
        master_id=_parse_int(request.form.get('master_id')),
        image=image,
        is_active=bool(request.form.get('is_active', True)),
        is_new=bool(request.form.get('is_new')),
        is_hit=bool(request.form.get('is_hit')),
        sort_order=_parse_int(request.form.get('sort_order'), 0),
    )
    db.session.add(service)
    try:
        _commit_with_retry()
        flash('Услуга добавлена', 'success')
    except Exception as e:
        flash(f'Ошибка сохранения: {e}', 'danger')
    return redirect(url_for('admin.services'))


@bp.route('/services/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def services_edit(id):
    service = db.session.get(Service, id)
    if not service:
        flash('Услуга не найдена', 'danger')
        return redirect(url_for('admin.services'))

    if request.method == 'GET':
        return redirect(url_for('admin.services'))

    service.name = request.form.get('name', '').strip() or service.name
    service.description = request.form.get('description', '').strip() or None
    service.price = _parse_int_money(request.form.get('price'), service.price)
    service.old_price = _parse_int_money(request.form.get('old_price'))
    service.duration = _parse_int(request.form.get('duration'))
    service.category_id = _parse_int(request.form.get('category_id'))
    service.master_id = _parse_int(request.form.get('master_id'))
    service.is_active = bool(request.form.get('is_active'))
    service.is_new = bool(request.form.get('is_new'))
    service.is_hit = bool(request.form.get('is_hit'))
    service.sort_order = _parse_int(request.form.get('sort_order'), 0)

    new_image = _save_upload(request.files.get('image'), 'services')
    if new_image:
        service.image = new_image

    try:
        _commit_with_retry()
        flash('Услуга обновлена', 'success')
    except Exception as e:
        flash(f'Ошибка сохранения: {e}', 'danger')
    return redirect(url_for('admin.services'))


@bp.route('/services/delete/<int:id>', methods=['POST'])
@login_required
def services_delete(id):
    service = db.session.get(Service, id)
    if not service:
        flash('Услуга не найдена', 'danger')
        return redirect(url_for('admin.services'))
    db.session.delete(service)
    try:
        _commit_with_retry()
        flash('Услуга удалена', 'success')
    except Exception as e:
        flash(f'Ошибка удаления: {e}', 'danger')
    return redirect(url_for('admin.services'))


@bp.route('/services/toggle/<int:id>', methods=['POST'])
@login_required
def services_toggle(id):
    service = db.session.get(Service, id)
    if not service:
        return jsonify({'ok': False, 'error': 'not found'}), 404
    service.is_active = not service.is_active
    try:
        _commit_with_retry()
        return jsonify({'ok': True, 'is_active': service.is_active})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────
#  Категории
# ─────────────────────────────────────────────────────────────

@bp.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Название категории обязательно', 'danger')
            return redirect(url_for('admin.categories'))

        existing = Category.query.filter(
            db.func.lower(Category.name) == name.lower()
        ).first()
        if existing:
            flash(f'Категория «{name}» уже существует', 'warning')
            return redirect(url_for('admin.categories'))

        slug = request.form.get('slug', '').strip() or _slugify(name)
        base_slug = slug
        i = 1
        while Category.query.filter_by(slug=slug).first():
            slug = f'{base_slug}-{i}'
            i += 1

        cat = Category(
            name=name,
            slug=slug,
            sort_order=_parse_int(request.form.get('sort_order'), 0),
        )
        db.session.add(cat)
        try:
            _commit_with_retry()
            flash(f'Категория «{name}» добавлена', 'success')
        except Exception as e:
            flash(f'Ошибка сохранения: {e}', 'danger')
        return redirect(url_for('admin.categories'))

    items = Category.query.order_by(Category.sort_order, Category.name).all()
    return render_template('admin/categories.html', categories=items)


@bp.route('/categories/edit/<int:id>', methods=['POST'])
@login_required
def categories_edit(id):
    cat = db.session.get(Category, id)
    if not cat:
        flash('Категория не найдена', 'danger')
        return redirect(url_for('admin.categories'))

    name = request.form.get('name', '').strip()
    if name:
        cat.name = name
    slug = request.form.get('slug', '').strip()
    if slug:
        cat.slug = slug
    cat.sort_order = _parse_int(request.form.get('sort_order'), cat.sort_order)

    try:
        _commit_with_retry()
        flash('Категория обновлена', 'success')
    except Exception as e:
        flash(f'Ошибка сохранения: {e}', 'danger')
    return redirect(url_for('admin.categories'))


@bp.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
def categories_delete(id):
    cat = db.session.get(Category, id)
    if not cat:
        flash('Категория не найдена', 'danger')
        return redirect(url_for('admin.categories'))

    if Service.query.filter_by(category_id=id).count() > 0:
        flash(
            f'Нельзя удалить «{cat.name}»: в категории есть услуги. '
            f'Сначала перенесите или удалите их.',
            'warning',
        )
        return redirect(url_for('admin.categories'))

    db.session.delete(cat)
    try:
        _commit_with_retry()
        flash('Категория удалена', 'success')
    except Exception as e:
        flash(f'Ошибка удаления: {e}', 'danger')
    return redirect(url_for('admin.categories'))


# ─────────────────────────────────────────────────────────────
#  Мастера
# ─────────────────────────────────────────────────────────────

@bp.route('/masters')
@login_required
def masters():
    items = Master.query.order_by(Master.sort_order, Master.name).all()
    return render_template('admin/masters.html', masters=items)


@bp.route('/masters/add', methods=['GET', 'POST'])
@login_required
def masters_add():
    if request.method == 'GET':
        return redirect(url_for('admin.masters'))

    name = request.form.get('name', '').strip()
    if not name:
        flash('Имя мастера обязательно', 'danger')
        return redirect(url_for('admin.masters'))

    photo = _save_upload(request.files.get('photo'), 'masters')
    master = Master(
        name=name,
        specialization=request.form.get('specialization', '').strip() or None,
        description=request.form.get('description', '').strip() or None,
        photo=photo,
        is_active=bool(request.form.get('is_active', True)),
        sort_order=_parse_int(request.form.get('sort_order'), 0),
    )
    db.session.add(master)
    try:
        _commit_with_retry()
        flash('Мастер добавлен', 'success')
    except Exception as e:
        flash(f'Ошибка сохранения: {e}', 'danger')
    return redirect(url_for('admin.masters'))


@bp.route('/masters/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def masters_edit(id):
    master = db.session.get(Master, id)
    if not master:
        flash('Мастер не найден', 'danger')
        return redirect(url_for('admin.masters'))

    if request.method == 'GET':
        return redirect(url_for('admin.masters'))

    master.name = request.form.get('name', '').strip() or master.name
    master.specialization = request.form.get('specialization', '').strip() or None
    master.description = request.form.get('description', '').strip() or None
    master.is_active = bool(request.form.get('is_active'))
    master.sort_order = _parse_int(request.form.get('sort_order'), 0)

    new_photo = _save_upload(request.files.get('photo'), 'masters')
    if new_photo:
        master.photo = new_photo

    try:
        _commit_with_retry()
        flash('Мастер обновлён', 'success')
    except Exception as e:
        flash(f'Ошибка сохранения: {e}', 'danger')
    return redirect(url_for('admin.masters'))


@bp.route('/masters/delete/<int:id>', methods=['POST'])
@login_required
def masters_delete(id):
    master = db.session.get(Master, id)
    if not master:
        flash('Мастер не найден', 'danger')
        return redirect(url_for('admin.masters'))
    Service.query.filter_by(master_id=id).update({'master_id': None})
    db.session.delete(master)
    try:
        _commit_with_retry()
        flash('Мастер удалён', 'success')
    except Exception as e:
        flash(f'Ошибка удаления: {e}', 'danger')
    return redirect(url_for('admin.masters'))


# ─────────────────────────────────────────────────────────────
#  Заявки
# ─────────────────────────────────────────────────────────────

@bp.route('/orders')
@login_required
def orders():
    status_filter = request.args.get('status', '').strip()
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    items = query.order_by(Order.created_at.desc()).all()

    statuses = [
        ('new', 'Новая'),
        ('processing', 'В работе'),
        ('done', 'Выполнена'),
        ('cancelled', 'Отменена'),
    ]
    return render_template(
        'admin/orders.html', orders=items,
        statuses=statuses, status_filter=status_filter,
    )


@bp.route('/orders/<int:id>')
@login_required
def orders_view(id):
    order = db.session.get(Order, id)
    if not order:
        flash('Заявка не найдена', 'danger')
        return redirect(url_for('admin.orders'))
    return render_template('admin/order_view.html', order=order)


@bp.route('/orders/status/<int:id>', methods=['POST'])
@login_required
def orders_status(id):
    order = db.session.get(Order, id)
    if not order:
        return jsonify({'ok': False, 'error': 'not found'}), 404

    data = request.get_json(silent=True) or {}
    status = (data.get('status') or '').strip()
    # ⚠️ 'processing' — совместимо с orders.html и models.py (комментарий)
    allowed = {'new', 'processing', 'done', 'cancelled'}
    if status not in allowed:
        return jsonify({'ok': False, 'error': 'invalid status'}), 400

    order.status = status
    try:
        _commit_with_retry()
        return jsonify({'ok': True, 'status': order.status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/orders/delete/<int:id>', methods=['POST'])
@login_required
def orders_delete(id):
    order = db.session.get(Order, id)
    if not order:
        flash('Заявка не найдена', 'danger')
        return redirect(url_for('admin.orders'))
    OrderItem.query.filter_by(order_id=id).delete()
    db.session.delete(order)
    try:
        _commit_with_retry()
        flash('Заявка удалена', 'success')
    except Exception as e:
        flash(f'Ошибка удаления: {e}', 'danger')
    return redirect(url_for('admin.orders'))