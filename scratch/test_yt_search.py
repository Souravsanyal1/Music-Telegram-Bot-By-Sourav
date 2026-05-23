import asyncio
import logging
from yt_dlp import YoutubeDL

logging.basicConfig(level=logging.INFO)

async def test_search():
    query = "Alan Walker Faded"
    print(f"Searching for: {query}")
    
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "geo_bypass": True,
        "extract_flat": "in_playlist",
    }
    
    loop = asyncio.get_event_loop()
    
    def search():
        with YoutubeDL(ydl_opts) as ydl:
            try:
                search_query = f"ytsearch1:{query}"
                info = ydl.extract_info(search_query, download=False)
                if not info or "entries" not in info:
                    print("No entries found")
                    return []
                
                songs = []
                entries = [e for e in info["entries"] if e is not None]
                for r in entries:
                    duration = int(r.get("duration", 0) or 0)
                    mins, secs = divmod(duration, 60)
                    songs.append({
                        "title": r.get("title"),
                        "url": r.get("url") or f"https://www.youtube.com/watch?v={r.get('id')}",
                        "duration": duration,
                        "uploader": r.get("uploader"),
                    })
                return songs
            except Exception as e:
                print(f"Extraction error: {e}")
                return []
                
    results = await loop.run_in_executor(None, search)
    print("Results:")
    for r in results:
        print(r)

if __name__ == "__main__":
    asyncio.run(test_search())
