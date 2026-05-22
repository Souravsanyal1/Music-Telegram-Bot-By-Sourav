import asyncio
import logging
import os
from yt_dlp import YoutubeDL
from youtubesearchpython import VideosSearch

logger = logging.getLogger("MusicBot.Downloader")

async def search_youtube(query: str, limit: int = 1) -> list:
    """
    Asynchronously searches YouTube for a given query and parses metadata.
    Returns a list of song dictionaries.
    """
    loop = asyncio.get_event_loop()
    
    def search():
        try:
            search_obj = VideosSearch(query, limit=limit)
            result = search_obj.result()
            if not result or not result.get("result"):
                logger.warning(f"No search results found for query: {query}")
                return []
            
            songs = []
            for r in result["result"]:
                duration_str = r.get("duration", "0:00")
                if not duration_str:
                    duration_str = "0:00"
                parts = duration_str.split(":")
                duration = 0
                try:
                    if len(parts) == 2:
                        duration = int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:
                        duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                except ValueError:
                    duration = 0
                
                thumbnails = r.get("thumbnails", [])
                thumb_url = thumbnails[0].get("url") if thumbnails else None
                
                songs.append({
                    "title": r.get("title", "Unknown Title"),
                    "duration": duration,
                    "duration_str": duration_str,
                    "thumbnail": thumb_url,
                    "url": r.get("link"),
                    "channel": r.get("channel", {}).get("name", "Unknown Channel"),
                })
            return songs
        except Exception as e:
            logger.error(f"YouTube search error for '{query}': {e}", exc_info=True)
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
