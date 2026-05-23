import asyncio
import logging
import os
from yt_dlp import YoutubeDL

logger = logging.getLogger("MusicBot.Downloader")

def clean_query(query: str) -> str:
    """Removes hashtags, mentions, and cleans up extra whitespace."""
    if not query:
        return ""
    cleaned = query.replace("#", " ").replace("@", " ")
    return " ".join(cleaned.split())


async def search_youtube(query: str, limit: int = 1) -> list:
    """
    Asynchronously searches YouTube for a given query and parses metadata using yt-dlp.
    Returns a list of song dictionaries.
    """
    query = clean_query(query)
    if not query:
        return []
        
    loop = asyncio.get_event_loop()
    
    def search():
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "geo_bypass": True,
            "extract_flat": "in_playlist",
            "cookiefile": "cookies.txt" if os.path.exists("cookies.txt") else None,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            try:
                search_query = f"ytsearch{limit}:{query}"
                info = ydl.extract_info(search_query, download=False)
                if not info or "entries" not in info:
                    logger.warning(f"No search results found for query: {query}")
                    return []
                
                songs = []
                entries = [e for e in info["entries"] if e is not None]
                for r in entries[:limit]:
                    duration = int(r.get("duration", 0) or 0)
                    mins, secs = divmod(duration, 60)
                    hrs, mins = divmod(mins, 60)
                    if hrs > 0:
                        duration_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
                    else:
                        duration_str = f"{mins:02d}:{secs:02d}"
                        
                    songs.append({
                        "title": r.get("title", "Unknown Title"),
                        "duration": duration,
                        "duration_str": duration_str,
                        "thumbnail": r.get("thumbnail") or (r.get("thumbnails")[0]["url"] if r.get("thumbnails") else None),
                        "url": r.get("url") or f"https://www.youtube.com/watch?v={r.get('id')}",
                        "channel": r.get("uploader", "Unknown Channel"),
                    })
                return songs
            except Exception as e:
                logger.error(f"yt-dlp search error for '{query}': {e}", exc_info=True)
                return []
 
    return await loop.run_in_executor(None, search)


async def extract_audio_stream(url: str) -> dict:
    """
    Asynchronously extracts direct streaming URLs and detailed metadata from a YouTube/YouTube Music video URL.
    Returns a song dictionary containing stream_url, title, duration, and channel.
    """
    loop = asyncio.get_event_loop()
    
    def extract():
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "geo_bypass": True,
            # If cookies.txt exists in the working directory, use it to bypass age restrictions
            "cookiefile": "cookies.txt" if os.path.exists("cookies.txt") else None,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if not info:
                    logger.error(f"Failed to extract info from URL: {url}")
                    return None
                
                # If playlist or multi-entry, extract the first entry
                if "entries" in info:
                    entries = [e for e in info["entries"] if e is not None]
                    if not entries:
                        return None
                    video = entries[0]
                else:
                    video = info
                
                # Locate direct streaming URL
                stream_url = video.get("url")
                if not stream_url and "formats" in video:
                    # Look for pure audio format
                    for f in video["formats"]:
                        if f.get("acodec") != "none" and f.get("vcodec") == "none":
                            stream_url = f.get("url")
                            break
                    if not stream_url:
                        # Fallback to the first format
                        stream_url = video["formats"][0].get("url")
                
                if not stream_url:
                    logger.error(f"Could not extract streaming audio URL from: {url}")
                    return None
                
                duration = int(video.get("duration", 0))
                # Format duration into MM:SS
                mins, secs = divmod(duration, 60)
                hrs, mins = divmod(mins, 60)
                if hrs > 0:
                    duration_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
                else:
                    duration_str = f"{mins:02d}:{secs:02d}"

                return {
                    "title": video.get("title", "Unknown Title"),
                    "duration": duration,
                    "duration_str": duration_str,
                    "thumbnail": video.get("thumbnail"),
                    "stream_url": stream_url,
                    "url": video.get("webpage_url", url),
                    "channel": video.get("uploader", "Unknown Channel"),
                }
            except Exception as e:
                logger.error(f"yt-dlp extraction error for URL '{url}': {e}", exc_info=True)
                return None

    return await loop.run_in_executor(None, extract)
