import aiosqlite
import json
from typing import List, Dict, Optional
from datetime import datetime

DB_NAME = 'shop_bot.db'

async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица городов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                aliases TEXT
            )
        ''')
        
        # Таблица товаров (БЕЗ привязки к городу, БЕЗ иконки)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL
            )
        ''')
        
        # Таблица районов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS districts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                city_id INTEGER,
                FOREIGN KEY (city_id) REFERENCES cities(id)
            )
        ''')
        
        # Таблица связи районов и товаров (многие ко многим)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS district_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                district_id INTEGER,
                product_id INTEGER,
                FOREIGN KEY (district_id) REFERENCES districts(id),
                FOREIGN KEY (product_id) REFERENCES products(id),
                UNIQUE(district_id, product_id)
            )
        ''')
        
        # Таблица способов оплаты
        await db.execute('''
            CREATE TABLE IF NOT EXISTS payment_methods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                code TEXT NOT NULL UNIQUE,
                rate REAL NOT NULL,
                address TEXT,
                enabled INTEGER DEFAULT 1
            )
        ''')
        
        # Таблица клиентов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                blocked INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица заявок
        await db.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number INTEGER UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                product_id INTEGER,
                city_id INTEGER,
                district_id INTEGER,
                payment_method TEXT,
                amount_rub REAL,
                amount_currency REAL,
                currency_code TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (city_id) REFERENCES cities(id),
                FOREIGN KEY (district_id) REFERENCES districts(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Таблица настроек
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        await db.commit()
        
        # Устанавливаем иконку по умолчанию
        await set_setting('product_icon', '📦')

# Города
async def add_city(name: str, aliases: List[str] = None):
    async with aiosqlite.connect(DB_NAME) as db:
        aliases_str = json.dumps(aliases) if aliases else '[]'
        await db.execute('INSERT INTO cities (name, aliases) VALUES (?, ?)', (name, aliases_str))
        await db.commit()

async def find_city(query: str) -> Optional[Dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM cities') as cursor:
            async for row in cursor:
                city_name = row['name'].lower()
                aliases = json.loads(row['aliases'])
                query_lower = query.lower().strip()
                
                if query_lower == city_name or query_lower in [a.lower() for a in aliases]:
                    return dict(row)
    return None

async def get_all_cities() -> List[Dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM cities') as cursor:
            return [dict(row) async for row in cursor]

# Товары (БЕЗ привязки к городу, БЕЗ иконки)
async def add_product(name: str, price: float):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT INTO products (name, price) VALUES (?, ?)', (name, price))
        await db.commit()

async def add_products_bulk(products: List[tuple]):
    """Массовое добавление товаров [(name, price), ...]"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.executemany('INSERT INTO products (name, price) VALUES (?, ?)', products)
        await db.commit()

async def get_all_products() -> List[Dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM products ORDER BY name') as cursor:
            return [dict(row) async for row in cursor]

async def get_products_by_city(city_id: int) -> List[Dict]:
    """Получить все уникальные товары, доступные в городе"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT DISTINCT p.* FROM products p
            JOIN district_products dp ON p.id = dp.product_id
            JOIN districts d ON dp.district_id = d.id
            WHERE d.city_id = ?
            ORDER BY p.name
        ''', (city_id,)) as cursor:
            return [dict(row) async for row in cursor]

async def get_products_by_district(district_id: int) -> List[Dict]:
    """Получить товары доступные в конкретном районе"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT p.* FROM products p
            JOIN district_products dp ON p.id = dp.product_id
            WHERE dp.district_id = ?
            ORDER BY p.name
        ''', (district_id,)) as cursor:
            return [dict(row) async for row in cursor]

async def delete_product(product_id: int):
    """Удалить товар из общего списка и всех районов"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Удаляем связи с районами
        await db.execute('DELETE FROM district_products WHERE product_id = ?', (product_id,))
        # Удаляем товар
        await db.execute('DELETE FROM products WHERE id = ?', (product_id,))
        await db.commit()

async def update_product_name(product_id: int, new_name: str):
    """Изменить название товара"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE products SET name = ? WHERE id = ?', (new_name, product_id))
        await db.commit()

# Районы
async def add_district(name: str, city_id: int, product_ids: List[int]):
    """Добавить район с товарами"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('INSERT INTO districts (name, city_id) VALUES (?, ?)', (name, city_id))
        district_id = cursor.lastrowid
        
        # Добавляем товары в район
        for product_id in product_ids:
            await db.execute('INSERT INTO district_products (district_id, product_id) VALUES (?, ?)',
                           (district_id, product_id))
        
        await db.commit()
        return district_id

async def get_districts_by_city(city_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM districts WHERE city_id = ?', (city_id,)) as cursor:
            return [dict(row) async for row in cursor]

async def get_districts_by_city_and_product(city_id: int, product_id: int) -> List[Dict]:
    """Получить районы города, где доступен конкретный товар"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT DISTINCT d.* FROM districts d
            JOIN district_products dp ON d.id = dp.district_id
            WHERE d.city_id = ? AND dp.product_id = ?
        ''', (city_id, product_id)) as cursor:
            return [dict(row) async for row in cursor]

# Заявки
async def create_order(user_id: int, product_id: int, city_id: int, district_id: int, 
                      payment_method: str, amount_rub: float, amount_currency: float, currency_code: str) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        # Получаем последний номер заявки
        async with db.execute('SELECT MAX(order_number) as max_num FROM orders') as cursor:
            row = await cursor.fetchone()
            from config import INITIAL_ORDER_NUMBER
            next_number = (row[0] + 1) if row[0] else INITIAL_ORDER_NUMBER
        
        await db.execute('''
            INSERT INTO orders (order_number, user_id, product_id, city_id, district_id, 
                              payment_method, amount_rub, amount_currency, currency_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (next_number, user_id, product_id, city_id, district_id, 
              payment_method, amount_rub, amount_currency, currency_code))
        await db.commit()
        return next_number

async def get_order_by_number(order_number: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM orders WHERE order_number = ?', (order_number,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def cancel_order(order_number: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE orders SET status = ? WHERE order_number = ?', ('cancelled', order_number))
        await db.commit()

async def complete_order(order_number: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE orders SET status = ? WHERE order_number = ?', ('paid', order_number))
        await db.commit()

# Настройки
async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        await db.commit()

async def get_setting(key: str, default: str = '') -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT value FROM settings WHERE key = ?', (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default

# Удаление и редактирование
async def delete_city(city_id: int):
    """Удалить город со всеми районами и связями товаров"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Получаем все районы города
        async with db.execute('SELECT id FROM districts WHERE city_id = ?', (city_id,)) as cursor:
            district_ids = [row[0] async for row in cursor]
        
        # Удаляем связи товаров с районами
        for district_id in district_ids:
            await db.execute('DELETE FROM district_products WHERE district_id = ?', (district_id,))
        
        # Удаляем районы
        await db.execute('DELETE FROM districts WHERE city_id = ?', (city_id,))
        
        # Удаляем город
        await db.execute('DELETE FROM cities WHERE id = ?', (city_id,))
        
        await db.commit()

async def delete_district(district_id: int):
    """Удалить район со всеми связями товаров"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Удаляем связи товаров
        await db.execute('DELETE FROM district_products WHERE district_id = ?', (district_id,))
        
        # Удаляем район
        await db.execute('DELETE FROM districts WHERE id = ?', (district_id,))
        
        await db.commit()

async def delete_product_from_district(district_id: int, product_id: int):
    """Удалить товар из района"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM district_products WHERE district_id = ? AND product_id = ?',
                        (district_id, product_id))
        await db.commit()

async def add_product_to_district(district_id: int, product_id: int):
    """Добавить товар в район"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Проверяем, нет ли уже этого товара в районе
        async with db.execute(
            'SELECT * FROM district_products WHERE district_id = ? AND product_id = ?',
            (district_id, product_id)
        ) as cursor:
            existing = await cursor.fetchone()
            if existing:
                return False  # Товар уже есть
        
        # Добавляем товар
        await db.execute('INSERT INTO district_products (district_id, product_id) VALUES (?, ?)',
                        (district_id, product_id))
        await db.commit()
        return True  # Товар добавлен

async def update_product_price(product_id: int, new_price: float):
    """Изменить цену товара"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE products SET price = ? WHERE id = ?', (new_price, product_id))
        await db.commit()

async def get_product_by_id(product_id: int) -> Optional[Dict]:
    """Получить товар по ID"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM products WHERE id = ?', (product_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_district_by_id(district_id: int) -> Optional[Dict]:
    """Получить район по ID"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM districts WHERE id = ?', (district_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_city_by_id(city_id: int) -> Optional[Dict]:
    """Получить город по ID"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM cities WHERE id = ?', (city_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# Способы оплаты
async def add_payment_method(name: str, code: str, rate: float, address: str = ''):
    """Добавить способ оплаты"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT INTO payment_methods (name, code, rate, address) VALUES (?, ?, ?, ?)',
            (name, code, rate, address)
        )
        await db.commit()

async def get_all_payment_methods() -> List[Dict]:
    """Получить все способы оплаты"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM payment_methods ORDER BY id') as cursor:
            return [dict(row) async for row in cursor]

async def get_enabled_payment_methods() -> List[Dict]:
    """Получить активные способы оплаты"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM payment_methods WHERE enabled = 1 ORDER BY id') as cursor:
            return [dict(row) async for row in cursor]

async def get_payment_method_by_code(code: str) -> Optional[Dict]:
    """Получить способ оплаты по коду"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM payment_methods WHERE code = ?', (code,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_payment_method_rate(code: str, new_rate: float):
    """Обновить курс способа оплаты"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE payment_methods SET rate = ? WHERE code = ?', (new_rate, code))
        await db.commit()

async def update_payment_method_address(code: str, new_address: str):
    """Обновить адрес/номер способа оплаты"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE payment_methods SET address = ? WHERE code = ?', (new_address, code))
        await db.commit()

async def delete_payment_method(code: str):
    """Удалить способ оплаты"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM payment_methods WHERE code = ?', (code,))
        await db.commit()

async def toggle_payment_method(code: str):
    """Включить/выключить способ оплаты"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE payment_methods SET enabled = 1 - enabled WHERE code = ?', (code,))
        await db.commit()

# Клиенты
async def add_or_update_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Добавить или обновить пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO users (id, username, first_name, last_name) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name
        ''', (user_id, username, first_name, last_name))
        await db.commit()

async def get_all_users() -> List[Dict]:
    """Получить всех пользователей"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM users ORDER BY created_at DESC') as cursor:
            return [dict(row) async for row in cursor]

async def block_user(user_id: int):
    """Заблокировать пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET blocked = 1 WHERE id = ?', (user_id,))
        await db.commit()

async def unblock_user(user_id: int):
    """Разблокировать пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET blocked = 0 WHERE id = ?', (user_id,))
        await db.commit()

async def is_user_blocked(user_id: int) -> bool:
    """Проверить, заблокирован ли пользователь"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT blocked FROM users WHERE id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else False

# Статистика
async def get_orders_count(start_date: str = None, end_date: str = None) -> int:
    """Получить количество заказов за период"""
    async with aiosqlite.connect(DB_NAME) as db:
        if start_date and end_date:
            async with db.execute(
                'SELECT COUNT(*) FROM orders WHERE created_at BETWEEN ? AND ?',
                (start_date, end_date)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0]
        else:
            async with db.execute('SELECT COUNT(*) FROM orders') as cursor:
                row = await cursor.fetchone()
                return row[0]

async def get_orders_by_status(status: str, start_date: str = None, end_date: str = None) -> List[Dict]:
    """Получить заказы по статусу за период"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        if start_date and end_date:
            async with db.execute(
                'SELECT * FROM orders WHERE status = ? AND created_at BETWEEN ? AND ? ORDER BY created_at DESC',
                (status, start_date, end_date)
            ) as cursor:
                return [dict(row) async for row in cursor]
        else:
            async with db.execute('SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC', (status,)) as cursor:
                return [dict(row) async for row in cursor]

# Экспорт/Импорт
async def export_catalog() -> Dict:
    """Экспорт витрины (товары, города, районы, связи)"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # Товары
        async with db.execute('SELECT * FROM products') as cursor:
            products = [dict(row) async for row in cursor]
        
        # Города
        async with db.execute('SELECT * FROM cities') as cursor:
            cities = [dict(row) async for row in cursor]
        
        # Районы
        async with db.execute('SELECT * FROM districts') as cursor:
            districts = [dict(row) async for row in cursor]
        
        # Связи товаров и районов
        async with db.execute('SELECT * FROM district_products') as cursor:
            district_products = [dict(row) async for row in cursor]
        
        # Способы оплаты
        async with db.execute('SELECT * FROM payment_methods') as cursor:
            payment_methods = [dict(row) async for row in cursor]
        
        # Иконка товаров
        product_icon = await get_setting('product_icon', '📦')
        
        return {
            'products': products,
            'cities': cities,
            'districts': districts,
            'district_products': district_products,
            'payment_methods': payment_methods,
            'product_icon': product_icon
        }

async def import_catalog(data: Dict):
    """Импорт витрины"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Очищаем старые данные
        await db.execute('DELETE FROM district_products')
        await db.execute('DELETE FROM districts')
        await db.execute('DELETE FROM cities')
        await db.execute('DELETE FROM products')
        await db.execute('DELETE FROM payment_methods')
        
        # Импортируем товары
        for product in data.get('products', []):
            await db.execute(
                'INSERT INTO products (id, name, price) VALUES (?, ?, ?)',
                (product['id'], product['name'], product['price'])
            )
        
        # Импортируем города
        for city in data.get('cities', []):
            await db.execute(
                'INSERT INTO cities (id, name, aliases) VALUES (?, ?, ?)',
                (city['id'], city['name'], city['aliases'])
            )
        
        # Импортируем районы
        for district in data.get('districts', []):
            await db.execute(
                'INSERT INTO districts (id, name, city_id) VALUES (?, ?, ?)',
                (district['id'], district['name'], district['city_id'])
            )
        
        # Импортируем связи
        for dp in data.get('district_products', []):
            await db.execute(
                'INSERT INTO district_products (id, district_id, product_id) VALUES (?, ?, ?)',
                (dp['id'], dp['district_id'], dp['product_id'])
            )
        
        # Импортируем способы оплаты
        for pm in data.get('payment_methods', []):
            await db.execute(
                'INSERT INTO payment_methods (id, name, code, rate, address, enabled) VALUES (?, ?, ?, ?, ?, ?)',
                (pm['id'], pm['name'], pm['code'], pm['rate'], pm.get('address', ''), pm.get('enabled', 1))
            )
        
        # Импортируем иконку
        if 'product_icon' in data:
            await set_setting('product_icon', data['product_icon'])
        
        await db.commit()

async def export_data() -> Dict:
    """Экспорт данных (клиенты, заказы)"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # Клиенты
        async with db.execute('SELECT * FROM users') as cursor:
            users = [dict(row) async for row in cursor]
        
        # Заказы
        async with db.execute('SELECT * FROM orders') as cursor:
            orders = [dict(row) async for row in cursor]
        
        return {
            'users': users,
            'orders': orders
        }

async def import_data(data: Dict):
    """Импорт данных"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Очищаем старые данные
        await db.execute('DELETE FROM orders')
        await db.execute('DELETE FROM users')
        
        # Импортируем клиентов
        for user in data.get('users', []):
            await db.execute(
                'INSERT INTO users (id, username, first_name, last_name, blocked, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (user['id'], user.get('username'), user.get('first_name'), user.get('last_name'), 
                 user.get('blocked', 0), user.get('created_at'))
            )
        
        # Импортируем заказы
        for order in data.get('orders', []):
            await db.execute('''
                INSERT INTO orders (id, order_number, user_id, product_id, city_id, district_id,
                                  payment_method, amount_rub, amount_currency, currency_code, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order['id'], order['order_number'], order['user_id'], order.get('product_id'),
                  order.get('city_id'), order.get('district_id'), order.get('payment_method'),
                  order.get('amount_rub'), order.get('amount_currency'), order.get('currency_code'),
                  order.get('status', 'pending'), order.get('created_at')))
        
        await db.commit()
