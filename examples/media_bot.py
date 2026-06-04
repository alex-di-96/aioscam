#!/usr/bin/env python3
"""
Media Bot — send and receive media files

DEMONSTRATES
────────────
  • bot.send_photo(chat_id, user_id, photo=path)    — upload image from disk
  • bot.send_video(...)                              — upload video from disk
  • bot.send_audio(...)                             — upload audio from disk
  • bot.send_document(...)                          — upload any file
  • bot.send_media(media=InputMedia(path))          — auto-detect type by extension
  • InputMedia(path)                                — file from disk (auto type)
  • InputMediaBuffer(bytes, filename, upload_type)  — file from memory buffer
  • bot.download_file(path, url, token)             — download received media
  • bot.download_file_bytes(url, token)             — download to bytes in memory

COMMANDS
────────
  /start         — show list of available commands
  /photo <path>  — send image file
  /video <path>  — send video file
  /audio <path>  — send audio file
  /doc   <path>  — send any document/file
  /media <path>  — send file with auto type detection
  /buffer_demo   — generate image in memory (PIL) and send without saving to disk
  <file>         — send ANY file to the bot → it downloads and reports file size

VISUAL IN MAX MESSENGER
───────────────────────
  /photo /tmp/photo.jpg → bot uploads photo, it appears inline in chat
  /doc /tmp/report.pdf  → bot sends file with name and size info
  Send a photo to bot   → "✅ Скачано! Тип: image, Размер: 42.3 KB"
  Send a sticker        → "✨ Стикер получен! Код: <code>" (bots can't send stickers)

SETUP
─────
  export MAX_BOT_TOKEN=your_token_here
  python media_bot.py

  Optional (for /buffer_demo):
    pip install pillow

MEDIA UPLOAD FLOW
─────────────────
  1. bot.get_upload_url(upload_type) → Max API returns a one-time upload URL
  2. PUT file bytes to that URL
  3. Include the returned token in send_message/send_photo/etc.

  InputMedia and InputMediaBuffer handle steps 1-2 automatically.
  They are passed to send_photo/send_video/send_media which call _send_with_media.
"""

import asyncio
import io
import logging
import os
from pathlib import Path

try:
    from PIL import Image as _PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from aioscam import Bot, Dispatcher, Router, Command, F
from aioscam import InputMedia, InputMediaBuffer, UploadType
from aioscam.enums import ParseMode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Setup ─────────────────────────────────────────────────────────────────────

dp = Dispatcher()
router = Router()

DOWNLOAD_DIR = Path(__file__).parent / "downloads"

# ── /start ────────────────────────────────────────────────────────────────────

@router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer(
        "🖼️ **AioScam Media Bot**\n\n"
        "**Отправка медиа (путь к файлу):**\n"
        "`/photo <path>` — изображение\n"
        "`/video <path>` — видео\n"
        "`/audio <path>` — аудио\n"
        "`/doc   <path>` — документ (любой файл)\n"
        "`/media <path>` — авто-определение типа\n\n"
        "**Из памяти (без файла на диске):**\n"
        "`/buffer_demo`  — PIL → зелёный квадрат 200×200\n\n"
        "**Скачивание:**\n"
        "Отправьте мне любой файл — я скачаю и сообщу размер."
    )

# ── Send media by file path ───────────────────────────────────────────────────

@router.message_created(Command("photo"))
async def cmd_photo(event):
    """Send image: /photo /path/to/image.jpg"""
    path = (event.text or "").replace("/photo", "", 1).strip()
    if not path or not os.path.exists(path):
        await event.answer(f"⚠️ Файл не найден: `{path or 'не указан'}`\nПример: `/photo /home/user/photo.jpg`")
        return
    await event.answer("⏳ Загружаю изображение...")
    try:
        await event.bot.send_photo(
            chat_id=event.chat_id, user_id=event.user_id,
            photo=path,
            caption=f"🖼️ `{os.path.basename(path)}`",
        )
    except Exception as e:
        await event.answer(f"❌ Ошибка: {e}")


@router.message_created(Command("video"))
async def cmd_video(event):
    """Send video: /video /path/to/video.mp4"""
    path = (event.text or "").replace("/video", "", 1).strip()
    if not path or not os.path.exists(path):
        await event.answer(f"⚠️ Файл не найден: `{path or 'не указан'}`\nПример: `/video /home/user/video.mp4`")
        return
    await event.answer("⏳ Загружаю видео...")
    try:
        await event.bot.send_video(
            chat_id=event.chat_id, user_id=event.user_id,
            video=path,
            caption=f"🎥 `{os.path.basename(path)}`",
        )
    except Exception as e:
        await event.answer(f"❌ Ошибка: {e}")


@router.message_created(Command("audio"))
async def cmd_audio(event):
    """Send audio: /audio /path/to/song.mp3"""
    path = (event.text or "").replace("/audio", "", 1).strip()
    if not path or not os.path.exists(path):
        await event.answer(f"⚠️ Файл не найден: `{path or 'не указан'}`\nПример: `/audio /home/user/song.mp3`")
        return
    await event.answer("⏳ Загружаю аудио...")
    try:
        await event.bot.send_audio(
            chat_id=event.chat_id, user_id=event.user_id,
            audio=path,
            caption=f"🎵 `{os.path.basename(path)}`",
        )
    except Exception as e:
        await event.answer(f"❌ Ошибка: {e}")


