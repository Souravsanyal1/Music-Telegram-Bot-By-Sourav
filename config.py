import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# Mandatory API credentials from my.telegram.org
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# Bot token from @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Pyrogram Session String for Assistant account
SESSION_STRING = os.getenv("SESSION_STRING")

# MongoDB connection string
MONGO_URI = os.getenv("MONGO_URI")

# Sudo users (admins) who can control playback and broadcast globally
SUDO_USERS = [int(x) for x in os.getenv("SUDO_USERS", "").split(",") if x.strip().isdigit()]

# Default Bot Username (will be resolved dynamically on boot)
BOT_USERNAME = os.getenv("BOT_USERNAME", "TelegramMusicBot")

# Force Join Channel (Optional, username with/without @ or direct chat ID)
FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL")
if FORCE_SUB_CHANNEL:
    FORCE_SUB_CHANNEL = FORCE_SUB_CHANNEL.strip()
    if FORCE_SUB_CHANNEL.startswith("-") and FORCE_SUB_CHANNEL[1:].isdigit():
        FORCE_SUB_CHANNEL = int(FORCE_SUB_CHANNEL)
    elif FORCE_SUB_CHANNEL.isdigit():
        FORCE_SUB_CHANNEL = int(FORCE_SUB_CHANNEL)

# Custom Invite Link for Private Groups/Channels (Optional)
FORCE_SUB_LINK = os.getenv("FORCE_SUB_LINK")

# Force Sub Group (Optional second requirement)
FORCE_SUB_GROUP = os.getenv("FORCE_SUB_GROUP")
if FORCE_SUB_GROUP:
    FORCE_SUB_GROUP = FORCE_SUB_GROUP.strip()
    if FORCE_SUB_GROUP.startswith("-") and FORCE_SUB_GROUP[1:].isdigit():
        FORCE_SUB_GROUP = int(FORCE_SUB_GROUP)
    elif FORCE_SUB_GROUP.isdigit():
        FORCE_SUB_GROUP = int(FORCE_SUB_GROUP)

FORCE_SUB_GROUP_LINK = os.getenv("FORCE_SUB_GROUP_LINK")

# Sane checks to help user debug missing configs on boot
def verify_config():
    missing = []
    if not API_ID:
        missing.append("API_ID")
    if not API_HASH:
        missing.append("API_HASH")
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not SESSION_STRING:
        missing.append("SESSION_STRING")
    if not MONGO_URI:
        missing.append("MONGO_URI")
        
    if missing:
        raise ValueError(
            f"❌ Critical environment variables are missing: {', '.join(missing)}\n"
            f"Please create a .env file or export them in your environment."
        )

# Parse API_ID to integer safely
if API_ID and str(API_ID).isdigit():
    API_ID = int(API_ID)
