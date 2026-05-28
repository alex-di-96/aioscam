# AioScam

Async Python framework for building Max messenger bots, inspired by aiogram architecture.

## Version

**v0.1.6.2** — Latest (2026-05-28)

### Latest changes
- ✅ **Rate Limiter** — token bucket, 429 retry, exponential backoff
- ✅ **Methods API** — `Bot.execute(GetMe())`, `Bot.execute(SendMessage(...))`
- ✅ **send_callback** — SDK-aligned (`message=`, `notification=`)
- ✅ **Type dedup** — single source truth for User/Message/MessageBody
- ✅ **EventContext** — `user_id`, `chat_id` convenience properties
- ✅ **Examples** — 12 bots, all fixed and tested

## Features

- 🚀 **Fully async** — Built on `asyncio` and `aiohttp`
- 🎯 **aiogram-style API** — Familiar decorators and patterns
- 🔄 **Router system** — Modular bot architecture with nesting support
- 🎭 **Magic Filters** — Declarative event filtering (`F.text`, `F.callback.payload`)
- 🔧 **Middleware** — Request/response processing pipeline
- 📦 **FSM** — Built-in finite state machine with MemoryStorage
- 🛡️ **StateGuard** — Blocks unauthorized commands/callbacks during active FSM states
- 📱 **Contact & Location** — Inline buttons for requesting phone number and geolocation
- 📝 **Text Formatting** — Markdown and HTML support
- 📋 **Bot Commands Menu** — `set_my_commands()` + `set_bot_info()`
- 🗑️ **Message Management** — Delete, pin, edit messages
- 🌐 **Webhook support** — aiohttp, FastAPI, Litestar
- 📡 **Polling mode** — Long-polling with exponential backoff
- 🛡️ **Rate Limiter** — Centralized token bucket with 429 retry and exponential backoff
- 🔒 **Security** — Webhook secret token, circular router detection
- 📦 **Python 3.9-3.12** — Wide version support
- 📚 **Full documentation** — RU + EN, integration guide
- 🎨 **IDE support** — Type hints, py.typed

## Installation

### From source (development)

```bash
git clone https://github.com/alex-di-96/aioscam.git
cd aioscam
pip install -e .
```

### With optional dependencies

```bash
# With FastAPI webhook support
pip install aioscam[fastapi]

# With Litestar webhook support
pip install aioscam[litestar]

# Development mode (pytest, ruff, mypy)
pip install aioscam[dev]
```

## Quick Start

### Echo Bot (Polling mode)

```python
import asyncio
from aioscam import Bot, Dispatcher, Router
from aioscam.filters import Command, F

dp = Dispatcher()
router = Router()

@router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer("Привет! Я эхо-бот. Напиши мне что-нибудь!")

@router.message_created()
async def echo_message(event):
    if event.message.has_text:
        await event.answer(event.text)

dp.include_router(router)

async def main():
    bot = Bot()  # Token from MAX_BOT_TOKEN env
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

### With Rate Limiter

```python
from aioscam import Bot
from aioscam.limiter import RateLimitConfig

# Strict mode for production (5 req/s, burst 10, 5 retries)
bot = Bot(rate_limit=RateLimitConfig.strict())

# Relaxed for development (30 req/s, burst 50)
bot = Bot(rate_limit=RateLimitConfig.relaxed())

# Custom settings
bot = Bot(rate_limit=RateLimitConfig(
    rate=10.0,    # requests per second
    burst=20,     # max burst size
    max_retries=3,
    backoff_base=1.0,
))
```

### Methods API

```python
from aioscam import Bot, GetMe, SendMessage

bot = Bot()

# Using method objects
me = await bot.execute(GetMe())
await bot.execute(SendMessage(
    chat_id=event.chat_id,
    text="Hello!",
    format="markdown",
))
```

### FSM Example

```python
from aioscam.fsm import State, StatesGroup

class MyState(StatesGroup):
    waiting_name = State()
    waiting_age = State()

@router.message_created(Command("register"))
async def cmd_register(event, state):
    await state.set_state(MyState.waiting_name)
    await event.answer("Введите имя:")

@router.message_created(MyState.waiting_name)
async def process_name(event, state):
    await state.update_data(name=event.text)
    await state.set_state(MyState.waiting_age)
    await event.answer("Введите возраст:")
