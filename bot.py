import os
from aiogram import Bot, Dispatcher
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner, Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from uuid import uuid4
import asyncio

# === Конфигурация ===
# Токен тг бота
TOKEN = os.getenv("BOT_TOKEN")  # безопасно вытаскиваем из окружения
TOKEN = ''
if not TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не задана!")

BOT_USERNAME = "PW6_Lotus_new_member_greet1_bot"

HERO_CLASSES_DICT =  {
    "Мечник": "class_blade",
    "Воин": "class_warrior",
    "Маг": "class_mage",
    "Танк": "class_tank",
    "Друид": "class_dru",
    "Жрец": "class_priest",
    "Лучник": "class_archer",
    "Ассасин": "class_assasin",
    "Окультист": "class_okul"
}

CALLBACK_TO_LABEL = {v: k for k, v in HERO_CLASSES_DICT.items()}

# Файл базы данных
DB_FILE = "onboarding.db"

PLAYERS_DB = {
    "shadowwalker": {"nickname": "ShadowWalker", "class": "Маг", "bm": "150000"},
    "bladeking": {"nickname": "BladeKing", "class": "Мечник", "bm": "142000"},
    "lightarcher": {"nickname": "LightArcher", "class": "Лучник", "bm": "135500"},
}

# === FSM (машина состояний) ===
class Onboarding(StatesGroup):
    nickname = State()  # Шаг 1: Никнейм
    player_class = State()  # Шаг 2: Класс персонажа
    player_bm = State() # Шаг 3: Класс БМ
    player_last_guild = State() # Шаг 4: Предыдущая гильдия 

# === Настройка ===
bot = Bot(token=TOKEN)
dp = Dispatcher()

# === Создание таблицы в SQLite ===
# async def init_db():
#     async with aiosqlite.connect(DB_FILE) as db:
#         await db.execute("""
#             CREATE TABLE IF NOT EXISTS users (
#                 user_id INTEGER PRIMARY KEY,
#                 nickname TEXT
#             );
#         """)
#         await db.commit()

# === Вспомогательные методы ===
def build_class_keyboard() -> InlineKeyboardMarkup:
    buttons = [ [InlineKeyboardButton(text=name, callback_data=data)]
                for name, data in HERO_CLASSES_DICT.items()
                ]
    return buttons

async def set_custom_title(user_id, chat_id, title):
    try:
        #Получаем информацию о пользователе
        member = await bot.get_chat_member(chat_id, user_id)
        #Если пользователь не админ, то даем ему базовые права
        if not isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
            res = await bot.promote_chat_member(chat_id=chat_id, 
                                                user_id=user_id, 
                                                can_invite_users = True)
            if not res: raise RuntimeError("Не удалось добавить права администратора")
        #Даем пользователю имя
        await bot.set_chat_administrator_custom_title(chat_id=chat_id, user_id=user_id, custom_title=title)
    except Exception as e:
        raise

# === 1. В группе: Приветствие нового участника ===
@dp.message(F.new_chat_members)
async def welcome_new_members(message: Message):
    link = f"https://t.me/{BOT_USERNAME}?start=onboarding_{message.chat.id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Заполнить анкету новичка", 
                                                                           url=link)]])
    #TODO: Обработать группу, чтобы сообщение было только в нужной
    for user in message.new_chat_members:
        username = user.username
        if username:
            mention = f"@{username}"
        else:
            mention = user.full_name
        await bot.send_message(
                                chat_id=message.chat.id,
                                message_thread_id=message.message_thread_id,  # Важно для форумов
                                text=f"Привет, {mention}! Добро пожаловать в группу гильдии Lotus.\nНажми кнопку ниже, чтобы начать:",
                                reply_markup=keyboard)

# === 2. В ЛС: Обработка нажатия на кнопку "Заполнить анкету новичка" ===
@dp.message(CommandStart(deep_link=True))
async def start_with_payload(message: Message, command: CommandStart, state: FSMContext):
    if command.args and command.args.startswith("onboarding_"):
        chat_id = int(command.args.split("_")[1])
        await state.update_data(origin_chat_id=chat_id)
        await message.answer("Привет! Давай заполним анкету.\n\nКакой у тебя ник в игре?")
        await state.set_state(Onboarding.nickname)  # Устанавливаем состояние
    else:
        await message.answer("Привет! Напиши /start для начала.")

# === 3. в ЛС: Обработка ника ===
@dp.message(Onboarding.nickname)
async def process_nickname(message: Message, state: FSMContext):
    nickname = message.text.strip()
    # Сохраняем ник и переходим к следующему шагу
    await state.update_data(nickname=nickname)
    keyboard = InlineKeyboardMarkup(inline_keyboard = build_class_keyboard())
    await message.answer("Отлично! Теперь выбери класс персонажа:", reply_markup=keyboard)
    await state.set_state(Onboarding.player_class)  # Переходим к следующему состоянию

# === 4. В ЛС: Обработка выбора класса ===
@dp.callback_query(F.data.in_(CALLBACK_TO_LABEL.keys()))
async def process_class(callback: CallbackQuery, state: FSMContext):
    await callback.answer() #Закрываем часики
    selected_class = CALLBACK_TO_LABEL.get(callback.data, "")
    # Сохраняем класс
    await state.update_data(player_class=selected_class)
    # Переходим в следующему шагу
    await callback.message.edit_text(f"Ты выбрал класс: {selected_class}.\nТеперь укажи свой БМ.")
    await state.set_state(Onboarding.player_bm)  # Переходим к следующему состоянию
    
