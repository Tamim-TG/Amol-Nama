import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from supabase import create_client, Client


# =========================
# SETTINGS
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


# Bangladesh Time (UTC+6)
BD_TZ = timezone(timedelta(hours=6))


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


# =========================
# DATE FUNCTIONS
# =========================

def bd_now():
    return datetime.now(BD_TZ)


def today():
    return bd_now().date()


def today_string():
    return today().isoformat()


# =========================
# /start
# =========================

@dp.message(Command("start"))
async def start_command(message: types.Message):

    await message.answer(
        "📚 Study Tracker Bot\n\n"
        "আজ কত ঘণ্টা পড়েছেন লিখুন:\n\n"
        "/study 2\n"
        "/study 3.5\n"
        "/study 5\n\n"
        "⚠️ একই দিনে আবার /study দিলে "
        "আগের সময় replace হবে।\n\n"
        "উদাহরণ:\n"
        "/study 4"
    )


# =========================
# /study
# =========================

@dp.message(Command("study"))
async def study_command(message: types.Message):

    parts = message.text.split()

    if len(parts) != 2:

        await message.answer(
            "❌ সঠিক নিয়ম:\n\n"
            "/study 2\n"
            "/study 3.5\n"
            "/study 5"
        )
        return

    try:
        hours = float(parts[1])

    except ValueError:

        await message.answer(
            "❌ সঠিক ঘণ্টা লিখুন।\n\n"
            "উদাহরণ: /study 3.5"
        )
        return

    if hours <= 0 or hours > 24:

        await message.answer(
            "❌ সময় 0-এর বেশি এবং সর্বোচ্চ 24 ঘণ্টা হতে হবে।"
        )
        return

    user = message.from_user
    chat = message.chat

    name = user.full_name or "Unknown"
    username = user.username or ""

    study_date = today_string()

    try:

        # Save group
        supabase.table("study_chats").upsert(
            {
                "chat_id": chat.id,
                "chat_title": chat.title or "Private"
            },
            on_conflict="chat_id"
        ).execute()


        # Save / replace today's study time
        supabase.table("study_records").upsert(
            {
                "chat_id": chat.id,
                "telegram_user_id": user.id,
                "name": name,
                "username": username,
                "study_date": study_date,
                "hours": hours
            },
            on_conflict="chat_id,telegram_user_id,study_date"
        ).execute()


        if hours.is_integer():
            hour_text = str(int(hours))
        else:
            hour_text = str(hours)


        await message.answer(
            f"✅ <b>সময় Save হয়েছে!</b>\n\n"
            f"👤 {name}\n"
            f"📚 সর্বশেষ সময়: <b>{hour_text} ঘণ্টা</b>\n\n"
            f"আগের সময় replace হয়েছে।",
            parse_mode="HTML"
        )

        logger.info(
            "Saved: chat=%s user=%s hours=%s date=%s",
            chat.id,
            user.id,
            hours,
            study_date
        )

    except Exception as e:

        logger.exception("Study save error")

        await message.answer(
            "⚠️ সময় Save করতে সমস্যা হয়েছে।"
        )


# =========================
# GET LEADERBOARD
# =========================

def get_leaderboard(chat_id, study_date):

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


# =========================
# LEADERBOARD TEXT
# =========================

def leaderboard_text(records, date_text):

    if not records:

        return (
            "🏆 <b>Study Leaderboard</b>\n"
            f"📅 {date_text}\n\n"
            "আজ কেউ Study Time দেয়নি।"
        )


    medals = ["🥇", "🥈", "🥉"]

    lines = [
        "🏆 <b>Study Leaderboard</b>",
        f"📅 {date_text}",
        ""
    ]


    for i, row in enumerate(records):

        name = row.get("name") or "Unknown"
        hours = float(row.get("hours") or 0)

        if hours.is_integer():
            hour_text = f"{int(hours)} ঘণ্টা"
        else:
            hour_text = f"{hours:g} ঘণ্টা"


        if i < 3:
            position = medals[i]
        else:
            position = f"{i + 1}."


        lines.append(
            f"{position} {name} — <b>{hour_text}</b>"
        )


    lines.append("")
    lines.append(
        "📌 প্রত্যেক সদস্যের সর্বশেষ দেওয়া সময় দেখানো হয়েছে।"
    )

    return "\n".join(lines)


# =========================
# /leaderboard
# =========================

@dp.message(Command("leaderboard"))
async def leaderboard_command(message: types.Message):

    date_text = today_string()

    try:

        records = get_leaderboard(
            message.chat.id,
            date_text
        )

        text = leaderboard_text(
            records,
            date_text
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

async def post_midnight_leaderboard():

    # রাত ১২টার পর আগের দিনের হিসাব
    previous_date = (
        today() - timedelta(days=1)
    ).isoformat()


    logger.info(
        "Posting leaderboard for %s",
        previous_date
    )


    try:

        result = (
            supabase
            .table("study_chats")
            .select("chat_id")
            .execute()
        )

        chats = result.data or []


        for chat in chats:

            chat_id = chat["chat_id"]

            try:

                # Already posted?
                already = (
                    supabase
                    .table("daily_posts")
                    .select("id")
                    .eq("chat_id", chat_id)
                    .eq("study_date", previous_date)
                    .limit(1)
                    .execute()
                )


                if already.data:
                    continue


                records = get_leaderboard(
                    chat_id,
                    previous_date
                )


                text = leaderboard_text(
                    records,
                    previous_date
                )


                sent = await bot.send_message(
                    chat_id,
                    text,
                    parse_mode="HTML"
                )


                # Mark as posted
                supabase.table("daily_posts").insert(
                    {
                        "chat_id": chat_id,
                        "study_date": previous_date,
                        "telegram_message_id": sent.message_id
                    }
                ).execute()


                logger.info(
                    "Leaderboard posted: %s",
                    chat_id
                )


            except Exception:

                logger.exception(
                    "Could not post to chat %s",
                    chat_id
                )


    except Exception:

        logger.exception(
            "Could not load study chats"
        )


# =========================
# MIDNIGHT TIMER
# =========================

async def midnight_scheduler():

    while True:

        now = bd_now()

        tomorrow = now.date() + timedelta(days=1)


        next_midnight = datetime.combine(
            tomorrow,
            datetime.min.time(),
            tzinfo=BD_TZ
        )


        seconds = (
            next_midnight - now
        ).total_seconds()


        logger.info(
            "Next reset/leaderboard in %.0f seconds",
            seconds
        )


        await asyncio.sleep(
            max(seconds, 1)
        )


        try:

            await post_midnight_leaderboard()

        except Exception:

            logger.exception(
                "Midnight task error"
            )


        # Prevent double execution
        await asyncio.sleep(5)


# =========================
# MAIN
# =========================

async def main():

    logger.info("🚀 Study Bot starting...")


    scheduler = asyncio.create_task(
        midnight_scheduler()
    )


    try:

        # Remove previous webhook
        await bot.delete_webhook(
            drop_pending_updates=False
        )


        # Start bot
        await dp.start_polling(bot)


    finally:

        scheduler.cancel()

        try:
            await scheduler
        except asyncio.CancelledError:
            pass

        await bot.session.close()


# =========================
# RUN
# =========================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        logger.info("Bot stopped")