```

### Callback handling

```python
@router.callback_query()
async def handle_callback(event):
    # event.answer() — convenience wrapper
    await event.answer("Button clicked!")

    # Or use send_callback directly
    await event.bot.send_callback(
        callback_id=event.callback_id,
        message="Response text",
        notification="Popup alert",  # optional
    )
```

## API Coverage

### Implemented Methods (35/35 core methods + set_bot_info)

| Category | Methods |
|----------|---------|
| **Bot Info** | `get_me`, `get_me_from_chat`, `change_info` |
| **Messages** | `send_message`, `edit_message`, `delete_message`, `get_message`, `get_messages`, `pin_message`, `delete_pin_message`, `get_pin_message` |
| **Callbacks/Actions** | `send_callback(callback_id, message=, notification=)`, `send_action` |
| **Chats** | `get_chats`, `get_chat_by_id`, `get_chat_by_link`, `edit_chat`, `delete_chat`, `add_chat_members`, `remove_member_chat`, `add_list_admin_chat`, `remove_admin`, `get_chat_members`, `get_chat_member`, `get_list_admin_chat`, `delete_me_from_chat` |
| **Updates** | `get_updates`, `get_last_marker` |
| **Webhooks** | `subscribe_webhook`, `unsubscribe_webhook`, `delete_webhook`, `get_subscriptions` |
| **Media** | `get_upload_url`, `upload_attachment`, `get_video` |

### Event Types (14 types)

`message_created`, `message_callback`, `message_edited`, `message_removed`, `bot_started`, `bot_stopped`, `bot_added`, `bot_removed`, `chat_title_changed`, `dialog_cleared`, `dialog_muted`, `dialog_unmuted`, `user_added`, `user_removed`

### Button Types (8 implemented)

`CallbackButton`, `LinkButton`, `ChatButton`, `MessageButton`, `ClipboardButton`, `OpenAppButton`, `RequestContactButton`, `RequestGeoLocationButton`

## Project Structure

```
aioscam/
├── bot/              # Bot client (35+ API methods)
├── client/           # HTTP client (aiohttp, rate-limited)
├── dispatcher/       # Dispatcher, Router, EventContext, StateGuard
├── enums/            # 15 enumeration files
├── exceptions/       # 12 exception classes
├── filters/          # BaseFilter, Command, Text, State, Magic Filters
├── fsm/              # State, StatesGroup, MemoryStorage, Scene
├── handler/          # MessageHandler, CallbackHandler, EventHandler
├── limiter/          # RateLimiter, RateLimitConfig
├── methods/          # API method wrappers (GetMe, SendMessage, GetUpdates)
├── middleware/       # BaseMiddleware, MiddlewareManager
├── types/            # Pydantic models (User, Chat, Message, etc.)
├── utils/            # KeyboardBuilder, formatting, deep_linking
└── webhook/          # aiohttp webhook handler
```

## Configuration

Create `.env` file:

```env
MAX_BOT_TOKEN=your_token_here
AIOSCAM_ENV=prod  # debug, test, prod
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Test rate limiter
python -m pytest tests/test_rate_limiter.py -v

# Test methods API
python -m pytest tests/test_methods.py -v
```

**Test Results**: 141/141 passing (100%)

## Example Bots

| File | Description |
|------|-------------|
| `examples/echo_bot.py` | Simple echo bot |
| `examples/fsm_bot.py` | FSM registration flow |
| `examples/keyboard_bot.py` | Inline keyboard demo |
| `examples/middleware_bot.py` | Logging + timing middleware |
| `examples/router_bot.py` | Multi-router architecture |
| `examples/webhook_bot.py` | Webhook mode (aiohttp) |
| `examples/deep_link_bot.py` | Deep links + referral |
| `examples/demo_bot.py` | Full-featured demo (1000+ lines) |
| `examples/rate_limited_bot.py` | Rate limiter demo |
| `examples/methods_bot.py` | Methods API demo |
| `examples/callback_bot.py` | send_callback demo |

## Deployment

Demo bot deployed on VPS with systemd service and autostart.

## Documentation

Full documentation available at: [https://aioscam.readthedocs.io/](https://aioscam.readthedocs.io/)

## License

MIT License
