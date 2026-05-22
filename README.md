# 🎵 Premium Telegram Music Bot 🚀

একটি প্রফেশনাল এবং অত্যন্ত প্রিমিয়াম টেলিগ্রাম মিউজিক বট যা **Pyrogram (v2)**, **PyTgCalls (v2)**, **MongoDB** এবং **yt-dlp** ব্যবহার করে গ্রুপ ভয়েস চ্যাট বা লাইভ স্ট্রিমিং এ সরাসরি হাই-কোয়ালিটি গান বাজাতে পারে। 

এতে রয়েছে প্রফেশনাল ইমেজ জেনারেশন ভিত্তিক অ্যালবাম/ভিডিও থাম্বনেইল প্লেয়ার কার্ড এবং পূর্ণাঙ্গ অ্যাডমিন কন্ট্রোল সিস্টেম।

---

## 🌟 Key Features
* 🎧 **হাই-কোয়ালিটি স্ট্রিমিং:** সরাসরি YouTube, YouTube Music, MP3 লিংক অথবা রেডিও স্ট্রিম গ্রুপ ভয়েস চ্যাটে প্লে করতে পারে।
* 🖼 **Aesthetic Thumbnail Player Card:** Pillow (PIL) দিয়ে তৈরি করা একটি আধুনিক ও আকর্ষণীয় সার্কুলার থাম্বনেইল কার্ড ইনলাইন প্লেয়ার বাটনসহ গ্রুপে পাঠায়।
* 🔁 **প্লেয়ার কন্ট্রোল ডেক:** ইনলাইন বাটন বা কমান্ডের সাহায্যে পজ (Pause), রিজিউম (Resume), স্কিপ (Skip), লুপ (Loop) এবং স্টপ (Stop) করা যায়।
* 📋 **কিউ সিস্টেম (Queue System):** একাধিক গান কিউতে অ্যাড করা এবং `/queue` কমান্ড দিয়ে আপকামিং ট্র্যাকের লিস্ট দেখা যায়।
* 📢 **অ্যাডমিন ব্রডকাস্ট:** ডাটাবেসে নিবন্ধিত সকল ইউজার ইনবক্স (PM) এবং গ্রুপ চ্যাটে এক ক্লিকে গ্লোবাল ব্রডকাস্ট পাঠানো যায় (FloodWait রেট লিমিট প্রটেকশনসহ)।
* 📊 **পরিসংখ্যান ট্র্যাকিং (Stats):** ডাটাবেস স্ট্যাটাস, সক্রিয় ভয়েস চ্যাট এবং ইউজারের সংখ্যা রিয়েল-টাইমে প্রদর্শন করে।

---

## ⚙️ Behind The Scene: Dual-Client Architecture
টেলিগ্রামের অফিসিয়াল বট এপিআই সরাসরি ভয়েস চ্যাটে অংশ নিতে পারে না। তাই এই বটটি **Dual-Client (দ্বৈত-ক্লায়েন্ট)** মডেল ব্যবহার করে:
1. **Bot Client:** বট টোকেন দিয়ে চলে। এটি গ্রুপে কমান্ড ও বাটনের ইন্টারঅ্যাকশন কন্ট্রোল করে।
2. **Assistant Client:** একটি সাধারণ টেলিগ্রাম অ্যাকাউন্ট যা **Pyrogram Session String** দিয়ে রান করে। এটি ভয়েস চ্যাটে যোগ দিয়ে গান স্ট্রিমিং করে।

---

## 🛠 Prerequisites

### ১. FFmpeg ইনস্টল করা
বটের অডিও ট্রান্সকোডিং ও পাইপিং এর জন্য হোস্টিং সার্ভার বা লোকাল পিসিতে **FFmpeg** ইনস্টল থাকা বাধ্যতামূলক।

