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
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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
    Generates an ultra-premium glassmorphic player card dashboard.
    Supports dynamic local image fallback (e.g., bot profile photo) or remote HTTP downloads.
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

    # 2. Setup Dimensions
    width, height = 1280, 720
    
    try:
        # Load source image or create a fallback colorful gradient base
        if temp_thumb and os.path.exists(temp_thumb):
            img_src = Image.open(temp_thumb)
        else:
            # Fallback deep-indigo default canvas
            img_src = Image.new("RGB", (width, height), (22, 16, 45))
            
        # 3. Create Ambient Glow Background
        bg = img_src.resize((width, height), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
        bg = bg.convert("RGBA")
        
        # Darkening overlay to ensure metadata pops
        dark_overlay = Image.new("RGBA", (width, height), (10, 10, 18, 195))
        bg = Image.alpha_composite(bg, dark_overlay)
        
        # Draw high-fidelity neon ambient glow orbs behind the glass panel
        glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        # Left-top glowing cyan orb
        glow_draw.ellipse((50, -80, 500, 370), fill=(0, 229, 255, 90))
        # Right-bottom glowing purple orb
        glow_draw.ellipse((800, 380, 1250, 830), fill=(180, 120, 255, 90))
        
        # Apply heavy blur to orbs to make them dreamy and soft
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=65))
        bg = Image.alpha_composite(bg, glow_layer)
        
        # 4. Draw Center Frosted-Glass Card
        # Panel bounds: (80, 80) to (1200, 640) -> Width: 1120, Height: 560
        glass_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glass_draw = ImageDraw.Draw(glass_layer)
        
        glass_draw.rounded_rectangle(
            (80, 80, 1200, 640),
            radius=30,
            fill=(15, 15, 27, 215),  # Frosted glass core
            outline=(255, 255, 255, 38),  # Thin elegant white border
            width=2
        )
        bg = Image.alpha_composite(bg, glass_layer)
        
        # 5. Crop and Draw Rounded Square Album Artwork (Left Column)
        # Position: (130, 130) to (470, 470) -> Size: 340x340 px
        art_size = 340
        thumb_resized = img_src.resize((art_size, art_size), Image.Resampling.LANCZOS)
        
        # Rounded mask for artwork
        art_mask = Image.new("L", (art_size, art_size), 0)
        mask_draw = ImageDraw.Draw(art_mask)
        mask_draw.rounded_rectangle((0, 0, art_size, art_size), radius=28, fill=255)
        
        bg.paste(thumb_resized, (130, 130), mask=art_mask)
        
        # Draw high-fidelity double border for the album artwork
        draw = ImageDraw.Draw(bg)
        # Inner white trim
        draw.rounded_rectangle(
            (130, 130, 470, 470),
            radius=28,
            outline=(255, 255, 255, 100),
            width=2
        )
        # Outer vibrant glowing purple border
        draw.rounded_rectangle(
            (126, 126, 474, 474),
            radius=30,
            outline=(180, 120, 255, 200),
            width=3
        )
        
        # 6. Load Premium Typography
        font_title = get_font(size=38, bold=True)
        font_channel = get_font(size=22, bold=False)
        font_meta = get_font(size=20, bold=False)
        font_meta_bold = get_font(size=20, bold=True)
        font_time = get_font(size=18, bold=False)
        font_badge = get_font(size=14, bold=True)
        font_ctrl = get_font(size=26, bold=False)
        
        # 7. Render Metadata Interface (Right Column)
        # Column X alignment starts at 520, Y ranges from 130 to 590
        
        # A. Streaming Pill Badge
        badge_x1, badge_y1, badge_x2, badge_y2 = 520, 135, 690, 170
        draw.rounded_rectangle(
            (badge_x1, badge_y1, badge_x2, badge_y2),
            radius=18,
            fill=(180, 120, 255, 35),
            outline=(180, 120, 255, 180),
            width=1
        )
        draw.text((540, 143), "● NOW PLAYING", fill=(195, 145, 255, 255), font=font_badge)
        
        # B. Track Title
        truncated_title = truncate_text(title, max_width=610, font=font_title)
        draw.text((520, 190), truncated_title, fill=(255, 255, 255, 255), font=font_title)
        
        # C. Artist/Channel Info
        truncated_channel = truncate_text(f"by {channel}", max_width=610, font=font_channel)
        draw.text((520, 255), truncated_channel, fill=(0, 229, 255, 255), font=font_channel)
        
        # D. Horizontal Thin Divider Line
        draw.line((520, 305, 1150, 305), fill=(255, 255, 255, 25), width=1)
        
        # E. Metadata Row (Requester & Duration Side-By-Side)
        # Left side: Requester
        draw.text((520, 330), "Requester: ", fill=(200, 200, 220, 180), font=font_meta)
        req_lbl_w = font_meta.getlength("Requester: ")
        truncated_req = truncate_text(requester_name, max_width=220, font=font_meta_bold)
        draw.text((520 + req_lbl_w, 330), truncated_req, fill=(195, 145, 255, 255), font=font_meta_bold)
        
        # Right side: Duration
        dur_val_w = font_meta_bold.getlength(duration_str)
        dur_lbl_w = font_meta.getlength("Duration: ")
        draw.text((1150 - dur_val_w - dur_lbl_w, 330), "Duration: ", fill=(200, 200, 220, 180), font=font_meta)
        draw.text((1150 - dur_val_w, 330), duration_str, fill=(255, 255, 255, 255), font=font_meta_bold)
        
        # F. Seek bar progress track & dynamic values
        bar_x_start = 520
        bar_x_end = 1150
        bar_y = 415
        bar_width = bar_x_end - bar_x_start
        
        # Standard gray progress line
        draw.line((bar_x_start, bar_y, bar_x_end, bar_y), fill=(55, 55, 75, 255), width=6)
        
        # Simulate active track progress (fixed at 40% for visual design)
        progress_ratio = 0.40
        progress_x = bar_x_start + int(bar_width * progress_ratio)
        
        # Active vibrant purple highlight track
        draw.line((bar_x_start, bar_y, progress_x, bar_y), fill=(180, 120, 255, 255), width=6)
        
        # Sleek progress indicator dot
        dot_r = 8
        draw.ellipse(
            (progress_x - dot_r, bar_y - dot_r, progress_x + dot_r, bar_y + dot_r),
            fill=(255, 255, 255, 255),
            outline=(180, 120, 255, 255),
            width=2
        )
        
        # Calculate dynamic matching elapsed time based on progress_ratio (40%)
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
            el_hr, el_min = divmod(el_min, 60)
            if el_hr > 0:
                elapsed_str = f"{el_hr:02d}:{el_min:02d}:{el_sec:02d}"
            else:
                elapsed_str = f"{el_min:02d}:{el_sec:02d}"
        except Exception:
            elapsed_str = "01:34"
            
        # Draw Seek bar timestamps
        draw.text((bar_x_start, bar_y + 12), elapsed_str, fill=(160, 160, 180, 255), font=font_time)
        
        total_str_w = font_time.getlength(duration_str)
        draw.text((bar_x_end - total_str_w, bar_y + 12), duration_str, fill=(160, 160, 180, 255), font=font_time)
        
        # G. Premium Mock Deck Controls
        ctrl_text = "⏮     ▶     ⏭     🔁"
        ctrl_w = font_ctrl.getlength(ctrl_text)
        ctrl_x = bar_x_start + (bar_width - ctrl_w) // 2
        draw.text((ctrl_x, 485), ctrl_text, fill=(200, 200, 220, 220), font=font_ctrl)
        
        # 8. Save output file
        bg.convert("RGB").save(output_filename, "PNG")
        logger.info(f"🎨 Generated ultra-premium player card: {output_filename}")
        
    except Exception as e:
        logger.error(f"Error compiling thumbnail image: {e}", exc_info=True)
        # Create plain fallback visual
        fallback_img = Image.new("RGB", (width, height), (22, 16, 45))
        fallback_img.save(output_filename, "PNG")
        
    finally:
        # Clean up temporary downloaded file
        if not use_local and temp_thumb and os.path.exists(temp_thumb):
            try:
                os.remove(temp_thumb)
            except Exception:
                pass
                
    return output_filename
