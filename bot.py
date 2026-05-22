from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    BotCommand
)
from aiogram.filters import CommandStart

import asyncio
import logging
import random
import sqlite3

from questions import COUNTRIES

import os
TOKEN = os.getenv("TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("game.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    score INTEGER DEFAULT 0,
    streak INTEGER DEFAULT 0
)
""")
conn.commit()


def create_user(user_id, username):
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username)
        VALUES (?, ?)
    """, (user_id, username))

    cursor.execute("""
        UPDATE users SET username = ? WHERE user_id = ?
    """, (username, user_id))

    conn.commit()


def get_score(user_id):
    r = cursor.execute(
        "SELECT score FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()
    return r[0] if r else 0


def get_streak(user_id):
    r = cursor.execute(
        "SELECT streak FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()
    return r[0] if r else 0


def add_score(user_id):
    cursor.execute(
        "UPDATE users SET score = score + 1 WHERE user_id=?",
        (user_id,)
    )
    conn.commit()


def increase_streak(user_id):
    cursor.execute(
        "UPDATE users SET streak = streak + 1 WHERE user_id=?",
        (user_id,)
    )
    conn.commit()


def reset_streak(user_id):
    cursor.execute(
        "UPDATE users SET streak = 0 WHERE user_id=?",
        (user_id,)
    )
    conn.commit()


def get_top_players():
    return cursor.execute("""
        SELECT username, score
        FROM users
        ORDER BY score DESC
        LIMIT 10
    """).fetchall()


# =========================
# GAME STATE
# =========================

user_questions = {}
user_modes = {}
question_tasks = {}
used_questions = {}

QUESTION_TIME = 10


# =========================
# MENU
# =========================

def menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Мир (195 стран)", callback_data="world")],

            [InlineKeyboardButton(text="🇪🇺 Европа", callback_data="Europe")],
            [InlineKeyboardButton(text="🏯 Азия", callback_data="Asia")],
            [InlineKeyboardButton(text="🌴 Африка", callback_data="Africa")],
            [InlineKeyboardButton(text="🗽 Америка", callback_data="America")],
            [InlineKeyboardButton(text="🏝 Океания", callback_data="Oceania")],

            # ✅ РЕЙТИНГ ВСЕГДА ДОСТУПЕН
            [InlineKeyboardButton(text="🏆 Рейтинг", callback_data="rating")]
        ]
    )


def create_keyboard(options):
    opts = options.copy()
    random.shuffle(opts)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=o, callback_data=o)]
            for o in opts
        ]
    )


# =========================
# QUESTION ENGINE (NO REPEATS)
# =========================

def get_question(user_id, region=None):

    if user_id not in used_questions:
        used_questions[user_id] = set()

    data = COUNTRIES

    if region:
        data = [c for c in COUNTRIES if c[2] == region]

    available = [
        c for c in data
        if c[0] not in used_questions[user_id]
    ]

    if not available:
        used_questions[user_id] = set()
        available = data

    country, capital, _ = random.choice(available)

    used_questions[user_id].add(country)

    capitals = [c[1] for c in data]

    wrong = random.sample([x for x in capitals if x != capital], 3)
    options = wrong + [capital]
    random.shuffle(options)

    return {
        "country": country,
        "capital": capital,
        "options": options
    }


# =========================
# TIMER
# =========================

async def timeout(chat_id, message_id, user_id):

    await asyncio.sleep(QUESTION_TIME)

    if user_id not in user_questions:
        return

    reset_streak(user_id)

    q = user_questions[user_id]

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"⏰ Время вышло!\n\n🏳 {q['country']}\n\n🏆 Очки: {get_score(user_id)}\n🔥 Серия: {get_streak(user_id)}",
            reply_markup=create_keyboard(q["options"])
        )
    except:
        pass


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):
    create_user(message.from_user.id, message.from_user.first_name)

    await message.answer(
        "🌍 WORLD QUIZ\n\nВыбери режим:",
        reply_markup=menu()
    )


# =========================
# CALLBACKS
# =========================

@dp.callback_query()
async def callback(callback: CallbackQuery):

    user_id = callback.from_user.id
    data = callback.data

    # ================= MODES =================

    if data in ["world", "Europe", "Asia", "Africa", "America", "Oceania"]:

        user_modes[user_id] = data

        region = None if data == "world" else data

        q = get_question(user_id, region)

        user_questions[user_id] = q

        await callback.message.edit_text(
            f"🏳 {q['country']}\n\n"
            f"🏆 Очки: {get_score(user_id)}\n"
            f"🔥 Серия: {get_streak(user_id)}",
            reply_markup=create_keyboard(q["options"])
        )

        task = asyncio.create_task(
            timeout(callback.message.chat.id,
                    callback.message.message_id,
                    user_id)
        )

        question_tasks[user_id] = task
        return


    # ================= RATING (FIXED) =================

    if data == "rating":

        players = get_top_players()

        text = "🏆 РЕЙТИНГ (ВСЕ ИГРОКИ)\n\n"

        if not players:
            text += "Пока нет игроков"
        else:
            i = 1
            for p in players:
                name = p[0] or "Unknown"
                score = p[1]

                medal = (
                    "🥇" if i == 1 else
                    "🥈" if i == 2 else
                    "🥉" if i == 3 else
                    f"{i}."
                )

                text += f"{medal} {name} — {score}\n"
                i += 1

        await callback.message.edit_text(text, reply_markup=menu())
        return


    # ================= ANSWERS =================

    q = user_questions.get(user_id)
    if not q:
        return

    if user_id in question_tasks:
        question_tasks[user_id].cancel()

    selected = data.strip()
    correct = q["capital"].strip()

    if selected == correct:
        add_score(user_id)
        increase_streak(user_id)
        result = "✅ Верно!"
    else:
        reset_streak(user_id)
        result = f"❌ Неверно!\nПравильный ответ: {correct}"

    mode = user_modes.get(user_id, "world")
    region = None if mode == "world" else mode

    new_q = get_question(user_id, region)

    user_questions[user_id] = new_q

    await callback.message.edit_text(
        f"{result}\n\n🏳 {new_q['country']}\n\n🏆 Очки: {get_score(user_id)}\n🔥 Серия: {get_streak(user_id)}",
        reply_markup=create_keyboard(new_q["options"])
    )

    task = asyncio.create_task(
        timeout(callback.message.chat.id,
                callback.message.message_id,
                user_id)
    )

    question_tasks[user_id] = task


# =========================
# MAIN
# =========================

async def main():
    print("Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())