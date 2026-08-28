import os
import asyncio
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

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

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

BD_TZ = ZoneInfo("Asia/Dhaka")


# =========================
# HELPERS
# =========================

def today_bd() -> date:
    return datetime.now(BD_TZ).date()


def format_hours(hours: float) -> str:
    if float(hours).is_integer():
        return str(int(hours))
    return f"{hours:.2f}".rstrip("0").rstrip(".")


async def save_group(chat_id: int, title: str):
    try:
        supabase.table("study_groups").upsert(
            {
                "chat_id": chat_id,
                "title": title or "Study Group",
            },
            on_conflict="chat_id"
        ).execute()
    except Exception as e:
        print("Group save error:", e)


# =========================
# /start
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "📚 <b>আমল নামা Study Bot</b>\n\n"
        "পড়ার সময় যোগ করতে:\n"
        "<code>/study 2</code>\n\n"
        "আবার পড়লে:\n"
        "<code>/study 3.5</code>\n\n"
        "তাহলে মোট হবে <b>5.5 ঘণ্টা</b>।\n\n"
        "🏆 Leaderboard দেখতে:\n"
        "<code>/leaderboard</code>"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )


# =========================
# /study
# =========================

async def study(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user = update.effective_user
    chat = update.effective_chat

    # Group save
    if chat and chat.type in ("group", "supergroup"):
        await save_group(
            chat.id,
            chat.title or "Study Group"
        )

    # Check argument
    if not context.args:
        await update.message.reply_text(
            "❌ কত ঘণ্টা পড়েছেন লিখুন।\n\n"
            "উদাহরণ:\n"
            "/study 2\n"
            "/study 3.5"
        )
        return

    try:
        hours = float(context.args[0])

        if hours <= 0:
            raise ValueError

        if hours > 24:
            await update.message.reply_text(
                "❌ একবারে সর্বোচ্চ ২৪ ঘণ্টা দিতে পারবেন।"
            )
            return

    except ValueError:
        await update.message.reply_text(
            "❌ সঠিক সময় দিন।\n\n"
            "উদাহরণ: /study 2 অথবা /study 3.5"
        )
        return

    study_date = today_bd()

    try:
        # প্রতিবার নতুন record হবে।
        # তাই আগের /study replace হবে না।
        supabase.table("study_logs").insert(
            {
                "chat_id": chat.id,
                "user_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "study_date": study_date.isoformat(),
                "hours": hours,
            }
        ).execute()

        # আজকের মোট হিসাব বের করা
        result = (
            supabase
            .table("study_logs")
            .select("hours")
            .eq("chat_id", chat.id)
            .eq("user_id", user.id)
            .eq("study_date", study_date.isoformat())
            .execute()
        )

        total = sum(
            float(row["hours"])
            for row in (result.data or [])
        )

        await update.message.reply_text(
            f"✅ <b>{format_hours(hours)} ঘণ্টা</b> যোগ হয়েছে।\n\n"
            f"📚 আজ আপনার মোট পড়া: "
            f"<b>{format_hours(total)} ঘণ্টা</b>",
            parse_mode="HTML"
        )

    except Exception as e:
        print("Study save error:", e)

        await update.message.reply_text(
            "⚠️ সময় Save করতে সমস্যা হয়েছে। "
            "কিছুক্ষণ পরে আবার চেষ্টা করুন।"
        )


# =========================
# /leaderboard
# =========================

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    chat = update.effective_chat

    if chat.type in ("group", "supergroup"):
        await save_group(
            chat.id,
            chat.title or "Study Group"
        )

    study_date = today_bd()

    try:
        result = (
            supabase
            .table("study_logs")
            .select(
                "user_id, username, first_name, hours"
            )
            .eq("chat_id", chat.id)
            .eq("study_date", study_date.isoformat())
            .execute()
        )

        rows = result.data or []

        if not rows:
            await update.message.reply_text(
                "🏆 আজ এখনো কেউ পড়ার সময় জমা দেয়নি।"
            )
            return

        totals = {}

        for row in rows:

            user_id = row["user_id"]

            if user_id not in totals:
                totals[user_id] = {
                    "name": row.get("first_name") or "Unknown",
                    "username": row.get("username"),
                    "hours": 0,
                }

            totals[user_id]["hours"] += float(
                row["hours"]
            )

        ranking = sorted(
            totals.values(),
            key=lambda x: x["hours"],
            reverse=True
        )

        medals = ["🥇", "🥈", "🥉"]

        text = (
            f"🏆 <b>আজকের Study Leaderboard</b>\n"
            f"📅 {study_date.strftime('%d-%m-%Y')}\n\n"
        )

        for i, person in enumerate(ranking, start=1):

            medal = medals[i - 1] if i <= 3 else f"{i}."

            name = person["name"]

            if person["username"]:
                name += f" (@{person['username']})"

            text += (
                f"{medal} <b>{name}</b> — "
                f"{format_hours(person['hours'])} ঘণ্টা\n"
            )

        await update.message.reply_text(
            text,
            parse_mode="HTML"
        )

    except Exception as e:
        print("Leaderboard error:", e)

        await update.message.reply_text(
            "⚠️ Leaderboard দেখাতে সমস্যা হয়েছে।"
        )


# =========================
# MIDNIGHT LEADERBOARD
# =========================

async def midnight_loop(application: Application):

    print("Midnight scheduler started.")

    last_report_date = None

    while True:

        try:
            now = datetime.now(BD_TZ)

            # রাত ১২টার পরপরই আগের দিনের রিপোর্ট
            if now.hour == 0 and now.minute == 0:

                yesterday = now.date() - timedelta(days=1)

                # একই দিন বারবার পাঠাবে না
                if last_report_date != yesterday:

                    print(
                        "Sending leaderboard for:",
                        yesterday
                    )

                    groups = (
                        supabase
                        .table("study_groups")
                        .select("chat_id, title")
                        .execute()
                    )

                    for group in (groups.data or []):

                        chat_id = group["chat_id"]

                        try:
                            result = (
                                supabase
                                .table("study_logs")
                                .select(
                                    "user_id, username, "
                                    "first_name, hours"
                                )
                                .eq("chat_id", chat_id)
                                .eq(
                                    "study_date",
                                    yesterday.isoformat()
                                )
                                .execute()
                            )

                            rows = result.data or []

                            if not rows:
                                continue

                            totals = {}

                            for row in rows:

                                uid = row["user_id"]

                                if uid not in totals:
                                    totals[uid] = {
                                        "name": (
                                            row.get("first_name")
                                            or "Unknown"
                                        ),
                                        "username": (
                                            row.get("username")
                                        ),
                                        "hours": 0,
                                    }

                                totals[uid]["hours"] += float(
                                    row["hours"]
                                )

                            ranking = sorted(
                                totals.values(),
                                key=lambda x: x["hours"],
                                reverse=True
                            )

                            medals = ["🥇", "🥈", "🥉"]

                            text = (
                                "🌙 <b>গতকালের Study Leaderboard</b>\n"
                                f"📅 {yesterday.strftime('%d-%m-%Y')}\n\n"
                            )

                            for i, person in enumerate(
                                ranking,
                                start=1
                            ):

                                medal = (
                                    medals[i - 1]
                                    if i <= 3
                                    else f"{i}."
                                )

                                name = person["name"]

                                if person["username"]:
                                    name += (
                                        f" (@{person['username']})"
                                    )

                                text += (
                                    f"{medal} <b>{name}</b> — "
                                    f"{format_hours(person['hours'])} ঘণ্টা\n"
                                )

                            await application.bot.send_message(
                                chat_id=chat_id,
                                text=text,
                                parse_mode="HTML"
                            )

                        except Exception as e:
                            print(
                                f"Report error for {chat_id}:",
                                e
                            )

                    last_report_date = yesterday

            await asyncio.sleep(20)

        except Exception as e:
            print("Midnight loop error:", e)
            await asyncio.sleep(30)


# =========================
# MAIN
# =========================

async def post_init(application: Application):

    asyncio.create_task(
        midnight_loop(application)
    )


def main():

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("study", study)
    )

    application.add_handler(
        CommandHandler("leaderboard", leaderboard)
    )

    print("Study Bot is running 24/7...")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
