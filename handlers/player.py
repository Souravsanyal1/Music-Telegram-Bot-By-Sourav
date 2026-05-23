from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
import os
import config
import logging

# Import queue states and controllers from handlers.play
import handlers.play
from handlers.play import (
    db_queue,
    active_calls,
    play_next_song,
)
from utils.inline import get_player_buttons
from pyrogram.types import InlineKeyboardMarkup

def get_updated_deck(group_data: dict, is_paused: bool = False) -> InlineKeyboardMarkup:
    """Helper to generate the player inline deck with dynamic real-time progress calculations."""
    curr = group_data.get("current_song")
    total = curr.get("duration", 0) if curr else 0
    elapsed = 0
    if curr and "start_time" in curr:
        import time
        elapsed = int(time.time() - curr["start_time"])
    return get_player_buttons(
        elapsed_secs=elapsed,
        total_secs=total,
        is_paused=is_paused,
        is_looping=group_data.get("is_looping", False)
    )

logger = logging.getLogger("MusicBot.Controller")

async def is_authorized(client: Client, chat_id: int, user_id: int) -> bool:
    """Verifies if a user is authorized to perform player control actions (Sudo, Admin, Creator)."""
    if user_id in config.SUDO_USERS:
        return True
        
    # Check if the user is a group administrator/owner
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in ["administrator", "owner"]:
            return True
    except Exception:
        pass
        
    return False


# COMMAND-BASED HANDLERS

@Client.on_message(filters.command(["pause", "p"]) & filters.group)
async def pause_command(client: Client, message: Message):
    if not client.me.is_bot:
        return
    if not handlers.play.pytgcalls_client:
        return await message.reply_text(
            "⚠️ <b>ভয়েস চ্যাট ইঞ্জিন বর্তমানে নিষ্ক্রিয় আছে!</b>"
        )
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    
    if chat_id not in active_calls:
        return await message.reply_text("❌ <b>বর্তমানে কোনো গান চলছে না!</b>")
        
    if not await is_authorized(client, chat_id, user_id):
        return await message.reply_text("❌ <b>অনুমতি নেই!</b> এই অ্যাকশনটি শুধুমাত্র গ্রুপ অ্যাডমিন বা সুডো ইউজারদের জন্য।")
        
    try:
        await handlers.play.pytgcalls_client.pause(chat_id)
        await message.reply_text("⏸ <b>মিউজিক স্ট্রিমিং সাময়িকভাবে বন্ধ (Paused) করা হয়েছে।</b>")
        
        # Dynamically update inline deck keyboard if active card message ID exists
        if chat_id in db_queue and db_queue[chat_id]["active_msg_id"]:
            try:
                await client.edit_message_reply_markup(
                    chat_id,
                    db_queue[chat_id]["active_msg_id"],
                    reply_markup=get_updated_deck(db_queue[chat_id], is_paused=True)
                )
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error pausing stream in {chat_id}: {e}")
        await message.reply_text(f"❌ <b>ব্যর্থ হয়েছে!</b> গানটি পজ করতে সমস্যা হচ্ছে।")


@Client.on_message(filters.command(["resume", "r"]) & filters.group)
async def resume_command(client: Client, message: Message):
    if not client.me.is_bot:
        return
    if not handlers.play.pytgcalls_client:
        return await message.reply_text(
            "⚠️ <b>ভয়েস চ্যাট ইঞ্জিন বর্তমানে নিষ্ক্রিয় আছে!</b>"
        )
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    
    if chat_id not in active_calls:
        return await message.reply_text("❌ <b>বর্তমানে কোনো গান চলছে না!</b>")
        
    if not await is_authorized(client, chat_id, user_id):
        return await message.reply_text("❌ <b>অনুমতি নেই!</b> এই অ্যাকশনটি শুধুমাত্র গ্রুপ অ্যাডমিন বা সুডো ইউজারদের জন্য।")
        
    try:
        await handlers.play.pytgcalls_client.resume(chat_id)
        await message.reply_text("▶️ <b>পজ করা গানটি পুনরায় প্লে (Resumed) করা হয়েছে।</b>")
        
        if chat_id in db_queue and db_queue[chat_id]["active_msg_id"]:
            try:
                await client.edit_message_reply_markup(
                    chat_id,
                    db_queue[chat_id]["active_msg_id"],
                    reply_markup=get_updated_deck(db_queue[chat_id], is_paused=False)
                )
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error resuming stream in {chat_id}: {e}")
        await message.reply_text(f"❌ <b>ব্যর্থ হয়েছে!</b> গানটি রিজিউম করতে সমস্যা হচ্ছে।")


