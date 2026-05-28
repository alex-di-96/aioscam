# AioScam — Documentation

## Version

**v0.1.1** — Production Ready

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Bot](#bot)
5. [Dispatcher and Router](#dispatcher-and-router)
6. [Filters](#filters)
7. [FSM](#fsm)
8. [Middleware](#middleware)
9. [Keyboards](#keyboards)
10. [Webhook](#webhook)
11. [Configuration](#configuration)

---

## Installation

```bash
# Basic installation
pip install aioscam

# With FastAPI support
pip install aioscam[fastapi]

# For development
pip install aioscam[dev]

# From source code
git clone https://github.com/alex-di-96/aioscam.git
cd aioscam
pip install -e .
```

### Requirements

- Python 3.9–3.12
- aiohttp >= 3.9.0
- magic-filter >= 1.0.0
- pydantic >= 2.0.0

---

## Quick Start

### Echo Bot (Polling mode)

```python
import asyncio
from aioscam import Bot, Dispatcher, Router
from aioscam.filters import Command

dp = Dispatcher()
router = Router()

@router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer("Hello! Send me something!")

@router.message_created()
async def echo(event):
    await event.answer(event.message.body.text)

dp.include_router(router)

async def main():
    bot = Bot()  # Token from MAX_BOT_TOKEN env variable
    await dp.start_polling(bot)

asyncio.run(main())
```

### Environment Variable

Create `.env` file:

```env
MAX_BOT_TOKEN=your_bot_token
AIOSCAM_ENV=prod
```

---

## Architecture

```
aioscam/
├── bot/              # Bot client (35 API methods)
├── client/           # HTTP client (aiohttp wrapper)
├── dispatcher/       # Dispatcher, Router, EventContext, StateGuard
├── enums/            # Enumerations (12 files)
├── exceptions/       # Exception classes
├── filters/          # BaseFilter, Command, Text, State, Magic Filters
├── fsm/              # State, StatesGroup, MemoryStorage, Scene
├── handler/          # MessageHandler, CallbackHandler, EventHandler
├── methods/          # API method wrappers
├── middleware/       # BaseMiddleware, MiddlewareManager
├── types/            # Pydantic models (User, Chat, Message, etc.)
├── utils/            # KeyboardBuilder, formatting, deep linking
└── webhook/          # aiohttp webhook handler
```

---

## Bot

### Core Methods

#### `send_message()`

Send a text message.

```python
msg = await bot.send_message(
    chat_id=123456,
    text="Hello, world!",
    user_id=789012
)
```

**Parameters:**
- `chat_id: int | str` — Chat ID
- `text: str` — Message text
- `user_id: int | None` — User ID (for private messages)
- `reply_to_mid: str | None` — Message ID to reply to
- `keyboard: dict | None` — Inline keyboard

**Returns:** `dict` — sent message data

#### `edit_message()`

Edit a message.

```python
await bot.edit_message(
    chat_id=123456,
    message_id="mid.abc123",
    text="Updated text"
)
```

#### `delete_message()`

Delete a message.

```python
await bot.delete_message(message_id="mid.abc123")
```

#### `request_contact()`

Request contact information.

```python
await bot.request_contact(
    chat_id=123456,
    text="Please share your contact:",
    button_text="📱 Share Contact"
)
```

#### `request_location()`

Request geolocation.

```python
await bot.request_location(
    chat_id=123456,
    text="Please share your location:",
    button_text="📍 Share Location"
)
```

---

## Dispatcher and Router

### Dispatcher

Central component for processing updates.

```python
from aioscam import Dispatcher

dp = Dispatcher()
await dp.start_polling(bot)  # Polling mode
```

### Router

Router for processing messages.

```python
from aioscam import Router

router = Router()

# Nested routers
admin_router = Router(name="admin")
user_router = Router(name="user")

router.include_router(admin_router)
router.include_router(user_router)
dp.include_router(router)
```

### EventContext

Event context passed to handlers.

**Attributes:**
- `event` — event data
- `bot` — bot instance
- `data` — shared data
- `state` — FSM context

---

## Filters

### Command

Filter by commands.

```python
from aioscam.filters import Command

@router.message_created(Command("start"))
async def cmd_start(event):
    ...
```

### Text

Filter by text content.

```python
from aioscam.filters import Text

@router.message_created(Text(contains="hello"))
async def handle_greeting(event):
    ...

@router.message_created(Text(startswith="/"))
async def handle_slash(event):
    ...
```

### Magic Filters

Declarative filtering.

```python
from aioscam.filters import F

@router.message_created(F.message.body.text.func(lambda t: "hello" in t.lower()))
async def handle_hello(event):
    ...

@router.message_created(F.callback.payload.startswith("action:"))
async def handle_callback(event):
    ...
```

---

## FSM

### State and StatesGroup

```python
from aioscam.fsm import State, StatesGroup

class Registration(StatesGroup):
    name = State()
    email = State()
    phone = State()
```

### Usage

```python
@router.message_created(Command("register"))
async def cmd_register(event, state):
    await state.set_state(Registration.name)
    await event.answer("Enter your name:")

@router.message_created(Registration.name)
async def process_name(event, state):
    await state.update_data(name=event.message.body.text)
    await state.set_state(Registration.email)
    await event.answer("Enter your email:")

@router.message_created(Registration.email)
async def process_email(event, state):
    data = await state.get_data()
    await event.answer(f"Registered: {data['name']}")
    await state.set_state(None)  # Clear state
```

### StateContext Methods

- `get_state()` — get current state
- `set_state(state)` — set state
- `get_data()` — get data
- `update_data(**kwargs)` — update data
- `clear()` — clear data

---

## Middleware

### Creating

```python
from aioscam.middleware import BaseMiddleware

class LoggingMiddleware(BaseMiddleware):
    async def on_message(self, event, handler):
        print(f"Received: {event.message.body.text}")
        return await handler(event)
```

### Registration

```python
router.message.middleware(LoggingMiddleware())
```

---

## Keyboards

### KeyboardBuilder

```python
from aioscam.utils import KeyboardBuilder

builder = KeyboardBuilder(inline=True)

# Callback button
builder.callback("Button 1", "action:one")

# Link
builder.link("Open website", "https://example.com")

# New row
builder.row()

# Contact request
builder.request_contact("📱 Share Contact")

# Location request
builder.request_location("📍 Share Location")

# Sending
await event.answer("Choose:", keyboard=builder.build().to_dict())
```

### Button Types

| Type | Description |
|------|-------------|
| `callback` | Callback button |
| `link` | Link |
| `chat` | Go to chat |
| `message` | Go to message |
| `clipboard` | Copy to clipboard |
| `open_app` | Open app |
| `request_contact` | Request contact |
| `request_geo_location` | Request location |
| `attachment` | Attachment |

---

## Webhook

### aiohttp

```python
from aiohttp import web
from aioscam import Bot, Dispatcher, Router

dp = Dispatcher()
router = Router()
dp.include_router(router)

async def webhook_handler(request):
    dp: Dispatcher = request.app['dp']
    bot: Bot = request.app['bot']
    return await dp.handle_webhook_request(bot, request)

async def on_startup(app):
    app['bot'] = Bot()
    app['dp'] = dp

app = web.Application()
app.router.add_post('/webhook', webhook_handler)
app.on_startup.append(on_startup)

web.run_app(app, host='0.0.0.0', port=8080)
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MAX_BOT_TOKEN` | ✅ | Bot token from Max Bot API |
| `AIOSCAM_ENV` | ❌ | Environment: `debug`, `test`, `prod` (default: `prod`) |
| `MAX_BASE_URL` | ❌ | API URL (default: `https://platform-api.max.ru`) |

### Usage

```python
from aioscam.config import get_config

config = get_config()
print(config.token)
print(config.env)  # debug, test, prod
```

### Modes

- `debug` — verbose logging
- `test` — minimal logging
- `prod` — production mode
