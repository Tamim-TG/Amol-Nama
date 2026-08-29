import os
import asyncio
from html import escape
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiohttp import web
from supabase import create_client, Client

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# ==================================================
# CONFIG
# ==================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

GROUP_ID = int(os.getenv("GROUP_ID", "0"))
DEV_CHAT_ID = int(os.getenv("DEV_CHAT_ID", "0"))

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# Active Developer conversations (in-memory)
ACTIVE_DEV_USERS = set()


# ==================================================
# TELEGRAM GROUP / CHANNEL
# ==================================================

CHANNEL_USERNAME = os.environ.get(
    "CHANNEL_USERNAME",
    "@FixerZoneOfficial"
)

# ==================================================
# TIMEZONE
# ==================================================

BD_TZ = ZoneInfo("Asia/Dhaka")


def bd_now():
    return datetime.now(BD_TZ)


def today():
    return bd_now().date().isoformat()


def yesterday():
    return (
        bd_now().date() - timedelta(days=1)
    ).isoformat()


# ==================================================
# HEALTH SERVER
# ==================================================

async def health(request):
    return web.Response(
        text="OK"
    )


async def start_health_server():

    app = web.Application()

    app.router.add_get(
        "/",
        health
    )

    port = int(
        os.environ.get(
            "PORT",
            "8080"
        )
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    print(
        f"Health server running on port {port}"
    )

    return runner


# ==================================================
# MEMBERSHIP CHECK
# ==================================================

async def check_membership(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return False

    user_id = update.effective_user.id

    try:

        # ------------------------------------------
        # GROUP CHECK
        # ------------------------------------------

        if GROUP_ID:

            group_member = await context.bot.get_chat_member(
                chat_id=GROUP_ID,
                user_id=user_id
            )

            group_status = group_member.status
            group_is_member = getattr(
                group_member, "is_member", True
            )

            if group_status in (
                "left",
                "kicked"
            ) or (
                group_status == "restricted"
                and not group_is_member
            ):

                await send_join_menu(
                    update
                )

                return False

        # ------------------------------------------
        # CHANNEL CHECK
        # ------------------------------------------

        channel_member = await context.bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id
        )

        channel_status = channel_member.status
        channel_is_member = getattr(
            channel_member, "is_member", True
        )

        if channel_status in (
            "left",
            "kicked"
        ) or (
            channel_status == "restricted"
            and not channel_is_member
        ):

            await send_join_menu(
                update
            )

            return False

        return True

    except Exception as e:

        print(
            "Membership check error:",
            e
        )

        # নিরাপত্তার জন্য join menu দেখাবে
        await send_join_menu(
            update
        )

        return False


# ==================================================
# JOIN MENU
# ==================================================

async def send_join_menu(
    update: Update
):

    if not update.message:
        return

    keyboard = [
        [
            "👥 Join Group"
        ],
        [
            "📢 Join Channel"
        ],
        [
            "✅ জয়েন করেছি"
        ]
    ]

    text = (
        "🔒 <b>বট ব্যবহার করতে হলে প্রথমে নিচের "
        "Group ও Channel-এ Join করুন।</b>\n\n"
        "Join করার পর নিচের ✅ "
        "<b>\"জয়েন করেছি\"</b> বাটনে ক্লিক করুন।"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )


# ==================================================
# MAIN PRIVATE MENU
# ==================================================

def get_main_keyboard():

    keyboard = [
        [
            "📚 Study",
            "🏆 Leaderboard"
        ],
        [
            "👨‍💻 Developer"
        ]
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True
    )


async def send_main_menu(
    update: Update
):

    if not update.message:
        return

    await update.message.reply_text(
        "নিচের একটি মেনু নির্বাচন করুন 👇",
        reply_markup=get_main_keyboard()
    )


# ==================================================
# /START
# ==================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    chat_type = update.effective_chat.type

    # ==================================================
    # GROUP
    # ==================================================

    # Group-এ কোনো button যাবে না
    if chat_type in (
        "group",
        "supergroup"
    ):

        # group-এ /start দিলে শুধু text
        await update.message.reply_text(
            "📚 Study Bot চালু আছে।\n\n"
            "📖 /study 2\n"
            "🏆 /leaderboard"
        )

        return

    # ==================================================
    # PRIVATE
    # ==================================================

    allowed = await check_membership(
        update,
        context
    )

    if not allowed:
        return

    await update.message.reply_text(
        "নিচের একটি মেনু নির্বাচন করুন 👇",
        reply_markup=get_main_keyboard()
    )


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

    allowed = await check_membership(
        update,
        context
    )

    if not allowed:
        return

    context.user_data[
        "waiting_for_study"
    ] = True

    await update.message.reply_text(
        "📚 <b>Study Time</b>\n\n"
        "আজ কত ঘণ্টা Study করেছেন?\n\n"
        "উদাহরণ:\n"
        "<code>2</code>\n"
        "<code>2.5</code>\n"
        "<code>3</code>",
        parse_mode="HTML"
    )

# ==================================================
# DEVELOPER BUTTON
# ==================================================

async def developer_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "💬 Contact Dev",
                callback_data="contact_dev"
            )
        ]
    ]

    await update.message.reply_text(
        "👨‍💻 <b>Developer</b>\n\n"
        "কোনো সমস্যা বা প্রয়োজন হলে "
        "Developer-এর সাথে যোগাযোগ করুন।",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================================================
# CONTACT DEVELOPER
# ==================================================

async def contact_dev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    user = query.from_user
    if not DEV_CHAT_ID:
        await query.message.reply_text("⚠️ Developer ID সেট করা হয়নি।")
        return

    ACTIVE_DEV_USERS.add(user.id)
    text = (
        "📩 <b>New Developer Contact</b>\n\n"
        f"👤 <b>Name:</b> {escape(user.full_name)}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
    )
    if user.username:
        text += f"🔗 <b>Username:</b> @{escape(user.username)}\n"
    text += "\n🟢 <b>Conversation Active</b>\nUser-এর পরের text message automatically এখানে আসবে।"
    keyboard = [[
        InlineKeyboardButton("💬 Reply", callback_data=f"reply_user:{user.id}"),
        InlineKeyboardButton("⛔ Stop", callback_data=f"stop_dev_chat:{user.id}")
    ]]
    await context.bot.send_message(chat_id=DEV_CHAT_ID, text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    await query.message.reply_text(
        "✅ <b>Developer conversation শুরু হয়েছে।</b>\n\n"
        "এখন আপনি সরাসরি message লিখুন।\n"
        "আপনার message automatically Developer-এর কাছে যাবে।\n\n"
        "Conversation বন্ধ করতে নিচের <b>Stop Conversation</b> চাপুন।",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⛔ Stop Conversation", callback_data="stop_my_dev_chat")]])
    )


# ==================================================
# REPLY TO USER
# ==================================================

async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    if DEV_CHAT_ID and (not query.message or query.message.chat_id != DEV_CHAT_ID):
        return
    try:
        user_id = int(query.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await query.message.reply_text("⚠️ User ID পাওয়া যায়নি।")
        return
    if user_id not in ACTIVE_DEV_USERS:
        await query.message.reply_text("⚠️ এই conversation এখন active নেই।")
        return
    context.user_data["reply_to_user"] = user_id
    await query.message.reply_text("✍️ <b>আপনার Reply লিখুন:</b>\n\nআপনি যে text পাঠাবেন, সেটাই User-এর কাছে যাবে।", parse_mode="HTML")


# ==================================================
# STOP DEVELOPER CONVERSATION
# ==================================================

async def stop_dev_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    if DEV_CHAT_ID and (not query.message or query.message.chat_id != DEV_CHAT_ID):
        return
    try:
        user_id = int(query.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await query.message.reply_text("⚠️ User ID পাওয়া যায়নি।")
        return
    ACTIVE_DEV_USERS.discard(user_id)
    if context.user_data.get("reply_to_user") == user_id:
        context.user_data["reply_to_user"] = None
    await query.message.reply_text(f"⛔ <b>Conversation বন্ধ করা হয়েছে।</b>\n\nUser ID: <code>{user_id}</code>", parse_mode="HTML")
    try:
        await context.bot.send_message(chat_id=user_id, text="⛔ <b>Developer conversation বন্ধ করা হয়েছে।</b>\n\nআবার কথা বলতে চাইলে <b>👨‍💻 Developer</b> → <b>💬 Contact Dev</b> চাপুন।", parse_mode="HTML")
    except Exception as e:
        print("Stop conversation user notification error:", e)


async def stop_my_dev_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    user = query.from_user
    ACTIVE_DEV_USERS.discard(user.id)
    await query.message.reply_text("⛔ <b>Developer conversation বন্ধ হয়েছে।</b>\n\nআবার যোগাযোগ করতে চাইলে Developer button থেকে Contact Dev চাপুন।", parse_mode="HTML")
    if DEV_CHAT_ID:
        try:
            await context.bot.send_message(chat_id=DEV_CHAT_ID, text=(
                "⛔ <b>User conversation বন্ধ করেছে</b>\n\n"
                f"👤 <b>Name:</b> {escape(user.full_name)}\n"
                f"🆔 <b>User ID:</b> <code>{user.id}</code>"
            ), parse_mode="HTML")
        except Exception as e:
            print("User stop notification error:", e)


# ==================================================
# SEND DEVELOPER REPLY
# ==================================================

async def send_dev_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_chat.type != "private":
        return
    if DEV_CHAT_ID and update.effective_chat.id != DEV_CHAT_ID:
        return
    target_user_id = context.user_data.get("reply_to_user")
    if not target_user_id:
        return
    if target_user_id not in ACTIVE_DEV_USERS:
        context.user_data["reply_to_user"] = None
        await update.message.reply_text("⚠️ এই User-এর conversation আর active নেই।")
        return
    message_text = update.message.text
    if not message_text:
        return
    try:
        await context.bot.send_message(chat_id=target_user_id, text=f"👨‍💻 <b>Developer</b>\n\n{escape(message_text)}", parse_mode="HTML")
        await update.message.reply_text("✅ Reply User-এর কাছে পাঠানো হয়েছে।")
    except Exception as e:
        print("Developer reply error:", e)
        await update.message.reply_text("⚠️ User-এর কাছে Reply পাঠানো যায়নি।")


# ==================================================
# FORWARD ACTIVE USER MESSAGE TO DEVELOPER
# ==================================================

async def forward_user_message_to_dev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_chat.type != "private":
        return False
    user = update.effective_user
    if not user or user.id not in ACTIVE_DEV_USERS or not DEV_CHAT_ID:
        return False
    message_text = update.message.text
    if not message_text:
        return False
    text = (
        "📨 <b>Message from User</b>\n\n"
        f"👤 <b>Name:</b> {escape(user.full_name)}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
    )
    if user.username:
        text += f"🔗 <b>Username:</b> @{escape(user.username)}\n"
    text += f"\n💬 <b>Message:</b>\n{escape(message_text)}"
    keyboard = [[
        InlineKeyboardButton("💬 Reply", callback_data=f"reply_user:{user.id}"),
        InlineKeyboardButton("⛔ Stop", callback_data=f"stop_dev_chat:{user.id}")
    ]]
    try:
        await context.bot.send_message(chat_id=DEV_CHAT_ID, text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return True
    except Exception as e:
        print("Forward user message error:", e)
        return False

# ==================================================
# SAVE STUDY TIME
# ==================================================

async def save_study_time(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    if not context.user_data.get(
        "waiting_for_study"
    ):
        return

    allowed = await check_membership(
        update,
        context
    )

    if not allowed:
        return

    value = update.message.text.strip()

    try:

        hours = float(value)

        if hours <= 0:
            raise ValueError

        if hours > 24:
            await update.message.reply_text(
                "❌ ২৪ ঘণ্টার বেশি দেওয়া যাবে না।"
            )
            return

    except ValueError:

        await update.message.reply_text(
            "❌ সঠিক সংখ্যা দিন।\n\n"
            "উদাহরণ: 2 অথবা 2.5"
        )

        return

    user = update.effective_user

    # Private chat-এ save করার সময়
    # GROUP_ID ব্যবহার করা হচ্ছে।
    #
    # এতে private button থেকে দেওয়া Study Time
    # নির্দিষ্ট group-এর leaderboard-এ যাবে।

    if not GROUP_ID:

        await update.message.reply_text(
            "⚠️ GROUP_ID সেট করা হয়নি।"
        )

        return

    data = {
        "chat_id": GROUP_ID,
        "user_id": user.id,
        "username": user.username or "",
        "full_name": user.full_name,
        "study_date": today(),
        "hours": hours,
        "updated_at": bd_now().isoformat()
    }

    try:

        supabase.table(
            "study_hours"
        ).upsert(
            data,
            on_conflict=(
                "chat_id,user_id,study_date"
            )
        ).execute()

        context.user_data[
            "waiting_for_study"
        ] = False

        await update.message.reply_text(
            "✅ <b>Study Time Save হয়েছে!</b>\n\n"
            f"👤 {user.full_name}\n"
            f"📚 আজকের সময়: "
            f"<b>{hours:g} ঘণ্টা</b>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )

    except Exception as e:

        print(
            "Study save error:",
            e
        )

        await update.message.reply_text(
            "⚠️ Study time save করতে "
            "সমস্যা হয়েছে।"
        )


# ==================================================
# GROUP /study COMMAND
# ==================================================

async def study(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    # শুধু group-এ command
    if update.effective_chat.type not in (
        "group",
        "supergroup"
    ):

        await update.message.reply_text(
            "📚 Private chat-এ নিচের "
            "Study button ব্যবহার করুন।"
        )

        return

    allowed = await check_membership(
        update,
        context
    )

    if not allowed:
        return

    # argument নেই
    if not context.args:

        await update.message.reply_text(
            "❌ কত ঘণ্টা পড়েছেন লিখুন।\n\n"
            "উদাহরণ:\n"
            "/study 2\n"
            "/study 2.5"
        )

        return

    try:

        hours = float(
            context.args[0]
        )

        if hours <= 0:
            raise ValueError

        if hours > 24:

            await update.message.reply_text(
                "❌ ২৪ ঘণ্টার বেশি দেওয়া যাবে না।"
            )

            return

    except ValueError:

        await update.message.reply_text(
            "❌ সঠিক সংখ্যা দিন।\n\n"
            "উদাহরণ:\n"
            "/study 2\n"
            "/study 2.5"
        )

        return

    user = update.effective_user
    chat = update.effective_chat

    data = {
        "chat_id": chat.id,
        "user_id": user.id,
        "username": user.username or "",
        "full_name": user.full_name,
        "study_date": today(),
        "hours": hours,
        "updated_at": bd_now().isoformat()
    }

    try:

        supabase.table(
            "study_hours"
        ).upsert(
            data,
            on_conflict=(
                "chat_id,user_id,study_date"
            )
        ).execute()

        await update.message.reply_text(
            "✅ <b>Study Time Save হয়েছে!</b>\n\n"
            f"👤 {user.full_name}\n"
            f"📚 আজকের সময়: "
            f"<b>{hours:g} ঘণ্টা</b>",
            parse_mode="HTML"
        )

    except Exception as e:

        print(
            "Study command save error:",
            e
        )

        await update.message.reply_text(
            "⚠️ Study time save করতে "
            "সমস্যা হয়েছে।"
        )


# ==================================================
# GET LEADERBOARD
# ==================================================

def get_leaderboard(
    chat_id,
    study_date
):

    result = (
        supabase
        .table("study_hours")
        .select(
            "user_id, username, full_name, hours"
        )
        .eq(
            "chat_id",
            chat_id
        )
        .eq(
            "study_date",
            study_date
        )
        .order(
            "hours",
            desc=True
        )
        .execute()
    )

    return result.data or []


# ==================================================
# LEADERBOARD
# ==================================================

async def leaderboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    # Private button
    if update.effective_chat.type == "private":

        allowed = await check_membership(
            update,
            context
        )

        if not allowed:
            return

        chat_id = GROUP_ID

    # Group command
    elif update.effective_chat.type in (
        "group",
        "supergroup"
    ):

        allowed = await check_membership(
            update,
            context
        )

        if not allowed:
            return

        chat_id = update.effective_chat.id

    else:
        return

    if not chat_id:

        await update.message.reply_text(
            "⚠️ GROUP_ID সেট করা হয়নি।"
        )

        return

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
                parse_mode="HTML",
                reply_markup=(
                    get_main_keyboard()
                    if update.effective_chat.type
                    == "private"
                    else None
                )
            )

            return

        medals = [
            "🥇",
            "🥈",
            "🥉"
        ]

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
                f"<b>{escape(str(name))}</b> — "
                f"{hours:g} ঘণ্টা\n"
            )

        text += (
            "\n━━━━━━━━━━━━━━\n"
            f"📅 {study_date}\n"
            "🌙 রাত ১২টায় নতুন দিনের "
            "হিসাব শুরু হবে।"
        )

        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=(
                get_main_keyboard()
                if update.effective_chat.type
                == "private"
                else None
            )
        )

    except Exception as e:

        print(
            "Leaderboard error:",
            e
        )

        await update.message.reply_text(
            "⚠️ Leaderboard দেখাতে "
            "সমস্যা হয়েছে।"
        )


# ==================================================
# JOIN BUTTON HANDLER
# ==================================================

async def join_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    text = update.message.text

    if text == "👥 Join Group":

        await update.message.reply_text(
            "👥 নিচের Group-এ Join করুন:\n\n"
            "https://t.me/+ft6UwgnBRfhjZWFl"
        )

        return

    if text == "📢 Join Channel":

        await update.message.reply_text(
            "📢 Channel-এ Join করুন:\n\n"
            "https://t.me/FixerZoneOfficial"
        )

        return

    if text == "✅ জয়েন করেছি":

        allowed = await check_membership(
            update,
            context
        )

        if allowed:

            await update.message.reply_text(
                "✅ আপনার Join সম্পন্ন হয়েছে।\n\n"
                "নিচের একটি মেনু নির্বাচন করুন 👇",
                reply_markup=get_main_keyboard()
            )

        return


# ==================================================
# PRIVATE TEXT HANDLER
# ==================================================

async def private_text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    text = update.message.text

    if await forward_user_message_to_dev(update, context):
        return

    # ----------------------------------------------
    # Developer Reply
    # ----------------------------------------------

    if context.user_data.get(
        "reply_to_user"
    ):

        await send_dev_reply(
            update,
            context
        )

        return
    # ----------------------------------------------
    # Waiting for study number
    # ----------------------------------------------

    if context.user_data.get(
        "waiting_for_study"
    ):

        # Join button হলে study input হিসেবে নেবে না
        if text in (
            "👥 Join Group",
            "📢 Join Channel",
            "✅ জয়েন করেছি"
        ):
            await join_button(
                update,
                context
            )
            return

        await save_study_time(
            update,
            context
        )

        return

    # ----------------------------------------------
    # Study
    # ----------------------------------------------

    if text == "📚 Study":

        await study_button(
            update,
            context
        )

        return

    # ----------------------------------------------
    # Leaderboard
    # ----------------------------------------------

    if text == "🏆 Leaderboard":

        await leaderboard(
            update,
            context
        )

        return

    # ----------------------------------------------
    # Developer
    # ----------------------------------------------

    if text == "👨‍💻 Developer":

        await developer_button(
            update,
            context
        )

        return

    # ----------------------------------------------
    # Join menu buttons
    # ----------------------------------------------

    if text in (
        "👥 Join Group",
        "📢 Join Channel",
        "✅ জয়েন করেছি"
    ):

        await join_button(
            update,
            context
        )

        return


# ==================================================
# YESTERDAY LEADERBOARD
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
            for row in (
                groups.data or []
            )
            if row.get("chat_id")
        )

        for chat_id in chat_ids:

            try:

                rows = get_leaderboard(
                    chat_id,
                    report_date
                )

                if not rows:
                    continue

                medals = [
                    "🥇",
                    "🥈",
                    "🥉"
                ]

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
                        f"<b>{escape(str(name))}</b> — "
                        f"{hours:g} ঘণ্টা\n"
                    )

                text += (
                    "\n━━━━━━━━━━━━━━\n"
                    "📚 নতুন দিনের Study Time "
                    "শুরু হয়েছে।"
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

    last_date = today()

    while True:

        try:

            current_date = today()

            if current_date != last_date:

                await send_yesterday_leaderboards(
                    application
                )

                last_date = current_date

            await asyncio.sleep(10)

        except asyncio.CancelledError:

            raise

        except Exception as e:

            print(
                "Midnight loop error:",
                e
            )

            await asyncio.sleep(10)


# ==================================================
# MAIN
# ==================================================

async def main():

    await start_health_server()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # ----------------------------------------------
    # Commands
    # ----------------------------------------------

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

    # ----------------------------------------------
    # Private buttons / text
    # ----------------------------------------------

    # One handler manages all private text.
    # Active Developer conversations are checked first, so every
    # user text message is forwarded until Stop is pressed.
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            private_text_handler
        )
    )

    # ----------------------------------------------
    # Developer callbacks
    # ----------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            contact_dev,
            pattern="^contact_dev$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            reply_to_user,
            pattern="^reply_user:"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            stop_dev_conversation,
            pattern="^stop_dev_chat:"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            stop_my_dev_conversation,
            pattern="^stop_my_dev_chat$"
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

        try:
            await scheduler
        except asyncio.CancelledError:
            pass

        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await health_runner.cleanup()


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )
