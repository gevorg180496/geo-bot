import asyncio
import logging
import os
import random

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

from questions import questions

TOKEN = os.getenv("TOKEN")

WEBHOOK_PATH = "/webhook"
geo-bot

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

user_questions = {}
used_questions = {}

QUESTION_TIME = 10


# =========================
# КНОПКИ
# =========================

def create_keyboard(options):

    random.shuffle(options)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=option,
                    callback_data=option
                )
            ]
            for option in options
        ]
    )

    return keyboard


def create_menu():

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="🌍 Все страны мира",
                    callback_data="world"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🏛 Европа",
                    callback_data="europe"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🏯 Азия",
                    callback_data="asia"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🦁 Африка",
                    callback_data="africa"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🗽 Америка",
                    callback_data="america"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🏝 Океания",
                    callback_data="oceania"
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

    return keyboard


# =========================
# ВОПРОСЫ
# =========================

def get_questions_by_region(region):

    if region == "world":
        return questions

    return [
        q for q in questions
        if q["region"] == region
    ]


def get_question(user_id, region):

    key = f"{user_id}_{region}"

    if key not in used_questions:
        used_questions[key] = []

    region_questions = get_questions_by_region(region)

    available_questions = [
        q for q in region_questions
        if q["country"] not in used_questions[key]
    ]

    if len(available_questions) == 0:

        used_questions[key] = []

        available_questions = region_questions

    question = random.choice(available_questions)

    used_questions[key].append(question["country"])

    return question


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):

    text = (
        "🌍 <b>WORLD QUIZ</b>\n\n"
        "Выберите режим:"
    )

    await message.answer(
        text,
        reply_markup=create_menu()
    )


# =========================
# CALLBACKS
# =========================

@dp.callback_query()
async def callbacks(callback: CallbackQuery):

    user_id = callback.from_user.id
    data = callback.data

    if data == "rating":

        text = (
            "🏆 Рейтинг пока в разработке"
        )

        await callback.message.edit_text(
            text,
            reply_markup=create_menu()
        )

        return

    question = get_question(user_id, data)

    user_questions[user_id] = {
        "question": question,
        "region": data
    }

    keyboard = create_keyboard(question["options"])

    text = (
        f"🌍 Какая столица у страны:\n\n"
        f"🏳 {question['country']}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )


# =========================
# ОТВЕТЫ
# =========================

@dp.callback_query()
async def answer_handler(callback: CallbackQuery):

    user_id = callback.from_user.id

    if user_id not in user_questions:
        return

    current = user_questions[user_id]

    question = current["question"]
    region = current["region"]

    selected_answer = callback.data

    correct_answer = question["capital"]

    if selected_answer == correct_answer:
        result = "✅ Верно!"
    else:
        result = (
            f"❌ Неверно!\n"
            f"Правильный ответ: {correct_answer}"
        )

    new_question = get_question(user_id, region)

    user_questions[user_id] = {
        "question": new_question,
        "region": region
    }

    keyboard = create_keyboard(new_question["options"])

    text = (
        f"{result}\n\n"
        f"🌍 Какая столица у страны:\n\n"
        f"🏳 {new_question['country']}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )


# =========================
# WEBHOOK
# =========================

async def on_startup(bot: Bot):

    await bot.set_webhook(WEBHOOK_URL)

    print("Webhook started...")


async def on_shutdown(bot: Bot):

    await bot.delete_webhook()

    print("Webhook stopped...")


async def handle(request):

    update = await request.json()

    await dp.feed_webhook_update(
        bot,
        update
    )

    return web.Response()


async def main():

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    app.router.add_post(
        WEBHOOK_PATH,
        handle
    )

    runner = web.AppRunner(app)

    await runner.setup()

    port = int(os.getenv("PORT", 10000))

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
