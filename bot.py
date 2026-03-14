import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession

from config import BOT_TOKEN, PROXY_URL
import database as db
from handlers import client, admin

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота с прокси (если задан)
if PROXY_URL:
    session = AiohttpSession(proxy=PROXY_URL)
    bot = Bot(token=BOT_TOKEN, session=session)
else:
    bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключение роутеров
dp.include_router(client.router)
dp.include_router(admin.router)

async def main():
    """Запуск бота"""
    # Инициализация базы данных
    await db.init_db()
    
    print("🤖 Бот запущен!")
    
    # Запуск polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
