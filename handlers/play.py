import os
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import config
from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from pytgcalls.types import MediaStream

from database.mongo import add_chat
from utils.downloaders import search_youtube, extract_audio_stream
from utils.thumbnails import generate_thumbnail
from utils.inline import get_player_buttons, generate_text_progress_bar

logger = logging.getLogger("MusicBot.Player")

# Thread-safe global states
db_queue = {}  # Format: {chat_id: {"queue": [], "is_looping": False, "current_song": None, "active_msg_id": None}}
active_calls = set()

# Reference to the PyTgCalls instance and Clients (assigned dynamically on boot in main.py)
pytgcalls_client: PyTgCalls = None
bot_client: Client = None
assistant_client: Client = None

def init_clients(py_calls: PyTgCalls, bot: Client, assistant: Client):
    """Initializes global references to clients from main.py."""
    global pytgcalls_client, bot_client, assistant_client
    pytgcalls_client = py_calls
    bot_client = bot
    assistant_client = assistant


async def play_next_song(chat_id: int):
    """Fetches the next song in queue, plays it, and updates player UI."""
    if chat_id not in db_queue:
        return
        
    group_data = db_queue[chat_id]
    
    # Clean up previous song's temporary file if it was a downloaded TG file
    if not (group_data["is_looping"] and group_data["current_song"]):
        if group_data.get("current_song") and group_data["current_song"].get("local_path"):
            old_path = group_data["current_song"]["local_path"]
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                    logger.info(f"Successfully cleaned up old TG download file: {old_path}")
                except Exception as clean_err:
                    logger.warning(f"Could not delete old TG file {old_path}: {clean_err}")
    
    # Handle Song Looping
    if group_data["is_looping"] and group_data["current_song"]:
        # Re-play current song
        song_data = group_data["current_song"]
    else:
        # Check if queue has next items
        if not group_data["queue"]:
            # Queue is empty, exit voice chat gracefully
            try:
                await pytgcalls_client.leave_call(chat_id)
            except Exception:
                pass
            if chat_id in active_calls:
                active_calls.remove(chat_id)
                
            # Clean up the last song's local file
            if group_data.get("current_song") and group_data["current_song"].get("local_path"):
                old_path = group_data["current_song"]["local_path"]
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass
            group_data["current_song"] = None
            
            # Send notification
            if bot_client:
                await bot_client.send_message(
                    chat_id,
                    "👋 <b>ভয়েস চ্যাট কিউ খালি!</b> আমি এখন বিদায় নিচ্ছি। আবার গান শুনতে <code>/play</code> ব্যবহার করুন।"
                )
            return
            
        # Pop next song
        song_data = group_data["queue"].pop(0)
        group_data["current_song"] = song_data

    # Notify playing next song
    status_msg = None
    if bot_client:
        status_msg = await bot_client.send_message(
            chat_id,
            f"🎵 <b>'{song_data['title']}'</b> এক্সট্র্যাক্ট করা হচ্ছে... দয়া করে অপেক্ষা করুন। 🎧"
        )
        
    # Extract Direct Audio Stream Link or Download Telegram File
    is_tg_file = song_data.get("is_tg_file", False)
    extracted_data = None
    
    if is_tg_file:
        if status_msg:
            await status_msg.edit(f"📥 <b>'{song_data['title']}'</b> ডাউনলোড করা হচ্ছে... দয়া করে অপেক্ষা করুন। 🎧")
        try:
            tg_file_path = await assistant_client.download_media(song_data["file_id"])
            if not tg_file_path or not os.path.exists(tg_file_path):
                raise ValueError("Downloaded file path is invalid")
            
            song_data["local_path"] = tg_file_path
            extracted_data = {
                "title": song_data["title"],
                "duration_str": song_data["duration_str"],
                "thumbnail": None,
                "stream_url": tg_file_path,
                "channel": song_data["channel"] or "Telegram Audio"
            }
        except Exception as err:
            logger.error(f"Telegram file download failed: {err}")
            if status_msg:
                await status_msg.edit("❌ <b>দুঃখিত!</b> টেলিগ্রাম ফাইলটি ডাউনলোড করা যায়নি। পরের গানটি লোড করা হচ্ছে...")
            group_data["current_song"] = None
            await play_next_song(chat_id)
            return
    else:
        extracted_data = await extract_audio_stream(song_data["url"])
        if not extracted_data or "error" in extracted_data:
            err_msg = extracted_data.get("error", "Unknown extraction error") if extracted_data else "No data returned"
            logger.error(f"Extraction failed for {song_data['title']}: {err_msg}")
            if status_msg:
                await status_msg.edit(
                    f"❌ <b>দুঃখিত! এই গানটি এক্সট্র্যাক্ট করা যায়নি।</b>\n\n"
                    f"🔍 <b>কারণ:</b> <code>{err_msg}</code>\n\n"
                    f"<i>পরের গানটি লোড করা হচ্ছে...</i>"
                )
                await asyncio.sleep(5)
            # Try playing next
            group_data["current_song"] = None
            await play_next_song(chat_id)
            return

    # Dynamic Card Generation
    thumb_path = f"thumb_{chat_id}.png"
    
    # Check if thumbnail exists, if not fall back to bot's profile photo
    thumb_url = extracted_data.get("thumbnail")
    if not thumb_url:
        bot_photo_path = "bot_profile.png"
        if not os.path.exists(bot_photo_path) and bot_client:
            try:
                bot_me = await bot_client.get_me()
                if bot_me.photo:
                    logger.info("Downloading bot's profile photo for fallback card artwork...")
                    await bot_client.download_media(bot_me.photo.big_file_id, file_name=bot_photo_path)
            except Exception as e:
                logger.warning(f"Could not download bot profile photo: {e}")
        
        if os.path.exists(bot_photo_path):
            thumb_url = bot_photo_path

    await generate_thumbnail(
        title=extracted_data["title"],
        duration_str=extracted_data["duration_str"],
        thumbnail_url=thumb_url,
        requester_name=song_data["requester"],
        channel=extracted_data["channel"],
        output_filename=thumb_path
    )
    
    # Ensure Assistant is in the group chat and has joined
    if bot_client and assistant_client:
        try:
            assistant_me = await assistant_client.get_me()
            try:
                await bot_client.get_chat_member(chat_id, assistant_me.id)
            except Exception:
                # Assistant is not in group, try to add them directly
                try:
                    await bot_client.add_chat_members(chat_id, assistant_me.id)
                    logger.info(f"Successfully added Assistant @{assistant_me.username} to chat {chat_id}")
                except Exception as add_err:
                    logger.warning(f"Could not add Assistant directly: {add_err}. Trying via invite link.")
                    try:
                        invite_link = await bot_client.export_chat_invite_link(chat_id)
                        await assistant_client.join_chat(invite_link)
                        logger.info(f"Assistant @{assistant_me.username} successfully joined chat {chat_id} via invite link")
                    except Exception as join_err:
                        logger.error(f"Assistant failed to join chat {chat_id}: {join_err}")
                        error_text = (
                            f"❌ <b>অ্যাসিস্ট্যান্ট গ্রুপে যুক্ত হতে পারেনি!</b>\n\n"
                            f"দয়া করে অ্যাসিস্ট্যান্ট অ্যাকাউন্ট 👤 @{assistant_me.username or assistant_me.first_name} কে গ্রুপে এড করুন এবং কথা বলার পারমিশন দিন।"
                        )
                        if status_msg:
                            await status_msg.edit(error_text)
                        else:
                            await bot_client.send_message(chat_id, error_text)
                        # Reset states to prevent bot freezing
                        group_data["current_song"] = None
                        if chat_id in active_calls:
                            active_calls.remove(chat_id)
                        return
        except Exception as outer_err:
            logger.error(f"Error checking/adding assistant to voice chat: {outer_err}")

    # Stream in Voice Chat using PyTgCalls
    try:
        await pytgcalls_client.play(chat_id, MediaStream(extracted_data["stream_url"], video_flags=MediaStream.Flags.IGNORE))
        active_calls.add(chat_id)
    except Exception as e:
        logger.error(f"PyTgCalls streaming failed for {chat_id}: {e}")
        if status_msg:
            await status_msg.edit(f"❌ <b>ভয়েস চ্যাটে স্ট্রিম শুরু করতে ব্যর্থ হয়েছে!</b>\n\n<i>নিশ্চিত করুন অ্যাসিস্ট্যান্ট অ্যাকাউন্টটি চ্যাটে যুক্ত আছে এবং কথা বলার পারমিশন আছে।</i>")
        # Reset states to prevent bot freezing
        group_data["current_song"] = None
        if chat_id in active_calls:
            active_calls.remove(chat_id)
        try:
            await pytgcalls_client.leave_call(chat_id)
        except Exception:
            pass
        return

    # Delete waiting message
    if status_msg:
        await status_msg.delete()

    # Send Player UI Card
    if bot_client and os.path.exists(thumb_path):
        caption_text = (
            f"🧙‍♀️ ✨ <b>STARTED STREAMING |</b>\n\n"
            f"🧙‍♀️ <b>Title :</b> <a href='{song_data['url']}'>{extracted_data['title']}</a>\n"
            f"⏱ <b>Duration :</b> <code>{extracted_data['duration_str']}</code> MINUTES\n"
            f"👤 <b>Requested by :</b> {song_data['requester_mention']} 🎸"
        )
        try:
            import time
            song_data["start_time"] = time.time()
            
            sent_msg = await bot_client.send_photo(
                chat_id,
                photo=thumb_path,
                caption=caption_text,
                reply_markup=get_player_buttons(
                    elapsed_secs=0,
                    total_secs=song_data.get("duration", 0),
                    is_paused=False,
                    is_looping=group_data["is_looping"]
                )
            )
            # Save active player card message ID for dynamic updates
            group_data["active_msg_id"] = sent_msg.id
        except Exception as e:
            logger.error(f"Error sending player card: {e}")
            
        # Clean local thumbnail file
        try:
            os.remove(thumb_path)
        except Exception:
            pass


