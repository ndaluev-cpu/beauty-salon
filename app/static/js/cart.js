/**
 * Корзина заявок MODA.
 * Работает и для услуг (без size/color), и для товаров (с size/color).
 * Хранится в localStorage под ключом 'shop_cart'.
 */
const Cart = {
    items: [],

    // ── Инициализация ──────────────────────────────────────
    init() {
        this.load();
    },

    load() {
        try {
            const saved = localStorage.getItem('shop_cart');
            this.items = saved ? JSON.parse(saved) : [];
            if (!Array.isArray(this.items)) this.items = [];
        } catch (e) {
            console.warn('Cart: не удалось прочитать localStorage', e);
            this.items = [];
        }
        this.updateUI();
    },

    save() {
        try {
            localStorage.setItem('shop_cart', JSON.stringify(this.items));
        } catch (e) {
            console.warn('Cart: не удалось сохранить в localStorage', e);
        }
        this.updateUI();
    },

    // ── Ключ позиции: услуги без size/color, товары с ними ──
    keyOf(p) {
        return `${p.id}_${p.size || ''}_${p.color || ''}`;
    },

    // ── Добавить ───────────────────────────────────────────
    /**
     * @param {Object} product
     *   { id, name, price, image, size?, color? }
     */
    add(product) {
        if (!product || product.id === undefined) return;

        const k = this.keyOf(product);
        const existing = this.items.find(i => this.keyOf(i) === k);

        if (existing) {
            existing.quantity += 1;
        } else {
            this.items.push({
                id: product.id,
                name: product.name || '',
                price: Number(product.price) || 0,
                image: product.image || '',
                size: product.size || '',
                color: product.color || '',
                quantity: 1,
            });
        }
        this.save();
        this.showNotification('Добавлено в заявку');
    },

    // ── Удалить ────────────────────────────────────────────
    /**
     * Можно вызывать:
     *   Cart.remove(id)                — удалит все позиции с этим id
     *   Cart.remove(id, size, color)   — удалит конкретную позицию
     */
    remove(id, size, color) {
        if (size === undefined && color === undefined) {
            // удалить все позиции с этим id
            this.items = this.items.filter(i => i.id !== id);
        } else {
            this.items = this.items.filter(i => {
                return !(i.id === id
                    && (i.size || '') === (size || '')
                    && (i.color || '') === (color || ''));
            });
        }
        this.save();
    },

    // ── Изменить количество ────────────────────────────────
    /**
     * Cart.updateQuantity(id, quantity)
     * Cart.updateQuantity(id, quantity, size, color)
     */
    updateQuantity(id, quantity, size, color) {
        const item = (size === undefined && color === undefined)
            ? this.items.find(i => i.id === id)
            : this.items.find(i =>
                i.id === id
                && (i.size || '') === (size || '')
                && (i.color || '') === (color || '')
            );
        if (!item) return;

        const q = Math.max(0, Number(quantity) || 0);
        if (q === 0) {
            this.remove(id, item.size, item.color);
            return;
        }
        item.quantity = q;
        this.save();
    },

    // ── Очистить ───────────────────────────────────────────
    clear() {
        this.items = [];
        this.save();
    },

    // ── Суммы ──────────────────────────────────────────────
    getTotal() {
        return this.items.reduce(
            (sum, i) => sum + (Number(i.price) || 0) * (Number(i.quantity) || 0),
            0
        );
    },

    getCount() {
        return this.items.reduce(
            (sum, i) => sum + (Number(i.quantity) || 0),
            0
        );
    },

    // ── UI: счётчик в шапке ────────────────────────────────
    updateUI() {
        document.querySelectorAll('.cart-count').forEach(el => {
            el.textContent = this.getCount();
        });
    },

    // ── Тост ───────────────────────────────────────────────
    showNotification(message) {
        const n = document.createElement('div');
        n.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #d4819a;
            color: #fff;
            padding: 14px 22px;
            border-radius: 10px;
            box-shadow: 0 8px 24px rgba(181,101,129,.35);
            z-index: 9999;
            font-family: 'Poppins', sans-serif;
            font-size: 14px;
            font-weight: 500;
            opacity: 0;
            transform: translateY(10px);
            transition: opacity .25s, transform .25s;
        `;
        n.textContent = message;
        document.body.appendChild(n);
        requestAnimationFrame(() => {
            n.style.opacity = '1';
            n.style.transform = 'translateY(0)';
        });
        setTimeout(() => {
            n.style.opacity = '0';
            n.style.transform = 'translateY(10px)';
            setTimeout(() => n.remove(), 300);
        }, 1800);
    }
};

document.addEventListener('DOMContentLoaded', () => Cart.init());