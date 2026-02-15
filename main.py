import asyncio
import os
import random
from datetime import datetime
import asyncpg
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    WebAppInfo
)
from aiogram.filters import CommandStart

# ================= CONFIG =================

BOT_TOKEN = os.getenv("8464060678:AAEy8RGmfQX88EXRrzRqJvpSIgZ8G_bU2eA")
DATABASE_URL = os.getenv("DATABASE_URL")
MINI_APP_URL = os.getenv("https://t.me/Duafubot/umma")
CHANNEL_URL = os.getenv("t.me/duafu")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
pool = None

# ================= TEXTS =================

REMINDERS = {
    0: [  # Monday
        "🤲 Новая неделя — начни её с дуа.",
        "🌿 Возможно, сегодня чьё-то сердце ждёт твоей молитвы."
    ],
    1: [
        "📖 Каждое искреннее дуа записывается.",
        "🤍 Поддержи кого-то сегодня своей молитвой."
    ],
    2: [
        "🌙 Даже одно дуа может изменить судьбу.",
        "🤲 Зайди в Duafu и поддержи брата или сестру."
    ],
    3: [
        "🌅 Ночь перед пятницей — время дуа.",
        "🤍 Подготовься к благословенному дню."
    ],
    4: [
        "🌙 Сегодня Джума — лучший день для дуа.",
        "🤲 Удели время молитве за других."
    ],
    5: [
        "🌿 Продолжай добро после пятницы.",
        "🤍 Duafu ждёт твоего участия."
    ],
    6: [
        "🌅 Заверши неделю с дуа.",
        "🤲 Пусть новая неделя начнётся с награды."
    ],
}

HADITHS = [
    "📖 Аллах помогает рабу, пока раб помогает своему брату. (Муслим)",
    "📖 Дуа — это поклонение. (Тирмизи)",
    "📖 Лучший день, в который взошло солнце — пятница. (Муслим)",
    "📖 Кто облегчает положение верующего, тому Аллах облегчит. (Муслим)",
    "📖 Аллах ближе к вам, чем вы думаете."
]

# ================= DATABASE =================

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)

    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            daily_enabled BOOLEAN DEFAULT FALSE,
            hadith_enabled BOOLEAN DEFAULT FALSE
        );
        """)

# ================= START =================

@dp.message(CommandStart())
async def start(message: Message):
    async with pool.acquire() as conn:
        await conn.execute("""
        INSERT INTO users (user_id)
        VALUES ($1)
        ON CONFLICT (user_id) DO NOTHING
        """, message.from_user.id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🤲 Открыть Duafu",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )],
        [
            InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about"),
            InlineKeyboardButton(text="🌿 Напоминания Duafu", callback_data="reminders")
        ]
    ])

    await message.answer(
        "Assalamu alaikum wa rahmatullahi wa barakatuh 🤲\n\n"
        "Duafu — платформа, где мусульмане делают дуа друг за друга.\n"
        "Пусть каждое дуа станет причиной награды.",
        reply_markup=keyboard
    )

# ================= ABOUT =================

@dp.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    text = (
        "🤍 Duafu объединяет мусульман в дуа.\n\n"
        "📢 Наш официальный канал:\n"
        f"{CHANNEL_URL}\n\n"
        "Вы можете поддержать проект подарками или Telegram Stars для канала ⭐"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Перейти в канал", url=CHANNEL_URL)]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)

# ================= REMINDER SETTINGS =================

@dp.callback_query(F.data == "reminders")
async def reminder_settings(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤲 Включить напоминания о дуа", callback_data="toggle_daily")],
        [InlineKeyboardButton(text="📖 Включить хадис недели", callback_data="toggle_hadith")],
        [InlineKeyboardButton(text="❌ Отключить все уведомления", callback_data="disable_all")]
    ])

    await callback.message.edit_text(
        "Выберите тип уведомлений:",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "toggle_daily")
async def toggle_daily(callback: CallbackQuery):
    async with pool.acquire() as conn:
        await conn.execute("""
        UPDATE users SET daily_enabled = NOT daily_enabled WHERE user_id=$1
        """, callback.from_user.id)

    await callback.answer("Настройка обновлена ✅")

@dp.callback_query(F.data == "toggle_hadith")
async def toggle_hadith(callback: CallbackQuery):
    async with pool.acquire() as conn:
        await conn.execute("""
        UPDATE users SET hadith_enabled = NOT hadith_enabled WHERE user_id=$1
        """, callback.from_user.id)

    await callback.answer("Настройка обновлена ✅")

@dp.callback_query(F.data == "disable_all")
async def disable_all(callback: CallbackQuery):
    async with pool.acquire() as conn:
        await conn.execute("""
        UPDATE users SET daily_enabled = FALSE, hadith_enabled = FALSE WHERE user_id=$1
        """, callback.from_user.id)

    await callback.answer("Все уведомления отключены ❌")

# ================= SCHEDULER =================

async def scheduler():
    while True:
        now = datetime.utcnow()
        weekday = now.weekday()

        async with pool.acquire() as conn:
            users = await conn.fetch("SELECT * FROM users")

        for user in users:
            if user["daily_enabled"] and now.hour in [10, 18]:
                text = random.choice(REMINDERS[weekday])
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🤲 Открыть Duafu",
                        web_app=WebAppInfo(url=MINI_APP_URL)
                    )]
                ])
                try:
                    await bot.send_message(user["user_id"], text, reply_markup=keyboard)
                except:
                    pass

            if user["hadith_enabled"] and weekday == 4 and now.hour == 12:
                hadith = HADITHS[now.isocalendar().week % len(HADITHS)]
                try:
                    await bot.send_message(user["user_id"], hadith)
                except:
                    pass

        await asyncio.sleep(3600)

# ================= MAIN =================

async def main():
    await init_db()
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())