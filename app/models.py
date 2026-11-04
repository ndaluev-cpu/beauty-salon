from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app import db


class Admin(UserMixin, db.Model):
    """Администратор админ-панели."""
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Admin {self.username}>'


class Category(db.Model):
    """Категория услуг: Ногти, Волосы, Брови и т.д."""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Одна категория — много услуг
    services = db.relationship(
        'Service',
        backref='category',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Category {self.name}>'


class Master(db.Model):
    """Мастер / сотрудник салона."""
    __tablename__ = 'masters'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(200))
    description = db.Column(db.Text)
    photo = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Один мастер — много услуг
    services = db.relationship(
        'Service',
        backref='master',
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<Master {self.name}>'


class Service(db.Model):
    """Услуга салона: маникюр, стрижка, окрашивание и т.д."""
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Integer, nullable=False)
    old_price = db.Column(db.Integer)
    duration = db.Column(db.Integer)  # в минутах

    category_id = db.Column(
        db.Integer,
        db.ForeignKey('categories.id', ondelete='SET NULL')
    )
    master_id = db.Column(
        db.Integer,
        db.ForeignKey('masters.id', ondelete='SET NULL')
    )

    image = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    is_new = db.Column(db.Boolean, default=False)
    is_hit = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Service {self.name}>'


class Order(db.Model):
    """Заявка от клиента на услугу(и)."""
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(32), nullable=False)
    email = db.Column(db.String(128))
    comment = db.Column(db.Text)
    preferred_date = db.Column(db.Date)
    preferred_time = db.Column(db.Time)
    total = db.Column(db.Integer, default=0)
    status = db.Column(db.String(32), default='new')  # new, processing, done, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Одна заявка — много позиций
    items = db.relationship(
        'OrderItem',
        backref='order',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Order #{self.id} {self.customer_name}>'


class OrderItem(db.Model):
    """Позиция в заявке (конкретная услуга)."""
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey('orders.id', ondelete='CASCADE'),
        nullable=False
    )
    service_id = db.Column(
        db.Integer,
        db.ForeignKey('services.id', ondelete='SET NULL')
    )
    service_name = db.Column(db.String(200))
    master_name = db.Column(db.String(100))
    price = db.Column(db.Integer)
    quantity = db.Column(db.Integer, default=1)

    def __repr__(self):
        return f'<OrderItem {self.service_name}>'