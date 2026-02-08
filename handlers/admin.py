from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
from config import ADMIN_IDS

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

class AdminStates(StatesGroup):
    # Города
    adding_city_name = State()
    adding_city_aliases = State()
    
    # Товары
    selecting_city_for_product = State()
    adding_product_name = State()
    adding_product_icon = State()
    adding_product_price = State()
    
    # Районы
    selecting_city_for_district = State()
    adding_district_name = State()
    
    # Настройки
    setting_card_number = State()
    setting_payment_instruction = State()
    setting_btc_address = State()
    setting_btc_instruction = State()
    setting_operator_link = State()
    setting_success_message = State()
    setting_timeout_message = State()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=kb.admin_main_kb(),
        parse_mode='HTML'
    )

# === ГОРОДА ===
@router.message(F.text == "🏙 Города")
async def cities_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    cities = await db.get_all_cities()
    cities_text = "\n".join([f"• {city['name']}" for city in cities]) if cities else "Нет городов"
    
    await message.answer(
        f"🏙 <b>Города:</b>\n\n{cities_text}\n\n"
        "Для добавления города используйте:\n"
        "/add_city",
        parse_mode='HTML'
    )

@router.message(Command("add_city"))
async def add_city_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("Введите название города:")
    await state.set_state(AdminStates.adding_city_name)

@router.message(AdminStates.adding_city_name)
async def add_city_name(message: Message, state: FSMContext):
    await state.update_data(city_name=message.text)
    await message.answer(
        "Введите варианты написания города через запятую\n"
        "(например: Москва, москва, Moskva)\n\n"
        "Или отправьте '-' чтобы пропустить:"
    )
    await state.set_state(AdminStates.adding_city_aliases)

@router.message(AdminStates.adding_city_aliases)
async def add_city_aliases(message: Message, state: FSMContext):
    data = await state.get_data()
    city_name = data['city_name']
    
    aliases = []
    if message.text != '-':
        aliases = [a.strip() for a in message.text.split(',')]
    
    await db.add_city(city_name, aliases)
    await message.answer(f"✅ Город '{city_name}' добавлен!")
    await state.clear()

# === ТОВАРЫ ===
@router.message(F.text == "📦 Товары")
async def products_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "📦 <b>Товары</b>\n\n"
        "Для добавления товара используйте:\n"
        "/add_product",
        parse_mode='HTML'
    )

@router.message(Command("add_product"))
async def add_product_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    cities = await db.get_all_cities()
    if not cities:
        await message.answer("❌ Сначала добавьте города!")
        return
    
    cities_text = "\n".join([f"{i+1}. {city['name']}" for i, city in enumerate(cities)])
    await state.update_data(cities=cities)
    
    await message.answer(
        f"Выберите город (введите номер):\n\n{cities_text}"
    )
    await state.set_state(AdminStates.selecting_city_for_product)

@router.message(AdminStates.selecting_city_for_product)
async def select_city_for_product(message: Message, state: FSMContext):
    data = await state.get_data()
    cities = data['cities']
    
    try:
        city_index = int(message.text) - 1
        city = cities[city_index]
        await state.update_data(city_id=city['id'])
        await message.answer("Введите название товара:")
        await state.set_state(AdminStates.adding_product_name)
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер города. Попробуйте еще раз:")

@router.message(AdminStates.adding_product_name)
async def add_product_name(message: Message, state: FSMContext):
    await state.update_data(product_name=message.text)
    await message.answer("Введите иконку товара (emoji) или '-' чтобы пропустить:")
    await state.set_state(AdminStates.adding_product_icon)

@router.message(AdminStates.adding_product_icon)
async def add_product_icon(message: Message, state: FSMContext):
    icon = message.text if message.text != '-' else '📦'
    await state.update_data(product_icon=icon)
    await message.answer("Введите цену товара (в рублях):")
    await state.set_state(AdminStates.adding_product_price)

@router.message(AdminStates.adding_product_price)
async def add_product_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        data = await state.get_data()
        
        await db.add_product(
            name=data['product_name'],
            icon=data['product_icon'],
            price=price,
            city_id=data['city_id']
        )
        
        await message.answer(f"✅ Товар '{data['product_name']}' добавлен!")
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверная цена. Введите число:")

