# AioScam Documentation

Full documentation for AioScam framework.

## Installation

```bash
pip install aioscam
```

## Quick Start

### 1. Echo Bot

```python
import asyncio
from aioscam import Bot, Dispatcher, Router, Command

dp = Dispatcher()
router = Router()

@router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer("Привет! Я эхо-бот.")

@router.message_created()
async def echo(event):
    await event.answer(event.text)

dp.include_router(router)

async def main():
    bot = Bot()  # Token from MAX_BOT_TOKEN
    await dp.start_polling(bot)

asyncio.run(main())
```

### 2. Environment Setup

Set your bot token:

```bash
export MAX_BOT_TOKEN="your_bot_token_here"
```

## Core Concepts

### Bot

The `Bot` class is your interface to the Max API.

```python
from aioscam import Bot

# From environment variable
bot = Bot()

# Explicit token
bot = Bot(token="your_token")

# Custom timeout
bot = Bot(timeout=60)
```

#### Bot Methods

- `get_me()` - Get bot information
- `send_message(chat_id, text, keyboard, format, autosplit=False)` - Send text message; autosplit=True splits text >4000 chars into multiple messages
- `edit_message(chat_id, message_id, text)` - Edit message
- `delete_message(message_id)` - Delete message (matches Go SDK)
- `get_message(message_id)` - Get single message
- `get_messages(chat_id, limit, offset)` - Get messages list
- `pin_message(chat_id, message_id)` - Pin message
- `delete_pin_message(message_id)` - Unpin message
- `send_callback(callback_id, message, notification, keyboard)` - Answer callback (with optional inline keyboard)
- `send_action(chat_id, action)` - Send typing indicator
- `send_photo(chat_id, photo, caption)` - Send photo (file or URL)
- `send_video(chat_id, video, caption)` - Send video
- `send_audio(chat_id, audio, caption)` - Send audio
- `send_document(chat_id, document, caption)` - Send document
- `send_media(chat_id, attachment)` - Send any media type
- `download_file(path, url, token)` - Download file to disk
- `download_file_bytes(url, token)` - Download file to memory
- `get_chats()` - Get all chats
- `get_chat_by_id(chat_id)` - Get chat info
- `edit_chat(chat_id, title, description)` - Edit chat
- `add_members_chat(chat_id, user_ids)` - Add members
- `remove_member_chat(chat_id, user_id)` - Remove member
- `get_updates(marker, limit, timeout)` - Get updates (polling)
- `subscribe_webhook(url)` - Subscribe webhook
- `unsubscribe_webhook()` - Unsubscribe webhook

### Dispatcher

The `Dispatcher` is the main event processor.

```python
from aioscam import Dispatcher, Router

dp = Dispatcher()
router = Router()

# Include router
dp.include_router(router)

# Start polling
await dp.start_polling(bot)
```

### Router

Routers organize handlers into modules.

```python
router = Router(name="admin")

@router.message_created(Command("admin"))
async def admin_cmd(event):
    await event.answer("Admin panel")

dp.include_router(router)
```

## Filters

### Command Filter

```python
@router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer("Started!")

# Multiple commands
@router.message_created(Command(["start", "help"]))
async def cmd_multi(event):
    await event.answer("Command received")
```

### Text Filter

```python
from aioscam.filters import Text

@router.message_created(Text(equals="hello"))
async def exact_match(event):
    await event.answer("Exact match!")

@router.message_created(Text(contains=["word1", "word2"]))
async def contains_match(event):
    await event.answer("Contains word!")

@router.message_created(Text(startswith="prefix"))
async def prefix_match(event):
    await event.answer("Starts with prefix!")
```

### Magic Filters

```python
from aioscam import F

@router.message_created(F.message.body.text.func(lambda t: "hello" in t.lower()))
async def hello_filter(event):
    await event.answer("Hello!")

@router.message_created(F.message.chat.type == "private")
async def private_only(event):
    await event.answer("Private chat!")
```

