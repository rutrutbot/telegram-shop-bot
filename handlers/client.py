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
    
    await callback.message.edit_text(
        "📦 Выберите товар:",
        reply_markup=kb.products_kb(products)
    )
    await state.set_state(OrderStates.selecting_product)
    await callback.answer()

@router.callback_query(F.data.startswith("product_"), OrderStates.selecting_product)
async def select_product(callback: CallbackQuery, state: FSMContext):
    """Выбор товара"""
    product_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    city_id = data['city_id']
    
    districts = await db.get_districts_by_city(city_id)
    
    if not districts:
        await callback.message.edit_text(
            "❌ К сожалению, в вашем городе нет доступных районов для этого товара."
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

@router.callback_query(F.data.startswith("district_"), OrderStates.selecting_district)
async def select_district(callback: CallbackQuery, state: FSMContext):
    """Выбор района"""
    district_id = int(callback.data.split("_")[1])
    await state.update_data(district_id=district_id)
    
    await callback.message.edit_text(
        "💰 Выберите способ оплаты:",
        reply_markup=kb.payment_methods_kb()
    )
    await state.set_state(OrderStates.selecting_payment)
    await callback.answer()

@router.callback_query(F.data.startswith("payment_"), OrderStates.selecting_payment)
async def select_payment(callback: CallbackQuery, state: FSMContext):
    """Выбор способа оплаты"""
    payment_method = callback.data.split("_")[1]
    data = await state.get_data()
    
    # Создаем заявку
    order_number = await db.create_order(
        user_id=callback.from_user.id,
        product_id=data['product_id'],
        city_id=data['city_id'],
        district_id=data['district_id'],
        payment_method=payment_method
    )
    
    await state.update_data(order_number=order_number)
    
    # Получаем данные для отображения
    products = await db.get_products_by_city(data['city_id'])
    product = next((p for p in products if p['id'] == data['product_id']), None)
    
    districts = await db.get_districts_by_city(data['city_id'])
    district = next((d for d in districts if d['id'] == data['district_id']), None)
    
    # Получаем настройки
    if payment_method == 'card':
        card_number = await db.get_setting('card_number', 'Не указан')
        payment_instruction = await db.get_setting('payment_instruction', 'Переведите указанную сумму на карту')
        
        order_text = (
            f"📋 <b>Номер заявки: {order_number}</b>\n\n"
            f"{product['icon']} <b>{product['name']}</b>\n"
            f"💰 Сумма: {product['price']}₽\n\n"
            f"📍 {data['city_name']}, {district['name']}\n\n"
            f"💳 <b>Номер карты:</b>\n<code>{card_number}</code>\n\n"
            f"📝 {payment_instruction}\n\n"
            f"⏰ У вас есть 30 минут на оплату"
        )
    else:
        btc_address = await db.get_setting('btc_address', 'Не указан')
        btc_instruction = await db.get_setting('btc_instruction', 'Переведите указанную сумму в BTC')
        
        order_text = (
            f"📋 <b>Номер заявки: {order_number}</b>\n\n"
            f"{product['icon']} <b>{product['name']}</b>\n"
            f"💰 Сумма: {product['price']}₽\n\n"
            f"📍 {data['city_name']}, {district['name']}\n\n"
            f"₿ <b>Bitcoin адрес:</b>\n<code>{btc_address}</code>\n\n"
            f"📝 {btc_instruction}\n\n"
            f"⏰ У вас есть 30 минут на оплату"
        )
    
    operator_link = await db.get_setting('operator_link', '')
    
    await callback.message.edit_text(
        order_text,
        reply_markup=kb.order_confirmation_kb(operator_link),
        parse_mode='HTML'
    )
    await state.set_state(OrderStates.waiting_payment)
    
    # Запускаем таймер на 30 минут
    asyncio.create_task(payment_timeout(callback.from_user.id, order_number, state))
    
    await callback.answer()

async def payment_timeout(user_id: int, order_number: int, state: FSMContext):
    """Таймер на оплату заявки"""
    from config import PAYMENT_TIMEOUT
    await asyncio.sleep(PAYMENT_TIMEOUT)
    
    # Проверяем, не оплачена ли уже заявка
    current_state = await state.get_state()
    if current_state == OrderStates.waiting_payment:
        await db.cancel_order(order_number)
        
        cancel_message = await db.get_setting(
            'order_timeout_message',
            '⏰ Время на оплату заявки истекло. Заявка отменена.'
        )
        
        from bot import bot
        await bot.send_message(user_id, cancel_message)
        await state.clear()

@router.callback_query(F.data == "order_paid", OrderStates.waiting_payment)
async def order_paid(callback: CallbackQuery, state: FSMContext):
    """Клиент нажал "Я оплатил" """
    data = await state.get_data()
    order_number = data['order_number']
    
    await db.complete_order(order_number)
    
    # Отправляем уведомление администраторам
    from config import ADMIN_IDS
    from bot import bot
    
    admin_notification = f"✅ Успешный клиент. Заявка № {order_number}"
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_notification)
        except Exception as e:
            print(f"Не удалось отправить уведомление админу {admin_id}: {e}")
    
    success_message = await db.get_setting(
        'payment_success_message',
        '✅ Спасибо! Мы получили информацию об оплате.\nМы свяжемся с вами в ближайшее время.'
    )
    operator_link = await db.get_setting('operator_link', '')
    
    await callback.message.edit_text(
        success_message,
        reply_markup=kb.contact_operator_kb(operator_link) if operator_link else None
    )
    await state.clear()
    await callback.answer()

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
