import asyncio
import logging
import os
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import yt_dlp
from fastapi import FastAPI
import uvicorn

# Tokenni Render muhitidan (Environment variable) yoki to'g'ridan-to'g'ri yozasiz
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "TOKEN_SHU_YERGA_YOZILADI")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Render serveri uxlab qolmasligi uchun FastAPI
app = FastAPI()

@app.get("/")
def index():
    return {"status": "YouTube Downloader Bot ishlayapti!"}

def run_fastapi():
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# Foydalanuvchi holatlari
class DownloaderStates(StatesGroup):
    waiting_for_url = State()

# Asosiy menyu
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📥 YouTube'dan yuklab olish")],
        [KeyboardButton(text="ℹ️ Yordam")]
    ],
    resize_keyboard=True
)

# Chat yonidagi buyruqlar
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🔄 Botni qayta ishga tushirish"),
        BotCommand(command="help", description="ℹ️ Yordam va ko'rsatma")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Assalomu alaykum, {message.from_user.first_name}!\n"
        "Men YouTube'dan istalgan sifatda video va qo'shiq (MP3) yuklab beruvchi botman.\n"
        "Boshlash uchun quyidagi tugmani bosing:",
        reply_markup=main_menu
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "ℹ️ **Qanday foydalaniladi?**\n"
        "1. '📥 YouTube'dan yuklab olish' tugmasini bosing.\n"
        "2. YouTube videosining havolasini (linkini) yuboring.\n"
        "3. O'zingizga kerakli sifatni (144p, 360p, 720p, 1080p) yoki MP3 audio formatini tanlang!",
        reply_markup=main_menu
    )

@dp.message(F.text == "📥 YouTube'dan yuklab olish")
async def ask_url(message: Message, state: FSMContext):
    await message.answer(
        "Menga YouTube videosining havolasini (linkini) yuboring:\n"
        "*(Masalan: https://youtu.be/...)*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Asosiy menyu")]], resize_keyboard=True)
    )
    await state.set_state(DownloaderStates.waiting_for_url)

@dp.message(F.text == "🔙 Asosiy menyu")
async def back_to_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyuga qaytdingiz:", reply_markup=main_menu)

@dp.message(DownloaderStates.waiting_for_url)
async def get_url(message: Message, state: FSMContext):
    if message.text == "🔙 Asosiy menyu":
        await back_to_menu(message, state)
        return

    url = message.text
    if "youtube.com" not in url and "youtu.be" not in url:
        await message.answer("⚠️ Iltimos, haqiqiy YouTube havolasini yuboring!")
        return

    await state.update_data(youtube_url=url)

    # Sifat tanlash uchun Inline tugmalar (144p, 360p, 720p, 1080p va MP3)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📱 144p", callback_data="dl_144"),
                InlineKeyboardButton(text="📱 360p", callback_data="dl_360")
            ],
            [
                InlineKeyboardButton(text="💻 720p (HD)", callback_data="dl_720"),
                InlineKeyboardButton(text="🖥 1080p (FHD)", callback_data="dl_1080")
            ],
            [
                InlineKeyboardButton(text="🎵 Audio / Qo'shiq (MP3)", callback_data="dl_audio")
            ]
        ]
    )
    await message.answer("Qaysi sifatda yoki formatda yuklab olmoqchisiz?", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("dl_"))
async def download_media(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    url = data.get("youtube_url")
    
    if not url:
        await callback.message.answer("Xatolik! Havola topilmadi. Qaytadan urinib ko'ring.")
        await callback.answer()
        return

    choice = callback.data.split("_")[1] # 144, 360, 720, 1080 yoki audio
    await callback.message.edit_text("⏳ Fayl yuklab olinmoqda va tayyorlanmoqda, biroz kuting...")

    file_path = None
    try:
        if choice == "audio":
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': '%(id)s.%(ext)s',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = f"{info['id']}.mp3"

            await callback.message.answer_audio(
                audio=FSInputFile(file_path),
                caption="🎵 Marhamat, qo'shig'ingiz tayyor!"
            )
        else:
            height = int(choice)
            ydl_opts = {
                'format': f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best',
                'outtmpl': '%(id)s.%(ext)s',
                'merge_output_format': 'mp4',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = f"{info['id']}.mp4"

            await callback.message.answer_video(
                video=FSInputFile(file_path),
                caption=f"✅ Marhamat, videongiz ({choice}p) tayyor!"
            )

    except Exception as e:
        await callback.message.answer(f"❌ Yuklab olishda xatolik yuz berdi: {e}")

    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    await state.clear()
    await callback.message.answer("Yana havola yuborishingiz mumkin:", reply_markup=main_menu)
    await callback.answer()

@dp.message(F.text == "ℹ️ Yordam")
async def help_menu_cmd(message: Message):
    await help_cmd(message)

# Botni ishga tushirish
async def main():
    logging.basicConfig(level=logging.INFO)
    
    server_thread = threading.Thread(target=run_fastapi, daemon=True)
    server_thread.start()
    
    await set_bot_commands(bot)
    print("YouTube yuklovchi bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
