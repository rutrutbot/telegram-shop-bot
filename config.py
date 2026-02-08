import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]

# Начальный номер заявки
INITIAL_ORDER_NUMBER = 10207903

# Время на оплату (в секундах)
PAYMENT_TIMEOUT = 30 * 60  # 30 минут
