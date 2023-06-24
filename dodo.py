from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import Dispatcher, Bot, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from dotenv import load_dotenv
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import logging, sqlite3, time, os

load_dotenv('.env')

bot = Bot(token=os.environ.get('token'))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)

dodo = sqlite3.connect('dodo.db')
cursor_users = dodo.cursor()
cursor_users.execute("""
    CREATE TABLE IF NOT EXISTS users (
        first_name VARCHAR(255),
        last_name VARCHAR(255),
        username VARCHAR(255),
        id_user INTEGER,
        phone_number INTEGER
    ); 
""")
cursor_users.connection.commit()

inline_buttons = [ 
    InlineKeyboardButton('Отправить номер', callback_data='number'),
    InlineKeyboardButton('Отправить местоположение', callback_data='location'),
    InlineKeyboardButton('Заказать еду', callback_data='order')
]
button = InlineKeyboardMarkup().add(*inline_buttons)

num_button = [
    KeyboardButton('Подтвердить номер', request_contact=True)
]
loc_button = [
    KeyboardButton('Подтвердить локацию', request_location=True)
]

number = ReplyKeyboardMarkup(resize_keyboard=True).add(*num_button)
location = ReplyKeyboardMarkup(resize_keyboard=True).add(*loc_button)

@dp.message_handler(commands='start')
async def start(message:types.Message):
    await message.answer(f'Здравствуйте, {message.from_user.full_name}')
    await message.answer("В этом боте вы можете оставить свой заказ на пиццу.\n\nНо не забывайте оставить ваш адрес и контактный номер!!!", reply_markup=button)
    cursor_users = dodo.cursor()
    cursor_users.execute("SELECT * FROM users")
    result = cursor_users.fetchall()
    if result == []:
        cursor_users.execute(f"INSERT INTO users VALUES ('{message.from_user.first_name}', '{message.from_user.last_name}', '{message.from_user.username}', '{message.from_user.id}', 'None');")
    dodo.commit()

@dp.callback_query_handler(lambda call : call)
async def inline(call):
    if call.data == 'number':
        await get_num(call.message)
    elif call.data == 'location':
        await get_loc(call.message)
    elif call.data == 'order':
        await bot.send_message(call.message.chat.id, 'Отправьте свой заказ, любой')
        await Orders.order.set()

@dp.message_handler(commands='contact')
async def get_num(message:types.Message):
    await message.answer('Подтвердите свой номер', reply_markup=number)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def add_number(message:types.Message):
    cursor = dodo.cursor()
    cursor.execute(f"UPDATE users SET phone_number = '{message.contact['phone_number']}' WHERE id_user = {message.from_user.id};")
    dodo.commit()
    await message.answer("Ваш номер успешно добавлен.",reply_markup=button)

dodo = sqlite3.connect('dodo.db')
cursor= dodo.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS address (
        id_user INTEGER,
        address_longtitude INTEGER,
        address_latitude INTEGER
    );
""")
cursor.connection.commit()

@dp.message_handler(commands='location')
async def get_loc(message:types.Message):
    await message.answer("Подтвердите отправку местоположения.", reply_markup=location)

@dp.message_handler(content_types=types.ContentType.LOCATION)
async def add_loc(message:types.Message):
    address = f"{message.location.longitude}, {message.location.latitude}"
    cursor = dodo.cursor()
    cursor.execute('SELECT * FROM address')
    res = cursor.fetchall()
    if res == []:
            cursor.execute(f"INSERT INTO address VALUES ('{message.from_user.id}', '{message.location.longitude}', '{message.location.latitude}');")
    dodo.commit()
    await message.answer("Ваш адрес успешно записан", reply_markup=types.ReplyKeyboardRemove())

dodo = sqlite3.connect('dodo.db')
cursor_orders = dodo.cursor()
cursor_orders.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        title VARCHAR(255),
        address_destination VARCHAR(255),
        date_time_order VARCHAR(255)
    );
""")
cursor_orders.connection.commit()


class Orders(StatesGroup):
    order = State()
    address = State()

@dp.message_handler(state=Orders.order)
async def get_order2(message:types.Message, state:FSMContext):
    await state.update_data(order=message.text)
    await message.answer('Отправьте ваш адрес в виде текста')
    await Orders.address.set()

@dp.message_handler(state=Orders.address)
async def get_address(message:types.Message, state:FSMContext):
    await state.update_data(address=message.text)
    data = await state.get_data()
    cursor = dodo.cursor()
    cursor.execute(f"INSERT INTO orders VALUES('{data['order']}', '{data['address']}', '{time.ctime()}')")
    dodo.commit()
    await state.finish()
    await message.answer("Ожидайте, ваш заказ принят")

executor.start_polling(dp)