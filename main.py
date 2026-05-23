import sys
# Avoid UnicodeEncodeError on Windows terminal when printing emojis
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

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

import pyrogram.utils

# Dynamic hotpatch to support expanded Telegram Chat/Channel IDs
def custom_get_peer_type(peer_id: int) -> str:
    if peer_id < 0:
        if peer_id <= -1000000000000:
            return "channel"
        else:
            return "chat"
    elif 0 < peer_id:
        return "user"
    raise ValueError(f"Peer id invalid: {peer_id}")

pyrogram.utils.get_peer_type = custom_get_peer_type
pyrogram.utils.MIN_CHANNEL_ID = -100999999999999
pyrogram.utils.MIN_CHAT_ID = -99999999999999

# Dynamic hotpatch to force port 80 for production MTProto connections
import pyrogram.session.internals.data_center
original_data_center_new = pyrogram.session.internals.data_center.DataCenter.__new__

def custom_data_center_new(cls, dc_id: int, test_mode: bool, ipv6: bool, media: bool):
    ip, port = original_data_center_new(cls, dc_id, test_mode, ipv6, media)
    if not test_mode:
        port = 80
    return ip, port

pyrogram.session.internals.data_center.DataCenter.__new__ = custom_data_center_new

import logging
from pyrogram import Client, ContinuePropagation
from pytgcalls import PyTgCalls, filters
from pytgcalls.types import Update

import config
from config import verify_config

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MusicBot.Main")

# Declare global client references (will be instantiated inside the active event loop in main())
bot_client = None
assistant_client = None
call_py = None

async def log_all_messages(client, message):
    logger.info(f"✨ DIRECT MESSAGE RECEIVED: {message.text or '[Media/None]'} from {message.from_user.id if message.from_user else 'unknown'}")
    raise ContinuePropagation


from pytgcalls.types import StreamEnded

async def stream_end_callback(client: PyTgCalls, update: Update):
    """Event handler triggered automatically by PyTgCalls when the current stream track ends."""
    if isinstance(update, StreamEnded):
        chat_id = update.chat_id
        logger.info(f"🎵 Stream finished in group chat: {chat_id}. Transitioning to next queue item.")
        
        from handlers.play import play_next_song
        # Execute next song playing in queue
        await play_next_song(chat_id)


async def ensure_assistant_online() -> bool:
    global assistant_client, call_py, bot_client
    if assistant_client and assistant_client.is_connected and call_py and call_py.is_running:
        return True

    logger.info("⏳ Ensuring Assistant Client and Voice Engine are online (lazy bootstrap)...")
    
    import os
    workdir = os.path.dirname(os.path.abspath(__file__))
    
    if not assistant_client:
        assistant_client = Client(
            name="MusicAssistant",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=config.SESSION_STRING,
            in_memory=False,
            workdir=workdir
        )
        
    if not assistant_client.is_connected:
        try:
            await assistant_client.start()
            logger.info("✅ Assistant Client started successfully!")
        except pyrogram.errors.AuthKeyUnregistered:
            logger.error("❌ Assistant Client Session String has expired or is unregistered!")
            assistant_client = None
            return False
        except pyrogram.errors.AuthKeyDuplicated:
            logger.warning("❌ Assistant Client has duplicate session active. Waiting 32 seconds for old Render container to terminate...")
            await asyncio.sleep(32)
            try:
                await assistant_client.start()
                logger.info("✅ Assistant Client started successfully after retry!")
            except Exception as e:
                logger.error(f"❌ Assistant Client failed to start after duplicate retry: {e}")
                assistant_client = None
                return False
        except Exception as e:
            logger.error(f"❌ Failed to start Assistant Client: {e}")
            assistant_client = None
            return False
            
    if not call_py:
        call_py = PyTgCalls(assistant_client)
        call_py.on_update(filters.stream_end())(stream_end_callback)
        
    if not call_py.is_running:
        try:
            await call_py.start()
            logger.info("✅ PyTgCalls voice engine established!")
        except Exception as e:
            logger.error(f"❌ Failed to start PyTgCalls engine: {e}")
            call_py = None
            return False
            
    from handlers.play import init_clients
    init_clients(call_py, bot_client, assistant_client)
    return True


async def main():
    global bot_client, assistant_client, call_py

    # Verify environment configurations
    try:
        verify_config()
    except ValueError as e:
        logger.error(e)
        return
        
    # Start health check server if PORT is provided (for Render / Heroku compatibility)
    import os
    port = os.getenv("PORT")
    if port:
        try:
            from aiohttp import web
            async def health_check(request):
                return web.Response(text="Bot is running!")
            app = web.Application()
            app.router.add_get("/", health_check)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", int(port))
            await site.start()
            print(f"✅ Web health check server started on port {port}")
        except Exception as e:
            print(f"⚠️ Failed to start health check server: {e}")

    print("🚀 Instantiating Telegram Clients within the active event loop...")
    
    import os
    workdir = os.path.dirname(os.path.abspath(__file__))

    # 1. Initialize Bot Client inside the loop to avoid loop mismatch issues
    bot_client = Client(
        name="MusicBot",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        bot_token=config.BOT_TOKEN,
        plugins=dict(root="handlers"),
        in_memory=False,
        workdir=workdir
    )
    
    # Register dynamic messaging logging handler
    from pyrogram.handlers import MessageHandler
    bot_client.add_handler(MessageHandler(log_all_messages), group=-1)

    # 2. Initialize Assistant Account User Client inside the loop
    assistant_client = Client(
        name="MusicAssistant",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=config.SESSION_STRING,
        in_memory=False,
        workdir=workdir
    )

    print("🚀 Bootstrapping Telegram Music Bot...")
    
    # Start bot with automatic FloodWait retry
    while True:
        try:
            await bot_client.start()
            break
        except pyrogram.errors.FloodWait as e:
            print(f"⚠️ Telegram returned FLOOD_WAIT for Bot Client. Sleeping for {e.value} seconds before retrying...")
            await asyncio.sleep(e.value + 2)
            
    bot_me = await bot_client.get_me()
    config.BOT_USERNAME = bot_me.username
    print(f"✅ Bot Client initialized as @{config.BOT_USERNAME}")
    
    # Attempt to start the Assistant Client on boot (will lazy load on-demand if it fails or overlaps)
    if config.SESSION_STRING:
        try:
            await ensure_assistant_online()
        except Exception as e:
            print(f"⚠️ Initial Assistant boot deferred: {e}")
    else:
        print("⚠️ SESSION_STRING is empty. Assistant Client will not be started.")
        from handlers.play import init_clients
        init_clients(None, bot_client, None)
    
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