* **Windows:** [FFmpeg Builds](https://ffmpeg.org/download.html) থেকে ডাউনলোড করে Environment Path এ যোগ করুন।
* **Ubuntu/VPS:**
  ```bash
  sudo apt update
  sudo apt install ffmpeg -y
  ```

---

## 🔑 Environment Variables Setup
প্রজেক্টের রুট ডিরেক্টরিতে একটি `.env` ফাইল তৈরি করুন এবং নিচের মানগুলো বসান:

```env
API_ID=1234567                # my.telegram.org থেকে সংগৃহীত
API_HASH=abcdef1234567890     # my.telegram.org থেকে সংগৃহীত
BOT_TOKEN=12345:ABC-XYZ       # @BotFather থেকে সংগৃহীত বটের টোকেন
SESSION_STRING=AQAAAA...      # অ্যাসিস্ট্যান্ট অ্যাকাউন্টের Pyrogram সেশন স্ট্রিং
MONGO_URI=mongodb+srv://...   # MongoDB ডাটাবেস কানেকশন লিংক
SUDO_USERS=1234567,8901234    # কমা দিয়ে আলাদা করা অ্যাডমিনদের টেলিগ্রাম আইডি

# Force Subscription System configs (Public / Private Channel & Group Support)
FORCE_SUB_CHANNEL=MyChannel   # পাবলিক চ্যাটের জন্য ইউজারনেম (যেমন: MyChannel) অথবা প্রাইভেট চ্যাটের জন্য Chat ID (যেমন: -1001234567890)
FORCE_SUB_LINK=https://t.me/+AbCd1234 # (ঐচ্ছিক/Optional) প্রাইভেট চ্যানেল বা গ্রুপের জন্য কাস্টম ইনভাইট লিংক
```

---

## 🧪 How to Generate Pyrogram SESSION_STRING
আপনার অ্যাসিস্ট্যান্ট অ্যাকাউন্টের জন্য `SESSION_STRING` তৈরি করতে আপনার লোকাল কম্পিউটারে নিচের কমান্ডগুলো রান করুন:

১. প্রয়োজনীয় লাইব্রেরি ইনস্টল করুন:
```bash
pip install pyrogram TgCrypto
```

২. একটি নতুন ফাইল তৈরি করুন `session_gen.py` এবং নিচের কোডটি পেস্ট করুন:
```python
import asyncio
from pyrogram import Client

async def main():
    api_id = int(input("Enter API_ID: "))
    api_hash = input("Enter API_HASH: ")
    async with Client(":memory:", api_id=api_id, api_hash=api_hash) as app:
        print("\n👇 Copy this complete Session String:")
        print(await app.export_session_string())
        print("👆 Copy the whole string carefully!\n")

asyncio.run(main())
```

৩. স্ক্রিপ্টটি রান করুন এবং আপনার ফোন নম্বর ও টেলিগ্রাম থেকে আসা ওটিপি (OTP) ও পাসওয়ার্ড দিয়ে লগইন করে সেশন স্ট্রিংটি সংগ্রহ করুন:
```bash
python session_gen.py
```

---

## 🚀 How to Run Locally

১. প্রজেক্টের ফোল্ডারে প্রবেশ করুন এবং ভার্চুয়াল এনভায়রনমেন্ট তৈরি করুন:
```bash
python -m venv venv
```
* **Windows (Activate):** `venv\Scripts\activate`
* **Linux/Mac (Activate):** `source venv/bin/activate`

২. ডিপেন্ডেন্সি বা লাইব্রেরিগুলো ইনস্টল করুন:
```bash
pip install -r requirements.txt
```

৩. বট চালু করুন:
```bash
python main.py
```

---

## 🚂 Deployment Guide

### Railway-তে ডেপ্লয় করার নিয়ম
Railway-তে অডিও কোয়ালিটি স্বাভাবিক রাখার জন্য এবং FFmpeg সচল করতে Nixpacks বা custom Dockerfile ব্যবহার করতে পারেন। Nixpacks এ অটোমেটিক `requirements.txt` ডিটেক্ট হবে।

১. Railway ড্যাশবোর্ডে নতুন প্রজেক্ট তৈরি করুন।
২. আপনার GitHub রিপোজিটরি কানেক্ট করুন।
৩. প্রজেক্টের **Variables** ট্যাবে গিয়ে আপনার `.env` এর সকল মান সেট করুন।
৪. **Nixpacks** বিল্ডপ্যাকে FFmpeg যুক্ত করতে Railway-তে Environment Variable এ এটি যোগ করুন:
   ```env
   NIXPACKS_APT_PKGS=ffmpeg
   ```
৫. Deploy বাটনে ক্লিক করুন। রেলওয়ে অটোমেটিক বিল্ড করে রান করে দেবে!

### VPS (Ubuntu)-তে ডেপ্লয় করার নিয়ম
VPS-এ ২৪ ঘণ্টা বট ব্যাকগ্রাউন্ডে সচল রাখতে `systemd` সার্ভিস তৈরি করুন:

১. সার্ভিস ফাইল তৈরি করুন:
```bash
sudo nano /etc/systemd/system/musicbot.service
```

২. নিচের কোডটি পেস্ট করুন (প্রজেক্ট পাথ ও ইউজার পরিবর্তন করুন):
```ini
[Unit]
Description=Telegram Music Bot Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/telegram-music-bot
ExecStart=/root/telegram-music-bot/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

৩. সার্ভিস সচল ও স্টার্ট করুন:
```bash
sudo systemctl daemon-reload
sudo systemctl enable musicbot
sudo systemctl start musicbot
```

৪. বটের লাইভ লগ দেখতে:
```bash
sudo journalctl -u musicbot -f
```

---

## 🛠 GitHub Push Commands

আপনার কোড গিটহাবে পুশ করতে নিজের কমান্ডগুলো টার্মিনালে একে একে রান করুন:

```bash
# ১. গিট রিপোজিটরি ইনিশিয়েলাইজ করুন
git init

# ২. সকল কোড ফাইল অ্যাড করুন (.env ব্যতীত)
git add .

# ৩. প্রথম কমিট করুন
git commit -m "feat: complete premium telegram music bot with pytgcalls v2, mongo and pillow cards"

# ৪. মেইন ব্রাঞ্চ সেট করুন
git branch -M main

# ৫. আপনার গিটহাব রিপোজিটরি লিংক করুন
git remote add origin <YOUR_GITHUB_REPO_URL>

# ৬. গিটহাবে পুশ করুন
git push -u origin main
```

---

## 🎵 Commands Reference

### 📣 User Commands
* `/play <গানের নাম বা লিংক>` - চ্যাটে অডিও স্ট্রিম চালু করে।
* `/pause` - চলমান গান পজ করে।
* `/resume` - পজ করা গান পুনরায় প্লে করে।
* `/skip` - চলমান গান বাদ দিয়ে কিউয়ের পরের গানটি বাজায়।
* `/loop` - বর্তমান গানটি বারবার বাজানোর জন্য লুপ অন/অফ করে।
* `/stop` বা `/end` - প্লেয়ার বন্ধ করে কিউ খালি করে দেয়।
* `/queue` - আপকামিং ১০টি গানের সিরিয়াল দেখায়।

### 🛠 Admin Only
* `/stats` - বটের রিয়েল-টাইম মেমোরি ও ডাটাবেস পরিসংখ্যান।
* `/clean` - মেমোরিতে থাকা নিষ্ক্রিয় চ্যাটের কিউ ডেটা ক্লিন করে।
* `/broadcast <মেসেজ>` - সকল নিবন্ধিত ইউজার ও চ্যাটে গ্লোবাল ব্রডকাস্ট পাঠায়।

*বটটি উপভোগ করুন! যেকোনো ফিডব্যাক জানাতে ভুলবেন না।* 🎵🚀
