import os
import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import logging

logger = logging.getLogger("MusicBot.Thumbnails")

def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Loads system fonts (supporting Windows paths) or falls back to default font."""
    font_name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        windir = os.environ.get("WINDIR", "C:\\Windows")
        font_path = os.path.join(windir, "Fonts", font_name)
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
        
        linux_fallbacks = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
        for path in linux_fallbacks:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
                
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def truncate_text(text: str, max_width: int, font: ImageFont.ImageFont) -> str:
    """Truncates text with ellipsis if it exceeds the max width in pixels."""
    if font.getlength(text) <= max_width:
        return text
        
    while len(text) > 0 and font.getlength(text + "...") > max_width:
        text = text[:-1]
    return text + "..."


async def generate_thumbnail(
    title: str,
    duration_str: str,
    thumbnail_url: str,
    requester_name: str,
    channel: str,
    output_filename: str = "thumbnail.png"
) -> str:
    """
    Generates a card matching the exact layout of the 2nd reference image:
    - Large circular album art in the top-center with a thick white border ring
    - Centered track name
    - Centered channel/artist metadata
    - Sleek horizontal progress seek bar with timestamps
    """
    temp_thumb = f"temp_{output_filename}"
    use_local = False
    
    # 1. Load or download the thumbnail artwork
    if thumbnail_url and os.path.exists(thumbnail_url):
        temp_thumb = thumbnail_url
        use_local = True
        logger.info(f"Using local file for card artwork: {thumbnail_url}")
    elif thumbnail_url and (thumbnail_url.startswith("http://") or thumbnail_url.startswith("https://")):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(thumbnail_url) as resp:
                    if resp.status == 200:
                        async with aiofiles.open(temp_thumb, mode="wb") as f:
                            await f.write(await resp.read())
                        logger.info("Successfully downloaded remote YouTube thumbnail.")
                    else:
                        logger.warning(f"Failed to fetch thumbnail ({resp.status}). Using fallback backdrop.")
                        temp_thumb = None
        except Exception as e:
            logger.error(f"Error downloading thumbnail: {e}")
            temp_thumb = None
    else:
        temp_thumb = None

    # Dimensions
    width, height = 1280, 720
    
    try:
        # Load source image or create fallback
        if temp_thumb and os.path.exists(temp_thumb):
            img_src = Image.open(temp_thumb)
        else:
            # Fallback red-gradient style base
            img_src = Image.new("RGB", (width, height), (50, 10, 15))
            
        # 3. Create Ambient Blurred Background
        bg = img_src.resize((width, height), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
        bg = bg.convert("RGBA")
        
        # Darkening overlay
        dark_overlay = Image.new("RGBA", (width, height), (15, 10, 15, 175))
        bg = Image.alpha_composite(bg, dark_overlay)
        
        # 4. Crop and Paste Perfect Circle (Center-Top)
        # Size of circular image: 360x360 px
        circle_size = 360
        thumb_resized = img_src.resize((circle_size, circle_size), Image.Resampling.LANCZOS)
        
        mask = Image.new("L", (circle_size, circle_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, circle_size, circle_size), fill=255)
        
        # Center-top coordinates: X = 460, Y = 70
        x_offset = (width - circle_size) // 2  # 460
        y_offset = 70
        bg.paste(thumb_resized, (x_offset, y_offset), mask=mask)
        
        # Draw high-fidelity white circular border ring
        draw = ImageDraw.Draw(bg)
        border_width = 10
        draw.ellipse(
            (
                x_offset - border_width // 2,
                y_offset - border_width // 2,
                x_offset + circle_size + border_width // 2,
                y_offset + circle_size + border_width // 2,
            ),
            outline=(255, 255, 255, 255),
            width=border_width,
        )
        
        # 5. Load Typography
        font_title = get_font(size=34, bold=True)
        font_meta = get_font(size=24, bold=False)
        font_time = get_font(size=20, bold=False)
        
        # 6. Render Song Title (Centered below circle)
        truncated_title = truncate_text(title, max_width=1100, font=font_title)
        title_w = font_title.getlength(truncated_title)
        draw.text(
            ((width - title_w) // 2, 460),
            truncated_title,
            fill=(255, 255, 255, 255),
            font=font_title
        )
        
        # 7. Render Channel/Artist details (Centered)
        meta_text = f"{channel} | Requested by {requester_name}"
        truncated_meta = truncate_text(meta_text, max_width=1100, font=font_meta)
        meta_w = font_meta.getlength(truncated_meta)
        draw.text(
            ((width - meta_w) // 2, 510),
            truncated_meta,
            fill=(230, 230, 230, 255),
            font=font_meta
        )
        
        # 8. Render Horizontal Seek Bar (Matches Reference Image)
        bar_x_start = 200
        bar_x_end = 1080
        bar_y = 580
        bar_width = bar_x_end - bar_x_start
        
        # Draw gray track line
        draw.line((bar_x_start, bar_y, bar_x_end, bar_y), fill=(160, 160, 160, 100), width=4)
        
        # Simulate active playhead progress (fixed 40% for visual design)
        progress_ratio = 0.40
        progress_x = bar_x_start + int(bar_width * progress_ratio)
        
        # Draw white active line
        draw.line((bar_x_start, bar_y, progress_x, bar_y), fill=(255, 255, 255, 255), width=4)
        
        # Draw white slider dot
        dot_r = 8
        draw.ellipse(
            (progress_x - dot_r, bar_y - dot_r, progress_x + dot_r, bar_y + dot_r),
            fill=(255, 255, 255, 255)
        )
        
        # Elapsed & Total timestamps underneath the bar
        elapsed_str = "00:00"
        try:
            parts = [int(p) for p in duration_str.split(":")]
            if len(parts) == 2:
                tot_sec = parts[0] * 60 + parts[1]
            elif len(parts) == 3:
                tot_sec = parts[0] * 3600 + parts[1] * 60 + parts[2]
            else:
                tot_sec = 240
            elapsed_sec = int(tot_sec * progress_ratio)
            el_min, el_sec = divmod(elapsed_sec, 60)
            elapsed_str = f"{el_min:02d}:{el_sec:02d}"
        except Exception:
            elapsed_str = "01:34"
            
        draw.text((bar_x_start, bar_y + 15), elapsed_str, fill=(230, 230, 230, 200), font=font_time)
        
        total_w = font_time.getlength(duration_str)
        draw.text((bar_x_end - total_w, bar_y + 15), duration_str, fill=(230, 230, 230, 200), font=font_time)
        
        # Save output
        bg.convert("RGB").save(output_filename, "PNG")
        logger.info(f"🎨 Generated circular user-reference player card: {output_filename}")
        
    except Exception as e:
        logger.error(f"Error compiling thumbnail image: {e}", exc_info=True)
        # Plain fallback
        fallback_img = Image.new("RGB", (width, height), (50, 10, 15))
        fallback_img.save(output_filename, "PNG")
        
    finally:
        if not use_local and temp_thumb and os.path.exists(temp_thumb):
            try:
                os.remove(temp_thumb)
            except Exception:
                pass
                
    return output_filename
