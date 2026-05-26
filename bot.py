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
rating = {}


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
                InlineKeyboardButton(
                    text="🌍 Все страны мира",
                    callback_data="ALL"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏛 Европа",
                    callback_data="Europe"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🕌 Азия",
                    callback_data="Asia"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🦁 Африка",
                    callback_data="Africa"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗽 Америка",
                    callback_data="America"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏝 Океания",
                    callback_data="Oceania"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏆 Рейтинг",
                    callback_data="rating"
                )
            ]
        ]
    )

    await message.answer(
        "🌍 WORLD QUIZ\n\nВыберите режим:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "rating")
async def show_rating(call: CallbackQuery):
    if not rating:
        await call.message.answer("🏆 Рейтинг пока пуст.")
        await call.answer()
        return

    text = "🏆 Рейтинг игроков:\n\n"

    sorted_rating = sorted(
        rating.items(),
        key=lambda x: x[1],
        reverse=True
    )

    for i, (name, score) in enumerate(sorted_rating[:10], start=1):
        text += f"{i}. {name} — {score}\n"

    await call.message.answer(text)
    await call.answer()


@dp.callback_query()
async def region_selected(call: CallbackQuery):
    region = call.data
    user_id = call.from_user.id

    if region == "ALL":
        questions = generate_questions()
    else:
        questions = generate_questions(region)

    random.shuffle(questions)

    users[user_id] = {
        "score": 0,
        "questions": questions,
    }

    await send_question(call.message, user_id)

    await call.answer()


async def send_question(message, user_id):
    question = get_question(user_id)

    if not question:
        score = users[user_id]["score"]

        username = (
            message.chat.username
            or message.chat.first_name
            or "Игрок"
        )

        if username not in rating:
            rating[username] = 0

        if score > rating[username]:
            rating[username] = score

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 Играть снова",
                        callback_data="restart"
                    )
                ]
            ]
        )

        await message.answer(
            f"🎉 Игра окончена!\n\n"
            f"Ваш результат: {score}",
            reply_markup=keyboard
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
        f"Столица какой страны?\n\n"
        f"{question['country']}",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "restart")
async def restart(call: CallbackQuery):
    await start(call.message)
    await call.answer()


@dp.callback_query(F.data.startswith("answer|"))
async def answer_handler(call: CallbackQuery):
    user_id = call.from_user.id
    answer = call.data.split("|")[1]

    question = users[user_id]["current"]

    if answer == question["capital"]:
        users[user_id]["score"] += 1

        await call.message.answer(
            "✅ Правильно!"
        )
    else:
        await call.message.answer(
            f"❌ Неправильно!\n\n"
            f"Правильный ответ: {question['capital']}"
        )

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
    print("BOT STARTED")

    web.run_app(
        app,
        host="0.0.0.0",
        port=PORT
    )
