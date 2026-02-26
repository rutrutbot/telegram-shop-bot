from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json
from datetime import datetime, timedelta

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
    deleting_city = State()
    
    # Товары
    adding_products_bulk = State()
    deleting_product = State()
    editing_product_name_select = State()
    editing_product_name_new = State()
    setting_product_icon = State()
    
    # Районы
    selecting_city_for_district = State()
    adding_district_name = State()
    selecting_products_for_district = State()
    deleting_district_city = State()
    deleting_district = State()
    removing_product_from_district_city = State()
    removing_product_from_district_district = State()
    removing_product_from_district_product = State()
    adding_product_to_district_city = State()
    adding_product_to_district_district = State()
    adding_product_to_district_products = State()
    
    # Способы оплаты
    adding_payment_name = State()
    adding_payment_code = State()
    adding_payment_rate = State()
    adding_payment_address = State()
    adding_payment_instruction = State()
    editing_rate_select = State()
    editing_rate_new = State()
    editing_address_select = State()
    editing_address_new = State()
    deleting_payment = State()
    
    # Клиенты
    blocking_user = State()
    unblocking_user = State()
    
    # Статистика
    stats_period = State()
    
    # Настройки
    setting_operator_link = State()
    setting_success_message = State()
    setting_timeout_message = State()


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    """Админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    await state.clear()
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=kb.admin_main_kb(),
        parse_mode='HTML'
    )

# === ГОРОДА ===
@router.message(F.text == "🏙 Города")
async def cities_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    cities = await db.get_all_cities()
    cities_text = "\n".join([f"• {city['name']}" for city in cities]) if cities else "Нет городов"
    
    await message.answer(
        f"🏙 <b>Города:</b>\n\n{cities_text}\n\n"
        "Команды:\n"
        "/add_city - Добавить город\n"
        "/delete_city - Удалить город",
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

@router.message(Command("delete_city"))
async def delete_city_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    cities = await db.get_all_cities()
    if not cities:
        await message.answer("❌ Нет городов для удаления!")
        return
    
    cities_text = "\n".join([f"{i+1}. {city['name']}" for i, city in enumerate(cities)])
    await state.update_data(cities=cities)
    
    await message.answer(
        f"⚠️ <b>Удаление города</b>\n\n"
        f"Выберите город для удаления (введите номер):\n\n{cities_text}\n\n"
        f"<i>Будут удалены все районы и связи товаров этого города.\n"
        f"Товары останутся в общем списке.</i>",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.deleting_city)

@router.message(AdminStates.deleting_city)
async def delete_city_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    cities = data['cities']
    
    try:
        city_index = int(message.text) - 1
        city = cities[city_index]
        
        await db.delete_city(city['id'])
        await message.answer(f"✅ Город '{city['name']}' удален со всеми районами!")
        await state.clear()
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер города. Попробуйте еще раз:")


# === ТОВАРЫ ===
@router.message(F.text == "📦 Товары")
async def products_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    products = await db.get_all_products()
    product_icon = await db.get_setting('product_icon', '📦')
    products_text = "\n".join([f"• {product_icon} {p['name']} - {p['price']}₽" for p in products]) if products else "Нет товаров"
    
    await message.answer(
        f"📦 <b>Товары:</b>\n\n{products_text}\n\n"
        f"Текущая иконка: {product_icon}\n\n"
        "Команды:\n"
        "/add_products_bulk - Массовое добавление товаров\n"
        "/delete_product - Удалить товар\n"
        "/edit_product_name - Изменить название товара\n"
        "/set_product_icon - Изменить иконку для всех товаров",
        parse_mode='HTML'
    )

@router.message(Command("add_products_bulk"))
async def add_products_bulk_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "📝 <b>Массовое добавление товаров</b>\n\n"
        "Отправьте список товаров в формате:\n"
        "<code>Название - Цена</code>\n\n"
        "Пример:\n"
        "<code>Товар А - 3000\n"
        "Товар Б - 5000\n"
        "Товар В - 12000</code>",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.adding_products_bulk)

@router.message(AdminStates.adding_products_bulk)
async def add_products_bulk_process(message: Message, state: FSMContext):
    try:
        lines = message.text.strip().split('\n')
        products = []
        
        for line in lines:
            if '-' not in line:
                continue
            parts = line.split('-')
            if len(parts) != 2:
                continue
            
            name = parts[0].strip()
            price = float(parts[1].strip())
            products.append((name, price))
        
        if not products:
            await message.answer("❌ Не удалось распознать товары. Проверьте формат.")
            return
        
        await db.add_products_bulk(products)
        await message.answer(f"✅ Добавлено товаров: {len(products)}")
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}\n\nПроверьте формат данных.")

@router.message(Command("delete_product"))
async def delete_product_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    products = await db.get_all_products()
    if not products:
        await message.answer("❌ Нет товаров!")
        return
    
    product_icon = await db.get_setting('product_icon', '📦')
    products_text = "\n".join([f"{i+1}. {product_icon} {p['name']} - {p['price']}₽" for i, p in enumerate(products)])
    await state.update_data(products=products)
    
    await message.answer(
        f"⚠️ <b>Удаление товара</b>\n\n"
        f"Выберите товар (введите номер):\n\n{products_text}\n\n"
        f"<i>Товар будет удален из всех районов!</i>",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.deleting_product)

@router.message(AdminStates.deleting_product)
async def delete_product_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    products = data['products']
    
    try:
        product_index = int(message.text) - 1
        product = products[product_index]
        
        await db.delete_product(product['id'])
        await message.answer(f"✅ Товар '{product['name']}' удален из всех районов!")
        await state.clear()
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер товара. Попробуйте еще раз:")

@router.message(Command("edit_product_name"))
async def edit_product_name_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    products = await db.get_all_products()
    if not products:
        await message.answer("❌ Нет товаров!")
        return
    
    product_icon = await db.get_setting('product_icon', '📦')
    products_text = "\n".join([f"{i+1}. {product_icon} {p['name']}" for i, p in enumerate(products)])
    await state.update_data(products=products)
    
    await message.answer(
        f"✏️ <b>Изменение названия товара</b>\n\n"
        f"Выберите товар (введите номер):\n\n{products_text}",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.editing_product_name_select)

@router.message(AdminStates.editing_product_name_select)
async def edit_product_name_select(message: Message, state: FSMContext):
    data = await state.get_data()
    products = data['products']
    
    try:
        product_index = int(message.text) - 1
        product = products[product_index]
        await state.update_data(selected_product=product)
        
        await message.answer(
            f"Текущее название: <b>{product['name']}</b>\n\n"
            f"Введите новое название:",
            parse_mode='HTML'
        )
        await state.set_state(AdminStates.editing_product_name_new)
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер товара. Попробуйте еще раз:")

@router.message(AdminStates.editing_product_name_new)
async def edit_product_name_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    product = data['selected_product']
    new_name = message.text.strip()
    
    await db.update_product_name(product['id'], new_name)
    await message.answer(
        f"✅ Название товара изменено:\n"
        f"'{product['name']}' → '{new_name}'"
    )
    await state.clear()

@router.message(Command("set_product_icon"))
async def set_product_icon_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    current_icon = await db.get_setting('product_icon', '📦')
    await message.answer(
        f"🎨 <b>Изменение иконки товаров</b>\n\n"
        f"Текущая иконка: {current_icon}\n\n"
        f"Отправьте новую иконку (emoji):",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.setting_product_icon)

@router.message(AdminStates.setting_product_icon)
async def set_product_icon_confirm(message: Message, state: FSMContext):
    new_icon = message.text.strip()
    await db.set_setting('product_icon', new_icon)
    await message.answer(f"✅ Иконка товаров изменена на: {new_icon}")
    await state.clear()
# ПРОДОЛЖЕНИЕ handlers/admin_complete.py
# Этот код нужно добавить в конец файла handlers/admin_complete.py

# === РАЙОНЫ ===
@router.message(F.text == "📍 Районы")
async def districts_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    await message.answer(
        "📍 <b>Районы</b>\n\n"
        "Команды:\n"
        "/add_district - Добавить район\n"
        "/delete_district - Удалить район\n"
        "/add_product_to_district - Добавить товар в район\n"
        "/remove_product - Удалить товар из района",
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
    await state.update_data(district_name=message.text)
    
    products = await db.get_all_products()
    
    if not products:
        await message.answer("❌ Сначала добавьте товары через /add_products_bulk!")
        await state.clear()
        return
    
    product_icon = await db.get_setting('product_icon', '📦')
    products_text = "\n".join([f"{i+1}. {product_icon} {p['name']} - {p['price']}₽" for i, p in enumerate(products)])
    await state.update_data(products=products)
    
    await message.answer(
        f"📦 <b>Выберите товары для этого района</b>\n\n"
        f"{products_text}\n\n"
        f"Введите номера товаров через запятую (например: 1,3,5)\n"
        f"Или введите 'все' чтобы добавить все товары:",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.selecting_products_for_district)

@router.message(AdminStates.selecting_products_for_district)
async def select_products_for_district(message: Message, state: FSMContext):
    data = await state.get_data()
    products = data['products']
    
    try:
        if message.text.lower() == 'все':
            product_ids = [p['id'] for p in products]
        else:
            indices = [int(x.strip()) - 1 for x in message.text.split(',')]
            product_ids = [products[i]['id'] for i in indices]
        
        await db.add_district(
            name=data['district_name'],
            city_id=data['city_id'],
            product_ids=product_ids
        )
        
        await message.answer(f"✅ Район '{data['district_name']}' добавлен с {len(product_ids)} товарами!")
        await state.clear()
    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат. Введите номера через запятую (например: 1,2,3):")


@router.message(Command("delete_district"))
async def delete_district_start(message: Message, state: FSMContext):
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
    await state.set_state(AdminStates.deleting_district_city)

@router.message(AdminStates.deleting_district_city)
async def delete_district_select_city(message: Message, state: FSMContext):
    data = await state.get_data()
    cities = data['cities']
    
    try:
        city_index = int(message.text) - 1
        city = cities[city_index]
        
        districts = await db.get_districts_by_city(city['id'])
        if not districts:
            await message.answer(f"❌ В городе '{city['name']}' нет районов!")
            await state.clear()
            return
        
        districts_text = "\n".join([f"{i+1}. {d['name']}" for i, d in enumerate(districts)])
        await state.update_data(city=city, districts=districts)
        
        await message.answer(
            f"⚠️ <b>Удаление района из города '{city['name']}'</b>\n\n"
            f"Выберите район (введите номер):\n\n{districts_text}",
            parse_mode='HTML'
        )
        await state.set_state(AdminStates.deleting_district)
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер города. Попробуйте еще раз:")

@router.message(AdminStates.deleting_district)
async def delete_district_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    districts = data['districts']
    
    try:
        district_index = int(message.text) - 1
        district = districts[district_index]
        
        await db.delete_district(district['id'])
        await message.answer(f"✅ Район '{district['name']}' удален!")
        await state.clear()
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер района. Попробуйте еще раз:")

@router.message(Command("add_product_to_district"))
async def add_product_to_district_start(message: Message, state: FSMContext):
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
    await state.set_state(AdminStates.adding_product_to_district_city)

@router.message(AdminStates.adding_product_to_district_city)
async def add_product_to_district_select_city(message: Message, state: FSMContext):
    data = await state.get_data()
    cities = data['cities']
    
    try:
        city_index = int(message.text) - 1
        city = cities[city_index]
        
        districts = await db.get_districts_by_city(city['id'])
        if not districts:
            await message.answer(f"❌ В городе '{city['name']}' нет районов!")
            await state.clear()
            return
        
        districts_text = "\n".join([f"{i+1}. {d['name']}" for i, d in enumerate(districts)])
        await state.update_data(city=city, districts=districts)
        
        await message.answer(
            f"Выберите район (введите номер):\n\n{districts_text}"
        )
        await state.set_state(AdminStates.adding_product_to_district_district)
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер города. Попробуйте еще раз:")

@router.message(AdminStates.adding_product_to_district_district)
async def add_product_to_district_select_district(message: Message, state: FSMContext):
    data = await state.get_data()
    districts = data['districts']
    
    try:
        district_index = int(message.text) - 1
        district = districts[district_index]
        
        all_products = await db.get_all_products()
        if not all_products:
            await message.answer("❌ Нет товаров в общем списке!")
            await state.clear()
            return
        
        existing_products = await db.get_products_by_district(district['id'])
        existing_ids = [p['id'] for p in existing_products]
        
        available_products = [p for p in all_products if p['id'] not in existing_ids]
        
        if not available_products:
            await message.answer(
                f"✅ В районе '{district['name']}' уже есть все товары из общего списка!"
            )
            await state.clear()
            return
        
        product_icon = await db.get_setting('product_icon', '📦')
        products_text = "\n".join([
            f"{i+1}. {product_icon} {p['name']} - {p['price']}₽" 
            for i, p in enumerate(available_products)
        ])
        await state.update_data(district=district, available_products=available_products)
        
        await message.answer(
            f"➕ <b>Добавление товаров в район '{district['name']}'</b>\n\n"
            f"Доступные товары:\n{products_text}\n\n"
            f"Введите номера товаров через запятую (например: 1,3,5)\n"
            f"Или введите 'все' чтобы добавить все товары:",
            parse_mode='HTML'
        )
        await state.set_state(AdminStates.adding_product_to_district_products)
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер района. Попробуйте еще раз:")

@router.message(AdminStates.adding_product_to_district_products)
async def add_product_to_district_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    available_products = data['available_products']
    district = data['district']
    
    try:
        if message.text.lower() == 'все':
            product_ids = [p['id'] for p in available_products]
        else:
            indices = [int(x.strip()) - 1 for x in message.text.split(',')]
            product_ids = [available_products[i]['id'] for i in indices]
        
        added_count = 0
        for product_id in product_ids:
            success = await db.add_product_to_district(district['id'], product_id)
            if success:
                added_count += 1
        
        await message.answer(
            f"✅ Добавлено товаров в район '{district['name']}': {added_count}"
        )
        await state.clear()
    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат. Введите номера через запятую (например: 1,2,3):")

@router.message(Command("remove_product"))
async def remove_product_start(message: Message, state: FSMContext):
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
    await state.set_state(AdminStates.removing_product_from_district_city)

@router.message(AdminStates.removing_product_from_district_city)
async def remove_product_select_city(message: Message, state: FSMContext):
    data = await state.get_data()
    cities = data['cities']
    
    try:
        city_index = int(message.text) - 1
        city = cities[city_index]
        
        districts = await db.get_districts_by_city(city['id'])
        if not districts:
            await message.answer(f"❌ В городе '{city['name']}' нет районов!")
            await state.clear()
            return
        
        districts_text = "\n".join([f"{i+1}. {d['name']}" for i, d in enumerate(districts)])
        await state.update_data(city=city, districts=districts)
        
        await message.answer(
            f"Выберите район (введите номер):\n\n{districts_text}"
        )
        await state.set_state(AdminStates.removing_product_from_district_district)
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер города. Попробуйте еще раз:")

@router.message(AdminStates.removing_product_from_district_district)
async def remove_product_select_district(message: Message, state: FSMContext):
    data = await state.get_data()
    districts = data['districts']
    
    try:
        district_index = int(message.text) - 1
        district = districts[district_index]
        
        products = await db.get_products_by_district(district['id'])
        if not products:
            await message.answer(f"❌ В районе '{district['name']}' нет товаров!")
            await state.clear()
            return
        
        product_icon = await db.get_setting('product_icon', '📦')
        products_text = "\n".join([f"{i+1}. {product_icon} {p['name']} - {p['price']}₽" for i, p in enumerate(products)])
        await state.update_data(district=district, products=products)
        
        await message.answer(
            f"⚠️ <b>Удаление товара из района '{district['name']}'</b>\n\n"
            f"Выберите товар (введите номер):\n\n{products_text}",
            parse_mode='HTML'
        )
        await state.set_state(AdminStates.removing_product_from_district_product)
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер района. Попробуйте еще раз:")

@router.message(AdminStates.removing_product_from_district_product)
async def remove_product_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    products = data['products']
    district = data['district']
    
    try:
        product_index = int(message.text) - 1
        product = products[product_index]
        
        await db.delete_product_from_district(district['id'], product['id'])
        await message.answer(
            f"✅ Товар '{product['name']}' удален из района '{district['name']}'!\n\n"
            f"<i>Товар остался в общем списке товаров.</i>",
            parse_mode='HTML'
        )
        await state.clear()
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер товара. Попробуйте еще раз:")
# ПРОДОЛЖЕНИЕ handlers/admin_complete.py - ЧАСТЬ 3
# Этот код нужно добавить после part2

# === СПОСОБЫ ОПЛАТЫ ===
@router.message(F.text == "💱 Оплата")
async def payment_methods_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    methods = await db.get_all_payment_methods()
    
    if methods:
        methods_text = "\n".join([
            f"• {pm['name']} ({pm['code'].upper()}): 1 = {pm['rate']}₽ {'✅' if pm['enabled'] else '❌'}"
            for pm in methods
        ])
    else:
        methods_text = "Нет способов оплаты"
    
    await message.answer(
        f"💱 <b>Способы оплаты:</b>\n\n{methods_text}\n\n"
        "Команды:\n"
        "/add_payment - Добавить способ оплаты\n"
        "/edit_rate - Изменить курс\n"
        "/edit_address - Изменить адрес/номер\n"
        "/delete_payment - Удалить способ оплаты\n"
        "/toggle_payment - Включить/выключить",
        parse_mode='HTML'
    )

@router.message(Command("add_payment"))
async def add_payment_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "💱 <b>Добавление способа оплаты</b>\n\n"
        "Введите название (например: Bitcoin, USDT TRC-20):",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.adding_payment_name)

@router.message(AdminStates.adding_payment_name)
async def add_payment_name(message: Message, state: FSMContext):
    await state.update_data(payment_name=message.text)
    await message.answer(
        "Введите код (например: btc, usdt_trc20):\n\n"
        "<i>Код должен быть уникальным, без пробелов</i>",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.adding_payment_code)

@router.message(AdminStates.adding_payment_code)
async def add_payment_code(message: Message, state: FSMContext):
    code = message.text.strip().lower().replace(' ', '_')
    await state.update_data(payment_code=code)
    await message.answer(
        f"Введите курс (1 {code.upper()} = X рублей):\n\n"
        f"Например: 5330490.41"
    )
    await state.set_state(AdminStates.adding_payment_rate)

@router.message(AdminStates.adding_payment_rate)
async def add_payment_rate(message: Message, state: FSMContext):
    try:
        rate = float(message.text)
        await state.update_data(payment_rate=rate)
        await message.answer(
            "Введите адрес/номер для оплаты:\n\n"
            "Или отправьте '-' чтобы пропустить"
        )
        await state.set_state(AdminStates.adding_payment_address)
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число:")

@router.message(AdminStates.adding_payment_address)
async def add_payment_address(message: Message, state: FSMContext):
    address = message.text if message.text != '-' else ''
    await state.update_data(payment_address=address)
    await message.answer(
        "Введите инструкцию по оплате:\n\n"
        "Или отправьте '-' для стандартной инструкции"
    )
    await state.set_state(AdminStates.adding_payment_instruction)

@router.message(AdminStates.adding_payment_instruction)
async def add_payment_instruction(message: Message, state: FSMContext):
    data = await state.get_data()
    
    instruction = message.text if message.text != '-' else 'Переведите указанную сумму'
    
    # Добавляем способ оплаты
    await db.add_payment_method(
        name=data['payment_name'],
        code=data['payment_code'],
        rate=data['payment_rate'],
        address=data['payment_address']
    )
    
    # Сохраняем инструкцию
    instruction_key = f"payment_instruction_{data['payment_code']}"
    await db.set_setting(instruction_key, instruction)
    
    await message.answer(
        f"✅ Способ оплаты добавлен!\n\n"
        f"Название: {data['payment_name']}\n"
        f"Код: {data['payment_code']}\n"
        f"Курс: 1 = {data['payment_rate']}₽"
    )
    await state.clear()

@router.message(Command("edit_rate"))
async def edit_rate_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    methods = await db.get_all_payment_methods()
    if not methods:
        await message.answer("❌ Нет способов оплаты!")
        return
    
    methods_text = "\n".join([
        f"{i+1}. {pm['name']} - 1 = {pm['rate']}₽"
        for i, pm in enumerate(methods)
    ])
    await state.update_data(payment_methods=methods)
    
    await message.answer(
        f"💱 <b>Изменение курса</b>\n\n"
        f"Выберите способ оплаты (введите номер):\n\n{methods_text}",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.editing_rate_select)

@router.message(AdminStates.editing_rate_select)
async def edit_rate_select(message: Message, state: FSMContext):
    data = await state.get_data()
    methods = data['payment_methods']
    
    try:
        method_index = int(message.text) - 1
        method = methods[method_index]
        await state.update_data(selected_method=method)
        
        await message.answer(
            f"Текущий курс {method['name']}: 1 = {method['rate']}₽\n\n"
            f"Введите новый курс:"
        )
        await state.set_state(AdminStates.editing_rate_new)
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер. Попробуйте еще раз:")

@router.message(AdminStates.editing_rate_new)
async def edit_rate_confirm(message: Message, state: FSMContext):
    try:
        new_rate = float(message.text)
        data = await state.get_data()
        method = data['selected_method']
        
        await db.update_payment_method_rate(method['code'], new_rate)
        await message.answer(
            f"✅ Курс {method['name']} изменен:\n"
            f"{method['rate']}₽ → {new_rate}₽"
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число:")

@router.message(Command("edit_address"))
async def edit_address_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    methods = await db.get_all_payment_methods()
    if not methods:
        await message.answer("❌ Нет способов оплаты!")
        return
    
    methods_text = "\n".join([
        f"{i+1}. {pm['name']} - {pm['address'] or 'не указан'}"
        for i, pm in enumerate(methods)
    ])
    await state.update_data(payment_methods=methods)
    
    await message.answer(
        f"💱 <b>Изменение адреса/номера</b>\n\n"
        f"Выберите способ оплаты (введите номер):\n\n{methods_text}",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.editing_address_select)

@router.message(AdminStates.editing_address_select)
async def edit_address_select(message: Message, state: FSMContext):
    data = await state.get_data()
    methods = data['payment_methods']
    
    try:
        method_index = int(message.text) - 1
        method = methods[method_index]
        await state.update_data(selected_method=method)
        
        await message.answer(
            f"Текущий адрес {method['name']}:\n"
            f"<code>{method['address'] or 'не указан'}</code>\n\n"
            f"Введите новый адрес/номер:",
            parse_mode='HTML'
        )
        await state.set_state(AdminStates.editing_address_new)
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер. Попробуйте еще раз:")

@router.message(AdminStates.editing_address_new)
async def edit_address_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    method = data['selected_method']
    new_address = message.text.strip()
    
    await db.update_payment_method_address(method['code'], new_address)
    await message.answer(
        f"✅ Адрес {method['name']} изменен!"
    )
    await state.clear()

@router.message(Command("delete_payment"))
async def delete_payment_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    methods = await db.get_all_payment_methods()
    if not methods:
        await message.answer("❌ Нет способов оплаты!")
        return
    
    methods_text = "\n".join([
        f"{i+1}. {pm['name']}"
        for i, pm in enumerate(methods)
    ])
    await state.update_data(payment_methods=methods)
    
    await message.answer(
        f"⚠️ <b>Удаление способа оплаты</b>\n\n"
        f"Выберите способ оплаты (введите номер):\n\n{methods_text}",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.deleting_payment)

@router.message(AdminStates.deleting_payment)
async def delete_payment_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    methods = data['payment_methods']
    
    try:
        method_index = int(message.text) - 1
        method = methods[method_index]
        
        await db.delete_payment_method(method['code'])
        await message.answer(f"✅ Способ оплаты '{method['name']}' удален!")
        await state.clear()
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер. Попробуйте еще раз:")

@router.message(Command("toggle_payment"))
async def toggle_payment_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    methods = await db.get_all_payment_methods()
    if not methods:
        await message.answer("❌ Нет способов оплаты!")
        return
    
    methods_text = "\n".join([
        f"{i+1}. {pm['name']} {'✅' if pm['enabled'] else '❌'}"
        for i, pm in enumerate(methods)
    ])
    await state.update_data(payment_methods=methods)
    
    await message.answer(
        f"💱 <b>Включить/выключить способ оплаты</b>\n\n"
        f"Выберите способ оплаты (введите номер):\n\n{methods_text}",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.deleting_payment)

@router.message(AdminStates.deleting_payment)
async def toggle_payment_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    methods = data['payment_methods']
    
    try:
        method_index = int(message.text) - 1
        method = methods[method_index]
        
        await db.toggle_payment_method(method['code'])
        new_status = "включен" if not method['enabled'] else "выключен"
        await message.answer(f"✅ Способ оплаты '{method['name']}' {new_status}!")
        await state.clear()
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер. Попробуйте еще раз:")


# === КЛИЕНТЫ ===
@router.message(F.text == "👥 Клиенты")
async def users_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    await message.answer(
        "👥 <b>Управление клиентами</b>\n\n"
        "Команды:\n"
        "/users_list - Список всех клиентов\n"
        "/block_user - Заблокировать клиента\n"
        "/unblock_user - Разблокировать клиента",
        parse_mode='HTML'
    )

@router.message(Command("users_list"))
async def users_list(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    users = await db.get_all_users()
    
    if not users:
        await message.answer("📋 Нет зарегистрированных клиентов")
        return
    
    users_text = []
    for user in users[:50]:  # Показываем первых 50
        status = "🚫" if user['blocked'] else "✅"
        username = f"@{user['username']}" if user['username'] else "без username"
        name = user['first_name'] or "Без имени"
        users_text.append(f"{status} {name} ({username}) - ID: {user['id']}")
    
    text = "\n".join(users_text)
    await message.answer(
        f"👥 <b>Клиенты ({len(users)} всего):</b>\n\n{text}",
        parse_mode='HTML'
    )

@router.message(Command("block_user"))
async def block_user_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "🚫 <b>Блокировка клиента</b>\n\n"
        "Введите ID клиента:",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.blocking_user)

@router.message(AdminStates.blocking_user)
async def block_user_confirm(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        await db.block_user(user_id)
        await message.answer(f"✅ Клиент {user_id} заблокирован!")
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный ID. Введите число:")

@router.message(Command("unblock_user"))
async def unblock_user_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "✅ <b>Разблокировка клиента</b>\n\n"
        "Введите ID клиента:",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.unblocking_user)

@router.message(AdminStates.unblocking_user)
async def unblock_user_confirm(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        await db.unblock_user(user_id)
        await message.answer(f"✅ Клиент {user_id} разблокирован!")
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный ID. Введите число:")

# === СТАТИСТИКА ===
@router.message(F.text == "📊 Статистика")
async def stats_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        "Команды:\n"
        "/stats - Статистика заказов",
        parse_mode='HTML'
    )

@router.message(Command("stats"))
async def stats_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "📊 <b>Статистика заказов</b>\n\n"
        "Выберите период:\n"
        "1. За сегодня\n"
        "2. За неделю\n"
        "3. За месяц\n"
        "4. За все время",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.stats_period)

@router.message(AdminStates.stats_period)
async def stats_show(message: Message, state: FSMContext):
    try:
        choice = int(message.text)
        
        now = datetime.now()
        
        if choice == 1:
            start_date = now.replace(hour=0, minute=0, second=0).isoformat()
            end_date = now.isoformat()
            period_name = "сегодня"
        elif choice == 2:
            start_date = (now - timedelta(days=7)).isoformat()
            end_date = now.isoformat()
            period_name = "за неделю"
        elif choice == 3:
            start_date = (now - timedelta(days=30)).isoformat()
            end_date = now.isoformat()
            period_name = "за месяц"
        elif choice == 4:
            start_date = None
            end_date = None
            period_name = "за все время"
        else:
            await message.answer("❌ Неверный выбор. Введите число от 1 до 4:")
            return
        
        total_orders = await db.get_orders_count(start_date, end_date)
        paid_orders = await db.get_orders_by_status('paid')
        pending_orders = await db.get_orders_by_status('pending')
        cancelled_orders = await db.get_orders_by_status('cancelled')
        
        # Фильтруем по периоду
        if start_date and end_date:
            paid_orders = [o for o in paid_orders if start_date <= o['created_at'] <= end_date]
            pending_orders = [o for o in pending_orders if start_date <= o['created_at'] <= end_date]
            cancelled_orders = [o for o in cancelled_orders if start_date <= o['created_at'] <= end_date]
        
        stats_text = (
            f"📊 <b>Статистика {period_name}</b>\n\n"
            f"Всего заказов: {total_orders}\n"
            f"✅ Оплачено: {len(paid_orders)}\n"
            f"⏳ В ожидании: {len(pending_orders)}\n"
            f"❌ Отменено: {len(cancelled_orders)}"
        )
        
        await message.answer(stats_text, parse_mode='HTML')
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число от 1 до 4:")

# === БЭКАП ===
@router.message(Command("export_catalog"))
async def export_catalog(message: Message):
    """Экспорт витрины"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде")
        return
    
    try:
        data = await db.export_catalog()
        
        # Сохраняем в JSON
        filename = f'catalog_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        file = FSInputFile(filename)
        await message.answer_document(
            file,
            caption="📦 Экспорт витрины (товары, города, районы, способы оплаты)\n\n"
                    "Для импорта используйте /import_catalog"
        )
        
        # Удаляем временный файл
        import os
        os.remove(filename)
    except Exception as e:
        await message.answer(f"❌ Ошибка при экспорте: {e}")

