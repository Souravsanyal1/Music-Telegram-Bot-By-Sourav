from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import config

def get_start_buttons(bot_username: str) -> InlineKeyboardMarkup:
    """Returns a beautiful inline keyboard for the bot start greeting."""
    buttons = [
        [
            InlineKeyboardButton(
                "➕ Add Bot to Group ➕",
                url=f"https://t.me/{bot_username}?startgroup=true"
            )
        ],
        [
            InlineKeyboardButton("🌐 Support Channel", url="https://t.me/telegram"),
            InlineKeyboardButton("🛠 Creator", url="https://t.me/telegram")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def get_player_buttons(is_paused: bool = False, is_looping: bool = False) -> InlineKeyboardMarkup:
    """
    Returns the interactive inline audio deck matching premium players:
    [ ⏸ / ▶️ ] [ 🔁 ] [ ⏭ Skip ] [ ⏹ Stop ]
    """
    pause_play_btn = (
        InlineKeyboardButton("▶️ Resume", callback_data="c_resume") if is_paused
        else InlineKeyboardButton("⏸ Pause", callback_data="c_pause")
    )
    
    loop_btn = (
        InlineKeyboardButton("🔁 Loop On", callback_data="c_unloop") if is_looping
        else InlineKeyboardButton("🔁 Loop Off", callback_data="c_loop")
    )
    
    buttons = [
        [
            pause_play_btn,
            loop_btn
        ],
        [
            InlineKeyboardButton("⏭ Skip", callback_data="c_skip"),
            InlineKeyboardButton("⏹ Stop", callback_data="c_stop")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def generate_text_progress_bar(elapsed_secs: int, total_secs: int) -> str:
    """Generates an aesthetic text-based audio seek bar e.g. '01:34 ───O─────── 04:00'."""
    if total_secs <= 0:
        return "00:00 ───O─────── 00:00"
        
    bar_length = 12
    progress_ratio = min(1.0, max(0.0, elapsed_secs / total_secs))
    filled_length = int(progress_ratio * bar_length)
    
    bar = ""
    for i in range(bar_length):
        if i == filled_length:
            bar += "🔘"
        else:
            bar += "─"
            
    # Format times into MM:SS
    elapsed_min, elapsed_sec = divmod(elapsed_secs, 60)
    total_min, total_sec = divmod(total_secs, 60)
    
    elapsed_str = f"{elapsed_min:02d}:{elapsed_sec:02d}"
    total_str = f"{total_min:02d}:{total_sec:02d}"
    
    return f"{elapsed_str} {bar} {total_str}"
