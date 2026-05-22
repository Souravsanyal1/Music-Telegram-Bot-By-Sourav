import os
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
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

# Reference to the PyTgCalls instance and Bot Client (assigned dynamically on boot in main.py)
pytgcalls_client: PyTgCalls = None
bot_client: Client = None

def init_clients(py_calls: PyTgCalls, bot: Client):
    """Initializes global references to clients from main.py."""
    global pytgcalls_client, bot_client
    pytgcalls_client = py_calls
    bot_client = bot


async def play_next_song(chat_id: int):
    """Fetches the next song in queue, plays it, and updates player UI."""
    if chat_id not in db_queue:
        return
        
    group_data = db_queue[chat_id]
    
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
        
    # Extract Direct Audio Stream Link
    extracted_data = await extract_audio_stream(song_data["url"])
    if not extracted_data:
        if status_msg:
            await status_msg.edit("❌ <b>দুঃখিত!</b> এই গানটি এক্সট্র্যাক্ট করা যায়নি। পরের গানটি লোড করা হচ্ছে...")
        # Try playing next
        group_data["current_song"] = None
        await play_next_song(chat_id)
        return

    # Dynamic Card Generation
    thumb_path = f"thumb_{chat_id}.png"
    await generate_thumbnail(
        title=extracted_data["title"],
        duration_str=extracted_data["duration_str"],
        thumbnail_url=extracted_data["thumbnail"],
        requester_name=song_data["requester"],
        channel=extracted_data["channel"],
        output_filename=thumb_path
    )
    
    # Stream in Voice Chat using PyTgCalls
    try:
        await pytgcalls_client.play(chat_id, MediaStream(extracted_data["stream_url"], video_flags=MediaStream.Flags.IGNORE))
        active_calls.add(chat_id)
    except Exception as e:
        logger.error(f"PyTgCalls streaming failed for {chat_id}: {e}")
        if status_msg:
            await status_msg.edit(f"❌ <b>ভয়েস চ্যাটে স্ট্রিম শুরু করতে ব্যর্থ হয়েছে!</b>\n\n<i>নিশ্চিত করুন অ্যাসিস্ট্যান্ট অ্যাকাউন্টটি চ্যাটে যুক্ত আছে এবং কথা বলার পারমিশন আছে।</i>")
        return

    # Delete waiting message
    if status_msg:
        await status_msg.delete()

    # Send Player UI Card
    if bot_client and os.path.exists(thumb_path):
        caption_text = (
            f"⚡ <b>স্ট্রিমিং শুরু হয়েছে!</b>\n\n"
            f"🎵 <b>নাম:</b> <a href='{song_data['url']}'>{extracted_data['title']}</a>\n"
            f"⏱ <b>সময়কাল:</b> <code>{extracted_data['duration_str']}</code> মিনিট\n"
            f"🎙 <b>চ্যানেল:</b> <code>{extracted_data['channel']}</code>\n"
            f"👤 <b>অনুরোধকারী:</b> {song_data['requester_mention']}\n\n"
            f"🎧 <i>গ্রুপ ভয়েস চ্যাটে গান চলছে!</i>"
        )
        try:
            sent_msg = await bot_client.send_photo(
                chat_id,
                photo=thumb_path,
                caption=caption_text,
                reply_markup=get_player_buttons(is_paused=False, is_looping=group_data["is_looping"])
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
    """
    Handles the /play command in groups.
    Supports YouTube URLs, YouTube Music, and direct query searches.
    Manages voice chat auto-join and queues.
    """
    chat_id = message.chat.id
    user = message.from_user
    
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ <b>কমান্ডটি অসম্পূর্ণ!</b>\n\n"
            "গানের নাম অথবা YouTube লিংক দিন।\n"
            "যেমন: <code>/play Alan Walker Faded</code>\n"
            "অথবা: <code>/play https://youtu.be/dQw4w9WgXcQ</code>"
        )
        
    query = " ".join(message.command[1:])
    
    # Save active chat details to MongoDB database asynchronously
    await add_chat(chat_id, message.chat.title)
    
    # Initial status message
    status_msg = await message.reply_text("🔍 <b>ইউটিউবে খোঁজা হচ্ছে...</b> দয়া করে অপেক্ষা করুন।")
    
    song_info = None
    # Check if query is a YouTube URL
    if "youtube.com/" in query or "youtu.be/" in query:
        # Direct URL extraction
        extracted = await extract_audio_stream(query)
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
        results = await search_youtube(query, limit=1)
        if results:
            song_info = results[0]
            
    if not song_info:
        return await status_msg.edit("❌ <b>দুঃখিত!</b> আপনার কাঙ্ক্ষিত গানটি খুঁজে পাওয়া যায়নি।")
        
    # Append requester details
    song_info["requester"] = user.first_name if user else "Unknown User"
    song_info["requester_mention"] = user.mention if user else "Unknown User"
    
    # Setup queue for this group if not already present
    if chat_id not in db_queue:
        db_queue[chat_id] = {
            "queue": [],
            "is_looping": False,
            "current_song": None,
            "active_msg_id": None
        }
        
    group_data = db_queue[chat_id]
    
    # Check if a song is already playing in the voice chat
    if chat_id in active_calls or group_data["current_song"] is not None:
        # Add to queue
        group_data["queue"].append(song_info)
        queue_pos = len(group_data["queue"])
        await status_msg.delete()
        await message.reply_text(
            f"➕ <b>কিউতে যোগ করা হয়েছে!</b>\n\n"
            f"🎵 <b>গান:</b> <code>{song_info['title']}</code>\n"
            f"🔢 <b>অবস্থান:</b> <code>#{queue_pos}</code>\n"
            f"👤 <b>অনুরোধকারী:</b> {song_info['requester_mention']}"
        )
    else:
        # Start playback directly
        await status_msg.delete()
        group_data["current_song"] = song_info
        await play_next_song(chat_id)


@Client.on_message(filters.command("queue") & filters.group)
async def queue_command(client: Client, message: Message):
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
