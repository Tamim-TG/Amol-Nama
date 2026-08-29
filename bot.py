import os
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiohttp import web
from supabase import create_client, Client

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)


# ==================================================
# CONFIG
# ==================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

GROUP_ID = -1003925259261
CHANNEL_USERNAME = "@FixerZoneOfficial"

PORT = int(os.getenv("PORT", "8080"))

BD_TZ = ZoneInfo("Asia/Dhaka")


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


# ==================================================
# DATE / TIME
# ==================================================

def bd_now():
    return datetime.now(BD_TZ)


def today():
    return bd_now().date().isoformat()


def yesterday():
    return (
        bd_now().date() - timedelta(days=1)
    ).isoformat()


# ==================================================
# MEMBERSHIP CHECK
# ==================================================

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not user:
        return False

    # --------------------------
    # GROUP CHECK
    # --------------------------

    try:

        group_member = await context.bot.get_chat_member(
            GROUP_ID,
            user.id
        )

        group_status = group_member.status

        if group_status in ("left", "kicked"):

            keyboard = [
                [
                    InlineKeyboardButton(
                        "👥 Join Group",
                        url="https://t.me/+ft6UwgnBRfhjZWFl"
                    )
                ]
            ]

            await update.message.reply_text(
                "❌ আগে Group-এ Join করুন।\n\n"
                "Join করার পর আবার command দিন।",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            return False

    except Exception as e:

        print("Group membership error:", e)

        await update.message.reply_text(
            "⚠️ Group membership check করা যাচ্ছে না।"
        )

        return False


    # --------------------------
    # CHANNEL CHECK
    # --------------------------

    try:

        channel_member = await context.bot.get_chat_member(
            CHANNEL_USERNAME,
            user.id
        )

        channel_status = channel_member.status

        if channel_status in ("left", "kicked"):

            keyboard = [
                [
                    InlineKeyboardButton(
                        "📢 Join Channel",
                        url="https://t.me/FixerZoneOfficial"
                    )
                ]
            ]

            await update.message.reply_text(
                "❌ আগে Channel-এ Join করুন।\n\n"
                "Join করার পর আবার command দিন।",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            return False

    except Exception as e:

        print("Channel membership error:", e)

        await update.message.reply_text(
            "⚠️ Channel membership check করা যাচ্ছে না।"
        )

        return False


    return True


# ==================================================
# /START
# ==================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return


    chat = update.effective_chat


    # ==================================================
    # GROUP
    # ==================================================

    if chat.type in ("group", "supergroup"):

        await update.message.reply_text(
            "📚 <b>আমল নামা Study Bot</b>\n\n"
            "📖 /study 2\n"
            "🏆 /leaderboard",
            parse_mode="HTML"
        )

        return


    # ==================================================
    # PRIVATE
    # ==================================================

    # নিচের ৩টি বাটন সবসময় থাকবে
    reply_keyboard = [
        [
            KeyboardButton("📚 Study"),
            KeyboardButton("🏆 Leaderboard")
        ],
        [
            KeyboardButton("👨‍💻 Developer")
        ]
    ]

    reply_markup = ReplyKeyboardMarkup(
        reply_keyboard,
        resize_keyboard=True,
        is_persistent=True
    )


    # ==================================================
    # JOIN BUTTONS
    # ==================================================

    join_keyboard = [
        [
            InlineKeyboardButton(
                "🤧 গ্রুপে জয়েন",
                url="https://t.me/+ft6UwgnBRfhjZWFl"
            )
        ],
        [
            InlineKeyboardButton(
                "📢 চ্যানেলে জয়েন",
                url="https://t.me/FixerZoneOfficial"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ জয়েন করেছি",
                callback_data="check_membership"
            )
        ]
    ]


    join_markup = InlineKeyboardMarkup(
        join_keyboard
    )


    text = (
        "🔒 <b>বট ব্যবহার করতে হলে প্রথমে নিচের সবগুলোতে জয়েন করুন।</b>\n\n"
        "জয়েন করার পর নিচের ✅ "
        "\"জয়েন করেছি\" বাটনে ক্লিক করুন।"
    )


    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=join_markup
    )


    # নিচের Reply Keyboard আলাদা message হিসেবে পাঠানো হচ্ছে
    await update.message.reply_text(
        "👇 নিচের মেনু থেকে অপশন নির্বাচন করুন।",
        reply_markup=reply_markup
    )

# ==================================================
# /STUDY
# ==================================================

async def study(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if not update.effective_user:
        return

    # Membership check
    allowed = await check_membership(
        update,
        context
    )

    if not allowed:
        return

    # ==================================================
# STUDY BUTTON
# ==================================================

async def study_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    await update.message.reply_text(
        "📚 <b>Study Time</b>\n\n"
        "আজ কত ঘণ্টা Study করেছেন?\n\n"
        "উদাহরণ:\n"
        "<code>2</code>\n"
        "<code>2.5</code>\n"
        "<code>3</code>",
        parse_mode="HTML"
    )

    context.user_data["waiting_for_study"] = True


    # --------------------------
    # ARGUMENT CHECK
    # --------------------------

    if not context.args:

        await update.message.reply_text(
            "❌ কত ঘণ্টা পড়েছেন লিখুন।\n\n"
            "হিসাব করে সঠিক লিখুন"
        )

        return


    try:

        hours = float(context.args[0])

    except ValueError:

        await update.message.reply_text(
            "❌ সঠিক সংখ্যা দিন।\n\n"
            "উদাহরণ: /study 3.5"
        )

        return


    if hours <= 0 or hours > 24:

        await update.message.reply_text(
            "❌ সময় 0-এর বেশি এবং সর্বোচ্চ 24 ঘণ্টা হতে হবে।"
        )

        return


    user = update.effective_user
    chat = update.effective_chat

    study_date = today()


    # --------------------------
    # SAVE / REPLACE
    # --------------------------

    data = {
        "chat_id": chat.id,
        "user_id": user.id,
        "username": user.username or "",
        "full_name": user.full_name,
        "study_date": study_date,
        "hours": hours,
        "updated_at": bd_now().isoformat()
    }


    try:

        supabase.table(
    "study_hours"
).upsert(
    data,
    on_conflict="chat_id,user_id,study_date"
).execute()


        await update.message.reply_text(
            "✅ <b>Study Time Save হয়েছে!</b>\n\n"
            f"👤 {user.full_name}\n"
            f"📚 আজকের সময়: <b>{hours:g} ঘণ্টা</b>\n\n",
            parse_mode="HTML"
        )


    except Exception as e:

        print("Study save error:", e)

        await update.message.reply_text(
            "⚠️ Study time save করতে সমস্যা হয়েছে।"
        )


# ==================================================
# LEADERBOARD DATA
# ==================================================

def get_leaderboard(chat_id, study_date):

    result = (
        supabase
        .table("study_hours")
        .select(
            "user_id, username, full_name, hours"
        )
        .eq("study_date", study_date)
        .order("hours", desc=True)
        .execute()
    )

    return result.data or []


# ==================================================
# /LEADERBOARD
# ==================================================

async def leaderboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    allowed = await check_membership(
        update,
        context
    )

    if not allowed:
        return


    chat_id = update.effective_chat.id
    study_date = today()


    try:

        rows = get_leaderboard(
            chat_id,
            study_date
        )


        if not rows:

            await update.message.reply_text(
                "🏆 <b>আজকের Leaderboard</b>\n\n"
                "এখনো কেউ Study Time দেয়নি।",
                parse_mode="HTML"
            )

            return


        medals = ["🥇", "🥈", "🥉"]

        text = (
            "🏆 <b>আজকের Study Leaderboard</b>\n"
            "━━━━━━━━━━━━━━\n\n"
        )


        for index, row in enumerate(rows):

            name = (
                row.get("full_name")
                or row.get("username")
                or "Unknown"
            )

            hours = float(
                row.get("hours", 0)
            )


            if index < 3:
                position = medals[index]
            else:
                position = f"{index + 1}."


            text += (
                f"{position} "
                f"<b>{name}</b> — "
                f"{hours:g} ঘণ্টা\n"
            )


        text += (
            "\n━━━━━━━━━━━━━━\n"
            f"📅 {study_date}\n"
            "🌙 রাত ১২টায় নতুন দিনের হিসাব শুরু হবে।"
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


# ==================================================
# MIDNIGHT LEADERBOARD
# ==================================================

async def send_yesterday_leaderboards(
    application: Application
):

    report_date = yesterday()


    try:

        groups = (
            supabase
            .table("study_hours")
            .select("chat_id")
            .execute()
        )


        chat_ids = set(
            row["chat_id"]
            for row in (groups.data or [])
        )


        for chat_id in chat_ids:

            try:

                rows = get_leaderboard(
                    chat_id,
                    report_date
                )


                if not rows:
                    continue


                medals = ["🥇", "🥈", "🥉"]

                text = (
                    "🌙 <b>গতকালের Study Leaderboard</b>\n"
                    "━━━━━━━━━━━━━━\n\n"
                    f"📅 {report_date}\n\n"
                )


                for index, row in enumerate(rows):

                    name = (
                        row.get("full_name")
                        or row.get("username")
                        or "Unknown"
                    )

                    hours = float(
                        row.get("hours", 0)
                    )


                    if index < 3:
                        position = medals[index]
                    else:
                        position = f"{index + 1}."


                    text += (
                        f"{position} "
                        f"<b>{name}</b> — "
                        f"{hours:g} ঘণ্টা\n"
                    )


                text += (
                    "\n━━━━━━━━━━━━━━\n"
                    "📚 নতুন দিনের Study Time শুরু হয়েছে।"
                )


                await application.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="HTML"
                )


            except Exception as e:

                print(
                    f"Could not send leaderboard "
                    f"to {chat_id}:",
                    e
                )


    except Exception as e:

        print(
            "Midnight leaderboard error:",
            e
        )


# ==================================================
# MIDNIGHT LOOP
# ==================================================

async def midnight_loop(
    application: Application
):

    print("🌙 Midnight scheduler started.")

    last_processed = None


    while True:

        try:

            now = bd_now()

            current_date = now.date()

            # রাত ১২টা
            if now.hour == 0 and now.minute == 0:

                if last_processed != current_date:

                    await send_yesterday_leaderboards(
                        application
                    )

                    last_processed = current_date


            await asyncio.sleep(20)


        except Exception as e:

            print(
                "Midnight loop error:",
                e
            )

            await asyncio.sleep(30)


# ==================================================
# HEALTH SERVER
# ==================================================

async def health(request):

    return web.Response(
        text="Amol Nama Study Bot is running ✅"
    )


async def start_health_server():

    app = web.Application()

    app.router.add_get(
        "/",
        health
    )

    app.router.add_get(
        "/health",
        health
    )


    runner = web.AppRunner(app)

    await runner.setup()


    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()


    print(
        f"Health server running on port {PORT}"
    )


# ==================================================
# MAIN
# ==================================================

async def main():

    await start_health_server()


    keyboard = [
        [
            KeyboardButton("📚 Study"),
            KeyboardButton("🏆 Leaderboard")
        ],
        [
            KeyboardButton("👨‍💻 Developer")
        ]
    ]


    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True
    )


    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )


    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    application.add_handler(
        CommandHandler(
            "study",
            study
        )
    )


    application.add_handler(
        CommandHandler(
            "leaderboard",
            leaderboard
        )
    )

    application.add_handler(
    MessageHandler(
        filters.Regex("^📚 Study$"),
        study_button
    )
)

    await application.initialize()

    await application.start()

    await application.updater.start_polling(
        allowed_updates=Update.ALL_TYPES
    )


    print(
        "🚀 Amol Nama Study Bot is running 24/7!"
    )


    scheduler = asyncio.create_task(
        midnight_loop(application)
    )


    try:

        while True:
            await asyncio.sleep(3600)

    finally:

        scheduler.cancel()

        await application.updater.stop()
        await application.stop()
        await application.shutdown()

# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print("Bot stopped.")
