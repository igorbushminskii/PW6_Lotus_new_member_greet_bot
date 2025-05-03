import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.enums import ChatType
from aiogram import F
import asyncio
import socket


# Вставь свой токен
TOKEN = os.getenv("BOT_TOKEN")  # безопасно вытаскиваем из окружения
if not TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не задана!")

bot = Bot(token=TOKEN)
dp = Dispatcher()


# Заглушка: слушаем порт, чтобы Render не ругался
async def fake_web_server():
    port = int(os.getenv("PORT", 10000))  # Render прокидывает PORT
    server = socket.socket()
    server.bind(("0.0.0.0", port))
    server.listen(1)
    print(f"Fake HTTP server listening on port {port}")
    while True:
        await asyncio.sleep(3600)  # просто "живём"


# Ответ на /start
@dp.message(CommandStart())
async def start_command(message: Message):
    await message.answer("Привет! Я работаю и в форумах тоже 😉")

# Обработка новых участников (в том числе в темах)
@dp.message(F.new_chat_members)
async def welcome_new_members(message: Message):
    for user in message.new_chat_members:
        username = user.username
        if username:
            mention = f"@{username}"
        else:
            mention = user.full_name
        await bot.send_message(
            chat_id=message.chat.id,
            message_thread_id=message.message_thread_id,  # Важно для форумов
            text=f"Привет, {mention}! Добро пожаловать в группу Гильдии Lotus. Зайди в чат https://t.me/PW6_Lotus/7 и укажи свои ник/класс/имя. Если ты еще не в гильдии, то укажи БМ и дождись ответа о возможности вступления от администраторов."
        )

# Обработка обычных сообщений (в темах тоже)
@dp.message(F.text)
async def echo(message: Message):
    pass
    #Здесь может быть обработака текстовых сообщений
    # await bot.send_message(
    #     chat_id=message.chat.id,
    #     message_thread_id=message.message_thread_id,  # Чтобы ответить в той же теме
    #     text=f"Ты написал: {message.text}"
    # )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
