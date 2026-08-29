import os
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiohttp import web
from supabase import create_client, Client

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ==================================================
# TELEGRAM GROUP / CHANNEL
# ==================================================

# তোমার GROUP ID এখানে দাও
# উদাহরণ: -1001234567890
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))

# তোমার Channel username
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

            if group_status in (
                "left",
                "kicked"
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

        if channel_status in (
            "left",
            "kicked"
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
            "📨 OTP গ্রুপে জয়েন"
        ],
        [
            "📢 চ্যানেলে জয়েন"
        ],
        [
            "✅ জয়েন করেছি"
        ]
    ]

    text = (
        "🔒 <b>বট ব্যবহার করতে হলে প্রথমে নিচের "
        "সবগুলোতে জয়েন করুন।</b>\n\n"
        "জয়েন করার পর নিচের ✅ "
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

    await update.message.reply_text(
        "👨‍💻 <b>Developer</b>\n\n"
        "কোনো সমস্যা বা প্রয়োজন হলে নিচের button চাপুন।",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "💬 Contact Dev",
                    callback_data="contact_dev"
                )
            ]
        ])
    )


# ==================================================
# CONTACT DEVELOPER
# ==================================================

async def contact_dev(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not query or not query.from_user:
        return

    await query.answer()

    user = query.from_user
    dev_chat_id = int(os.getenv("DEV_CHAT_ID", "0"))

    if not dev_chat_id:
        await query.message.reply_text(
            "⚠️ Developer ID সেট করা হয়নি।"
        )
        return

    # Contact Dev চাপলে Developer conversation শুরু হবে।
    # Study input state বন্ধ করা হবে যাতে User-এর message
    # আর study number হিসেবে ধরা না হয়।
    context.user_data["dev_active"] = True
    context.user_data["waiting_for_study"] = False

    text = (
        "📩 <b>New Developer Contact</b>\n\n"
        f"👤 <b>Name:</b> {user.full_name}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
    )

    if user.username:
        text += f"🔗 <b>Username:</b> @{user.username}\n"

    text += (
        "\n💬 User এখন Developer-এর সাথে active conversation-এ আছে।\n"
        "User-এর পরের message automatically এখানে আসবে।"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "💬 Reply",
                callback_data=f"reply_user:{user.id}"
            ),
            InlineKeyboardButton(
                "⛔ Stop",
                callback_data=f"stop_dev:{user.id}"
            )
        ]
    ]

    try:
        await context.bot.send_message(
            chat_id=dev_chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await query.message.reply_text(
            "✅ <b>Developer Contact active হয়েছে।</b>\n\n"
            "এখন আপনার পরের message automatically Developer-এর কাছে যাবে।\n"
            "Developer conversation বন্ধ করলে আবার স্বাভাবিক menu ব্যবহার করতে পারবেন।",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )

    except Exception as e:
        print("Contact developer error:", e)
        context.user_data["dev_active"] = False
        await query.message.reply_text(
            "⚠️ Developer-এর কাছে যোগাযোগের message পাঠানো যায়নি।"
        )


# ==================================================
# REPLY TO USER
# ==================================================

async def reply_to_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not query or not query.from_user:
        return

    await query.answer()

    dev_chat_id = int(os.getenv("DEV_CHAT_ID", "0"))

    if not dev_chat_id or query.from_user.id != dev_chat_id:
        return

    try:
        user_id = int(query.data.split(":", 1)[1])
    except (ValueError, IndexError, AttributeError):
        return

    context.user_data["reply_to_user"] = user_id

    await query.message.reply_text(
        "✍️ <b>আপনার Reply লিখুন:</b>\n\n"
        "যে text পাঠাবেন, সেটাই User-এর কাছে Developer reply হিসেবে যাবে।",
        parse_mode="HTML"
    )


# ==================================================
# STOP DEVELOPER CONVERSATION
# ==================================================

async def stop_dev(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not query or not query.from_user:
        return

    await query.answer()

    dev_chat_id = int(os.getenv("DEV_CHAT_ID", "0"))

    if not dev_chat_id or query.from_user.id != dev_chat_id:
        return

    try:
        user_id = int(query.data.split(":", 1)[1])
    except (ValueError, IndexError, AttributeError):
        return

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "⛔ <b>Developer conversation বন্ধ করা হয়েছে।</b>\n\n"
                "এখন আপনি আবার Study, Leaderboard অথবা Developer ব্যবহার করতে পারবেন।"
            ),
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        print("Stop developer user notification error:", e)

    await query.message.reply_text(
        f"⛔ User <code>{user_id}</code>-এর Developer conversation বন্ধ হয়েছে।",
        parse_mode="HTML"
    )


# ==================================================
# SEND DEVELOPER REPLY
# ==================================================

async def send_dev_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.effective_user:
        return False

    if update.effective_chat.type != "private":
        return False

    dev_chat_id = int(os.getenv("DEV_CHAT_ID", "0"))

    if not dev_chat_id or update.effective_user.id != dev_chat_id:
        return False

    target_user_id = context.user_data.get("reply_to_user")

    if not target_user_id:
        return False

    message_text = update.message.text

    if not message_text:
        return False

    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                "👨‍💻 <b>Developer Reply</b>\n\n"
                f"{message_text}"
            ),
            parse_mode="HTML"
        )

        context.user_data["reply_to_user"] = None

        await update.message.reply_text(
            "✅ Reply User-এর কাছে পাঠানো হয়েছে।"
        )

    except Exception as e:
        print("Developer reply error:", e)
        await update.message.reply_text(
            "⚠️ User-এর কাছে Reply পাঠানো যায়নি।"
        )

    return True


