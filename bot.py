import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from supabase import create_client, Client


# =========================
# CONFIG
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is missing")

if not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_KEY is missing")


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# Bangladesh time = UTC+6
BD_TZ = timezone(timedelta(hours=6))


# =========================
# DATE
# =========================

def today_bd():
    return datetime.now(BD_TZ).date()


def today_string():
    return today_bd().isoformat()


# =========================
# /start
# =========================

@dp.message(Command("start"))
async def start_command(message: types.Message):

    await message.answer(
        "📚 Study Tracker Bot\n\n"
        "আপনার আজকের পড়ার সময় দিতে লিখুন:\n\n"
        "/study 2\n\n"
        "এখানে 2 মানে 2 ঘণ্টা।\n\n"
        "একই দিনে আবার /study দিলে আগের সময় "
        "replace হয়ে নতুন সময় save হবে।\n\n"
        "উদাহরণ:\n"
        "/study 5.5"
    )


# =========================
# /study
# =========================

@dp.message(Command("study"))
async def study_command(message: types.Message):

    args = message.text.split()

    if len(args) != 2:

        await message.answer(
            "❌ সঠিক format:\n\n"
            "/study 2\n"
            "/study 3.5"
        )

        return

    try:
        hours = float(args[1])

    except ValueError:

        await message.answer(
            "❌ ঘণ্টার সংখ্যা সঠিকভাবে দিন।\n\n"
            "উদাহরণ:\n"
            "/study 2.5"
        )

        return

    if hours <= 0 or hours > 24:

        await message.answer(
            "❌ সময় 0 থেকে 24 ঘণ্টার মধ্যে হতে হবে।"
        )

        return

    user = message.from_user
    chat = message.chat

    user_name = (
        user.full_name
        or user.username
        or str(user.id)
    )

    username = user.username or ""

    study_date = today_string()

    try:

        # Group/chat save
        supabase.table("study_chats").upsert(
            {
                "chat_id": chat.id,
                "chat_title": chat.title or "Private"
            },
            on_conflict="chat_id"
        ).execute()

        # User + today's value
        # Same user + same day = replace previous value
        supabase.table("study_records").upsert(
            {
                "chat_id": chat.id,
                "telegram_user_id": user.id,
                "name": user_name,
                "username": username,
                "study_date": study_date,
                "hours": hours
            },
            on_conflict="chat_id,telegram_user_id,study_date"
        ).execute()

        await message.answer(
            f"✅ Saved!\n\n"
            f"👤 {user_name}\n"
            f"📚 আজকের সর্বশেষ সময়: {hours:g} ঘণ্টা\n\n"
            f"আগের সময় replace হয়ে গেছে।"
        )

        logger.info(
            "Study saved | chat=%s user=%s hours=%s date=%s",
            chat.id,
            user.id,
            hours,
            study_date
        )

    except Exception as e:

        logger.exception("Database error")

        await message.answer(
            "⚠️ Data save করতে সমস্যা হয়েছে। "
            "কিছুক্ষণ পরে আবার চেষ্টা করুন।"
        )


# =========================
# LEADERBOARD
# =========================

async def get_leaderboard(chat_id: int, study_date: str):

    result = (
        supabase
        .table("study_records")
        .select("name, username, hours")
        .eq("chat_id", chat_id)
        .eq("study_date", study_date)
        .order("hours", desc=True)
        .execute()
    )

    return result.data or []


def make_leaderboard(records, date_string):

    if not records:

        return (
            f"🏆 <b>Study Leaderboard</b>\n"
            f"📅 {date_string}\n\n"
            f"আজ এখনো কেউ study time দেয়নি।"
        )

    medals = ["🥇", "🥈", "🥉"]

    lines = [
        "🏆 <b>Study Leaderboard</b>",
        f"📅 {date_string}",
        ""
    ]

    for index, row in enumerate(records):

        name = row.get("name") or "Unknown"
        hours = float(row.get("hours") or 0)

        if hours.is_integer():
            hour_text = f"{int(hours)} ঘণ্টা"
        else:
            hour_text = f"{hours:g} ঘণ্টা"

        if index < 3:
            prefix = medals[index]
        else:
            prefix = f"{index + 1}."

        lines.append(
            f"{prefix} {name} — <b>{hour_text}</b>"
        )

    lines.extend(
        [
            "",
            "📌 প্রত্যেকের সর্বশেষ দেওয়া সময় দেখানো হয়েছে।"
        ]
    )

    return "\n".join(lines)


# =========================
# /leaderboard
# =========================

@dp.message(Command("leaderboard"))
async def leaderboard_command(message: types.Message):

    study_date = today_string()

    try:

        records = await get_leaderboard(
            message.chat.id,
            study_date
        )

        text = make_leaderboard(
            records,
            study_date
        )

        await message.answer(
            text,
            parse_mode="HTML"
        )

    except Exception:

        logger.exception("Leaderboard error")

        await message.answer(
            "⚠️ Leaderboard দেখাতে সমস্যা হয়েছে।"
        )


# =========================
# MIDNIGHT LEADERBOARD
# =========================

async def post_daily_leaderboards():

    """
    Every day after midnight:
    - previous day's leaderboard is posted
    - previous data remains in Supabase
    - new day automatically starts
    """

    yesterday = (
        today_bd() - timedelta(days=1)
    ).isoformat()

    logger.info(
        "Preparing leaderboard for %s",
        yesterday
    )

    try:

        chats_result = (
            supabase
            .table("study_chats")
            .select("chat_id, chat_title")
            .execute()
        )

        chats = chats_result.data or []

        for chat in chats:

            chat_id = chat["chat_id"]

            try:

                # Check if already posted
                existing = (
                    supabase
                    .table("daily_posts")
                    .select("id")
                    .eq("chat_id", chat_id)
                    .eq("study_date", yesterday)
                    .limit(1)
                    .execute()
                )

                if existing.data:
                    continue

                records = await get_leaderboard(
                    chat_id,
                    yesterday
                )

                text = make_leaderboard(
                    records,
                    yesterday
                )

                sent = await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="HTML"
                )

                # Save post information
                supabase.table("daily_posts").insert(
                    {
                        "chat_id": chat_id,
                        "study_date": yesterday,
                        "telegram_message_id": sent.message_id
                    }
                ).execute()

                logger.info(
                    "Leaderboard posted | chat=%s date=%s",
                    chat_id,
                    yesterday
                )

            except Exception:

                logger.exception(
                    "Could not post leaderboard | chat=%s",
                    chat_id
                )

    except Exception:

        logger.exception(
            "Could not load chats"
        )


# =========================
# MIDNIGHT SCHEDULER
# =========================

async def midnight_scheduler():

    while True:

        now = datetime.now(BD_TZ)

        tomorrow = (
            now.date() + timedelta(days=1)
        )

        next_midnight = datetime.combine(
            tomorrow,
            datetime.min.time(),
            tzinfo=BD_TZ
        )

        seconds = (
            next_midnight - now
        ).total_seconds()

        logger.info(
            "Next midnight in %.0f seconds",
            seconds
        )

        # Sleep until midnight
        await asyncio.sleep(
            max(seconds, 1)
        )

        try:

            await post_daily_leaderboards()

        except Exception:

            logger.exception(
                "Midnight task failed"
            )

        # Small delay so it doesn't run twice
        await asyncio.sleep(5)


# =========================
# MAIN
# =========================

async def main():

    logger.info(
        "Study Bot starting..."
    )

    scheduler_task = asyncio.create_task(
        midnight_scheduler()
    )

    try:

        # Delete old webhook if any
        await bot.delete_webhook(
            drop_pending_updates=False
        )

        # Start Telegram polling
        await dp.start_polling(bot)

    finally:

        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

        await bot.session.close()


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        logger.info(
            "Bot stopped"
        )