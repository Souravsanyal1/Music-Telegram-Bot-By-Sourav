import asyncio
import os
import sys

# Add current workspace to Python path to allow importing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.downloaders import search_youtube, extract_audio_stream

async def run_test():
    query = "\u09a4\u09be\u09ae\u09be\u0995 \u09aa\u09be\u09a4\u09be" # Bengali query 'তামাক পাতা'
    print("Searching YouTube for Bengali query...")
    results = await search_youtube(query, limit=1)
    if not results:
        print("Search failed to return any results.")
        return
        
    song = results[0]
    print("\n--- Search Result ---")
    print(f"Title length: {len(song['title'])}")
    print(f"URL: {song['url']}")
    print(f"Duration: {song['duration_str']} ({song['duration']} sec)")
    
    print("\nExtracting audio stream...")
    extracted = await extract_audio_stream(song['url'])
    if extracted and "error" not in extracted:
        print("--- Extraction Succeeded ---")
        print(f"Stream URL starts with: {extracted['stream_url'][:80]}...")
        print(f"Duration: {extracted['duration_str']}")
    else:
        print("--- Extraction Failed ---")
        if extracted:
            print(f"Error detail: {extracted.get('error')}")

if __name__ == "__main__":
    asyncio.run(run_test())
