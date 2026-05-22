import sys
import asyncio

# Setup the asyncio event loop before importing Pyrogram to prevent RuntimeError under Python 3.10+
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client

async def main():
    print("🤖 Pyrogram Session String Generator")
    print("-----------------------------------")
    
    api_id = input("Enter your API_ID (e.g. 12345): ").strip()
    api_hash = input("Enter your API_HASH: ").strip()
    
    if not api_id or not api_hash:
        print("❌ API_ID and API_HASH cannot be empty!")
        return
        
    try:
        api_id = int(api_id)
    except ValueError:
        print("❌ API_ID must be a number!")
        return

    print("\nStarting Pyrogram Client to generate session string...")
    async with Client(
        name="session_generator",
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True
    ) as app:
        session_str = await app.export_session_string()
        print("\n✨ SUCCESS! Here is your SESSION_STRING:\n")
        print(session_str)
        print("\nCopy this string and paste it in your .env file.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSession generation cancelled.")