# ==================================================
# FORWARD USER MESSAGE TO DEVELOPER
# ==================================================

async def forward_user_message_to_dev(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.effective_user:
        return False

    if update.effective_chat.type != "private":
        return False

    if not context.user_data.get("dev_active"):
        return False

    # Main menu buttons must always keep working.
    text = update.message.text or ""

    if text in (
        "📚 Study",
        "🏆 Leaderboard",
        "👨‍💻 Developer"
    ):
        return False

    dev_chat_id = int(os.getenv("DEV_CHAT_ID", "0"))

    if not dev_chat_id:
        context.user_data["dev_active"] = False
        return False

    user = update.effective_user

    header = (
        "📩 <b>Message from User</b>\n\n"
        f"👤 <b>Name:</b> {user.full_name}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
    )

    if user.username:
        header += f"🔗 <b>Username:</b> @{user.username}\n"

    header += "\n💬 <b>Message:</b>"

    keyboard = [
        [
            InlineKeyboardButton(
                "💬 Reply",
                callback_data=f"reply_user:{user.id}"
            ),
            InlineKeyboardButton(
                "⛔ Stop",
                callback_data=f"stop_dev:{user.id}"
            )
        ]
    ]

    try:
        await context.bot.send_message(
            chat_id=dev_chat_id,
            text=header,
            parse_mode="HTML"
        )

        # Text message
        if update.message.text:
            await context.bot.send_message(
                chat_id=dev_chat_id,
                text=update.message.text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # Other message types are copied to Developer.
            await context.bot.copy_message(
                chat_id=dev_chat_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )

            await context.bot.send_message(
                chat_id=dev_chat_id,
                text="👇 এই User-কে Reply করতে button ব্যবহার করুন।",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    except Exception as e:
        print("Forward user message error:", e)
        await update.message.reply_text(
            "⚠️ Message Developer-এর কাছে পাঠানো যায়নি।"
        )

    return True


# ==================================================
# SAVE STUDY TIME
# ==================================================
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
                f"<b>{name}</b> — "
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

    await update.message.reply_text(
        "👨‍💻 <b>Developer</b>\n\n"
        "📚 Amol Nama Study Bot\n\n"
        "🤖 Study Time Tracker\n"
        "🏆 Daily Leaderboard",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
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

    if text == "📨 OTP গ্রুপে জয়েন":

        await update.message.reply_text(
            "👥 নিচের Group-এ Join করুন:\n\n"
            "https://t.me/+ft6UwgnBRfhjZWFl"
        )

        return

    if text == "📢 চ্যানেলে জয়েন":

        await update.message.reply_text(
            "📢 Channel-এ Join করুন:\n\n"
            "https://t.me/FixerZoneOfficial"
        )

        return

    if text == "📣 ফেসবুক বট চ্যানেলে জয়েন":

        await update.message.reply_text(
            "📣 Facebook Bot Channel"
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

    text = update.message.text or ""

    # --------------------------------------------------
    # Main menu buttons ALWAYS have priority.
    # --------------------------------------------------

    if text == "📚 Study":
        context.user_data["dev_active"] = False
        context.user_data["reply_to_user"] = None
        await study_button(update, context)
        return

    if text == "🏆 Leaderboard":
        context.user_data["dev_active"] = False
        context.user_data["waiting_for_study"] = False
        context.user_data["reply_to_user"] = None
        await leaderboard(update, context)
        return

    if text == "👨‍💻 Developer":
        await developer_button(update, context)
        return

    # --------------------------------------------------
    # Developer conversation.
    # --------------------------------------------------

    if context.user_data.get("dev_active"):
        handled = await forward_user_message_to_dev(
            update,
            context
        )
        if handled:
            return

    # --------------------------------------------------
    # Waiting for study number.
    # --------------------------------------------------

    if context.user_data.get("waiting_for_study"):

        if text in (
            "📨 OTP গ্রুপে জয়েন",
            "📢 চ্যানেলে জয়েন",
            "✅ জয়েন করেছি"
        ):
            await join_button(update, context)
            return

        await save_study_time(update, context)
        return

    # --------------------------------------------------
    # Join menu buttons.
    # --------------------------------------------------

    if text in (
        "📨 OTP গ্রুপে জয়েন",
        "📢 চ্যানেলে জয়েন",
        "✅ জয়েন করেছি"
    ):
        await join_button(update, context)
        return


# ==================================================
# DEVELOPER MESSAGE HANDLER
# ==================================================

async def developer_message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.effective_user:
        return

    dev_chat_id = int(os.getenv("DEV_CHAT_ID", "0"))

    if not dev_chat_id:
        return

    if update.effective_chat.type != "private":
        return

    if update.effective_user.id != dev_chat_id:
        return

    await send_dev_reply(update, context)


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
                        f"<b>{name}</b> — "
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
    # Developer callbacks
    # ----------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            contact_dev,
            pattern=r"^contact_dev$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            reply_to_user,
            pattern=r"^reply_user:\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            stop_dev,
            pattern=r"^stop_dev:\d+$"
        )
    )

    # ----------------------------------------------
    # Developer's own private messages
    # ----------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            developer_message_handler
        ),
        group=0
    )

    # ----------------------------------------------
    # All private user text / buttons
    # ----------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            private_text_handler
        ),
        group=1
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


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )
