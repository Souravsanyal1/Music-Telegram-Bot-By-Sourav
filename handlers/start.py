from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant
from database.mongo import add_user
from utils.inline import get_start_buttons
import config
import logging

logger = logging.getLogger("MusicBot.Start")

# FORCE SUBSCRIPTION SYSTEM HELPERS

async def check_force_sub(client: Client, user_id: int) -> bool:
    """Checks if the user is a member of all configured force channel/groups."""
    # Check main channel
    if config.FORCE_SUB_CHANNEL:
        try:
            chat_member = await client.get_chat_member(config.FORCE_SUB_CHANNEL, user_id)
            if chat_member.status in ["left", "kicked"]:
                return False
        except UserNotParticipant:
            return False
        except Exception as e:
            # ValueError/KeyError from in_memory peer cache — allow user through
            logger.warning(f"Force sub channel check skipped for {user_id}: {e}")

    # Check force group (if configured)
    if config.FORCE_SUB_GROUP:
        try:
            chat_member = await client.get_chat_member(config.FORCE_SUB_GROUP, user_id)
            if chat_member.status in ["left", "kicked"]:
                return False
        except UserNotParticipant:
            return False
        except Exception as e:
            # ValueError/KeyError from in_memory peer cache — allow user through
            logger.warning(f"Force sub group check skipped for {user_id}: {e}")

    return True


def get_force_sub_markup() -> InlineKeyboardMarkup:
    """Returns an inline keyboard prompting the user to join the update channel and/or group."""
    buttons = []

    # Add channel join button if configured
    if config.FORCE_SUB_CHANNEL:
        channel_link = config.FORCE_SUB_LINK or str(config.FORCE_SUB_CHANNEL)
        if not (str(channel_link).startswith("https://") or str(channel_link).startswith("t.me/")):
            channel_link = f"https://t.me/{str(channel_link).replace('@', '')}"
        buttons.append([InlineKeyboardButton("📢 Join Channel", url=channel_link)])

    # Add group join button if configured
    if config.FORCE_SUB_GROUP:
        group_link = config.FORCE_SUB_GROUP_LINK or str(config.FORCE_SUB_GROUP)
        if not (str(group_link).startswith("https://") or str(group_link).startswith("t.me/")):
            group_link = f"https://t.me/{str(group_link).replace('@', '')}"
        buttons.append([InlineKeyboardButton("👥 Join Group", url=group_link)])

    buttons.append([InlineKeyboardButton("🔄 Verify / Try Again", callback_data="c_verify_sub")])
    return InlineKeyboardMarkup(buttons)


# PRIVATE COMMANDS WITH FORCE JOIN CHECK

@Client.on_message(filters.command("start") & filters.private)
async def start_private(client: Client, message: Message):
    """Greets the user in PM, checks force channel join, and logs registration details."""
    user = message.from_user
    
    # 1. Force Subscription Check
    if not await check_force_sub(client, user.id):
        welcome_back_text = (
            "⚠️ <b>সদস্যতা নিশ্চিত করুন!</b>\n\n"
            "আমাদের প্রিমিয়াম মিউজিক বটটি ব্যবহার করতে আপনাকে প্রথমে আমাদের চ্যানেল বা গ্রুপে যুক্ত হতে হবে।\n\n"
            "নিচের বাটনটি ক্লিক করে জয়েন করুন এবং তারপর <b>🔄 Verify / Try Again</b> বাটনে ক্লিক করুন!"
        )
        return await message.reply_text(
            welcome_back_text,
            reply_markup=get_force_sub_markup()
        )

    # 2. Add user to database asynchronously
    await add_user(
        user_id=user.id,
        first_name=user.first_name,
        username=user.username
    )
    
    welcome_text = (
        f"👋 <b>হলো {user.first_name}!</b>\n\n"
        f"🤖 আমি একটি <b>প্রিমিয়াম টেলিগ্রাম মিউজিক বট</b>। "
        f"গ্রুপ ভয়েস চ্যাট বা লাইভে হাই-কোয়ালিটি গান শুনতে আমার সাহায্য নিতে পারেন।\n\n"
        f"🎵 <b>আমার প্রধান ফিচারসমূহ:</b>\n"
        f"⚡ <code>/play [গানের নাম বা লিংক]</code> দিয়ে যেকোনো গান চালান।\n"
        f"🎧 YouTube / YouTube Music / MP3 লিংক সাপোর্ট করে।\n"
        f"📊 সুন্দর প্রফেশনাল মিউজিক প্লেয়ার ইন্টারফেস।\n"
        f"🔁 লুপ, স্কিপ, পজ এবং রিজিউম কন্ট্রোল।\n\n"
        f"💡 কিভাবে শুরু করবেন জানতে <code>/help</code> পাঠান!"
    )
    
    await message.reply_text(
        welcome_text,
        reply_markup=get_start_buttons(config.BOT_USERNAME)
    )


