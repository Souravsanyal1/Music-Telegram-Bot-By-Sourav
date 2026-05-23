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
        ]
    ]
    
    # Dynamically add Force Join Channel/Group buttons if configured
    if config.FORCE_SUB_CHANNEL:
        channel_link = config.FORCE_SUB_LINK or str(config.FORCE_SUB_CHANNEL)
        if not (str(channel_link).startswith("https://") or str(channel_link).startswith("t.me/")):
            channel_link = f"https://t.me/{str(channel_link).replace('@', '')}"
        buttons.append([InlineKeyboardButton("📢 Join Update Channel", url=channel_link)])

    if config.FORCE_SUB_GROUP:
        group_link = config.FORCE_SUB_GROUP_LINK or str(config.FORCE_SUB_GROUP)
        if not (str(group_link).startswith("https://") or str(group_link).startswith("t.me/")):
            group_link = f"https://t.me/{str(group_link).replace('@', '')}"
        buttons.append([InlineKeyboardButton("👥 Join Support Group", url=group_link)])
        
    # Developer/Creator and Support links row
    dev_id = config.SUDO_USERS[0] if config.SUDO_USERS else 6427121076
    dev_button = InlineKeyboardButton("🛠 Creator", url=f"tg://user?id={dev_id}")
        
    # Support Channel or generic help
    support_link = config.FORCE_SUB_LINK or "https://t.me/telegram"
    if not (str(support_link).startswith("https://") or str(support_link).startswith("t.me/")):
        support_link = f"https://t.me/{str(support_link).replace('@', '')}"
        
    buttons.append([
        InlineKeyboardButton("🌐 Support", url=support_link),
        dev_button
    ])
    
    return InlineKeyboardMarkup(buttons)


def get_player_buttons(elapsed_secs: int = 0, total_secs: int = 0, is_paused: bool = False, is_looping: bool = False) -> InlineKeyboardMarkup:
    """
    Returns the interactive inline audio deck matching the 2nd image:
    [ Elapsed ────🔘──────── Total ]
    [ ◀ (Play) ] [ Ⅱ (Pause) ] [ 🔄 (Loop) ] [ ⏭ (Skip) ] [ ⏹ (Stop) ]
    """
    progress_text = generate_text_progress_bar(elapsed_secs, total_secs)
    
    buttons = [
        [
            InlineKeyboardButton(progress_text, callback_data="c_empty")
        ],
        [
            InlineKeyboardButton("◀", callback_data="c_resume"),
            InlineKeyboardButton("Ⅱ", callback_data="c_pause"),
            InlineKeyboardButton("🔄" if is_looping else "🔁", callback_data="c_unloop" if is_looping else "c_loop"),
            InlineKeyboardButton("⏭", callback_data="c_skip"),
            InlineKeyboardButton("⏹", callback_data="c_stop")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def generate_text_progress_bar(elapsed_secs: int, total_secs: int) -> str:
    """Generates an aesthetic text-based audio seek bar e.g. '01:34 ────🔘──────── 04:00'."""
    if total_secs <= 0:
        return "00:00 ────🔘──────── 00:00"
        
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
