from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Dict

def city_confirmation_kb(city_name: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения города"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_city_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"confirm_city_no")
        ],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

def products_kb(products: List[Dict], product_icon: str = '📦') -> InlineKeyboardMarkup:
    """Клавиатура выбора товара"""
    buttons = []
    for product in products:
        text = f"{product_icon} {product['name']} - {product['price']}₽"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"product_{product['id']}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_city")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def districts_kb(districts: List[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура выбора района"""
    buttons = []
    for district in districts:
        buttons.append([InlineKeyboardButton(text=district['name'], callback_data=f"district_{district['id']}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_products")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_methods_kb(payment_methods: List[Dict]) -> InlineKeyboardMarkup:
    """Клавиатура выбора способа оплаты"""
    buttons = []
    for pm in payment_methods:
        buttons.append([InlineKeyboardButton(text=pm['name'], callback_data=f"payment_{pm['code']}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_districts")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def order_confirmation_kb(operator_link: str = None) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения оплаты"""
    buttons = [
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="order_paid")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="order_cancel")]
    ]
    
    if operator_link:
        buttons.append([InlineKeyboardButton(text="👤 Связаться с оператором", url=operator_link)])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def contact_operator_kb(operator_link: str) -> InlineKeyboardMarkup:
    """Клавиатура со ссылкой на оператора"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Связаться с оператором", url=operator_link)],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

def admin_main_kb() -> ReplyKeyboardMarkup:
    """Главная клавиатура админа"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏙 Города"), KeyboardButton(text="📦 Товары")],
            [KeyboardButton(text="📍 Районы"), KeyboardButton(text="💱 Оплата")],
            [KeyboardButton(text="👥 Клиенты"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="⚙️ Настройки")]
        ],
        resize_keyboard=True
    )