@Client.on_message(filters.command("start") & filters.group)
async def start_group(client: Client, message: Message):
    """Simple greeting when bot start command is triggered in a group chat."""
    await message.reply_text(
        f"🎵 <b>মিউজিক বট সক্রিয় আছে!</b>\n\n"
        f"🎤 গ্রুপ ভয়েস চ্যাটে গান চালাতে টাইপ করুন:\n"
        f"👉 <code>/play [গানের নাম বা লিংক]</code>\n\n"
        f"📩 পার্সোনাল ইনবক্সে আরও বাটন এবং অনবোর্ডিং দেখতে আমাকে স্টার্ট করুন!"
    )


@Client.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """Displays a list of available player controls and admin commands."""
    user_id = message.from_user.id if message.from_user else 0
    
    # Check force sub in private chat
    if message.chat.type == "private":
        if not await check_force_sub(client, user_id):
            return await message.reply_text(
                "⚠️ <b>সদস্যতা নিশ্চিত করুন!</b>\n\n"
                "বটটি ব্যবহার করতে আপনাকে প্রথমে আমাদের চ্যানেল বা গ্রুপে যুক্ত হতে হবে।",
                reply_markup=get_force_sub_markup()
            )
            
        await add_user(
            user_id=user_id,
            first_name=message.from_user.first_name,
            username=message.from_user.username
        )
        
    help_text = (
        f"🎵 <b>মিউজিক বটের কমান্ড গাইড</b> 🎧\n\n"
        f"📣 <b>ইউজার কমান্ডস:</b>\n"
        f"▶️ <code>/play [গানের নাম বা লিংক]</code> - সরাসরি গান বা মিউজিক প্লে করুন।\n"
        f"⏸ <code>/pause</code> - চলমান গান সাময়িকভাবে পজ করুন।\n"
        f"▶️ <code>/resume</code> - পজ করা গান পুনরায় চালু করুন।\n"
        f"⏭ <code>/skip</code> - বর্তমান গান বাদ দিয়ে পরের গানে যান।\n"
        f"🔁 <code>/loop</code> - লুপ সক্রিয়/নিষ্ক্রিয় করুন (একই গান বারবার চলবে)।\n"
        f"⏹ <code>/stop</code> বা <code>/end</code> - গান বন্ধ করে ভয়েস চ্যাট থেকে বের করুন।\n"
        f"📋 <code>/queue</code> - আপকামিং গানের তালিকা দেখুন।\n\n"
        f"🛠 <b>অ্যাডমিন কমান্ডস (শুধুমাত্র সুডো ইউজারদের জন্য):</b>\n"
        f"📢 <code>/broadcast [মেসেজ]</code> - সকল ইউজার ও চ্যাটে মেসেজ পাঠান।\n"
        f"📊 <code>/stats</code> - বটের রিয়েল-টাইম স্ট্যাটিস্টিকস দেখুন।\n"
        f"🧹 <code>/clean</code> - বটের মেমোরি ও কিউ (queue) পরিষ্কার করুন।"
    )
    await message.reply_text(help_text)


# CALLBACK QUERY HANDLER FOR FORCE VERIFICATION

@Client.on_callback_query(filters.regex(pattern=r"^c_verify_sub$"))
async def verify_sub_callback(client: Client, callback_query: CallbackQuery):
    """Callback query to verify if the user joined the update channel and unlocks features."""
    user = callback_query.from_user
    
    if await check_force_sub(client, user.id):
        # Delete membership prompt card
        await callback_query.message.delete()
        
        # Add user database registration asynchronously
        await add_user(
            user_id=user.id,
            first_name=user.first_name,
            username=user.username
        )
        
        welcome_text = (
            f"👋 <b>হলো {user.first_name}!</b>\n\n"
            f"🤖 আমি একটি <b>প্রিমিয়াম টেলিগ্রাম মিউজিক বট</b>। "
            f"গ্রুপ ভয়েস চ্যাট বা লাইভে হাই-কোয়ালিটি গান শুনতে আমার সাহায্য নিতে পারেন।\n\n"
            f"🎵 <b>আমার প্রধান ফিচারসমূহ:</b>\n"
            f"⚡ <code>/play [গানের নাম বা লিংক]</code> দিয়ে যেকোনো গান চালান।\n"
            f"🎧 YouTube / YouTube Music / MP3 লিংক সাপোর্ট করে।\n"
            f"📊 সুন্দর প্রফেশনাল মিউজিক প্লেয়ার ইন্টারফেস।\n"
            f"🔁 লুপ, স্কিপ, পজ এবং রিজিউম কন্ট্রোল।\n\n"
            f"💡 কিভাবে শুরু করবেন জানতে <code>/help</code> পাঠান!"
        )
        
        await client.send_message(
            chat_id=callback_query.message.chat.id,
            text=welcome_text,
            reply_markup=get_start_buttons(config.BOT_USERNAME)
        )
        await callback_query.answer("✅ সফলভাবে যাচাই করা হয়েছে! বট ব্যবহারের জন্য উন্মুক্ত। 😊", show_alert=True)
    else:
        await callback_query.answer("❌ আপনি এখনো আমাদের চ্যানেল বা গ্রুপে জয়েন করেননি! দয়া করে জয়েন করে আবার চেষ্টা করুন।", show_alert=True)
