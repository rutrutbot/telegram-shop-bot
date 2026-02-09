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
    deleting_city = State()
    
    # Товары
    adding_product_name = State()
    adding_product_icon = State()
    adding_product_price = State()
    editing_product_price = State()
    editing_product_new_price = State()
    
    # Районы
    selecting_city_for_district = State()
    adding_district_name = State()
    selecting_products_for_district = State()
    deleting_district_city = State()
    deleting_district = State()
    removing_product_from_district_city = State()
    removing_product_from_district_district = State()
    removing_product_from_district_product = State()
    
    # Настройки
    setting_card_number = State()
    setting_payment_instruction = State()
    setting_btc_address = State()
    setting_btc_instruction = State()
    setting_operator_link = State()
    setting_success_message = State()
    setting_timeout_message = State()

@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    """Админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    # Сбрасываем состояние пользователя
    await state.clear()
    
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=kb.admin_main_kb(),
        parse_mode='HTML'
    )

@router.message(Command("export_db"))
async def export_database(message: Message):
    """Экспорт базы данных"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде")
        return
    
    import os
    from aiogram.types import FSInputFile
    
    db_path = 'shop_bot.db'
    
    if not os.path.exists(db_path):
        await message.answer("❌ База данных не найдена!")
        return
    
    try:
        file = FSInputFile(db_path)
        await message.answer_document(
            file,
            caption="📦 Резервная копия базы данных\n\n"
                    "Сохраните этот файл. После обновления бота используйте /import_db"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при экспорте базы: {e}")

@router.message(Command("import_db"))
async def import_database_start(message: Message):
    """Начало импорта базы данных"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде")
        return
    
    await message.answer(
        "📥 <b>Импорт базы данных</b>\n\n"
        "Отправьте файл shop_bot.db\n\n"
        "⚠️ <b>ВНИМАНИЕ:</b> Текущая база данных будет полностью заменена!",
        parse_mode='HTML'
    )

@router.message(F.document)
async def import_database_file(message: Message):
    """Импорт файла базы данных"""
    if not is_admin(message.from_user.id):
        return
    
    import os
    
    # Проверяем имя файла
    if message.document.file_name != 'shop_bot.db':
        await message.answer("❌ Неверное имя файла. Отправьте файл shop_bot.db")
        return
    
    try:
        # Скачиваем файл
        file = await message.bot.get_file(message.document.file_id)
        await message.bot.download_file(file.file_path, 'shop_bot.db')
        
        await message.answer(
            "✅ База данных успешно импортирована!\n\n"
            "Перезапустите бота командой /start для применения изменений."
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при импорте базы: {e}")

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
    products_text = "\n".join([f"• {p['icon']} {p['name']} - {p['price']}₽" for p in products]) if products else "Нет товаров"
    
    await message.answer(
        f"📦 <b>Товары:</b>\n\n{products_text}\n\n"
        "Команды:\n"
        "/add_product - Добавить товар\n"
        "/edit_price - Изменить цену товара",
        parse_mode='HTML'
    )

@router.message(Command("add_product"))
async def add_product_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer("Введите название товара:")
    await state.set_state(AdminStates.adding_product_name)

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
            price=price
        )
        
        await message.answer(f"✅ Товар '{data['product_name']}' добавлен в общий список!")
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверная цена. Введите число:")

@router.message(Command("edit_price"))
async def edit_price_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    products = await db.get_all_products()
    if not products:
        await message.answer("❌ Нет товаров!")
        return
    
    products_text = "\n".join([f"{i+1}. {p['icon']} {p['name']} - {p['price']}₽" for i, p in enumerate(products)])
    await state.update_data(products=products)
    
    await message.answer(
        f"💰 <b>Изменение цены</b>\n\n"
        f"Выберите товар (введите номер):\n\n{products_text}",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.editing_product_price)

@router.message(AdminStates.editing_product_price)
async def edit_price_select(message: Message, state: FSMContext):
    data = await state.get_data()
    products = data['products']
    
    try:
        product_index = int(message.text) - 1
        product = products[product_index]
        await state.update_data(selected_product=product)
        
        await message.answer(
            f"Текущая цена товара '{product['name']}': {product['price']}₽\n\n"
            f"Введите новую цену:"
        )
        await state.set_state(AdminStates.editing_product_new_price)
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер товара. Попробуйте еще раз:")

@router.message(AdminStates.editing_product_new_price)
async def edit_price_confirm(message: Message, state: FSMContext):
    try:
        new_price = float(message.text)
        data = await state.get_data()
        product = data['selected_product']
        
        await db.update_product_price(product['id'], new_price)
        await message.answer(
            f"✅ Цена товара '{product['name']}' изменена:\n"
            f"{product['price']}₽ → {new_price}₽"
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверная цена. Введите число:")

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
    
    # Показываем список всех товаров для выбора
    products = await db.get_all_products()
    
    if not products:
        await message.answer("❌ Сначала добавьте товары через /add_product!")
        await state.clear()
        return
    
    products_text = "\n".join([f"{i+1}. {p['icon']} {p['name']} - {p['price']}₽" for i, p in enumerate(products)])
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
        
        products_text = "\n".join([f"{i+1}. {p['icon']} {p['name']} - {p['price']}₽" for i, p in enumerate(products)])
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

# === НАСТРОЙКИ ===
@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
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
