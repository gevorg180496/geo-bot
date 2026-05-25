import asyncio
import json
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
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = "https://geo-bot-bg9k.onrender.com/webhook"

# =========================
# ЗАГРУЗКА ВОПРОСОВ
# =========================

with open("questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

# =========================
# РЕЙТИНГ
# =========================

RATING_FILE = "rating.json"

if not os.path.exists(RATING_FILE):
    with open(RATING_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

with open(RATING_FILE, "r", encoding="utf-8") as f:
    rating_data = json.load(f)

# =========================
# ПОЛЬЗОВАТЕЛИ
# =========================

users = {}

# =========================
# РЕГИОНЫ
# =========================

REGIONS = {
    "world": "🌍 Весь мир",
    "europe": "🏰 Европа",
    "asia": "🏯 Азия",
    "africa": "🦁 Африка",
    "north_america": "🗽 Северная Америка",
    "south_america": "🦜 Южная Америка",
    "oceania": "🏝 Океания",
}

# =========================
# МЕНЮ
# =========================

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌍 Весь мир",
                    callback_data="region_world",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏰 Европа",
                    callback_data="region_europe",
                ),
                InlineKeyboardButton(
                    text="🏯 Азия",
                    callback_data="region_asia",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🦁 Африка",
                    callback_data="region_africa",
                ),
                InlineKeyboardButton(
                    text="🗽 Северная Америка",
                    callback_data="region_north_america",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🦜 Южная Америка",
                    callback_data="region_south_america",
                ),
                InlineKeyboardButton(
                    text="🏝 Океания",
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

# =========================
# ФИЛЬТР ПО РЕГИОНУ
# =========================

def get_questions_by_region(region):
    if region == "world":
        return questions

    return [
        q for q in questions
        if q.get("region") == region
    ]

# =========================
# НОВЫЙ КРУГ
# =========================

def start_new_round(user_id, region):
    region_questions = get_questions_by_region(region)

    shuffled = region_questions.copy()
    random.shuffle(shuffled)

    users[user_id] = {
        "region": region,
        "questions": shuffled,
        "current": 0,
        "score": 0,
    }

# =========================
# ТЕКУЩИЙ ВОПРОС
# =========================

def get_current_question(user_id):
    user = users[user_id]

    if user["current"] >= len(user["questions"]):
        return None

    return user["questions"][user["current"]]

# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🌎 <b>Квиз по географии</b>\n\n"
        "Выбери режим:",
        reply_markup=main_menu(),
    )

# =========================
# CALLBACKS
# =========================

@dp.callback_query(F.data.startswith("region_"))
async def choose_region(callback: CallbackQuery):
    region = callback.data.replace("region_", "")

    start_new_round(callback.from_user.id, region)

    question = get_current_question(callback.from_user.id)

    await callback.message.edit_text(
        f"🌍 Страна:\n\n"
        f"<b>{question['country']}</b>\n\n"
        f"Напиши столицу:",
    )

    await callback.answer()

# =========================
# РЕЙТИНГ
# =========================

@dp.callback_query(F.data == "rating")
async def show_rating(callback: CallbackQuery):
    if not rating_data:
        text = "🏆 Рейтинг пока пуст."
    else:
        sorted_rating = sorted(
            rating_data.items(),
            key=lambda x: x[1],
            reverse=True
        )

        lines = []

        for i, (name, score) in enumerate(sorted_rating[:10], start=1):
            lines.append(f"{i}. {name} — {score}")

        text = "🏆 <b>ТОП игроков</b>\n\n" + "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=main_menu(),
    )

    await callback.answer()

# =========================
# ОТВЕТЫ
# =========================

@dp.message()
async def answers(message: Message):
    user_id = message.from_user.id

    if user_id not in users:
        return

    user = users[user_id]

    question = get_current_question(user_id)

    if not question:
        return

    user_answer = message.text.strip().lower()
    correct_answer = question["capital"].strip().lower()

    if user_answer == correct_answer:
        user["score"] += 1

        text = "✅ Правильно!"
    else:
        text = (
            f"❌ Неправильно!\n\n"
            f"Правильный ответ:\n"
            f"<b>{question['capital']}</b>"
        )

    user["current"] += 1

    next_question = get_current_question(user_id)

    if next_question:
        await message.answer(
            f"{text}\n\n"
            f"🌍 Следующая страна:\n\n"
            f"<b>{next_question['country']}</b>\n\n"
            f"Напиши столицу:"
        )
    else:
        final_score = user["score"]
        total = len(user["questions"])

        region = user["region"]

        result_text = (
            f"🏁 Круг завершён!\n\n"
            f"🎯 Результат: {final_score}/{total}"
        )

        if region == "world":
            username = message.from_user.first_name

            old_score = rating_data.get(username, 0)

            if final_score > old_score:
                rating_data[username] = final_score

                with open(RATING_FILE, "w", encoding="utf-8") as f:
                    json.dump(rating_data, f, ensure_ascii=False, indent=2)

                result_text += "\n\n🏆 Новый рекорд!"

        await message.answer(
            result_text,
            reply_markup=main_menu(),
        )

# =========================
# WEBHOOK
# =========================

async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()

async def handle(request):
    update = await request.json()
    await dp.feed_webhook_update(
        bot=bot,
        update=update
    )
    return web.Response()

# =========================
# MAIN
# =========================

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    app.router.add_post(WEBHOOK_PATH, handle)

    port = int(os.environ.get("PORT", 10000))

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    print("Bot started...")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