@Client.on_message(filters.command("play") & filters.group)
async def play_command(client: Client, message: Message):
    if not client.me.is_bot:
        return
    """
    Handles the /play command in groups.
    Supports YouTube URLs, YouTube Music, direct query searches, and replied audio files.
    Manages voice chat auto-join and queues.
    """
    chat_id = message.chat.id
    user = message.from_user
    
    reply = message.reply_to_message
    has_reply_audio = reply and (reply.audio or reply.voice or (reply.document and reply.document.mime_type and reply.document.mime_type.startswith("audio/")))
    
    if len(message.command) < 2 and not has_reply_audio:
        return await message.reply_text(
            "❌ <b>কমান্ডটি অসম্পূর্ণ!</b>\n\n"
            "গানের নাম অথবা YouTube লিংক দিন।\n"
            "যেমন: <code>/play Alan Walker Faded</code>\n"
            "অথবা: <code>/play https://youtu.be/dQw4w9WgXcQ</code>\n"
            "অথবা কোনো অডিও ফাইলের রিপ্লাই দিয়ে লিখুন: <code>/play</code>"
        )
        
    # Setup queue for this group if not already present
    if chat_id not in db_queue:
        db_queue[chat_id] = {
            "queue": [],
            "is_looping": False,
            "current_song": None,
            "active_msg_id": None
        }
        
    group_data = db_queue[chat_id]
    
    # Handle replied Telegram audio files directly
    if has_reply_audio:
        status_msg = await message.reply_text("📥 <b>অডিও ফাইলটি বিশ্লেষণ করা হচ্ছে...</b> দয়া করে অপেক্ষা করুন। 🎧")
        was_idle = (chat_id not in active_calls and group_data["current_song"] is None)
        
        audio_obj = reply.audio or reply.voice or reply.document
        title = "Unknown Audio"
        performer = "Telegram Audio"
        duration = 0
        file_id = audio_obj.file_id
        
        if reply.audio:
            title = reply.audio.title or "Unknown Audio"
            performer = reply.audio.performer or "Unknown Artist"
            duration = reply.audio.duration or 0
        elif reply.voice:
            title = f"Voice Note from {reply.from_user.first_name if reply.from_user else 'User'}"
            performer = "Voice Note"
            duration = reply.voice.duration or 0
        elif reply.document:
            title = reply.document.file_name or "Unknown Audio File"
            performer = "Document Audio"
            
        full_title = f"{performer} - {title}" if performer not in ["Unknown Artist", "Telegram Audio", "Document Audio", "Voice Note"] else title
        mins, secs = divmod(duration, 60)
        duration_str = f"{mins:02d}:{secs:02d}"
        
        song_info = {
            "title": full_title,
            "duration": duration,
            "duration_str": duration_str,
            "thumbnail": None,
            "url": f"tg_file_id:{file_id}",
            "channel": performer,
            "requester": user.first_name if user else "Unknown User",
            "requester_mention": user.mention if user else "Unknown User",
            "file_id": file_id,
            "is_tg_file": True
        }
        
        group_data["queue"].append(song_info)
        
        if was_idle:
            await play_next_song(chat_id)
            
        try:
            await status_msg.delete()
        except Exception:
            pass
            
        is_currently_playing = (group_data["current_song"] and group_data["current_song"]["url"] == song_info["url"])
        if not (is_currently_playing and len(group_data["queue"]) == 0):
            queue_pos = len(group_data["queue"])
            await message.reply_text(
                f"➕ <b>কিউতে যোগ করা হয়েছে! (টেলিগ্রাম অডিও)</b>\n\n"
                f"🎵 <b>গান:</b> <code>{song_info['title']}</code>\n"
                f"🔢 <b>অবস্থান:</b> <code>#{queue_pos}</code>\n"
                f"👤 <b>অনুরোধকারী:</b> {song_info['requester_mention']}"
            )
        return

    raw_query = " ".join(message.command[1:])
    
    # Save active chat details to MongoDB database asynchronously
    await add_chat(chat_id, message.chat.title)
    
    # Parse multiple queries separated by | or newlines
    queries = []
    if "|" in raw_query:
        queries = [q.strip() for q in raw_query.split("|") if q.strip()]
    elif "\n" in raw_query:
        queries = [q.strip() for q in raw_query.split("\n") if q.strip()]
    else:
        # Check if multiple space-separated YouTube/Music links are provided
        parts = [p.strip() for p in raw_query.split(" ") if p.strip()]
        if len(parts) > 1 and all(p.startswith("http") for p in parts):
            queries = parts
        else:
            queries = [raw_query]
            
    # Setup queue for this group if not already present
    if chat_id not in db_queue:
        db_queue[chat_id] = {
            "queue": [],
            "is_looping": False,
            "current_song": None,
            "active_msg_id": None
        }
        
    group_data = db_queue[chat_id]
    
    # Initial status message
    status_msg = await message.reply_text("🔍 <b>অনুরোধ করা গানগুলো বিশ্লেষণ করা হচ্ছে...</b> দয়া করে অপেক্ষা করুন।")
    
    was_idle = (chat_id not in active_calls and group_data["current_song"] is None)
    added_songs = []
    failed_songs = []
    
    for q in queries:
        song_info = None
        # Check if query is a YouTube URL
        if "youtube.com/" in q or "youtu.be/" in q:
            # Direct URL extraction
            extracted = await extract_audio_stream(q)
            if extracted:
                song_info = {
                    "title": extracted["title"],
                    "duration": extracted["duration"],
                    "duration_str": extracted["duration_str"],
                    "thumbnail": extracted["thumbnail"],
                    "url": extracted["url"],
                    "channel": extracted["channel"],
                }
        else:
            # Search by name
            results = await search_youtube(q, limit=1)
            if results:
                song_info = results[0]
                
        if not song_info:
            failed_songs.append(q)
            continue
            
        # Append requester details
        song_info["requester"] = user.first_name if user else "Unknown User"
        song_info["requester_mention"] = user.mention if user else "Unknown User"
        
        # Append to queue first
        group_data["queue"].append(song_info)
        added_songs.append(song_info)
        
    # Start playing if the player was idle and we added at least one song
    if was_idle and group_data["queue"]:
        await play_next_song(chat_id)
            
    # Delete status waiting card
    try:
        await status_msg.delete()
    except Exception:
        pass
        
    if added_songs:
        if len(added_songs) == 1:
            song = added_songs[0]
            # If it was queued (meaning it is not the currently active song playing right now)
            is_currently_playing = (group_data["current_song"] and group_data["current_song"]["url"] == song["url"])
            if is_currently_playing and len(group_data["queue"]) == 0:
                pass
            else:
                queue_pos = len(group_data["queue"])
                await message.reply_text(
                    f"➕ <b>কিউতে যোগ করা হয়েছে!</b>\n\n"
                    f"🎵 <b>গান:</b> <code>{song['title']}</code>\n"
                    f"🔢 <b>অবস্থান:</b> <code>#{queue_pos}</code>\n"
                    f"👤 <b>অনুরোধকারী:</b> {song['requester_mention']}"
                )
        else:
            # Multiple songs added successfully
            summary_text = "➕ <b>একাধিক গান কিউতে যোগ করা হয়েছে!</b>\n\n"
            for idx, song in enumerate(added_songs, start=1):
                summary_text += f"<code>{idx}.</code> <a href='{song['url']}'>{song['title']}</a>\n"
            summary_text += f"\n👤 <b>অনুরোধকারী:</b> {user.mention if user else 'Unknown User'}"
            await message.reply_text(summary_text, disable_web_page_preview=True)
            
    if failed_songs:
        fail_text = "❌ <b>নিম্নলিখিত গানগুলো খুঁজে পাওয়া যায়নি:</b>\n\n"
        for idx, q in enumerate(failed_songs, start=1):
            fail_text += f"<code>{idx}.</code> <i>{q}</i>\n"
        await message.reply_text(fail_text)


