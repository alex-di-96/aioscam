#!/usr/bin/env python3
"""
AioScam Framework - Media Bot Example

Demonstrates sending and receiving media files:
- Images (photo)
- Videos
- Audio files
- Documents (any file)
- Stickers (receive only — bots cannot send stickers)
- Downloading received media to disk
"""

import asyncio
import logging
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from aioscam import Bot, Dispatcher, Command, F
from aioscam import InputMedia, InputMediaBuffer, UploadType
from aioscam.enums import ParseMode

dp = Dispatcher()

# ── /start ────────────────────────────────────────────────────────────────────

@dp.message_created(Command("start"))
async def cmd_start(event):
    await event.answer(
        "🖼️ **AioScam Media Bot**\n\n"
        "Доступные команды:\n\n"
        "**Отправка медиа (путь к файлу):**\n"
        "`/photo <path>` — отправить изображение\n"
        "`/video <path>` — отправить видео\n"
        "`/audio <path>` — отправить аудио\n"
        "`/doc <path>` — отправить документ (любой файл)\n"
        "`/media <path>` — авто-определение типа по расширению\n\n"
        "**Скачивание входящего медиа:**\n"
        "Просто отправьте мне любой файл — я его скачаю и сообщу размер.\n\n"
        "**Стикеры:**\n"
        "Отправьте стикер — я покажу его код."
    )


# ── Send media by path ────────────────────────────────────────────────────────

@dp.message_created(Command("photo"))
async def cmd_photo(event):
    """Send an image by file path: /photo /path/to/image.jpg"""
    text = event.text or ""
    path = text.replace("/photo", "", 1).strip()

    if not path or not os.path.exists(path):
        await event.answer(f"⚠️ Файл не найден: `{path or 'не указан'}`\n\nПример: `/photo /home/user/photo.jpg`")
        return

    await event.answer("⏳ Загружаю изображение...")
    try:
        await event.bot.send_photo(
            chat_id=event.chat_id,
            user_id=event.user_id,
            photo=path,
            caption=f"🖼️ Изображение: `{os.path.basename(path)}`",
        )
    except Exception as e:
        await event.answer(f"❌ Ошибка: {e}")


@dp.message_created(Command("video"))
async def cmd_video(event):
    """Send a video by file path: /video /path/to/video.mp4"""
    text = event.text or ""
    path = text.replace("/video", "", 1).strip()

    if not path or not os.path.exists(path):
        await event.answer(f"⚠️ Файл не найден: `{path or 'не указан'}`\n\nПример: `/video /home/user/video.mp4`")
        return

    await event.answer("⏳ Загружаю видео (может занять время)...")
    try:
        await event.bot.send_video(
            chat_id=event.chat_id,
            user_id=event.user_id,
            video=path,
            caption=f"🎥 Видео: `{os.path.basename(path)}`",
        )
    except Exception as e:
        await event.answer(f"❌ Ошибка: {e}")


@dp.message_created(Command("audio"))
async def cmd_audio(event):
    """Send an audio file: /audio /path/to/audio.mp3"""
    text = event.text or ""
    path = text.replace("/audio", "", 1).strip()

    if not path or not os.path.exists(path):
        await event.answer(f"⚠️ Файл не найден: `{path or 'не указан'}`\n\nПример: `/audio /home/user/song.mp3`")
        return

    await event.answer("⏳ Загружаю аудио...")
    try:
        await event.bot.send_audio(
            chat_id=event.chat_id,
            user_id=event.user_id,
            audio=path,
            caption=f"🎵 Аудио: `{os.path.basename(path)}`",
        )
    except Exception as e:
        await event.answer(f"❌ Ошибка: {e}")


@dp.message_created(Command("doc"))
async def cmd_document(event):
    """Send a document/file: /doc /path/to/file.pdf"""
    text = event.text or ""
    path = text.replace("/doc", "", 1).strip()

    if not path or not os.path.exists(path):
        await event.answer(f"⚠️ Файл не найден: `{path or 'не указан'}`\n\nПример: `/doc /home/user/report.pdf`")
        return

    size = os.path.getsize(path)
    await event.answer(f"⏳ Загружаю файл ({_fmt_size(size)})...")
    try:
        await event.bot.send_document(
            chat_id=event.chat_id,
            user_id=event.user_id,
            document=path,
            caption=f"📎 Файл: `{os.path.basename(path)}` ({_fmt_size(size)})",
        )
    except Exception as e:
        await event.answer(f"❌ Ошибка: {e}")


