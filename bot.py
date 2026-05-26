import os
import random
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)

from questions import generate_questions

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = "https://geo-bot-bg9k.onrender.com/webhook"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

users = {}


def get_question(user_id):
    user = users[user_id]

    if not user["questions"]:
        return None

    return user["questions"].pop()


@dp.message(CommandStart())
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🌍 Европа", callback_data="Europe")
            ],
            [
                InlineKeyboardButton(text="🌏 Азия", callback_data="Asia")
            ],
            [
                InlineKeyboardButton(text="🌍 Африка", callback_data="Africa")
            ],
            [
                InlineKeyboardButton(text="🌎 Америка", callback_data="America")
            ],
            [
                InlineKeyboardButton(text="🌏 Океания", callback_data="Oceania")
            ],
        ]
    )

    await message.answer(
        "Выбери регион:",
        reply_markup=keyboard
    )


@dp.callback_query()
async def callbacks(call: CallbackQuery):
    region = call.data
    user_id = call.from_user.id

    questions = generate_questions(region)
    random.shuffle(questions)

    users[user_id] = {
        "score": 0,
        "questions": questions
    }

    await send_question(call.message, user_id)

    await call.answer()


async def send_question(message, user_id):
    question = get_question(user_id)

    if not question:
        score = users[user_id]["score"]

        await message.answer(
            f"🎉 Игра окончена!\n\nРезультат: {score}"
        )
        return

    users[user_id]["current"] = question

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=option,
                    callback_data=f"answer|{option}"
                )
            ]
            for option in question["options"]
        ]
    )

    await message.answer(
        f"Столица какой страны?\n\n{question['country']}",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("answer|"))
async def answers(call: CallbackQuery):
    user_id = call.from_user.id
    answer = call.data.split("|")[1]

    question = users[user_id]["current"]

    if answer == question["capital"]:
        users[user_id]["score"] += 1
        text = "✅ Правильно!"
    else:
        text = f"❌ Неправильно!\nПравильный ответ: {question['capital']}"

    await call.message.answer(text)

    await send_question(call.message, user_id)

    await call.answer()


async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)


app = web.Application()

SimpleRequestHandler(
    dispatcher=dp,
    bot=bot,
).register(app, path=WEBHOOK_PATH)

setup_application(app, dp, bot=bot)

PORT = int(os.environ.get("PORT", 10000))

if __name__ == "__main__":
    try:
        web.run_app(app, host="0.0.0.0", port=PORT)
    except Exception as e:
        print("START ERROR:", e)
