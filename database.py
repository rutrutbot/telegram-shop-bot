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
        
        # Таблица товаров
        await db.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                icon TEXT,
                price REAL NOT NULL,
                city_id INTEGER,
                FOREIGN KEY (city_id) REFERENCES cities(id)
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

# Товары
async def add_product(name: str, icon: str, price: float, city_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT INTO products (name, icon, price, city_id) VALUES (?, ?, ?, ?)',
                        (name, icon, price, city_id))
        await db.commit()

async def get_products_by_city(city_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM products WHERE city_id = ?', (city_id,)) as cursor:
            return [dict(row) async for row in cursor]

# Районы
async def add_district(name: str, city_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT INTO districts (name, city_id) VALUES (?, ?)', (name, city_id))
        await db.commit()

async def get_districts_by_city(city_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM districts WHERE city_id = ?', (city_id,)) as cursor:
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
