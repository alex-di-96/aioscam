# AioScam

Async Python framework for building Max messenger bots, inspired by aiogram architecture.

## Version

**v0.1.5.1** — Production Ready (2026-05-19)

### Latest features
- ✨ `format` parameter in `send_message()` and `edit_message()` — Markdown and HTML support
- ✨ `Bot(parse_mode=ParseMode.MARKDOWN)` — default text formatting for all messages
- ✨ `event.hide_keyboard()` — Telegram-style one_time_keyboard
- ✨ `event.answer_and_hide_keyboard()` — answer with keyboard removal
- ✅ Verified: **bold** `[links](url)` render correctly with `format:markdown`
- ✅ Verified: `<b>bold</b> <i>italic</i> <a href="...">links</a>` render with `format:html`

## Features

- 🚀 **Fully async** - Built on `asyncio` and `aiohttp`
- 🎯 **aiogram-style API** - Familiar decorators and patterns
- 🔄 **Router system** - Modular bot architecture with nesting support
- 🎭 **Magic Filters** - Declarative event filtering (`F.text`, `F.callback.payload`)
- 🔧 **Middleware** - Request/response processing pipeline
- 📦 **FSM** - Built-in finite state machine with MemoryStorage
- 🛡️ **StateGuard** - Blocks unauthorized commands/callbacks during active FSM states
- 📱 **Contact & Location** - Inline buttons for requesting phone number and geolocation
- ⌨️ **one_time_keyboard** - Auto-hide inline keyboards after button click (Telegram-style)
- 📝 **Text Formatting** - Markdown (`**bold**`, `[link](url)`) and HTML (`<b>bold</b>`, `<i>italic</i>`, `<a href="...">link</a>`)
- 📋 **Bot Commands Menu** - `set_my_commands()` + `set_bot_info()` for bot profile
- 🔄 **Auto-cleanup** - Middleware-based message tracking + one_time_keyboard
- 🗑️ **Message Management** - Delete sent messages
- 🌐 **Webhook support** - aiohttp, FastAPI, Litestar
- 📡 **Polling mode** - Long-polling with exponential backoff
- 🔒 **Security** - Webhook secret token, circular router detection, race condition prevention
- 📦 **Python 3.9-3.12** - Wide version support
- 📚 **Full documentation** - RU + EN, integration guide
- 🎨 **IDE support** - Type hints, py.typed, VSCode + PyCharm settings

## Installation

### TestPyPI (Testing)

```bash
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ aioscam
```

> ⚠️ Test version on TestPyPI. For production, install from source.

### Basic installation

```bash
pip install aioscam

# With FastAPI webhook support
pip install aioscam[fastapi]

# With Litestar webhook support
pip install aioscam[litestar]

# Development mode
pip install aioscam[dev]
```

### PyPI Status

- **PyPI**: ✅ Published ([pypi.org/project/aioscam/](https://pypi.org/project/aioscam/))
- **TestPyPI**: ✅ Published ([test.pypi.org/project/aioscam/](https://test.pypi.org/project/aioscam/))

### Quick install

```bash
pip install aioscam
```

### From source

```bash
git clone https://github.com/alex-di-96/aioscam.git
cd aioscam
pip install -e .
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
    await event.message.answer("Привет! Я эхо-бот. Напиши мне что-нибудь!")

@router.message_created()
async def echo_message(event):
    await event.message.answer(event.message.body.text)

dp.include_router(router)

async def main():
    bot = Bot()  # Token from MAX_BOT_TOKEN env
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

### With Magic Filters

```python
@router.message_created(F.message.body.text.func(lambda t: "привет" in t.lower()))
async def handle_hello(event):
    await event.message.answer("Привет! Как дела?")
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
    await event.message.answer("Введите имя:")

@router.message_created(MyState.waiting_name)
async def process_name(event, state):
    await state.update_data(name=event.message.body.text)
    await state.set_state(MyState.waiting_age)
    await event.message.answer("Введите возраст:")
```

### Webhook mode (aiohttp)

```python
async def main():
    bot = Bot()
    await dp.handle_webhook(bot=bot, host="0.0.0.0", port=8080)
```

## API Coverage

### Implemented Methods (35/35 core methods + set_bot_info)

| Category | Methods |
|----------|---------|
| **Bot Info** | `get_me`, `get_me_from_chat`, `change_info` |
| **Messages** | `send_message`, `edit_message`, `delete_message(message_id)`, `get_message`, `get_messages`, `pin_message`, `delete_pin_message`, `get_pin_message` |
| **Callbacks/Actions** | `send_callback(callback_id, answer, ...)`, `send_action` |
| **Chats** | `get_chats`, `get_chat_by_id`, `get_chat_by_link`, `edit_chat`, `delete_chat`, `add_chat_members`, `remove_member_chat`, `add_list_admin_chat`, `remove_admin`, `get_chat_members`, `get_chat_member`, `get_list_admin_chat`, `delete_me_from_chat` |
| **Updates** | `get_updates`, `get_last_marker` |
| **Webhooks** | `subscribe_webhook`, `unsubscribe_webhook`, `delete_webhook`, `get_subscriptions` |
| **Media** | `get_upload_url`, `upload_attachment`, `get_video` |

### Event Types (14 types)

`message_created`, `message_callback`, `message_edited`, `message_removed`, `bot_started`, `bot_stopped`, `bot_added`, `bot_removed`, `chat_title_changed`, `dialog_cleared`, `dialog_muted`, `dialog_unmuted`, `user_added`, `user_removed`

### Button Types (8 implemented)

`CallbackButton`, `LinkButton`, `ChatButton`, `MessageButton`, `ClipboardButton`, `OpenAppButton`, `RequestContactButton`, `RequestGeoLocationButton`

### Sender Actions (9 types)

`typing`, `upload_photo`, `record_video`, `upload_video`, `record_audio`, `upload_audio`, `upload_document`, `finding_location`, `choosing_sticker`

## Project Structure

```
aioscam/
├── bot/              # Bot client (35 API methods)
├── client/           # HTTP client (aiohttp wrapper)
├── dispatcher/       # Dispatcher, Router, EventContext, StateGuard
├── enums/            # 12 enumeration files
├── exceptions/       # 12 exception classes
├── filters/          # BaseFilter, Command, Text, State, Magic Filters
├── fsm/              # State, StatesGroup, MemoryStorage, Scene
├── handler/          # MessageHandler, CallbackHandler, EventHandler
├── methods/          # API method wrappers
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

# v0.1.5 feature tests (26/26 passing)
python -m pytest tests/test_v015.py -v
```

**Test Results**: 100/100 passing (100%)

## Deployment

Demo bot deployed on VPS with systemd service and autostart.

## Documentation

Full documentation available at: [https://aioscam.readthedocs.io/](https://aioscam.readthedocs.io/)

## License

MIT License
