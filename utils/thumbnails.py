import os
import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import logging

logger = logging.getLogger("MusicBot.Thumbnails")

# Helper to load system font or fallback gracefully
def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Loads system fonts (supporting Windows paths) or falls back to default font."""
    font_name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        # Check standard Windows directory
        windir = os.environ.get("WINDIR", "C:\\Windows")
        font_path = os.path.join(windir, "Fonts", font_name)
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
        
        # Check linux/unix fallback paths just in case of VPS deployments
        linux_fallbacks = [
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
        for path in linux_fallbacks:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
                
        # Default fallback
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
    Downloads the YouTube video thumbnail, applies a premium dark blurred glassmorphism overlay,
    crops a circular profile card in the center with a high-fidelity white border ring, and draws
    polished music player metadata and progress bar.
    """
    temp_thumb = f"temp_{output_filename}"
    
    # 1. Download YouTube thumbnail asynchronously
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail_url) as resp:
                if resp.status == 200:
                    async with aiofiles.open(temp_thumb, mode="wb") as f:
                        await f.write(await resp.read())
                else:
                    logger.warning(f"Failed to fetch thumbnail ({resp.status}). Using fallback backdrop.")
                    temp_thumb = None
    except Exception as e:
        logger.error(f"Error downloading thumbnail: {e}")
        temp_thumb = None

    # 2. Setup Base Images
    # Canvas Size: 1280x720 (Standard 720p HD Card)
    width, height = 1280, 720
    
    try:
        if temp_thumb and os.path.exists(temp_thumb):
            img_src = Image.open(temp_thumb)
        else:
            # Fallback aesthetic dark-purple canvas
            img_src = Image.new("RGB", (width, height), (32, 10, 50))
            
        # 3. Create Blurred Glassmorphism Backdrop
        # Resize source image to fill canvas, crop, and apply heavy Gaussian Blur
        bg = img_src.resize((width, height), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=25))
        
        # Draw semi-transparent dark overlay to enhance text readability
        overlay = Image.new("RGBA", (width, height), (15, 10, 20, 160))
        bg = bg.convert("RGBA")
        bg = Image.alpha_composite(bg, overlay)
        
        # 4. Create Circular Cropped Album/Video Art
        # Size of circular image: 340x340 px
        circle_size = 340
        thumb_resized = img_src.resize((circle_size, circle_size), Image.Resampling.LANCZOS)
        
        # Generate alpha mask for perfect circle
        mask = Image.new("L", (circle_size, circle_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, circle_size, circle_size), fill=255)
        
        # Crop and paste circle in center-top: (1280 - 340) // 2 = 470
        x_offset = (width - circle_size) // 2 # 470
        y_offset = 60
        
        bg.paste(thumb_resized, (x_offset, y_offset), mask=mask)
        
        # Draw high-fidelity white circular border ring
        draw = ImageDraw.Draw(bg)
        border_width = 8
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
        
        # 5. Load Premium Typography
        font_title = get_font(size=36, bold=True)
        font_meta = get_font(size=24, bold=False)
        font_bold = get_font(size=24, bold=True)
        
        # 6. Render Song Metadata
        # Truncate Title to fit within safe bounds
        truncated_title = truncate_text(title, max_width=1000, font=font_title)
        
        # Center-align Title Text
        title_width = font_title.getlength(truncated_title)
        draw.text(
            ((width - title_width) // 2, 430),
            truncated_title,
            fill=(255, 255, 255, 255),
            font=font_title,
        )
        
        # Channel/Artist info
        truncated_channel = truncate_text(f"by {channel}", max_width=800, font=font_meta)
        channel_width = font_meta.getlength(truncated_channel)
        draw.text(
            ((width - channel_width) // 2, 480),
            truncated_channel,
            fill=(200, 200, 220, 255),
            font=font_meta,
        )

        # "Duration" and "Requested By" aligned side-by-side or stacked cleanly
        req_text = f"Requested By: "
        req_val = f"{requester_name}"
        dur_text = f"Duration: "
        dur_val = f"{duration_str}"
        
        # Draw bottom-left: Requested by
        draw.text((100, 540), req_text, fill=(230, 230, 250, 200), font=font_meta)
        req_text_width = font_meta.getlength(req_text)
        draw.text((100 + req_text_width, 540), req_val, fill=(195, 145, 255, 255), font=font_bold)
        
        # Draw bottom-right: Duration
        dur_full_text = f"{dur_text}{dur_val}"
        dur_width = font_bold.getlength(dur_full_text)
        draw.text((width - 100 - dur_width, 540), dur_text, fill=(230, 230, 250, 200), font=font_meta)
        dur_label_width = font_meta.getlength(dur_text)
        draw.text((width - 100 - dur_width + dur_label_width, 540), dur_val, fill=(255, 255, 255, 255), font=font_bold)
        
        # 7. Render Aesthetics Audio Progress Bar
        bar_x_start = 100
        bar_x_end = width - 100 # 1180
        bar_y = 610
        bar_width = bar_x_end - bar_x_start # 1080
        
        # Base bar (gray track)
        draw.line((bar_x_start, bar_y, bar_x_end, bar_y), fill=(100, 100, 110, 255), width=6)
        
        # progress simulated at 40% for visual flavor
        progress_ratio = 0.40
        progress_x = bar_x_start + int(bar_width * progress_ratio)
        
        # Played bar (purple/white progress track)
        draw.line((bar_x_start, bar_y, progress_x, bar_y), fill=(180, 120, 255, 255), width=6)
        
        # Progress Dot "O" circle overlay
        dot_radius = 8
        draw.ellipse(
            (progress_x - dot_radius, bar_y - dot_radius, progress_x + dot_radius, bar_y + dot_radius),
            fill=(255, 255, 255, 255),
            outline=(180, 120, 255, 255),
            width=2,
        )
        
        # Left timestamp (elapsed)
        elapsed_str = "01:34"
        draw.text((bar_x_start, bar_y + 15), elapsed_str, fill=(180, 180, 200, 255), font=font_meta)
        
        # Right timestamp (total duration)
        draw.text((bar_x_end - font_meta.getlength(duration_str), bar_y + 15), duration_str, fill=(180, 180, 200, 255), font=font_meta)
        
        # 8. Save output
        bg.convert("RGB").save(output_filename, "PNG")
        logger.info(f"🎨 Successfully generated beautiful thumbnail card: {output_filename}")
        
    except Exception as e:
        logger.error(f"Error compiling thumbnail image: {e}", exc_info=True)
        # Create a simple emergency visual
        fallback_img = Image.new("RGB", (width, height), (32, 10, 50))
        fallback_img.save(output_filename, "PNG")
        
    finally:
        # Cleanup temporary downloaded image
        if temp_thumb and os.path.exists(temp_thumb):
            try:
                os.remove(temp_thumb)
            except Exception:
                pass
                
    return output_filename
