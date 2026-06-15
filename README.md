# AioScam

Async Python framework for building Max messenger bots, inspired by aiogram architecture.

## Version

**v0.1.8** — Latest (2026-06-15)

### What's new in v0.1.8
- ✅ **`send_action()`** — fixed API path (`/chats/{chat_id}/actions`) and `SenderAction` values
- ✅ **`SendCallback`** method object — answer callback queries via `bot.send_callback()`
- ✅ **`send_message(autosplit=True)`** — opt-in splitting of messages >4000 chars, keyboard on last chunk
- ✅ **StateGuard callbacks** — `state_guard_callbacks` now accepts `magic_filter.F` expressions
  (`.startswith()`, `.contains()`, `.regexp()`, `& | ~`) alongside exact-match strings
- ✅ **Parallel update processing** — `asyncio.create_task()` per update in `start_polling()`
- ✅ **Streaming uploads/downloads** — no full in-memory reads for media
- ✅ **569/569 tests passing**

## Features

- 🚀 **Fully async** — `asyncio` + `aiohttp`
- 🎯 **aiogram-style API** — familiar decorators and patterns
- 🔄 **Router system** — modular, nestable
- 🎭 **Magic Filters** — `F.text`, `F.callback.payload`, `F.message.body.text`
- 🔧 **Middleware** — request/response pipeline
- 📦 **FSM** — `State`, `StatesGroup`, `MemoryStorage`
- 🛡️ **StateGuard** — blocks unauthorized commands during active FSM
- 🖼️ **Media** — upload/download images, video, audio, documents
- 📱 **Contact & Location** — inline buttons for phone and geolocation
- 📝 **Formatting** — Markdown and HTML
- 🔗 **Deep links** — `create_deep_link`, `parse_deep_link`, `StartCommand` filter
- 🌍 **I18n** — JSON-based translations, auto locale from `user_locale`
- 📋 **Bot Commands** — `set_my_commands()`, `set_bot_info()`
- 🗑️ **Message Management** — delete, pin, edit
- 🌐 **Webhook** — aiohttp, FastAPI, Litestar
- 📡 **Polling** — long-polling with exponential backoff
- 🛡️ **Rate Limiter** — token bucket, 429 retry, exponential backoff
- 🔒 **Security** — webhook secret token, circular router detection
- 📦 **Python 3.9–3.12**

## Installation

```bash
git clone https://github.com/alex-di-96/aioscam.git
cd aioscam
pip install -e .
```

```bash
pip install aioscam[fastapi]   # FastAPI webhook
pip install aioscam[litestar]  # Litestar webhook
pip install aioscam[dev]       # pytest, ruff, mypy
```

## Quick Start

```python
import asyncio
from aioscam import Bot, Dispatcher, Router
from aioscam.filters import Command, F

dp = Dispatcher()
router = Router()

@router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer("Hello! Send me anything.")

@router.message_created()
async def echo(event):
    await event.answer(event.text)

dp.include_router(router)

async def main():
    bot = Bot()  # token from MAX_BOT_TOKEN env
    await dp.start_polling(bot)

asyncio.run(main())
```

## Media

```python
from aioscam import InputMedia, InputMediaBuffer, UploadType

# Send from file path (type auto-detected from extension)
await bot.send_photo(chat_id=cid, user_id=uid, photo="photo.jpg")
await bot.send_video(chat_id=cid, user_id=uid, video="video.mp4", caption="Watch!")
await bot.send_document(chat_id=cid, user_id=uid, document="report.pdf")
await bot.send_audio(chat_id=cid, user_id=uid, audio="song.mp3")

# Auto-detect type
await bot.send_media(chat_id=cid, user_id=uid, media="anyfile.ext")

# From bytes buffer (no file on disk)
data = open("photo.jpg", "rb").read()
await bot.send_photo(chat_id=cid, user_id=uid, photo=data)

# Download incoming media into memory
image_bytes = await bot.download_file_bytes(url, token)

# Download to disk with unique temp name
path = Bot.make_temp_path(".jpg")  # /tmp/aioscam_20260528_143022_847291.jpg
await bot.download_file(path, url, token)
```

## FSM

```python
from aioscam.fsm import State, StatesGroup

class Registration(StatesGroup):
    waiting_name = State()
    waiting_age = State()
    waiting_email = State()
    waiting_phone = State()

@router.message_created(Command("register"))
async def start(event, state):
    await state.set_state(Registration.waiting_name)
    await event.answer("Step 1/4: Enter your name:")

@router.message_created(StateFilter(Registration.waiting_name))
async def name(event, state):
    await state.update_data(name=event.text)
    await state.set_state(Registration.waiting_age)
    await event.answer("Step 2/4: Enter your age:")
```

