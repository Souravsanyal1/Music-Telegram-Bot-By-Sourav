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

# Setup sys.path to include the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongo import is_db_connected, add_user, get_total_users

async def test():
    print("Testing MongoDB connection...")
    connected = await is_db_connected()
    print(f"MongoDB Ping connection status: {connected}")
    
    if connected:
        print("Getting total users...")
        try:
            total = await get_total_users()
            print(f"Total registered users: {total}")
            
            print("Testing add_user with dummy ID 999999...")
            await add_user(999999, "Test User", "test_user_dummy")
            print("✅ Successfully added/updated dummy user in MongoDB!")
        except Exception as e:
            print(f"❌ Database operation failed: {e}")
    else:
        print("❌ MongoDB is NOT connected/pingable!")

if __name__ == "__main__":
    asyncio.run(test())
