import asyncio
import logging
import os
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.filters import Command
import yt_dlp
from fastapi import FastAPI
import uvicorn

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8969955147:AAE_qR8e_Of6jSI4UC07-6-4LSM70gquUJ4")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Render serveri uxlab qolmasligi uchun FastAPI
app = FastAPI()

@app.get("/")
def index():
    return {"status": "YouTube va Instagram Downloader Bot ishlayapti!"}

def run_fastapi():
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# Chat yonidagi buyruqlar
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🔄 Botni qayta ishga tushirish"),
        BotCommand(command="help", description="ℹ️ Yordam va ko'rsatma")
    ]
    # Agar BotCommand import qilingan bo'lmasa, xatolik bermasligi uchun shart emas, lekin quyidagicha ishlatamiz:

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(
        f"Assalomu alaykum, {message.from_user.first_name}!\n"
        "Men **YouTube** va **Instagram** havolalarini yuborsangiz, ularni to'g'ridan-to'g'ri yuklab beraman.\n\n"
        "Shunchaki menga videoning linkini yuboring! 📥"
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "ℹ️ **Qanday foydalaniladi?**\n"
        "Menga shunchaki quyidagi saytlarning havolasini yuboring:\n"
        "• YouTube (video yoki shorts)\n"
        "• Instagram (Reels yoki post video)\n\n"
        "Bot havolani o'qib, videoni o'zingizga yuboradi!"
    )

# Har qanday matnli xabarni tekshirish (Havola kelganini aniqlash uchun)
@dp.message(F.text)
async def handle_url(message: Message):
    url = message.text.strip()
    
    # YouTube yoki Instagram havolasi ekanligini tekshiramiz
    is_youtube = "youtube.com" in url or "youtu.be" in url
    is_instagram = "instagram.com" in url
    
    if not is_youtube and not is_instagram:
        await message.answer("⚠️ Iltimos, haqiqiy **YouTube** yoki **Instagram** havolasini yuboring!")
        return

    status_msg = await message.answer("⏳ Video yuklab olinmoqda, biroz kuting...")

    file_path = None
    try:
        # yt-dlp sozlamalari (cookies.txt mavjud bo'lsa ishlatadi)
        ydl_opts = {
            'format': 'best/bestvideo+bestaudio',
            'outtmpl': '%(id)s.%(ext)s',
            'merge_output_format': 'mp4',
        }
        
        # Agar cookies.txt fayli yuklangan bo'lsa qo'shamiz
        if os.path.exists("cookies.txt"):
            ydl_opts['cookiefile'] = 'cookies.txt'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_ext = info.get('ext', 'mp4')
            file_id = info.get('id', 'video')
            
            # Fayl nomini aniqlash
            if os.path.exists(f"{file_id}.mp4"):
                file_path = f"{file_id}.mp4"
            else:
                # Topilmasa, papkadagi oxirgi yuklangan mos keluvchi faylni olamiz
                for f in os.listdir('.'):
                    if f.startswith(file_id) and f.endswith(('.mp4', '.mkv', '.webm', '.mov')):
                        file_path = f
                        break

        if file_path and os.path.exists(file_path):
            await message.answer_video(
                video=FSInputFile(file_path),
                caption="✅ Marhamat, videongiz tayyor!"
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Videoni yuklab bo'lmadi yoki fayl topilmadi.")

    except Exception as e:
        await status_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")

    # Yuklab olingandan keyin serverni tozalash uchun faylni o'chiramiz
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

# Botni ishga tushirish
async def main():
    logging.basicConfig(level=logging.INFO)
    
    server_thread = threading.Thread(target=run_fastapi, daemon=True)
    server_thread.start()
    
    print("YouTube va Instagram yuklovchi bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