## FSM (Finite State Machine)

### Basic Usage

```python
from aioscam.fsm import State, StatesGroup

class MyState(StatesGroup):
    step1 = State()
    step2 = State()

@router.message_created(Command("start"))
async def cmd_start(event, state):
    await state.set_state(MyState.step1)
    await event.answer("Step 1: Enter name")

@router.message_created(MyState.step1)
async def step1_handler(event, state):
    await state.update_data(name=event.text)
    await state.set_state(MyState.step2)
    await event.answer("Step 2: Enter age")

@router.message_created(MyState.step2)
async def step2_handler(event, state):
    await state.update_data(age=event.text)
    data = await state.get_data()
    await state.set_state(None)  # Clear state
    
    await event.answer(
        f"Done! Name: {data['name']}, Age: {data['age']}"
    )
```

### Cancel State

```python
@router.message_created(Command("cancel"))
async def cmd_cancel(event, state):
    current = await state.get_state()
    if current:
        await state.set_state(None)
        await event.answer("Cancelled")
```

## Middleware

### Logging Middleware

```python
@router.middleware()
async def logging_middleware(event, handler):
    print(f"Event: {event}")
    result = await handler(event)
    print(f"Done")
    return result
```

### Timing Middleware

```python
import time

@router.middleware()
async def timing_middleware(event, handler):
    start = time.time()
    result = await handler(event)
    duration = time.time() - start
    print(f"Handler took: {duration:.3f}s")
    return result
```

## Keyboards

### Inline Keyboard

```python
from aioscam.utils.keyboard import KeyboardBuilder

@router.message_created(Command("menu"))
async def cmd_menu(event):
    builder = KeyboardBuilder(inline=True)
    
    builder.callback("Stats", "action:stats")
    builder.callback("Settings", "action:settings")
    builder.row()
    builder.link("Website", "https://example.com")
    
    keyboard = builder.build()
    
    await event.answer(
        "Choose action:",
        keyboard=keyboard.to_dict()
    )
```

### Callback Handler

```python
@router.message_callback()
async def handle_callback(event):
    data = event.callback.payload  # callback data string

    if data == "action:stats":
        await event.answer("📊 Statistics")
    elif data == "action:settings":
        await event.answer("⚙️ Settings")
```

## Webhook Mode

### aiohttp

```python
from aiohttp import web
from aioscam.webhook import AiohttpWebhookHandler

async def main():
    bot = Bot()
    
    app = web.Application()
    handler = AiohttpWebhookHandler(bot, dp, path="/webhook")
    app.router.add_post("/webhook", handler.handle)
    
    await bot.subscribe_webhook("https://your-domain.com/webhook")
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    
    while True:
        await asyncio.sleep(3600)
```

## WebApp Mode (Mini Apps)

Max WebApps run as HTML/CSS/JS inside the client's WebView. `aioscam.webapp` validates what the
page sends you and pushes events back to it over SSE:

```python
from aiohttp import web
from aioscam.webapp import validate_init_data, EventStreamManager
from aioscam.webapp.aiohttp import WebAppMiddleware

events = EventStreamManager()

async def api_send(request):
    raw_init_data = request.headers.get("Authorization", "").removeprefix("MaxWebApp ")
    data = validate_init_data(raw_init_data, bot.token)
    body = await request.json()
    await bot.send_message(chat_id=data.chat.id, user_id=data.user.id, text=body["text"])
    return web.json_response({"ok": True})

async def api_events(request):
    raw_init_data = request.query.get("initData", "")
    data = validate_init_data(raw_init_data, bot.token)
    return await events.stream(request, user_id=data.user.id)

app = web.Application(middlewares=[WebAppMiddleware(bot_token=bot.token)])
app.router.add_post("/api/send", api_send)
app.router.add_get("/api/events", api_events)
app.router.add_static("/", path="examples/webapp/")
```