@dp.message_created(Command("media"))
async def cmd_media(event):
    """Auto-detect type and send: /media /path/to/file"""
    text = event.text or ""
    path = text.replace("/media", "", 1).strip()

    if not path or not os.path.exists(path):
        await event.answer(f"⚠️ Файл не найден: `{path or 'не указан'}`")
        return

    media = InputMedia(path)
    await event.answer(f"⏳ Загружаю `{os.path.basename(path)}` как **{media.type.value}**...")
    try:
        await event.bot.send_media(
            chat_id=event.chat_id,
            user_id=event.user_id,
            media=media,
            caption=f"📁 `{os.path.basename(path)}` (тип: {media.type.value})",
        )
    except Exception as e:
        await event.answer(f"❌ Ошибка: {e}")


# ── Receive and download media ────────────────────────────────────────────────

DOWNLOAD_DIR = Path(__file__).parent / "downloads"


async def _download_attachment(event, att: dict) -> str:
    """Download attachment and return saved path."""
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    att_type = att.get("type", "unknown")
    payload = att.get("payload", {})
    url = None
    token = None

    if isinstance(payload, dict):
        url = payload.get("url")
        token = payload.get("token")
        # Image: token may be nested in photos
        if att_type == "image" and not token:
            photos = payload.get("photos", {})
            if isinstance(photos, dict) and photos:
                key = next(iter(photos))
                photo = photos[key]
                if isinstance(photo, dict):
                    url = photo.get("url") or url
                    token = photo.get("token")

    if not url or not token:
        return None

    ext_map = {"image": ".jpg", "video": ".mp4", "audio": ".mp3", "file": ""}
    ext = ext_map.get(att_type, "")
    save_path = str(DOWNLOAD_DIR / f"download_{att_type}{ext}")

    status = await event.bot.download_file(save_path, url, token)
    return save_path if status == 200 else None


@dp.message_created(F.message.body.text == "")
async def handle_incoming_media(event):
    """Handle messages with attachments (no text) — download and report."""
    raw = event.data.get("raw_update", {})
    body = raw.get("message", {}).get("body", {})
    attachments = body.get("attachments", [])

    if not attachments:
        return

    for att in attachments:
        att_type = att.get("type", "unknown")

        if att_type == "sticker":
            # Stickers cannot be sent by bots — show payload info
            payload = att.get("payload", {})
            code = payload.get("code", "?") if isinstance(payload, dict) else "?"
            url = payload.get("url", "") if isinstance(payload, dict) else ""
            await event.answer(
                f"✨ **Стикер получен!**\n\n"
                f"Код: `{code}`\n"
                f"URL: `{url}`\n\n"
                f"⚠️ Боты не могут отправлять стикеры через API."
            )
            continue

        await event.answer(f"📥 Получил `{att_type}`, скачиваю...")

        saved = await _download_attachment(event, att)
        if saved:
            size = os.path.getsize(saved)
            await event.answer(
                f"✅ Скачано!\n\n"
                f"Тип: `{att_type}`\n"
                f"Сохранён: `{saved}`\n"
                f"Размер: **{_fmt_size(size)}**"
            )
        else:
            payload = att.get("payload", {})
            await event.answer(
                f"⚠️ Не удалось скачать `{att_type}`\n\n"
                f"Возможно, URL или токен не предоставлены.\n"
                f"Payload: `{str(payload)[:100]}`"
            )


# ── Buffer upload demo ────────────────────────────────────────────────────────

@dp.message_created(Command("buffer_demo"))
async def cmd_buffer_demo(event):
    """Demo: create image from bytes buffer and send"""
    # Minimal 1x1 red PNG
    png_bytes = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,   # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,   # 1x1
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,   # 8bit RGB
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,   # IDAT chunk
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
        0x00, 0x00, 0x02, 0x00, 0x01, 0xE2, 0x21, 0xBC,
        0x33, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,   # IEND
        0x44, 0xAE, 0x42, 0x60, 0x82,
    ])

    media = InputMediaBuffer(png_bytes, "red_pixel.png", UploadType.IMAGE)
    await event.answer("⏳ Отправляю изображение из буфера памяти...")

    try:
        await event.bot.send_media(
            chat_id=event.chat_id,
            user_id=event.user_id,
            media=media,
            caption="🔴 Изображение создано из bytes buffer (1×1 px PNG)",
        )
    except Exception as e:
        await event.answer(f"❌ Ошибка: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 ** 2:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 ** 2:.1f} MB"


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    bot = Bot(parse_mode=ParseMode.MARKDOWN)
    me = await bot.get_me()
    print(f"\n{'='*50}")
    print(f"🖼️  AioScam Media Bot")
    print(f"Bot: {me.get('first_name', 'Unknown')}")
    print(f"Downloads: {DOWNLOAD_DIR}")
    print(f"{'='*50}\n")

    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
