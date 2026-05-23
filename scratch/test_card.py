import asyncio
import os
import sys
from PIL import Image, ImageDraw

# Add current workspace to Python path to allow importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.thumbnails import generate_thumbnail

async def run_test():
    print("=== Starting player card design compilation verification tests ===")
    
    # 1. Setup paths
    output_yt = "test_card_youtube.png"
    output_local = "test_card_local.png"
    
    # Clean old test outputs if any
    for path in [output_yt, output_local, "bot_profile.png"]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
                
    # Create a dummy local profile photo for testing fallback scenario
    print("Creating a mock 'bot_profile.png' for testing...")
    mock_profile = Image.new("RGB", (400, 400), (147, 51, 234))
    draw_mock = ImageDraw.Draw(mock_profile)
    draw_mock.ellipse((50, 50, 350, 350), fill=(255, 255, 255))
    draw_mock.text((150, 180), "BOT", fill=(147, 51, 234))
    mock_profile.save("bot_profile.png")
    
    # 2. Test scenario A: YouTube thumbnail URL (Remote)
    print("Generating player card with remote YouTube thumbnail URL...")
    test_yt_url = "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
    try:
        await generate_thumbnail(
            title="Alan Walker - Faded (Remix & Extended Version 2026)",
            duration_str="04:20",
            thumbnail_url=test_yt_url,
            requester_name="Sourav Sanyal",
            channel="Alan Walker Music",
            output_filename=output_yt
        )
        if os.path.exists(output_yt):
            print(f"Success! Generated remote YouTube card: {os.path.abspath(output_yt)}")
        else:
            print("Failed to generate remote card (File does not exist).")
    except Exception as e:
        print(f"Error during remote card generation: {e}")
        import traceback
        traceback.print_exc()

    # 3. Test scenario B: Local profile fallback
    print("Generating player card with local profile photo fallback...")
    try:
        await generate_thumbnail(
            title="Bangla Classic Hits Medley - Lofi Mashup",
            duration_str="12:35",
            thumbnail_url="bot_profile.png",
            requester_name="Sourav",
            channel="Telegram Audio Library",
            output_filename=output_local
        )
        if os.path.exists(output_local):
            print(f"Success! Generated local fallback card: {os.path.abspath(output_local)}")
        else:
            print("Failed to generate local card (File does not exist).")
    except Exception as e:
        print(f"Error during local card generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
