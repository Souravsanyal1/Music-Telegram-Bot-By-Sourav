import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client

async def main():
    try:
        api_id = int(input("🔑 Enter your API_ID (from my.telegram.org): "))
        api_hash = input("🔑 Enter your API_HASH (from my.telegram.org): ")
        
        print("\n⏳ Connecting to Telegram...")
        async with Client("session_generator", api_id=api_id, api_hash=api_hash, in_memory=True) as app:
            print("\n👇 Copy this complete Session String:")
            print(await app.export_session_string())
            print("👆 Copy the whole string carefully!\n")
    except ValueError:
        print("\n❌ Error: API_ID must be a valid integer.")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
