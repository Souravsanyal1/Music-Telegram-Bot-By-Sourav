import asyncio

# Setup the asyncio event loop before importing Pyrogram to prevent RuntimeError on newer Python versions
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client

API_ID = 35441827
API_HASH = "0a33260aa2d0a4f789c7497adfdcd33f"

with Client(
    name="session_generator",
    api_id=API_ID,
    api_hash=API_HASH,
    in_memory=True
) as app:
    print("\nSESSION_STRING:\n")
    print(app.export_session_string())
