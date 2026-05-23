import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

import config
from database.mongo import (
    get_total_users,
    get_total_chats,
    get_all_users,
    get_all_chats,
    is_db_connected
)
from handlers.play import active_calls, db_queue

logger = logging.getLogger("MusicBot.Admin")

def sudo_only():
    """Custom Pyrogram filter to restrict command access to sudo users only."""
    return filters.create(lambda _, __, msg: msg.from_user and msg.from_user.id in config.SUDO_USERS)


@Client.on_message(filters.command("stats") & sudo_only() & filters.group)
@Client.on_message(filters.command("stats") & sudo_only() & filters.private)
async def stats_command(client: Client, message: Message):
    if not client.me.is_bot:
        return
    """Displays real-time server and bot database stats."""
    status_msg = await message.reply_text("📊 <b>স্ট্যাটিস্টিকস সংগ্রহ করা হচ্ছে...</b>")
    
    # DB stats
    users_count = await get_total_users()
    chats_count = await get_total_chats()
    db_status = "সক্রিয় 🟢" if await is_db_connected() else "নিষ্ক্রিয় 🔴"
    
    # Active calls
    live_calls_count = len(active_calls)
    
    # Queue size
    total_queued = sum(len(group["queue"]) for group in db_queue.values())
    
    stats_text = (
        f"📊 <b>টেলিগ্রাম মিউজিক বট স্ট্যাটিস্টিকস</b> 📊\n\n"
        f"📡 <b>MongoDB ডাটাবেস:</b> {db_status}\n"
        f"👥 <b>নিবন্ধিত ইউজার:</b> <code>{users_count}</code> জন\n"
        f"💬 <b>নিবন্ধিত গ্রুপ চ্যাট:</b> <code>{chats_count}</code> টি\n\n"
        f"🎧 <b>চলমান লাইভ স্ট্রিমিং:</b> <code>{live_calls_count}</code> টি গ্রুপে\n"
        f"📋 <b>মোট কিউতে থাকা গান:</b> <code>{total_queued}</code> টি\n\n"
        f"🛠 <i>বটটি বর্তমানে সক্রিয় ও স্বাভাবিকভাবে কাজ করছে!</i>"
    )
    
    await status_msg.edit(stats_text)


@Client.on_message(filters.command("clean") & sudo_only())
async def clean_command(client: Client, message: Message):
    if not client.me.is_bot:
        return
    """Clears cache, resets queues, and frees unused memory."""
    global db_queue, active_calls
    
    # Reset all queue data that aren't playing active streams
    active_chat_ids = list(active_calls)
    cleaned_groups = 0
    
    for chat_id in list(db_queue.keys()):
        if chat_id not in active_chat_ids:
            db_queue.pop(chat_id, None)
            cleaned_groups += 1
            
    await message.reply_text(f"🧹 <b>মেমোরি পরিষ্কার করা হয়েছে!</b>\n\n🗑 <code>{cleaned_groups}</code>টি নিষ্ক্রিয় চ্যাটের কিউ ডাটা ডিলিট করা হয়েছে।")


@Client.on_message(filters.command("broadcast") & sudo_only())
async def broadcast_command(client: Client, message: Message):
    if not client.me.is_bot:
        return
    """
    Broadcasts text, photo, video, or document messages globally to
    all registered user inboxes (PM) and group chats in the database.
    """
    # Verify if broadcast payload is provided (text or media reply)
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text(
            "❌ <b>মেসেজ বডি অনুপস্থিত!</b>\n\n"
            "ব্যবহার বিধি:\n"
            "👉 <code>/broadcast [মেসেজ]</code>\n"
            "👉 অথবা যেকোনো মেসেজের রিপ্লাই দিয়ে টাইপ করুন <code>/broadcast</code>"
        )
        
    broadcast_msg = message.reply_to_message if message.reply_to_message else message
    
    # If text broadcast from command
    text_to_send = None
    if not message.reply_to_message:
        text_to_send = " ".join(message.command[1:])

    status_msg = await message.reply_text("📢 <b>গ্লোবাল ব্রডকাস্ট শুরু হচ্ছে...</b> চ্যাট লিস্ট লোড করা হচ্ছে।")
    
    users = await get_all_users()
    chats = await get_all_chats()
    
    success_users, fail_users = 0, 0
    success_chats, fail_chats = 0, 0
    
    # 1. Broadcast to Users Inbox (PM)
    if users:
        await status_msg.edit(f"📢 <b>ইনবক্সে ব্রডকাস্ট পাঠানো হচ্ছে...</b>\n\n👥 মোট ইউজার: {len(users)}")
        for user_id in users:
            try:
                if text_to_send:
                    await client.send_message(user_id, text_to_send)
                else:
                    await broadcast_msg.copy(user_id)
                success_users += 1
                await asyncio.sleep(0.15)  # Flood prevention
            except FloodWait as f:
                await asyncio.sleep(f.value + 1)
                try:
                    if text_to_send:
                        await client.send_message(user_id, text_to_send)
                    else:
                        await broadcast_msg.copy(user_id)
                    success_users += 1
                except Exception:
                    fail_users += 1
            except Exception:
                fail_users += 1

    # 2. Broadcast to Group Chats
    if chats:
        await status_msg.edit(f"📢 <b>গ্রুপ চ্যাটে ব্রডকাস্ট পাঠানো হচ্ছে...</b>\n\n💬 মোট গ্রুপ: {len(chats)}")
        for chat_id in chats:
            try:
                if text_to_send:
                    await client.send_message(chat_id, text_to_send)
                else:
                    await broadcast_msg.copy(chat_id)
                success_chats += 1
                await asyncio.sleep(0.2)  # Higher delay for groups
            except FloodWait as f:
                await asyncio.sleep(f.value + 1)
                try:
                    if text_to_send:
                        await client.send_message(chat_id, text_to_send)
                    else:
                        await broadcast_msg.copy(chat_id)
                    success_chats += 1
                except Exception:
                    fail_chats += 1
            except Exception:
                fail_chats += 1

    # Format result panel
    result_text = (
        f"📢 <b>গ্লোবাল ব্রডকাস্ট সম্পন্ন হয়েছে!</b> ✅\n\n"
        f"👤 <b>ইউজার ইনবক্স ব্রডকাস্ট:</b>\n"
        f"✔️ সফলভাবে পাঠানো হয়েছে: <code>{success_users}</code>\n"
        f"❌ পাঠানো যায়নি: <code>{fail_users}</code>\n\n"
        f"💬 <b>গ্রুপ চ্যাট ব্রডকাস্ট:</b>\n"
        f"✔️ সফলভাবে পাঠানো হয়েছে: <code>{success_chats}</code>\n"
        f"❌ পাঠানো যায়নি: <code>{fail_chats}</code>\n\n"
        f"✨ <i>ব্রডকাস্ট ডাটাবেস রেকর্ড অনুযায়ী সম্পন্ন হয়েছে!</i>"
    )
    
    await status_msg.edit(result_text)
