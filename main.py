import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import pyrogram.errors
if not hasattr(pyrogram.errors, "GroupcallForbidden"):
    class GroupcallForbidden(Exception):
        pass
    pyrogram.errors.GroupcallForbidden = GroupcallForbidden

import logging
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import Update

import config
from config import verify_config

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MusicBot.Main")

# 1. Initialize Bot Client (using Pyrogram plugin system)
bot_client = Client(
    name="MusicBot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    plugins=dict(root="handlers"),
    in_memory=True
)

# 2. Initialize Assistant Account User Client
assistant_client = Client(
    name="MusicAssistant",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING,
    in_memory=True
)

# 3. Initialize PyTgCalls with Assistant User Client
call_py = PyTgCalls(assistant_client)


# Register PyTgCalls Stream End Event Handler
from pytgcalls.types import StreamEnded

@call_py.on_update()
async def stream_end_callback(client: PyTgCalls, update: Update):
    """Event handler triggered automatically by PyTgCalls when the current stream track ends."""
    if isinstance(update, StreamEnded):
        chat_id = update.chat_id
        logger.info(f"🎵 Stream finished in group chat: {chat_id}. Transitioning to next queue item.")
        
        from handlers.play import play_next_song
        # Execute next song playing in queue
        await play_next_song(chat_id)


async def main():
    # Verify environment configurations
    try:
        verify_config()
    except ValueError as e:
        logger.error(e)
        return
        
    print("🚀 Bootstrapping Telegram Music Bot...")
    
    # Start bot
    await bot_client.start()
    bot_me = await bot_client.get_me()
    config.BOT_USERNAME = bot_me.username
    print(f"✅ Bot Client initialized as @{config.BOT_USERNAME}")
    
    # Start assistant account
    await assistant_client.start()
    assistant_me = await assistant_client.get_me()
    print(f"✅ Assistant User Client initialized as @{assistant_me.username or assistant_me.first_name}")
    
    # Share references with play handler
    from handlers.play import init_clients
    init_clients(call_py, bot_client)
    
    # Start PyTgCalls WebRTC streamer
    await call_py.start()
    print("✅ PyTgCalls voice engine established!")
    
    print("\n🎵 Telegram Music Bot is now completely ONLINE and listening for commands! 🚀🎧")
    
    # Keep standard thread active
    from pyrogram import idle
    await idle()
    
    # Graceful shutdown
    print("\n🛑 Shutting down services...")
    await bot_client.stop()
    await assistant_client.stop()
    print("👋 Goodbye!")


if __name__ == "__main__":
    # Standard event loop executor
    asyncio.run(main())