@router.message(Command("import_catalog"))
async def import_catalog_start(message: Message):
    """Начало импорта витрины"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде")
        return
    
    await message.answer(
        "📥 <b>Импорт витрины</b>\n\n"
        "Отправьте JSON файл с витриной\n\n"
        "⚠️ <b>ВНИМАНИЕ:</b> Текущая витрина будет полностью заменена!",
        parse_mode='HTML'
    )

@router.message(Command("export_data"))
async def export_data(message: Message):
    """Экспорт данных"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде")
        return
    
    try:
        data = await db.export_data()
        
        # Сохраняем в JSON
        filename = f'data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        file = FSInputFile(filename)
        await message.answer_document(
            file,
            caption="📦 Экспорт данных (клиенты, заказы)\n\n"
                    "Для импорта используйте /import_data"
        )
        
        # Удаляем временный файл
        import os
        os.remove(filename)
    except Exception as e:
        await message.answer(f"❌ Ошибка при экспорте: {e}")

@router.message(Command("import_data"))
async def import_data_start(message: Message):
    """Начало импорта данных"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде")
        return
    
    await message.answer(
        "📥 <b>Импорт данных</b>\n\n"
        "Отправьте JSON файл с данными\n\n"
        "⚠️ <b>ВНИМАНИЕ:</b> Текущие данные будут полностью заменены!",
        parse_mode='HTML'
    )

@router.message(F.document)
async def import_file(message: Message):
    """Импорт файла"""
    if not is_admin(message.from_user.id):
        return
    
    filename = message.document.file_name
    
    try:
        # Скачиваем файл
        file = await message.bot.get_file(message.document.file_id)
        await message.bot.download_file(file.file_path, filename)
        
        # Читаем JSON
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Определяем тип файла
        if 'products' in data and 'cities' in data:
            # Это витрина
            await db.import_catalog(data)
            await message.answer("✅ Витрина успешно импортирована!")
        elif 'users' in data and 'orders' in data:
            # Это данные
            await db.import_data(data)
            await message.answer("✅ Данные успешно импортированы!")
        else:
            await message.answer("❌ Неверный формат файла")
        
        # Удаляем временный файл
        import os
        os.remove(filename)
    except Exception as e:
        await message.answer(f"❌ Ошибка при импорте: {e}")

# === НАСТРОЙКИ ===
@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    operator_link = await db.get_setting('operator_link', 'Не указана')
    
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        f"👤 Ссылка на оператора: {operator_link}\n\n"
        "Команды:\n"
        "/set_operator - Установить ссылку на оператора\n"
        "/set_success_message - Сообщение после оплаты\n"
        "/set_timeout_message - Сообщение при истечении времени",
        parse_mode='HTML'
    )

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
