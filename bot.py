import asyncio
import logging
import os
import random

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update,
)
from aiogram.client.default import DefaultBotProperties

from questions import generate_questions
questions = generate_questions()

# =========================
# НАСТРОЙКИ
# =========================

TOKEN = os.getenv("BOT_TOKEN")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://geo-bot-bg9k.onrender.com{WEBHOOK_PATH}"

PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)

# =========================
# BOT / DP
# =========================

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher()

# =========================
# ДАННЫЕ
# =========================

user_data = {}

regions = {
    "world": "🌍 Все страны мира",
    "europe": "🇪🇺 Европа",
    "asia": "🌏 Азия",
    "africa": "🌍 Африка",
    "north_america": "🌎 Северная Америка",
    "south_america": "🌎 Южная Америка",
    "oceania": "🌏 Океания",
}

# =========================
# КНОПКИ
# =========================


def main_menu():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌍 Все страны мира",
                    callback_data="region_world",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🇪🇺 Европа",
                    callback_data="region_europe",
                ),
                InlineKeyboardButton(
                    text="🌏 Азия",
                    callback_data="region_asia",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🌍 Африка",
                    callback_data="region_africa",
                ),
                InlineKeyboardButton(
                    text="🌎 Сев. Америка",
                    callback_data="region_north_america",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🌎 Юж. Америка",
                    callback_data="region_south_america",
                ),
                InlineKeyboardButton(
                    text="🌏 Океания",
                    callback_data="region_oceania",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏆 Рейтинг",
                    callback_data="rating",
                )
            ],
        ]
    )

    return keyboard


def answer_keyboard(options):
    buttons = []

    for option in options:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=option,
                    callback_data=f"answer_{option}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# =========================
# ВОПРОСЫ
# =========================


def get_questions_by_region(region):
    if region == "world":
        return questions

    return [
        q for q in questions
        if q.get("region") == region
    ]


def get_question(user_id, region):
    region_questions = get_questions_by_region(region)

    if user_id not in user_data:
        user_data[user_id] = {}

    if "used_questions" not in user_data[user_id]:
        user_data[user_id]["used_questions"] = {}

    if region not in user_data[user_id]["used_questions"]:
        user_data[user_id]["used_questions"][region] = []

    used = user_data[user_id]["used_questions"][region]

    available = [
        q for q in region_questions
        if q["country"] not in used
    ]

    # если круг закончился → начинаем новый
    if not available:
        user_data[user_id]["used_questions"][region] = []
        used = []
        available = region_questions.copy()

    question = random.choice(available)

    user_data[user_id]["used_questions"][region].append(
        question["country"]
    )

    return question


# =========================
# РЕЙТИНГ
# =========================


def get_rating_text():
    world_players = []

    for uid, data in user_data.items():
        score = data.get("world_score", 0)

        if score > 0:
            world_players.append(score)

    world_players.sort(reverse=True)

    if not world_players:
        return "🏆 Рейтинг пока пуст"

    text = "🏆 <b>Рейтинг мира</b>\n\n"

    for i, score in enumerate(world_players[:10], start=1):
        text += f"{i}. {score} очков\n"

    return text


# =========================
# START
# =========================


@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id

    if user_id not in user_data:
        user_data[user_id] = {
            "score": 0,
            "world_score": 0,
        }

    await message.answer(
        "🌍 <b>Добро пожаловать в ГеоКвиз!</b>\n\nВыберите режим:",
        reply_markup=main_menu(),
    )


# =========================
# CALLBACKS
# =========================


@dp.callback_query(F.data == "rating")
async def show_rating(callback: CallbackQuery):
    await callback.message.edit_text(
        get_rating_text(),
        reply_markup=main_menu(),
    )


@dp.callback_query(F.data.startswith("region_"))
async def choose_region(callback: CallbackQuery):
    region = callback.data.replace("region_", "")
    user_id = callback.from_user.id

    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]["region"] = region

    question = get_question(user_id, region)

    user_data[user_id]["current_question"] = question

    options = question["options"].copy()
    random.shuffle(options)

    await callback.message.edit_text(
        f"🌍 Где находится страна:\n\n"
        f"<b>{question['country']}</b>",
        reply_markup=answer_keyboard(options),
    )


@dp.callback_query(F.data.startswith("answer_"))
async def answer(callback: CallbackQuery):
    user_id = callback.from_user.id

    selected = callback.data.replace("answer_", "")

    question = user_data[user_id]["current_question"]

    correct = question["correct"]

    region = user_data[user_id]["region"]

    if selected == correct:
        text = "✅ Правильно!"

        user_data[user_id]["score"] = (
            user_data[user_id].get("score", 0) + 1
        )

        if region == "world":
            user_data[user_id]["world_score"] = (
                user_data[user_id].get("world_score", 0) + 1
            )

    else:
        text = (
            f"❌ Неправильно!\n\n"
            f"Правильный ответ: <b>{correct}</b>"
        )

    question = get_question(user_id, region)

    user_data[user_id]["current_question"] = question

    options = question["options"].copy()
    random.shuffle(options)

    await callback.message.edit_text(
        f"{text}\n\n"
        f"🌍 Следующая страна:\n\n"
        f"<b>{question['country']}</b>",
        reply_markup=answer_keyboard(options),
    )


# =========================
# WEBHOOK
# =========================


async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook set!")


async def on_shutdown(app):
    await bot.delete_webhook()
    print("Webhook deleted!")


async def handle_webhook(request):
    update = Update.model_validate(
        await request.json(),
        context={"bot": bot},
    )

    await dp.feed_update(bot, update)

    return web.Response()


# =========================
# APP
# =========================

app = web.Application()

app.router.add_post(WEBHOOK_PATH, handle_webhook)

app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

# =========================
# RUN
# =========================

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
