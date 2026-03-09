from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio

import database as db
import keyboards as kb

router = Router()

class OrderStates(StatesGroup):
    waiting_city = State()
    city_confirmation = State()
    selecting_product = State()
    selecting_district = State()
    selecting_payment = State()
    waiting_payment = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Начало работы с ботом"""
    # Проверяем блокировку
    if await db.is_user_blocked(message.from_user.id):
        await message.answer("❌ Вы заблокированы")
        return
    
    # Сохраняем пользователя
    await db.add_or_update_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Пожалуйста, введите название вашего города:"
    )
    await state.set_state(OrderStates.waiting_city)

@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.edit_text(
        "👋 Добро пожаловать!\n\n"
        "Пожалуйста, введите название вашего города:"
    )
    await state.set_state(OrderStates.waiting_city)
    await callback.answer()

@router.message(OrderStates.waiting_city)
async def process_city_input(message: Message, state: FSMContext):
    """Обработка ввода города"""
    city = await db.find_city(message.text)
    
    if not city:
        await message.answer(
            "❌ К сожалению, мы не работаем в этом городе.\n\n"
            "Попробуйте ввести название города еще раз:"
        )
        return
    
    await state.update_data(city_id=city['id'], city_name=city['name'])
    await message.answer(
        f"Ваш город: {city['name']}?",
        reply_markup=kb.city_confirmation_kb(city['name'])
    )
    await state.set_state(OrderStates.city_confirmation)

@router.callback_query(F.data == "confirm_city_no", OrderStates.city_confirmation)
async def city_no(callback: CallbackQuery, state: FSMContext):
    """Отказ от подтверждения города"""
    await callback.message.edit_text(
        "Пожалуйста, введите название вашего города еще раз:"
    )
    await state.set_state(OrderStates.waiting_city)
    await callback.answer()

@router.callback_query(F.data == "confirm_city_yes", OrderStates.city_confirmation)
async def city_yes(callback: CallbackQuery, state: FSMContext):
    """Подтверждение города"""
    data = await state.get_data()
    city_id = data['city_id']
    
    products = await db.get_products_by_city(city_id)
    
    if not products:
        await callback.message.edit_text(
            "❌ К сожалению, в вашем городе пока нет доступных товаров.\n\n"
            "Попробуйте выбрать другой город:"
        )
        await state.set_state(OrderStates.waiting_city)
        await callback.answer()
        return
    
    product_icon = await db.get_setting('product_icon', '📦')
    await callback.message.edit_text(
        "📦 Выберите товар:",
        reply_markup=kb.products_kb(products, product_icon)
    )
    await state.set_state(OrderStates.selecting_product)
    await callback.answer()

# Кнопка "Назад" к выбору города
@router.callback_query(F.data == "back_to_city")
async def back_to_city(callback: CallbackQuery, state: FSMContext):
    """Вернуться к выбору города"""
    await callback.message.edit_text(
        "Пожалуйста, введите название вашего города:"
    )
    await state.set_state(OrderStates.waiting_city)
    await callback.answer()

@router.callback_query(F.data.startswith("product_"), OrderStates.selecting_product)
async def select_product(callback: CallbackQuery, state: FSMContext):
    """Выбор товара"""
    product_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    city_id = data['city_id']
    
    # Получаем районы, где доступен этот товар
    districts = await db.get_districts_by_city_and_product(city_id, product_id)
    
    if not districts:
        await callback.message.edit_text(
            "❌ К сожалению, этот товар недоступен ни в одном районе вашего города."
        )
        await callback.answer()
        return
    
    await state.update_data(product_id=product_id)
    await callback.message.edit_text(
        "📍 Выберите район:",
        reply_markup=kb.districts_kb(districts)
    )
    await state.set_state(OrderStates.selecting_district)
    await callback.answer()

# Кнопка "Назад" к выбору товара
@router.callback_query(F.data == "back_to_products")
async def back_to_products(callback: CallbackQuery, state: FSMContext):
    """Вернуться к выбору товара"""
    data = await state.get_data()
    city_id = data['city_id']
    
    products = await db.get_products_by_city(city_id)
    product_icon = await db.get_setting('product_icon', '📦')
    
    await callback.message.edit_text(
        "📦 Выберите товар:",
        reply_markup=kb.products_kb(products, product_icon)
    )
    await state.set_state(OrderStates.selecting_product)
    await callback.answer()

@router.callback_query(F.data.startswith("district_"), OrderStates.selecting_district)
async def select_district(callback: CallbackQuery, state: FSMContext):
    """Выбор района"""
    district_id = int(callback.data.split("_")[1])
    await state.update_data(district_id=district_id)
    
    # Получаем активные способы оплаты
    payment_methods = await db.get_enabled_payment_methods()
    
    if not payment_methods:
        await callback.message.edit_text(
            "❌ К сожалению, способы оплаты временно недоступны."
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "💰 Выберите способ оплаты:",
        reply_markup=kb.payment_methods_kb(payment_methods)
    )
    await state.set_state(OrderStates.selecting_payment)
    await callback.answer()

# Кнопка "Назад" к выбору района
@router.callback_query(F.data == "back_to_districts")
async def back_to_districts(callback: CallbackQuery, state: FSMContext):
    """Вернуться к выбору района"""
    data = await state.get_data()
    city_id = data['city_id']
    product_id = data['product_id']
    
    districts = await db.get_districts_by_city_and_product(city_id, product_id)
    
    await callback.message.edit_text(
        "📍 Выберите район:",
        reply_markup=kb.districts_kb(districts)
    )
    await state.set_state(OrderStates.selecting_district)
    await callback.answer()

@router.callback_query(F.data.startswith("payment_"), OrderStates.selecting_payment)
async def select_payment(callback: CallbackQuery, state: FSMContext):
    """Выбор способа оплаты"""
    # Убираем префикс "payment_" чтобы получить код
    payment_code = callback.data.replace("payment_", "", 1)
    data = await state.get_data()
    
    # Получаем способ оплаты
    payment_method = await db.get_payment_method_by_code(payment_code)
    if not payment_method:
        await callback.message.edit_text("❌ Способ оплаты не найден")
        await callback.answer()
        return
    
    # Получаем данные товара
    product = await db.get_product_by_id(data['product_id'])
    district = await db.get_district_by_id(data['district_id'])
    
    # Конвертируем цену
    amount_rub = product['price']
    amount_currency = round(amount_rub / payment_method['rate'], 4)
    
    # Создаем заявку
    order_number = await db.create_order(
        user_id=callback.from_user.id,
        product_id=data['product_id'],
        city_id=data['city_id'],
        district_id=data['district_id'],
        payment_method=payment_code,
        amount_rub=amount_rub,
        amount_currency=amount_currency,
        currency_code=payment_code.upper()
    )
    
    await state.update_data(order_number=order_number)
    
    # Формируем сообщение
    product_icon = await db.get_setting('product_icon', '📦')
    
    order_text = (
        f"📋 <b>Номер заявки: {order_number}</b>\n\n"
        f"{product_icon} <b>{product['name']}</b>\n"
        f"💰 Сумма: {amount_currency} {payment_code.upper()}\n"
        f"<i>(≈ {amount_rub}₽)</i>\n\n"
        f"📍 {data['city_name']}, {district['name']}\n\n"
    )
    
    if payment_method['address']:
        order_text += f"<b>Адрес для оплаты:</b>\n<code>{payment_method['address']}</code>\n\n"
    
    # Получаем инструкцию
    instruction_key = f'payment_instruction_{payment_code}'
    instruction = await db.get_setting(instruction_key, 'Переведите указанную сумму')
    order_text += f"📝 {instruction}\n\n"
    order_text += f"⏰ У вас есть 30 минут на оплату"
    
    operator_link = await db.get_setting('operator_link', '')
    
    await callback.message.edit_text(
        order_text,
        reply_markup=kb.order_confirmation_kb(operator_link),
        parse_mode='HTML'
    )
    await state.set_state(OrderStates.waiting_payment)
    
    # Запускаем таймер на 30 минут
    asyncio.create_task(payment_timeout(callback.from_user.id, order_number, state, callback.bot))
    
    await callback.answer()

async def payment_timeout(user_id: int, order_number: int, state: FSMContext, bot):
    """Таймер на оплату заявки"""
    from config import PAYMENT_TIMEOUT
    await asyncio.sleep(PAYMENT_TIMEOUT)
    
    # Проверяем статус заявки
    order = await db.get_order_by_number(order_number)
    
    if order and order['status'] == 'pending':
        await db.cancel_order(order_number)
        
        cancel_message = await db.get_setting(
            'order_timeout_message',
            '⏰ Время на оплату заявки истекло. Заявка отменена.'
        )
        
        try:
            await bot.send_message(user_id, cancel_message)
        except Exception as e:
            print(f"Не удалось отправить уведомление об истечении времени: {e}")
        
        await state.clear()

@router.callback_query(F.data == "order_paid", OrderStates.waiting_payment)
async def order_paid(callback: CallbackQuery, state: FSMContext):
    """Клиент нажал "Я оплатил" """
    data = await state.get_data()
    order_number = data['order_number']
    
    await db.complete_order(order_number)
    
    # Получаем информацию о заказе для уведомления
    order = await db.get_order_by_number(order_number)
    product = await db.get_product_by_id(order['product_id'])
    
    # Отправляем уведомление администраторам
    from config import ADMIN_IDS
    
    admin_notification = (
        f"✅ Успешный клиент. Заявка № {order_number}\n"
        f"({product['name']} - {order['amount_currency']} {order['currency_code'].upper()})"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(admin_id, admin_notification)
        except Exception as e:
            print(f"Не удалось отправить уведомление админу {admin_id}: {e}")
    
    success_message = await db.get_setting(
        'payment_success_message',
        '✅ Спасибо! Мы получили информацию об оплате.\nМы свяжемся с вами в ближайшее время.'
    )
    operator_link = await db.get_setting('operator_link', '')
    
    try:
        await callback.message.edit_text(
            success_message,
            reply_markup=kb.contact_operator_kb(operator_link) if operator_link else None
        )
    except Exception as e:
        print(f"Ошибка при редактировании сообщения: {e}")
        await callback.message.answer(
            success_message,
            reply_markup=kb.contact_operator_kb(operator_link) if operator_link else None
        )
    
    await state.clear()
    await callback.answer("✅ Оплата подтверждена!")

@router.callback_query(F.data == "order_cancel", OrderStates.waiting_payment)
async def order_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена заявки"""
    data = await state.get_data()
    order_number = data['order_number']
    
    await db.cancel_order(order_number)
    await state.clear()
    
    await callback.message.edit_text(
        "❌ Заявка отменена.\n\n"
        "Пожалуйста, введите название вашего города:"
    )
    await state.set_state(OrderStates.waiting_city)
    await callback.answer()
