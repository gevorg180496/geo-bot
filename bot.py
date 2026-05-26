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

games = {}
ratings = {}


def get_question(user_id):
    game = games[user_id]

    if game["index"] >= len(game["questions"]):
        return None

    question = game["questions"][game["index"]]
    game["index"] += 1

    return question


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
        "🌍 WORLD QUIZ\n\nВыберите режим игры:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "rating")
async def show_rating(call: CallbackQuery):
    if not ratings:
        await call.message.answer("🏆 Рейтинг пока пуст.")
        await call.answer()
        return

    text = "🏆 ТОП ИГРОКОВ\n\n"

    sorted_rating = sorted(
        ratings.items(),
        key=lambda x: x[1],
        reverse=True
    )

    for i, (name, score) in enumerate(sorted_rating[:10], start=1):
        text += f"{i}. {name} — {score}\n"

    await call.message.answer(text)
    await call.answer()


@dp.callback_query(
    F.data.in_([
        "ALL",
        "Europe",
        "Asia",
        "Africa",
        "America",
        "Oceania"
    ])
)
async def region_selected(call: CallbackQuery):
    user_id = call.from_user.id
    region = call.data

    if region == "ALL":
        questions = generate_questions()
        mode = None
    else:
        questions = generate_questions(region)
        mode = region

    random.shuffle(questions)

    games[user_id] = {
        "questions": questions,
        "index": 0,
        "score": 0,
        "streak": 0,
        "best_streak": 0,
        "mode": mode
    }

    await send_question(call.message, user_id)

    await call.answer()


async def send_question(message, user_id):
    question = get_question(user_id)

    if not question:
        game = games[user_id]

        score = game["score"]
        best_streak = game["best_streak"]

        username = (
            message.chat.username
            or message.chat.first_name
            or "Игрок"
        )

        # рейтинг только для всех стран мира
        if game["mode"] is None:
            if username not in ratings:
                ratings[username] = 0

            if score > ratings[username]:
                ratings[username] = score

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
            f"✅ Правильных ответов: {score}\n"
            f"🔥 Лучшая серия: {best_streak}",
            reply_markup=keyboard
        )

        return

    games[user_id]["current"] = question

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
        f"🌍 Столица какой страны?\n\n"
        f"❓ {question['country']}",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("answer|"))
async def answer_handler(call: CallbackQuery):
    user_id = call.from_user.id
    answer = call.data.split("|")[1]

    game = games[user_id]
    question = game["current"]

    if answer == question["capital"]:
        game["score"] += 1
        game["streak"] += 1

        if game["streak"] > game["best_streak"]:
            game["best_streak"] = game["streak"]

        await call.message.answer("✅ Правильно!")

    else:
        game["streak"] = 0

        await call.message.answer(
            f"❌ Неправильно!\n\n"
            f"Правильный ответ: {question['capital']}"
        )

    await send_question(call.message, user_id)

    await call.answer()


@dp.callback_query(F.data == "restart")
async def restart(call: CallbackQuery):
    await start(call.message)
    await call.answer()


app = web.Application()

SimpleRequestHandler(
    dispatcher=dp,
    bot=bot,
).register(app, path=WEBHOOK_PATH)

setup_application(app, dp, bot=bot)

PORT = int(os.environ.get("PORT", 10000))


async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook set!")


app.on_startup.append(on_startup)

if __name__ == "__main__":
    print("BOT STARTED")

    web.run_app(
        app,
        host="0.0.0.0",
        port=PORT
    )