@router.message_created(Command("doc"))
async def cmd_document(event):
    """Send any file as a document: /doc /path/to/file.pdf"""
    path = (event.text or "").replace("/doc", "", 1).strip()
    if not path or not os.path.exists(path):
        await event.answer(f"⚠️ Файл не найден: `{path or 'не указан'}`\nПример: `/doc /home/user/report.pdf`")
        return
    size = os.path.getsize(path)
    await event.answer(f"⏳ Загружаю файл ({_fmt_size(size)})...")
    try:
        await event.bot.send_document(
            chat_id=event.chat_id, user_id=event.user_id,
            document=path,
            caption=f"📎 `{os.path.basename(path)}` ({_fmt_size(size)})",
        )
    except Exception as e:
        await event.answer(f"❌ Ошибка: {e}")


@router.message_created(Command("media"))
async def cmd_media(event):
    """
    Auto-detect type by extension and send: /media /path/to/file

    InputMedia(path) inspects the file extension to determine whether
    to use UploadType.IMAGE, VIDEO, AUDIO, or FILE.
    """
    path = (event.text or "").replace("/media", "", 1).strip()
    if not path or not os.path.exists(path):
        await event.answer(f"⚠️ Файл не найден: `{path or 'не указан'}`")
        return
    media = InputMedia(path)
    await event.answer(f"⏳ Загружаю `{os.path.basename(path)}` как **{media.type.value}**...")
    try:
        await event.bot.send_media(
            chat_id=event.chat_id, user_id=event.user_id,
            media=media,
            caption=f"📁 `{os.path.basename(path)}` (тип: {media.type.value})",
        )
    except Exception as e:
        await event.answer(f"❌ Ошибка: {e}")

# ── Buffer upload demo ─────────────────────────────────────────────────────────

@router.message_created(Command("buffer_demo"))
async def cmd_buffer_demo(event):
    """
    Generate a 200×200 green square with PIL and send from memory buffer.

    InputMediaBuffer(bytes, filename, upload_type) uploads data directly
    from a bytes object — no temporary file is written to disk.
    Requires: pip install pillow
    """
    if not HAS_PIL:
        await event.answer("⚠️ PIL не установлен: `pip install pillow`")
        return

    img = _PILImage.new("RGB", (200, 200), color=(0, 200, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    media = InputMediaBuffer(png_bytes, "green_square.png", UploadType.IMAGE)
    await event.answer("⏳ Отправляю 200×200 зелёный квадрат из буфера памяти...")
    try:
        await event.bot.send_media(
            chat_id=event.chat_id, user_id=event.user_id,
            media=media,
            caption="🟩 Изображение создано через PIL в памяти (200×200 px, без файла на диске)",
        )
    except Exception as e:
        await event.answer(f"❌ Ошибка: {e}")

# ── Receive and download incoming media ───────────────────────────────────────

@router.message_created()
async def handle_incoming_media(event):
    """
    Catch any message that has attachments (no text command).

    Received attachments contain a download URL and token.
    bot.download_file(save_path, url, token) fetches the file and writes it to disk.
    bot.download_file_bytes(url, token) fetches to a bytes object in memory.
    """
    if not event.message or not event.message.has_text:
        # Only handle messages without text (i.e., media messages)
        pass
    else:
        return

    raw = event.data.get("raw_update", {})
    body = raw.get("message", {}).get("body", {})
    attachments = body.get("attachments", [])
    if not attachments:
        return

    for att in attachments:
        att_type = att.get("type", "unknown")

        if att_type == "sticker":
            payload = att.get("payload", {})
            code = payload.get("code", "?") if isinstance(payload, dict) else "?"
            await event.answer(
                f"✨ **Стикер получен!**\n\nКод: `{code}`\n\n"
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
            await event.answer(f"⚠️ Не удалось скачать `{att_type}` — URL или токен не предоставлены.")

# ── Helpers ───────────────────────────────────────────────────────────────────

async def _download_attachment(event, att: dict) -> str | None:
    """Download an attachment dict; return saved path or None on failure."""
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    att_type = att.get("type", "unknown")
    payload = att.get("payload", {})
    url = token = None

    if isinstance(payload, dict):
        url = payload.get("url")
        token = payload.get("token")
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
    save_path = str(DOWNLOAD_DIR / f"download_{att_type}{ext_map.get(att_type, '')}")
    status = await event.bot.download_file(save_path, url, token)
    return save_path if status == 200 else None


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 ** 2:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 ** 2:.1f} MB"

# ── Router wiring ─────────────────────────────────────────────────────────────

dp.include_router(router)

# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    bot = Bot(parse_mode=ParseMode.MARKDOWN)
    me = await bot.get_me()
    print(f"\n{'='*50}")
    print(f"🖼️  AioScam Media Bot: {me.get('first_name', 'Unknown')}")
    print(f"Downloads directory: {DOWNLOAD_DIR}")
    print(f"{'='*50}\n")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
