import asyncio
import sys
import os

# Setup event loop first to avoid Pyrogram sync.py RuntimeError on Python 3.12+
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Hotpatch get_peer_type before importing pyrogram
import pyrogram.utils

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

# Setup sys.path to include the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyrogram import Client
import config
from handlers.start import check_force_sub

async def test():
    print("Starting Assistant Client to test check_force_sub...")
    assistant = Client(
        name="TestAssistant",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=config.SESSION_STRING,
        in_memory=True
    )
    
    await assistant.start()
    
    user_id = 6427121076 # User's ID
    print(f"\nTesting check_force_sub for user {user_id}...")
    try:
        result = await check_force_sub(assistant, user_id)
        print(f"Result of check_force_sub: {result}")
    except Exception as e:
        print(f"❌ check_force_sub raised an exception: {e}")
        
    await assistant.stop()
    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(test())
