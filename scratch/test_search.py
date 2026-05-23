import asyncio
import logging
from youtubesearchpython import VideosSearch

logging.basicConfig(level=logging.INFO)

async def test():
    query = "Alan Walker Faded"
    print(f"Searching for: {query}")
    try:
        search_obj = VideosSearch(query, limit=1)
        result = search_obj.result()
        print("Search Result:")
        print(result)
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test())