@Client.on_message(filters.command(["skip", "s"]) & filters.group)
async def skip_command(client: Client, message: Message):
    if not client.me.is_bot:
        return
    if not handlers.play.pytgcalls_client:
        return await message.reply_text(
            "⚠️ <b>ভয়েস চ্যাট ইঞ্জিন বর্তমানে নিষ্ক্রিয় আছে!</b>"
        )
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    
    if chat_id not in active_calls:
        return await message.reply_text("❌ <b>বর্তমানে কোনো গান চলছে না!</b>")
        
    if not await is_authorized(client, chat_id, user_id):
        return await message.reply_text("❌ <b>অনুমতি নেই!</b> এই অ্যাকশনটি শুধুমাত্র গ্রুপ অ্যাডমিন বা সুডো ইউজারদের জন্য।")
        
    await message.reply_text("⏭ <b>গানটি বাদ দিয়ে পরের গানটি লোড করা হচ্ছে...</b>")
    # Trigger play_next_song
    await play_next_song(chat_id)


@Client.on_message(filters.command(["stop", "end", "c"]) & filters.group)
async def stop_command(client: Client, message: Message):
    if not client.me.is_bot:
        return
    if not handlers.play.pytgcalls_client:
        return await message.reply_text(
            "⚠️ <b>ভয়েস চ্যাট ইঞ্জিন বর্তমানে নিষ্ক্রিয় আছে!</b>"
        )
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    
    if chat_id not in active_calls:
        return await message.reply_text("❌ <b>বর্তমানে কোনো গান চলছে না!</b>")
        
    if not await is_authorized(client, chat_id, user_id):
        return await message.reply_text("❌ <b>অনুমতি নেই!</b> এই অ্যাকশনটি শুধুমাত্র গ্রুপ অ্যাডমিন বা সুডো ইউজারদের জন্য।")
        
    try:
        await handlers.play.pytgcalls_client.leave_call(chat_id)
        if chat_id in active_calls:
            active_calls.remove(chat_id)
            
        # Reset queue data completely and clean up downloaded TG files
        if chat_id in db_queue:
            curr = db_queue[chat_id].get("current_song")
            if curr and curr.get("local_path"):
                if os.path.exists(curr["local_path"]):
                    try:
                        os.remove(curr["local_path"])
                    except Exception:
                        pass
            db_queue[chat_id]["queue"] = []
            db_queue[chat_id]["current_song"] = None
            
        await message.reply_text("⏹ <b>মিউজিক স্ট্রিমিং বন্ধ করে অ্যাসিস্ট্যান্ট বিদায় নিয়েছে!</b> চ্যাট কিউ খালি করা হয়েছে।")
    except Exception as e:
        logger.error(f"Error stopping stream in {chat_id}: {e}")
        await message.reply_text(f"❌ <b>ব্যর্থ হয়েছে!</b> ভয়েস চ্যাট বন্ধ করতে সমস্যা হচ্ছে।")


@Client.on_message(filters.command("loop") & filters.group)
async def loop_command(client: Client, message: Message):
    if not client.me.is_bot:
        return
    if not handlers.play.pytgcalls_client:
        return await message.reply_text(
            "⚠️ <b>ভয়েস চ্যাট ইঞ্জিন বর্তমানে নিষ্ক্রিয় আছে!</b>"
        )
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    
    if chat_id not in active_calls or chat_id not in db_queue:
        return await message.reply_text("❌ <b>বর্তমানে কোনো গান চলছে না!</b>")
        
    if not await is_authorized(client, chat_id, user_id):
        return await message.reply_text("❌ <b>অনুমতি নেই!</b> এই অ্যাকশনটি শুধুমাত্র গ্রুপ অ্যাডমিন বা সুডো ইউজারদের জন্য।")
        
    # Toggle loop state
    group_data = db_queue[chat_id]
    group_data["is_looping"] = not group_data["is_looping"]
    status = "সক্রিয় 🔁" if group_data["is_looping"] else "নিষ্ক্রিয় ❌"
    
    await message.reply_text(f"🔁 <b>সিঙ্গেল ট্র্যাক লুপ এখন {status}!</b>")
    
    # Update active player deck markup
    if group_data["active_msg_id"]:
        try:
            await client.edit_message_reply_markup(
                chat_id,
                group_data["active_msg_id"],
                reply_markup=get_updated_deck(group_data, is_paused=False)
            )
        except Exception:
            pass


