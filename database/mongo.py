import logging
from motor.motor_asyncio import AsyncIOMotorClient
import config

logger = logging.getLogger("MusicBot.Database")

# Initialize MongoDB client asynchronously
try:
    if config.MONGO_URI:
        client = AsyncIOMotorClient(config.MONGO_URI)
        db = client["TelegramMusicBot"]
        users_col = db["users"]
        chats_col = db["chats"]
        logger.info("📡 Successfully established async connection to MongoDB.")
    else:
        client = None
        db = None
        users_col = None
        chats_col = None
        logger.warning("⚠️ MONGO_URI is not set. Database features (broadcasting, logging) are disabled.")
except Exception as e:
    client = None
    db = None
    users_col = None
    chats_col = None
    logger.error(f"❌ Failed to connect to MongoDB: {e}. Running without database support.")

# Database Helper Functions
async def is_db_connected() -> bool:
    """Checks if database is active and connected."""
    if db is None:
        return False
    try:
        # Ping database
        await db.command("ping")
        return True
    except Exception:
        return False

# User Management Functions
async def add_user(user_id: int, first_name: str, username: str = None):
    """Saves a new user to the database when they start the bot."""
    if users_col is None:
        return
    try:
        user_data = {
            "_id": user_id,
            "first_name": first_name,
            "username": username,
        }
        # upsert=True inserts if not exists, otherwise updates
        await users_col.update_one({"_id": user_id}, {"$set": user_data}, upsert=True)
    except Exception as e:
        logger.error(f"Error adding user {user_id} to database: {e}")

async def get_total_users() -> int:
    """Returns total number of registered users."""
    if users_col is None:
        return 0
    try:
        return await users_col.count_documents({})
    except Exception as e:
        logger.error(f"Error getting total users: {e}")
        return 0

async def get_all_users() -> list:
    """Returns a list of all registered user IDs."""
    if users_col is None:
        return []
    try:
        users = []
        async for user in users_col.find({}, {"_id": 1}):
            users.append(user["_id"])
        return users
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []

# Chat/Group Management Functions
async def add_chat(chat_id: int, chat_title: str):
    """Saves a new group chat to the database when the bot starts playing music there."""
    if chats_col is None:
        return
    try:
        chat_data = {
            "_id": chat_id,
            "title": chat_title,
        }
        await chats_col.update_one({"_id": chat_id}, {"$set": chat_data}, upsert=True)
    except Exception as e:
        logger.error(f"Error adding chat {chat_id} to database: {e}")

async def get_total_chats() -> int:
    """Returns total number of registered group chats."""
    if chats_col is None:
        return 0
    try:
        return await chats_col.count_documents({})
    except Exception as e:
        logger.error(f"Error getting total chats: {e}")
        return 0

async def get_all_chats() -> list:
    """Returns a list of all registered group chat IDs."""
    if chats_col is None:
        return []
    try:
        chats = []
        async for chat in chats_col.find({}, {"_id": 1}):
            chats.append(chat["_id"])
        return chats
    except Exception as e:
        logger.error(f"Error getting all chats: {e}")
        return []