@Client.on_message(filters.command("queue") & filters.group)
async def queue_command(client: Client, message: Message):
    if not client.me.is_bot:
        return
    """Displays the list of upcoming songs in the queue."""
    chat_id = message.chat.id
    
    if chat_id not in db_queue or not db_queue[chat_id]["current_song"]:
        return await message.reply_text("📭 <b>প্লে-লিস্ট খালি!</b> বর্তমানে কোনো গান চলছে না।")
        
    group_data = db_queue[chat_id]
    current = group_data["current_song"]
    queue_list = group_data["queue"]
    
    response = (
        f"🎧 <b>চলমান গান:</b>\n"
        f"👉 <a href='{current['url']}'>{current['title']}</a> "
        f"[অনুরোধ করেছেন: {current['requester']}]\n\n"
    )
    
    if queue_list:
        response += f"📋 <b>আপকামিং গানসমূহ ({len(queue_list)}):</b>\n"
        for idx, song in enumerate(queue_list[:10], start=1):
            response += f"<code>{idx}.</code> <a href='{song['url']}'>{song['title']}</a> [অনুরোধকারী: {song['requester']}]\n"
            
        if len(queue_list) > 10:
            response += f"\n<i>... এবং আরও {len(queue_list) - 10}টি গান কিউতে আছে!</i>"
    else:
        response += "📋 <i>আপকামিং কিউতে আর কোনো গান নেই।</i>"
        
    await message.reply_text(response, disable_web_page_preview=True)


@Client.on_message(filters.command("play") & filters.private)
async def play_private_command(client: Client, message: Message):
    if not client.me.is_bot:
        return
    """
    Handles the /play command in private chats.
    Warns the user that /play only works inside groups, and offers a button to add the bot to a group.
    """
    buttons = [
        [
            InlineKeyboardButton(
                "➕ Add Bot to Group ➕",
                url=f"https://t.me/{config.BOT_USERNAME}?startgroup=true"
            )
        ]
    ]
    await message.reply_text(
        "❌ <b>দুঃখিত!</b>\n\n"
        "<code>/play</code> কমান্ডটি শুধুমাত্র গ্রুপে কাজ করে। গ্রুপ ভয়েস চ্যাটে গান শুনতে প্রথমে আমাকে আপনার গ্রুপে এড করুন এবং গান প্লে করুন।",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