# INLINE BUTTON CALLBACK QUERY HANDLERS

@Client.on_callback_query(filters.regex(pattern=r"^c_(pause|resume|skip|stop|loop|unloop)$"))
async def player_button_callbacks(client: Client, callback_query: CallbackQuery):
    if not client.me.is_bot:
        return
    if not handlers.play.pytgcalls_client:
        return await callback_query.answer(
            "⚠️ অ্যাসিস্ট্যান্ট অ্যাকাউন্ট নিষ্ক্রিয় বা সেশন নষ্ট হয়ে গেছে! মিউজিক কন্ট্রোল করা সম্ভব নয়।",
            show_alert=True
        )
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # Authorize user clicking inline controls
    if not await is_authorized(client, chat_id, user_id):
        return await callback_query.answer(
            "❌ আপনি অ্যাডমিন বা সুডো ইউজার নন, তাই এই বাটন কন্ট্রোল করতে পারবেন না!",
            show_alert=True
        )
        
    if chat_id not in active_calls or chat_id not in db_queue:
        return await callback_query.answer("⚠️ বর্তমানে কোনো লাইভ গান স্ট্রিমিং হচ্ছে না!", show_alert=True)
        
    group_data = db_queue[chat_id]

    if data == "c_pause":
        try:
            await handlers.play.pytgcalls_client.pause(chat_id)
            await callback_query.answer("⏸ মিউজিক পজ করা হয়েছে।", show_alert=False)
            await callback_query.message.edit_reply_markup(
                reply_markup=get_updated_deck(group_data, is_paused=True)
            )
        except Exception as e:
            logger.error(f"Callback pause error: {e}")
            await callback_query.answer("❌ পজ করতে ব্যর্থ হয়েছে!", show_alert=True)

    elif data == "c_resume":
        try:
            await handlers.play.pytgcalls_client.resume(chat_id)
            await callback_query.answer("▶️ মিউজিক রিজিউম করা হয়েছে।", show_alert=False)
            await callback_query.message.edit_reply_markup(
                reply_markup=get_updated_deck(group_data, is_paused=False)
            )
        except Exception as e:
            logger.error(f"Callback resume error: {e}")
            await callback_query.answer("❌ রিজিউম করতে ব্যর্থ হয়েছে!", show_alert=True)

    elif data == "c_skip":
        await callback_query.answer("⏭ বর্তমান গানটি স্কিপ করা হচ্ছে...", show_alert=False)
        # Edit markup to remove buttons temporarily
        try:
            await callback_query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await play_next_song(chat_id)

    elif data == "c_stop":
        try:
            await handlers.play.pytgcalls_client.leave_call(chat_id)
            if chat_id in active_calls:
                active_calls.remove(chat_id)
                
            # Clean up temporary downloaded file
            curr = group_data.get("current_song")
            if curr and curr.get("local_path"):
                if os.path.exists(curr["local_path"]):
                    try:
                        os.remove(curr["local_path"])
                    except Exception:
                        pass
            group_data["queue"] = []
            group_data["current_song"] = None
            
            await callback_query.answer("⏹ মিউজিক প্লেয়ার বন্ধ করা হয়েছে।", show_alert=True)
            # Remove photo player card buttons
            await callback_query.message.edit_reply_markup(reply_markup=None)
        except Exception as e:
            logger.error(f"Callback stop error: {e}")
            await callback_query.answer("❌ স্টপ করতে ব্যর্থ হয়েছে!", show_alert=True)

    elif data == "c_loop":
        group_data["is_looping"] = True
        await callback_query.answer("🔁 সিঙ্গেল লুপ চালু করা হয়েছে!", show_alert=False)
        await callback_query.message.edit_reply_markup(
            reply_markup=get_updated_deck(group_data, is_paused=False)
        )

    elif data == "c_unloop":
        group_data["is_looping"] = False
        await callback_query.answer("❌ লুপ বন্ধ করা হয়েছে!", show_alert=False)
        await callback_query.message.edit_reply_markup(
            reply_markup=get_updated_deck(group_data, is_paused=False)
        )


@Client.on_callback_query(filters.regex(pattern=r"^c_empty$"))
async def empty_callback(client: Client, callback_query: CallbackQuery):
    if not client.me.is_bot:
        return
    await callback_query.answer()
