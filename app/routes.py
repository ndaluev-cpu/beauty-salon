# app/routes.py
from datetime import datetime

from flask import (
    Blueprint, render_template, request, jsonify, abort, current_app
)
from sqlalchemy.exc import InterfaceError, OperationalError

from app import db
from app.models import Category, Service, Master, Order, OrderItem

bp = Blueprint('public', __name__)


# ─────────────────────────────────────────────────────────────
#  Главная
# ─────────────────────────────────────────────────────────────

@bp.route('/')
def index():
    """Главная: категории, новинки, популярные услуги."""
    categories = (
        Category.query
        .order_by(Category.sort_order, Category.name)
        .all()
    )
    new_services = (
        Service.query
        .filter_by(is_active=True, is_new=True)
        .order_by(Service.created_at.desc())
        .limit(6)
        .all()
    )
    popular_services = (
        Service.query
        .filter_by(is_active=True, is_hit=True)
        .order_by(Service.sort_order, Service.id)
        .limit(6)
        .all()
    )
    return render_template(
        'index.html',
        categories=categories,
        popular_services=popular_services,
        new_services=new_services,
    )


# ─────────────────────────────────────────────────────────────
#  Каталог
# ─────────────────────────────────────────────────────────────

@bp.route('/catalog')
def catalog():
    """Каталог услуг (страница; данные подгружаются AJAX-ом)."""
    categories = (
        Category.query
        .order_by(Category.sort_order, Category.name)
        .all()
    )
    masters = (
        Master.query
        .filter_by(is_active=True)
        .order_by(Master.sort_order, Master.name)
        .all()
    )
    return render_template(
        'catalog.html',
        categories=categories,
        masters=masters,
    )


@bp.route('/api/services')
def api_services():
    """API для AJAX-фильтрации в каталоге."""
    q = Service.query.filter_by(is_active=True)

    # Категория по slug
    category = request.args.get('category')
    if category and category != 'all':
        q = q.join(Category).filter(Category.slug == category)

    # Цена
    price_min = request.args.get('price_min', type=int)
    price_max = request.args.get('price_max', type=int)
    if price_min is not None:
        q = q.filter(Service.price >= price_min)
    if price_max is not None:
        q = q.filter(Service.price <= price_max)

    # Мастер
    master_id = request.args.get('master', type=int)
    if master_id:
        q = q.filter(Service.master_id == master_id)

    # Сортировка
    sort = request.args.get('sort', 'new')
    if sort == 'price_asc':
        q = q.order_by(Service.price.asc())
    elif sort == 'price_desc':
        q = q.order_by(Service.price.desc())
    else:
        q = q.order_by(Service.created_at.desc())

    services = q.all()

    return jsonify({
        'services': [{
            'id': s.id,
            'name': s.name,
            'price': s.price,
            'old_price': s.old_price,
            'duration': s.duration,
            'category': s.category.name if s.category else '',
            'category_slug': s.category.slug if s.category else '',
            'master': s.master.name if s.master else None,
            'image': s.image,             # только имя файла, напр. 'abc.jpg'
            'is_new': bool(s.is_new),
            'is_hit': bool(s.is_hit),
            'description': s.description or '',
        } for s in services],
        'count': len(services),
    })


# ─────────────────────────────────────────────────────────────
#  Карточка услуги
# ─────────────────────────────────────────────────────────────

@bp.route('/product/<int:id>')
def product(id):
    """Карточка услуги."""
    item = db.session.get(Service, id)
    if not item:
        abort(404)

    # Похожие услуги из той же категории
    related = []
    if item.category_id:
        related = (
            Service.query
            .filter(
                Service.category_id == item.category_id,
                Service.id != item.id,
                Service.is_active.is_(True),
            )
            .order_by(Service.sort_order, Service.id)
            .limit(4)
            .all()
        )

    return render_template('product.html', item=item, related=related)


# ─────────────────────────────────────────────────────────────
#  Корзина / оформление заявки
# ─────────────────────────────────────────────────────────────

@bp.route('/cart')
def cart():
    """Корзина заявки (данные в localStorage, сервер отдаёт только шаблон)."""
    return render_template('cart.html')


@bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Оформление заявки."""
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}

        name = (data.get('name') or '').strip()
        phone = (data.get('phone') or '').strip()
        email = (data.get('email') or '').strip() or None
        comment = (data.get('comment') or '').strip() or None
        items = data.get('items') or []

        if not name or not phone or not items:
            return jsonify({
                'ok': False,
                'error': 'Заполните имя и телефон'
            }), 400

        # Дата / время — необязательные, битые значения игнорируем
        preferred_date = None
        preferred_time = None
        try:
            raw_date = data.get('preferred_date')
            if raw_date:
                preferred_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            preferred_date = None
        try:
            raw_time = data.get('preferred_time')
            if raw_time:
                preferred_time = datetime.strptime(raw_time, '%H:%M').time()
        except (ValueError, TypeError):
            preferred_time = None

        # Валидация и подсчёт суммы
        total = 0
        parsed_items = []
        for i in items:
            try:
                price = int(i.get('price') or 0)
                quantity = int(i.get('quantity') or 1)
            except (ValueError, TypeError):
                return jsonify({
                    'ok': False,
                    'error': 'Некорректные данные услуги'
                }), 400
            if price < 0 or quantity < 1:
                return jsonify({
                    'ok': False,
                    'error': 'Некорректные данные услуги'
                }), 400
            total += price * quantity
            parsed_items.append({
                'service_id': i.get('id'),
                'service_name': (i.get('name') or '')[:200],
                'master_name': (i.get('master') or '')[:100],
                'price': price,
                'quantity': quantity,
            })

        order = Order(
            customer_name=name[:128],
            phone=phone[:32],
            email=email[:128] if email else None,
            comment=comment,
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            total=total,
            status='new',
        )
        db.session.add(order)

        try:
            db.session.flush()  # получить order.id

            for pi in parsed_items:
                db.session.add(OrderItem(
                    order_id=order.id,
                    service_id=pi['service_id'],
                    service_name=pi['service_name'],
                    master_name=pi['master_name'],
                    price=pi['price'],
                    quantity=pi['quantity'],
                ))

            db.session.commit()
            current_app.logger.info(
                f'Новая заявка #{order.id}: {name}, {phone}, {total} ₽'
            )
            return jsonify({'ok': True, 'order_id': order.id})

        except (InterfaceError, OperationalError) as e:
            db.session.rollback()
            try:
                db.engine.dispose()
            except Exception:
                pass
            current_app.logger.error(f'Обрыв соединения при сохранении заявки: {e}')
            return jsonify({
                'ok': False,
                'error': 'Соединение с БД прервалось. Попробуйте ещё раз.'
            }), 503

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(f'Ошибка сохранения заявки: {e}')
            return jsonify({
                'ok': False,
                'error': 'Ошибка сервера. Попробуйте ещё раз.'
            }), 500

    return render_template('checkout.html')


# ─────────────────────────────────────────────────────────────
#  Статичные страницы
# ─────────────────────────────────────────────────────────────

@bp.route('/thanks')
def thanks():
    return render_template('thanks.html')


@bp.route('/about')
def about():
    return render_template('about.html')


@bp.route('/contacts')
def contacts():
    return render_template('contacts.html')