## Rate Limiter

```python
from aioscam import Bot
from aioscam.limiter import RateLimitConfig

bot = Bot(rate_limit=RateLimitConfig.strict())   # 5 req/s, burst 10
bot = Bot(rate_limit=RateLimitConfig.relaxed())  # 30 req/s, burst 50
```

## API Coverage

| Category | Methods |
|----------|---------|
| **Bot Info** | `get_me`, `get_me_from_chat`, `change_info`, `set_bot_info`, `set_my_commands` |
| **Messages** | `send_message`, `edit_message`, `delete_message`, `get_message`, `get_messages`, `pin_message`, `delete_pin_message`, `get_pin_message` |
| **Media** | `send_photo`, `send_video`, `send_audio`, `send_document`, `send_media`, `download_file`, `download_file_bytes`, `get_upload_url`, `get_video` |
| **Callbacks** | `send_callback`, `send_action` |
| **Chats** | `get_chats`, `get_chat_by_id`, `get_chat_by_link`, `edit_chat`, `delete_chat`, `add_chat_members`, `remove_member_chat`, `add_list_admin_chat`, `remove_admin`, `get_chat_members`, `get_chat_member`, `get_list_admin_chat`, `delete_me_from_chat` |
| **Updates** | `get_updates`, `get_last_marker` |
| **Webhooks** | `subscribe_webhook`, `unsubscribe_webhook`, `get_subscriptions` |

**14 event types:** `message_created`, `message_callback`, `message_edited`, `message_removed`, `bot_started`, `bot_stopped`, `bot_added`, `bot_removed`, `chat_title_changed`, `dialog_cleared`, `dialog_muted`, `dialog_unmuted`, `user_added`, `user_removed`

**8 button types:** `CallbackButton`, `LinkButton`, `ChatButton`, `MessageButton`, `ClipboardButton`, `OpenAppButton`, `RequestContactButton`, `RequestGeoLocationButton`

## Project Structure

```
aioscam/
├── bot/          # Bot client — all API methods
├── client/       # HTTP client (aiohttp, rate-limited, file upload/download)
├── dispatcher/   # Dispatcher, Router, EventContext, StateGuard
├── enums/        # 15 enum files
├── exceptions/   # 12 exception classes
├── filters/      # Command, Text, StartCommand, StateFilter, ContentType, F
├── fsm/          # State, StatesGroup, MemoryStorage
├── handler/      # MessageHandler, CallbackHandler, EventHandler
├── i18n/         # I18n — JSON translations, locale detection
├── limiter/      # RateLimiter, RateLimitConfig
├── methods/      # BaseMethod, GetMe, SendMessage, GetUpdates
├── middleware/   # BaseMiddleware, MiddlewareManager
├── types/        # Pydantic models — User, Chat, Message, Attachment, etc.
└── utils/        # KeyboardBuilder, formatting, deep_linking, media
```

## Configuration

```env
MAX_BOT_TOKEN=your_token
AIOSCAM_ENV=prod   # debug | test | prod
```

## Testing

```bash
python -m pytest tests/ -v
```

**202/202 tests passing (100%)**

## Example Bots

| File | Description |
|------|-------------|
| `echo_bot.py` | Simple echo bot |
| `fsm_bot.py` | FSM registration flow |
| `keyboard_bot.py` | Inline keyboard demo |
| `callback_bot.py` | send_callback demo |
| `middleware_bot.py` | Logging + timing middleware |
| `router_bot.py` | Multi-router architecture |
| `webhook_bot.py` | Webhook mode (aiohttp) |
| `deep_link_bot.py` | Deep links + referral |
| `deep_link_test_bot.py` | Deep link raw update debugger |
| `i18n_bot.py` | Multilingual bot (ru/en) |
| `media_bot.py` | Media upload/download demo |
| `rate_limited_bot.py` | Rate limiter demo |
| `methods_bot.py` | Methods API demo |
| `demo_bot.py` | Full-featured demo (FSM, media, i18n, deep links, SQLAlchemy) |
| `run_bot.py` | Minimal launcher |

## License

[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0) — [aLex Di](https://github.com/alex-di-96)

Free for personal, educational, and other noncommercial use. Commercial use requires a separate license — contact the author.

## ☕ Support the Project

If you find AioScam useful and want to support its development, consider:

- 🍪 **Buy me a cookie** — [Boosty](https://boosty.to/alex.di/donate)
- ⭐ **Star the repo** — it helps with visibility
- 🐛 **Report bugs** — open issues for any problems you find
- 🤝 **Contribute** — PRs welcome!

Every cookie fuels more features, faster bug fixes, and better documentation! 🚀
