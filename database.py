import aiosqlite
import json
from typing import List, Dict, Optional

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
        
        # Таблица товаров (БЕЗ привязки к городу)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                icon TEXT,
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
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (city_id) REFERENCES cities(id),
                FOREIGN KEY (district_id) REFERENCES districts(id)
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

# Товары (БЕЗ привязки к городу)
async def add_product(name: str, icon: str, price: float):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT INTO products (name, icon, price) VALUES (?, ?, ?)',
                        (name, icon, price))
        await db.commit()

async def get_all_products() -> List[Dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM products') as cursor:
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
        ''', (district_id,)) as cursor:
            return [dict(row) async for row in cursor]

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
async def create_order(user_id: int, product_id: int, city_id: int, district_id: int, payment_method: str) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        # Получаем последний номер заявки
        async with db.execute('SELECT MAX(order_number) as max_num FROM orders') as cursor:
            row = await cursor.fetchone()
            from config import INITIAL_ORDER_NUMBER
            next_number = (row[0] + 1) if row[0] else INITIAL_ORDER_NUMBER
        
        await db.execute('''
            INSERT INTO orders (order_number, user_id, product_id, city_id, district_id, payment_method)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (next_number, user_id, product_id, city_id, district_id, payment_method))
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