# === 5. в ЛС: Обработка БМ ===
@dp.message(Onboarding.player_bm)
async def process_bm(message: Message, state: FSMContext):
    player_bm = message.text.strip()
    # Сохраняем БМ и переходим к следующему шагу
    await state.update_data(player_bm=player_bm)
    await message.answer("Отлично! Теперь укажи прошлую гильдию и причину ухода:")
    await state.set_state(Onboarding.player_last_guild)  # Переходим к следующему состоянию    


# === 6. в ЛС: Обработка гильдии===
@dp.message(Onboarding.player_last_guild)
async def process_last_guild(message: Message, state: FSMContext):
    player_last_guild = message.text.strip()
    # Сохраняем ник и переходим к следующему шагу
    data = await state.get_data()
    chat_id = data.get("origin_chat_id")
    nickname = data.get("nickname")
    player_class = data.get("player_class")
    player_bm = data.get("player_bm")
    await state.update_data(player_last_guild=player_last_guild)
    #Даем пользователю ник из игры:
    try:
        await  set_custom_title(user_id=message.from_user.id,
                                chat_id=chat_id,
                                title = nickname)
        res_set_title = f"Установлена должность: {nickname}"
    except Exception as e:
        res_set_title = f"Ошибка установки должности: {e}"

    #Сообщение в Личку:
    await message.answer(f"Ник: {nickname}\nКласс: {player_class}\nБМ: {player_bm}\nПрошлая гильдия: {player_last_guild}\nАнкета успешно заполнена!")
    #Сообщение в общую группу:
    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"📝 Новая анкета от {message.from_user.mention_html()}:\n\n"
            f"👤 Ник: {nickname}\n"
            f"⚔️ Класс: {player_class}\n"
            f"📊 БМ: {player_bm}\n"
            f"🏰 Прошлая гильдия: {player_last_guild}\n\n"
            f"{res_set_title}"),
        parse_mode="HTML"
    )
    await state.clear()  # Сброс состояния


@dp.message(Command("set_user_info"))
async def set_user_info(message: Message):
    title = message.text
    title = title.split(sep = ' ', maxsplit = 1)[1]
    title = title.strip()
    if not title:
        await message.reply(f"Введите ник в игре. Пример:\n/set_user_info <ник в игре>")
        return
    user_id = message.reply_to_message.from_user.id
    chat_id = message.chat.id
    try:
        await set_custom_title(user_id = user_id, 
                               chat_id = chat_id, 
                               title = title)
        await message.reply(f"Должность @{message.reply_to_message.from_user.username or user_id} установлена: {title}")
    except Exception as e:
        await message.reply(f"Ошибка: {e}")

@dp.inline_query()
async def inline_query_handler(inline_query: InlineQuery):
    query = inline_query.query.strip().lower()
    results = []

    for key, player in PLAYERS_DB.items():
        if query in key:
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=player["nickname"],
                    description=f'{player["class"]}, БМ: {player["bm"]}',
                    input_message_content=InputTextMessageContent(
                        message_text=(
                            f"📋 <b>{player['nickname']}</b>\n"
                            f"🎯 Класс: {player['class']}\n"
                            f"⚔️ БМ: {player['bm']}"
                        ),
                        parse_mode=ParseMode.HTML
                    )
                )
            )

    await inline_query.answer(results, cache_time=1)


if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))





# async def parse_text_to_title(text:str):
#     title = text
#     title = title.split(sep = ' ', maxsplit = 1)[1]
#     title = title.strip()
#     return title

# async def set_custom_title(user_id, chat_id, title):
#     try:
#         #Получаем информацию о пользователе
#         member = await bot.get_chat_member(chat_id, user_id)
#         #Если пользователь не админ, то даем ему базовые права
#         if not isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
#             res = await bot.promote_chat_member(chat_id=chat_id, 
#                                                 user_id=user_id, 
#                                                 can_invite_users = True)
#             if not res: raise RuntimeError("Не удалось добавить права администратора")
#         #Даем пользователю имя
#         await bot.set_chat_administrator_custom_title(chat_id=chat_id, user_id=user_id, custom_title=title)
#     except Exception as e:
#         raise

# @dp.message(Command("set_my_info"))
# async def set_my_info(message: Message):
#     title = await parse_text_to_title(message.text)
#     if not title:
#         await message.reply(f"Введите ник в игре. Пример:\n/set_my_info <ник в игре>")
#         return
#     user_id = message.from_user.id
#     chat_id = message.chat.id
#     try:
#         await set_custom_title(user_id = user_id, 
#                                chat_id = chat_id, 
#                                title = title)
#         await message.reply(f"Должность @{message.from_user.username or user_id} установлена: {title}")
#     except Exception as e:
#         await message.reply(f"Ошибка: {e}")


# @dp.message(Command("set_user_info"))
# async def set_user_info(message: Message):
#     title = await parse_text_to_title(message.text)
#     if not title:
#         await message.reply(f"Введите ник в игре. Пример:\n/set_user_info <ник в игре>")
#         return
#     user_id = message.reply_to_message.from_user.id
#     chat_id = message.chat.id
#     try:
#         await set_custom_title(user_id = user_id, 
#                                chat_id = chat_id, 
#                                title = title)
#         await message.reply(f"Должность @{message.reply_to_message.from_user.username or user_id} установлена: {title}")
#     except Exception as e:
#         await message.reply(f"Ошибка: {e}")
