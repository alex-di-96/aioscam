# AioScam Documentation

Full documentation for AioScam framework.

## Installation

```bash
pip install aoscam
```

## Quick Start

### 1. Echo Bot

```python
import asyncio
from aoscam import Bot, Dispatcher, Router, Command

dp = Dispatcher()
router = Router()

@router.message_created(Command("start"))
async def cmd_start(event):
    await event.message.answer("Привет! Я эхо-бот.")

@router.message_created()
async def echo(event):
    await event.message.answer(event.message.text)

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
from aoscam import Bot

# From environment variable
bot = Bot()

# Explicit token
bot = Bot(token="your_token")

# Custom timeout
bot = Bot(timeout=60)
```

#### Bot Methods

- `get_me()` - Get bot information
- `send_message(chat_id, text)` - Send text message
- `edit_message(chat_id, message_id, text)` - Edit message
- `delete_message(chat_id, message_id)` - Delete message
- `get_message(chat_id, message_id)` - Get single message
- `get_messages(chat_id, limit, offset)` - Get messages list
- `pin_message(chat_id, message_id)` - Pin message
- `delete_pin_message(chat_id, message_id)` - Unpin message
- `send_callback(chat_id, message_id, callback_id, text)` - Answer callback
- `send_action(chat_id, action)` - Send typing indicator
- `get_chats()` - Get all chats
- `get_chat_by_id(chat_id)` - Get chat info
- `edit_chat(chat_id, title, description)` - Edit chat
- `add_members_chat(chat_id, user_ids)` - Add members
- `remove_member_chat(chat_id, user_id)` - Remove member
- `get_updates(offset, limit, timeout)` - Get updates (polling)
- `subscribe_webhook(url)` - Subscribe webhook
- `unsubscribe_webhook()` - Unsubscribe webhook

### Dispatcher

The `Dispatcher` is the main event processor.

```python
from aoscam import Dispatcher, Router

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
    await event.message.answer("Admin panel")

dp.include_router(router)
```

## Filters

### Command Filter

```python
@router.message_created(Command("start"))
async def cmd_start(event):
    await event.message.answer("Started!")

# Multiple commands
@router.message_created(Command(["start", "help"]))
async def cmd_multi(event):
    await event.message.answer("Command received")
```

### Text Filter

```python
from aoscam.filters import Text

@router.message_created(Text(equals="hello"))
async def exact_match(event):
    await event.message.answer("Exact match!")

@router.message_created(Text(contains=["word1", "word2"]))
async def contains_match(event):
    await event.message.answer("Contains word!")

@router.message_created(Text(startswith="prefix"))
async def prefix_match(event):
    await event.message.answer("Starts with prefix!")
```

### Magic Filters

```python
from aoscam import F

@router.message_created(F.message.body.text.func(lambda t: "hello" in t.lower()))
async def hello_filter(event):
    await event.message.answer("Hello!")

@router.message_created(F.message.chat.type == "private")
async def private_only(event):
    await event.message.answer("Private chat!")
```

## FSM (Finite State Machine)

### Basic Usage

```python
from aoscam.fsm import State, StatesGroup

class MyState(StatesGroup):
    step1 = State()
    step2 = State()

@router.message_created(Command("start"))
async def cmd_start(event, state):
    await state.set_state(MyState.step1)
    await event.message.answer("Step 1: Enter name")

@router.message_created(MyState.step1)
async def step1_handler(event, state):
    await state.update_data(name=event.message.text)
    await state.set_state(MyState.step2)
    await event.message.answer("Step 2: Enter age")

@router.message_created(MyState.step2)
async def step2_handler(event, state):
    await state.update_data(age=event.message.text)
    data = await state.get_data()
    await state.set_state(None)  # Clear state
    
    await event.message.answer(
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
        await event.message.answer("Cancelled")
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
from aoscam.utils.keyboard import KeyboardBuilder

@router.message_created(Command("menu"))
async def cmd_menu(event):
    builder = KeyboardBuilder(inline=True)
    
    builder.callback("Stats", "action:stats")
    builder.callback("Settings", "action:settings")
    builder.row()
    builder.link("Website", "https://example.com")
    
    keyboard = builder.build()
    
    await event.message.answer(
        "Choose action:",
        keyboard=keyboard.to_dict()
    )
```

### Callback Handler

```python
@router.callback_query()
async def handle_callback(event):
    data = event.callback.data
    
    if data == "action:stats":
        await event.answer("📊 Statistics")
    elif data == "action:settings":
        await event.answer("⚙️ Settings")
```

## Webhook Mode

### aiohttp

```python
from aiohttp import web
from aoscam.webhook import AiohttpWebhookHandler

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

## Error Handling

### Exceptions

```python
from aoscam.exceptions import (
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
- `SenderAction` - typing, upload_photo, etc.
- `ParseMode` - none, markdown, html
- `ButtonType` - callback, link, chat, etc.

### Events

- `bot_started` - Bot started
- `bot_stopped` - Bot stopped
- `message_created` - New message
- `message_edited` - Message edited
- `message_callback` - Button clicked

## Examples

See `examples/` directory:

- `echo_bot.py` - Simple echo bot
- `fsm_bot.py` - Registration with FSM
- `middleware_bot.py` - Middleware usage
- `keyboard_bot.py` - Keyboards and buttons
- `webhook_bot.py` - Webhook mode
- `router_bot.py` - Multiple routers

## License

MIT License