# === РАЙОНЫ ===
@router.message(F.text == "📍 Районы")
async def districts_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "📍 <b>Районы</b>\n\n"
        "Для добавления района используйте:\n"
        "/add_district",
        parse_mode='HTML'
    )

@router.message(Command("add_district"))
async def add_district_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    cities = await db.get_all_cities()
    if not cities:
        await message.answer("❌ Сначала добавьте города!")
        return
    
    cities_text = "\n".join([f"{i+1}. {city['name']}" for i, city in enumerate(cities)])
    await state.update_data(cities=cities)
    
    await message.answer(
        f"Выберите город (введите номер):\n\n{cities_text}"
    )
    await state.set_state(AdminStates.selecting_city_for_district)

@router.message(AdminStates.selecting_city_for_district)
async def select_city_for_district(message: Message, state: FSMContext):
    data = await state.get_data()
    cities = data['cities']
    
    try:
        city_index = int(message.text) - 1
        city = cities[city_index]
        await state.update_data(city_id=city['id'])
        await message.answer("Введите название района:")
        await state.set_state(AdminStates.adding_district_name)
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер города. Попробуйте еще раз:")

@router.message(AdminStates.adding_district_name)
async def add_district_name(message: Message, state: FSMContext):
    data = await state.get_data()
    
    await db.add_district(
        name=message.text,
        city_id=data['city_id']
    )
    
    await message.answer(f"✅ Район '{message.text}' добавлен!")
    await state.clear()

# === НАСТРОЙКИ ===
@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    card_number = await db.get_setting('card_number', 'Не указан')
    operator_link = await db.get_setting('operator_link', 'Не указана')
    
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        f"💳 Номер карты: <code>{card_number}</code>\n"
        f"👤 Ссылка на оператора: {operator_link}\n\n"
        "Команды:\n"
        "/set_card - Установить номер карты\n"
        "/set_payment_instruction - Инструкция по оплате картой\n"
        "/set_btc - Установить Bitcoin адрес\n"
        "/set_btc_instruction - Инструкция по оплате BTC\n"
        "/set_operator - Установить ссылку на оператора\n"
        "/set_success_message - Сообщение после оплаты\n"
        "/set_timeout_message - Сообщение при истечении времени",
        parse_mode='HTML'
    )

@router.message(Command("set_card"))
async def set_card(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите номер карты:")
    await state.set_state(AdminStates.setting_card_number)

@router.message(AdminStates.setting_card_number)
async def save_card(message: Message, state: FSMContext):
    await db.set_setting('card_number', message.text)
    await message.answer("✅ Номер карты сохранен!")
    await state.clear()

@router.message(Command("set_payment_instruction"))
async def set_payment_instruction(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите инструкцию по оплате картой:")
    await state.set_state(AdminStates.setting_payment_instruction)

@router.message(AdminStates.setting_payment_instruction)
async def save_payment_instruction(message: Message, state: FSMContext):
    await db.set_setting('payment_instruction', message.text)
    await message.answer("✅ Инструкция сохранена!")
    await state.clear()

@router.message(Command("set_operator"))
async def set_operator(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите ссылку на оператора (например: https://t.me/username):")
    await state.set_state(AdminStates.setting_operator_link)

@router.message(AdminStates.setting_operator_link)
async def save_operator(message: Message, state: FSMContext):
    await db.set_setting('operator_link', message.text)
    await message.answer("✅ Ссылка на оператора сохранена!")
    await state.clear()

@router.message(Command("set_success_message"))
async def set_success_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите сообщение, которое увидит клиент после нажатия 'Я оплатил':")
    await state.set_state(AdminStates.setting_success_message)

@router.message(AdminStates.setting_success_message)
async def save_success_message(message: Message, state: FSMContext):
    await db.set_setting('payment_success_message', message.text)
    await message.answer("✅ Сообщение сохранено!")
    await state.clear()

@router.message(Command("set_timeout_message"))
async def set_timeout_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите сообщение при истечении времени на оплату:")
    await state.set_state(AdminStates.setting_timeout_message)

@router.message(AdminStates.setting_timeout_message)
async def save_timeout_message(message: Message, state: FSMContext):
    await db.set_setting('order_timeout_message', message.text)
    await message.answer("✅ Сообщение сохранено!")
    await state.clear()