`WebAppMiddleware` only validates paths starting with `/api` — static HTML/JS pages stay public.
A full example (REST+SSE backend, 4 frontend pages) is in `examples/webapp_bot.py` +
`examples/webapp/*.html`.

## Bot Capability Report

`GET /me` carries no permissions field, so check what your bot can actually do at startup:

```python
from aioscam.utils.capabilities import BotCapabilities

caps = await BotCapabilities.probe(bot, webapp_url="https://example.com/webapp")
caps.log_report(logger)
```

## Error Handling

### Exceptions

```python
from aioscam.exceptions import (
    AioScamError,
    ApiError,
    NetworkError,
    BotTokenError,
    TimeoutError,
)

try:
    await bot.send_message(chat_id=123, text="Hello")
except ApiError as e:
    print(f"API error: {e.code} - {e.message}")
except NetworkError as e:
    print(f"Network error: {e}")
```

Every exception carries a `.hint` with a concrete cause/fix, appended automatically to `str(e)`:

```python
try:
    bot = Bot()
except BotTokenError as e:
    print(e)       # "Bot token is not provided — pass token=... to Bot(), or set the MAX_BOT_TOKEN environment variable"
    print(e.hint)  # just the hint part
```

## API Reference

### Types

- `User` - User information
- `Chat` - Chat information
- `Message` - Message information
- `Update` - Update wrapper
- `Callback` - Callback data
- `Keyboard` - Keyboard markup
- `Attachment` - File attachment

### Enums

- `ChatType` - private, group, supergroup, channel
- `UpdateType` - All update types
- `SenderAction` - TYPING_ON, SENDING_PHOTO, SENDING_VIDEO, SENDING_AUDIO, SENDING_FILE, MARK_SEEN
- `ParseMode` - none, markdown, html
- `ButtonType` - callback, link, chat, etc.

### Events

- `bot_started` - Bot started (also handles deep links via `event.payload`)
- `bot_stopped` - Bot stopped
- `message_created` - New message
- `message_edited` - Message edited
- `message_callback` - Button clicked (use `@router.message_callback()`)

## Deep Links

```python
from aioscam import StartCommand

# Handle first-time bot start with payload (deep link)
@router.bot_started()
async def on_bot_started(event, state):
    if event.payload:
        await event.answer(f"Welcome! Payload: {event.payload}")
    else:
        await event.answer("Welcome!")

# Handle repeat visits via /start <payload> (existing users)
@router.message_created(StartCommand())
async def on_repeat_deeplink(event, state):
    payload = event.command_args
    if payload:
        await event.answer(f"Welcome back! Payload: {payload}")
```

> **Note:** `StartCommand()` handlers MUST be registered BEFORE `Command("start")`.

## Examples

See `examples/` directory (16 bots):

| File | Description |
|------|-------------|
| `demo_bot.py` | Full framework demo (1783 lines) — all features |
| `echo_bot.py` | Simple echo bot |
| `fsm_bot.py` | Registration with FSM |
| `callback_bot.py` | Callback API + inline keyboards |
| `deep_link_bot.py` | Deep links with referral system |
| `deep_link_test_bot.py` | Deep link debug/logging |
| `i18n_bot.py` | Internationalization (ru/en) |
| `keyboard_bot.py` | Keyboards and buttons |
| `media_bot.py` | Photo/video/audio/document handling |
| `methods_bot.py` | Structured API methods (BaseMethod) |
| `middleware_bot.py` | Logging and timing middleware |
| `rate_limited_bot.py` | Token bucket rate limiting |
| `router_bot.py` | Multiple routers and filtering |
| `run_bot.py` | Production-ready launcher |
| `webhook_bot.py` | Webhook mode with aiohttp |
| `webapp_bot.py` | WebApp (Mini App) REST+SSE backend — see `examples/webapp/*.html` |

## License

[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0) — free for personal, educational, and other noncommercial use. Commercial use requires a separate license.
