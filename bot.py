import asyncio
import logging
import os
import random

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Update
)

from questions import generate_questions

# ================= НАСТРОЙКИ =================

TOKEN = os.getenv("BOT_TOKEN")

WEBHOOK_HOST = "https://geo-bot-bg9k.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

# ================= ДАННЫЕ =================

user_sessions = {}
leaderboard = {}

# ================= КНОПКИ =================

def main_menu():
    keyboard = [
        [KeyboardButton(text="🌎 Все страны мира")],
        [KeyboardButton(text="🇪🇺 Европа"), KeyboardButton(text="🌏 Азия")],
        [KeyboardButton(text="🌍 Африка"), KeyboardButton(text="🌎 Америка")],
        [KeyboardButton(text="🏝️ Океания")],
        [KeyboardButton(text="🏆 Рейтинг")]
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

# ================= СТАРТ =================

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🌍 Добро пожаловать в Geo Bot!\n\n"
        "Выберите режим игры:",
        reply_markup=main_menu()
    )

# ================= СТАРТ ИГРЫ =================

async def start_game(message: Message, region_name, region_code):
    questions = generate_questions(region_code)

    random.shuffle(questions)

    user_sessions[message.chat.id] = {
        "questions": questions,
        "index": 0,
        "score": 0,
        "region": region_code
    }

    await message.answer(
        f"🎮 Режим: {region_name}\n\n"
        f"Удачи!"
    )

    await send_question(message.chat.id)

# ================= РЕЖИМЫ =================

@dp.message(F.text == "🌎 Все страны мира")
async def world(message: Message):
    await start_game(message, "Все страны мира", "WORLD")

@dp.message(F.text == "🇪🇺 Европа")
async def europe(message: Message):
    await start_game(message, "Европа", "Europe")

@dp.message(F.text == "🌏 Азия")
async def asia(message: Message):
    await start_game(message, "Азия", "Asia")

@dp.message(F.text == "🌍 Африка")
async def africa(message: Message):
    await start_game(message, "Африка", "Africa")

@dp.message(F.text == "🌎 Америка")
async def america(message: Message):
    await start_game(message, "Америка", "America")

@dp.message(F.text == "🏝️ Океания")
async def oceania(message: Message):
    await start_game(message, "Океания", "Oceania")

# ================= РЕЙТИНГ =================

@dp.message(F.text == "🏆 Рейтинг")
async def show_rating(message: Message):
    if not leaderboard:
        await message.answer("🏆 Рейтинг пока пуст.")
        return

    sorted_players = sorted(
        leaderboard.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    text = "🏆 Топ игроков:\n\n"

    for i, (user_id, score) in enumerate(sorted_players, start=1):
        try:
            user = await bot.get_chat(user_id)
            name = user.first_name
        except:
            name = "Игрок"

        text += f"{i}. {name} — {score}\n"

    await message.answer(text)

# ================= ВОПРОС =================

async def send_question(chat_id):
    session = user_sessions[chat_id]

    if session["index"] >= len(session["questions"]):
        streak = session["score"]

        text = (
            f"🎉 Игра окончена!\n\n"
            f"🔥 Правильных подряд: {streak}\n"
        )

        if session["region"] == "WORLD":
            old_score = leaderboard.get(chat_id, 0)

            if streak > old_score:
                leaderboard[chat_id] = streak
                text += "\n🏆 Новый рекорд!"
            else:
                text += f"\n🏆 Ваш рекорд: {old_score}"

        del user_sessions[chat_id]

        await bot.send_message(
            chat_id,
            text,
            reply_markup=main_menu()
        )
        return

    q = session["questions"][session["index"]]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=opt)]
            for opt in q["options"]
        ]
    )

    await bot.send_message(
        chat_id,
        f"🌍 Страна: <b>{q['country']}</b>\n\n"
        f"Выберите столицу:",
        reply_markup=kb
    )

# ================= ОТВЕТ =================

@dp.callback_query()
async def answer(callback: CallbackQuery):
    chat_id = callback.message.chat.id

    if chat_id not in user_sessions:
        return

    session = user_sessions[chat_id]
    q = session["questions"][session["index"]]

    if callback.data == q["capital"]:
        session["score"] += 1
        session["index"] += 1

        await callback.message.edit_text(
            f"✅ Правильно!\n"
            f"🔥 Серия: {session['score']}"
        )

        await send_question(chat_id)

    else:
        streak = session["score"]

        text = (
            f"❌ Неправильно!\n\n"
            f"Правильный ответ: {q['capital']}\n\n"
            f"🔥 Правильных подряд: {streak}"
        )

        if session["region"] == "WORLD":
            old_score = leaderboard.get(chat_id, 0)

            if streak > old_score:
                leaderboard[chat_id] = streak
                text += "\n🏆 Новый рекорд!"
            else:
                text += f"\n🏆 Ваш рекорд: {old_score}"

        del user_sessions[chat_id]

        await callback.message.edit_text(text)

        await bot.send_message(
            chat_id,
            "Выберите режим:",
            reply_markup=main_menu()
        )

    await callback.answer()

# ================= WEBHOOK =================

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook set: {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()

async def handle(request):
    data = await request.json()

    update = Update.model_validate(data)

    await dp.feed_update(bot, update)

    return web.Response(text="ok")

# ================= SERVER =================

app = web.Application()

app.router.add_post(WEBHOOK_PATH, handle)

app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
