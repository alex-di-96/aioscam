# AioScam — Documentation (EN)

**v0.2.0** | [Русский](../ru/README.md)

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Bot Methods](#bot-methods)
5. [Media](#media)
6. [Dispatcher & Router](#dispatcher--router)
7. [EventContext](#eventcontext)
8. [Filters](#filters)
9. [FSM](#fsm)
10. [Middleware](#middleware)
11. [Keyboards](#keyboards)
12. [Deep Links](#deep-links)
13. [I18n](#i18n)
14. [Rate Limiter](#rate-limiter)
15. [Webhook](#webhook)
16. [WebApp (Mini Apps)](#webapp-mini-apps)
17. [BotCapabilities](#botcapabilities)
18. [Exceptions & Hints](#exceptions--hints)
19. [Configuration](#configuration)

---

## Installation

```bash
git clone https://github.com/alex-di-96/aioscam.git
cd aioscam
pip install -e .

pip install aioscam[fastapi]   # FastAPI webhook
pip install aioscam[litestar]  # Litestar webhook
pip install aioscam[dev]       # pytest, ruff, mypy
```

`aioscam.webapp` (WebApp/Mini App support) needs **no extra install** — it only uses `aiohttp`
and `pydantic`, both already required by the base package. There is no `aioscam[webapp]` extra
because there is nothing extra to install; a plain `pip install aioscam` already gives you
`validate_init_data`, `EventStreamManager`, and `WebAppMiddleware`.

**Requirements:** Python 3.9–3.12, aiohttp>=3.9, aiofiles>=23.0, pydantic>=2.0, magic-filter>=1.0

---

## Quick Start

```python
import asyncio
from aioscam import Bot, Dispatcher, Router
from aioscam.filters import Command

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
    bot = Bot()  # token from MAX_BOT_TOKEN env var
    await dp.start_polling(bot)

asyncio.run(main())
```

---

## Architecture

```
aioscam/
├── bot/          # Bot — all API methods
├── client/       # HTTP client (aiohttp + rate limiter + upload/download)
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
├── utils/        # KeyboardBuilder, formatting, deep_linking, media, BotCapabilities
└── webapp/       # validate_init_data, validate_contact, EventStreamManager, WebAppMiddleware
```

---

## Bot Methods

### Messages
```python
await bot.send_message(chat_id=123, user_id=456, text="Hello!", format="markdown")
await bot.edit_message(message_id="mid.abc", text="Updated text")
await bot.delete_message(message_id="mid.abc")
await bot.send_action(chat_id=123, action=SenderAction.TYPING_ON)
```

### Chats & Users
```python
me = await bot.get_me()
chats = await bot.get_chats()
members = await bot.get_chat_members(chat_id=123)
await bot.add_chat_members(chat_id=123, user_ids=[456])
await bot.remove_member_chat(chat_id=123, user_id=456)
```

### Bot Info
```python
await bot.set_my_commands([BotCommand(name="start", description="Start the bot")])
await bot.set_bot_info(name="My Bot", description="Bot description")
```

---

## Media

### Sending

```python
from aioscam import InputMedia, InputMediaBuffer, UploadType

# From file path — type auto-detected from extension
await bot.send_photo(chat_id=123, user_id=456, photo="photo.jpg", caption="Look!")
await bot.send_video(chat_id=123, user_id=456, video="video.mp4")
await bot.send_audio(chat_id=123, user_id=456, audio="song.mp3")
await bot.send_document(chat_id=123, user_id=456, document="report.pdf")
await bot.send_media(chat_id=123, user_id=456, media="any_file.ext")  # auto-type

# From bytes buffer (no temp file on disk)
data = open("photo.jpg", "rb").read()
await bot.send_photo(chat_id=123, user_id=456, photo=data)
```

**Extension → UploadType mapping:**
- `.jpg .jpeg .png .gif .webp .bmp` → IMAGE
- `.mp4 .mov .avi .mkv .webm` → VIDEO
- `.mp3 .ogg .wav .m4a .flac .aac .opus` → AUDIO
- everything else → FILE

### Downloading

```python
# In-memory (for processing, PIL, ffmpeg, etc.)
data = await bot.download_file_bytes(url, token)   # → bytes | None

# To disk with unique datetime-stamped filename
path = Bot.make_temp_path(".jpg")  # /tmp/aioscam_20260528_143022_847291.jpg
await bot.download_file(path, url, token)           # → HTTP status code
```

### Receiving in handlers

```python
@router.message_created(F.message.body.text == "")
async def handle_media(event):
    raw = event.data.get("raw_update", {})
    attachments = raw.get("message", {}).get("body", {}).get("attachments", [])
    for att in attachments:
        url   = att.get("payload", {}).get("url")
        token = att.get("payload", {}).get("token")
        if url and token:
            data = await event.bot.download_file_bytes(url, token)
```

### Stickers

Bots **cannot send** stickers. On receive:
```python
if att.get("type") == "sticker":
    code = att.get("payload", {}).get("code")
    url  = att.get("payload", {}).get("url")
```

---

## Dispatcher & Router

```python
dp = Dispatcher(
    state_guard_commands={'/cancel', '/start'},
    state_guard_callbacks={'action:cancel'},
)
child = Router(name="child")
dp.include_router(child)
await dp.start_polling(bot, skip_updates=True)
```

---

## EventContext

| Property | Type | Description |
|----------|------|-------------|
| `user_id` | int\|None | Sender user ID |
| `chat_id` | int\|None | Chat ID |
| `text` | str\|None | Message text |
| `payload` | str\|None | Deep link payload |
| `locale` | str\|None | User locale (BCP 47) |
| `callback_data` | str\|None | Callback button data |
| `from_user` | User\|None | Sender object |

```python
await event.answer("Text", keyboard=kb, format="markdown")
await event.hide_keyboard("New text")
```

---

## Filters

```python
@router.message_created(Command("start"))
@router.message_created(Command(["start", "go"]))

@router.bot_started(StartCommand())              # any deep link payload
@router.message_created(StartCommand())          # repeat deep link visit
async def handler(event, start_payload: str = None): ...

@router.message_created(Text(contains=["hello"]))
@router.message_created(StateFilter(MyState.waiting_name))
@router.message_created(F.message.body.text.func(lambda t: "hi" in t.lower()))
@router.callback_query(F.callback_data.startswith("action:"))
```

---

## FSM

```python
from aioscam.fsm import State, StatesGroup

class MyState(StatesGroup):
    waiting_name  = State()
    waiting_phone = State()

await state.set_state(MyState.waiting_name)
await state.update_data(name="John")
data = await state.get_data()
await state.set_state(None)
```

**StateGuard** — blocks commands and callback buttons during an active FSM state:
```python
from magic_filter import F

dp = Dispatcher(
    state_guard_commands={'/cancel', '/start'},
    state_guard_callbacks=[
        'action:cancel',                # exact match
        F.startswith('confirm_'),       # also matches "confirm_yes|52507"
        F.regexp(r'^nav:(back|next)$'),
    ],
    state_guard_hint_func=lambda s: "expected input",
)
```
`state_guard_callbacks` — a list of strings (exact match) and/or `magic_filter.F` expressions
(`.startswith()`, `.contains()`, `.regexp()`, combinable via `& | ~`).
Use a list, not a `set` — `F` expressions are unhashable.

---

## Middleware

```python
async def my_middleware(event, handler):
    result = await handler(event)
    return result

router.middleware()(my_middleware)
```

---

## Keyboards

```python
from aioscam.utils.keyboard import KeyboardBuilder

builder = KeyboardBuilder(inline=True)
builder.callback("Button", "action:click")
builder.link("Website", "https://example.com")
builder.request_contact("📱 Share Phone")
builder.request_location("📍 Share Location")
builder.row()

await event.answer("Choose:", keyboard=builder.build().to_dict())
```

---

## Deep Links

```python
from aioscam.utils.deep_linking import create_deep_link, parse_deep_link

link = create_deep_link("mybot", "ref_123")  # https://max.ru/mybot?start=ref_123
info = parse_deep_link(link)  # {"bot_username": "mybot", "start": "ref_123"}
```

---

## I18n

```python
from aioscam import I18n
i18n = I18n(path="locales/", default_locale="en")
text = i18n.get("welcome", locale=event.locale or "en")
```

---

## Rate Limiter

```python
from aioscam.limiter import RateLimitConfig
bot = Bot(rate_limit=RateLimitConfig.strict())   # 5 req/s
bot = Bot(rate_limit=RateLimitConfig.relaxed())  # 30 req/s
```

---

## Webhook

```python
await dp.handle_webhook(bot=bot, host="0.0.0.0", port=8080,
                        path="/webhook", secret_token="secret")
```

---

## WebApp (Mini Apps)

Max opens WebApps (mini apps) as plain HTML/CSS/JS inside the client's WebView. `aioscam.webapp`
provides the server-side half: validating what the WebApp page sends you, and pushing events back
to it over SSE.

### Validating `initData`

Every Max WebApp page receives a signed `initData` string from `window.WebApp.initData`. Validate
it server-side before trusting any of it:

```python
from aioscam.webapp import validate_init_data, WebAppSignatureError, WebAppExpiredError

try:
    data = validate_init_data(raw_init_data, bot_token, max_age=3600)
except WebAppSignatureError:
    ...  # tampered or wrong bot_token
except WebAppExpiredError:
    ...  # auth_date older than max_age

print(data.user.id, data.start_param)
```

`validate_contact(...)` does the same HMAC check for the payload returned by `requestContact()`.

### Pushing events to the WebApp (SSE)

```python
from aioscam.webapp import EventStreamManager

events = EventStreamManager()

# in your /api/events route handler:
async def sse_handler(request):
    return await events.stream(request, user_id=data.user.id)

# anywhere else in the bot:
await events.publish(user_id=123, {"type": "bot_message", "text": "hi from the bot"})
await events.broadcast({"type": "announcement", "text": "deploy done"})
```

`EventSource` (the browser API behind SSE) cannot set custom headers, so the WebApp page passes
`initData` as a query parameter on the SSE request: `GET /api/events?initData=<raw>`.
`WebAppMiddleware` accepts `initData` from `Authorization: MaxWebApp <raw>`, the
`X-Webapp-Init-Data` header, or the `?initData=` query param — in that order.

### Protecting your `/api/*` routes

```python
from aioscam.webapp.aiohttp import WebAppMiddleware

app.middlewares.append(WebAppMiddleware(bot_token=bot.token))
```

The middleware only validates requests whose path starts with `/api`; everything else (including
`/static/*` and your HTML pages) is left untouched and stays publicly reachable. It also splits its
error responses on purpose: a request with no `initData` at all gets a plain 404 (indistinguishable
from a route that doesn't exist), while a request with a present-but-invalid `initData` (bad
signature, expired, malformed) gets 401. A blind path scanner that never sends `initData` can't
tell `/api/me` apart from a 404 on a path that was never registered.

### Landing page

`HomePage` gives the bare server root something safe to show instead of a hand-written `index.html`:
bot name/description (from `bot.get_me()`) and an "Open in Max" deep link, no JS required, nothing
that hints at `/api/*`. Mount your actual Mini App frontend under its own path and register *that*
path — not the bare root — as the Mini App URL in the Max bot dashboard:

```python
from aioscam.webapp.aiohttp import HomePage

app.router.add_get("/", HomePage(bot).handler)              # public landing page
app.router.add_get("/app", serve_index)                     # Mini App URL registered in the dashboard
app.router.add_static("/app", path=str(STATIC_DIR))
```

`HomePage(bot, title=..., description=..., extra_head=..., extra_body=...)` lets you override the
copy or inject your own markup/scripts on top of the default shell — see `examples/webapp_bot.py`.

### Masking `/api/*` from scanners

The 404/401 split above already hides whether a route exists from anyone who never sends
`initData`. To raise the bar further against wordlist-style scanners (which try common names like
`/api`, `/api/me`, `/api/auth`), move the API off the well-known `/api` prefix with `api_prefix`,
and add a `WebAppFailGuard` to stop responding altogether to addresses that keep failing auth:

```python
from aioscam.webapp.aiohttp import WebAppFailGuard, WebAppMiddleware

guard = WebAppFailGuard(max_failures=20, window=60, ban_seconds=300)
app.middlewares.append(
    WebAppMiddleware(bot_token=bot.token, api_prefix="/a8f3e1", fail_guard=guard)
)
```

Once an address crosses `max_failures` failed validations within `window` seconds, every request
from it gets a flat 404 for `ban_seconds` — no signature check is even attempted. This is a
defense-in-depth speed bump for automated probing, not a substitute for the HMAC check itself.
Remember that your frontend's `fetch`/`EventSource` calls must target the same `api_prefix` — see
how `examples/webapp_bot.py` does it below.

A full working example — REST endpoints (`/api/auth`, `/api/contact`, `/api/send`), the SSE
endpoint, and 4 frontend pages — lives in `examples/webapp_bot.py` + `examples/webapp/*.html`.
Set `WEBAPP_API_PREFIX=/your-secret` before launching it and the demo moves its whole API there:
the server rewrites the `const API_PREFIX = "/api";` line in each served page on the fly, so the
frontend picks up the real prefix without a build step or any hardcoded duplicate.

---

## BotCapabilities

Max's `GET /me` does not expose a permissions/capabilities field, so `BotCapabilities` builds a
best-effort picture from the bot's profile and configuration instead of letting you assume
features that may not be set up:

```python
from aioscam.utils.capabilities import BotCapabilities

caps = await BotCapabilities.probe(bot, webapp_url="https://example.com/webapp")
caps.log_report(logger)  # structured banner at startup, including warnings
```

Bridge SDK features (haptics, biometrics, NFC, QR, contacts) are client-side only — the server has
no way to know the end user's platform, so they are not part of this report; check
`window.WebApp.platform` in the frontend instead.

---

## Exceptions & Hints

Every framework exception carries a `.hint` — a concrete reason or fix — appended automatically
when you `str()` it:

```python
try:
    bot = Bot()
except BotTokenError as e:
    print(e)  # "Bot token is not provided — pass token=... to Bot(), or set the MAX_BOT_TOKEN environment variable"
    print(e.hint)  # just the hint
```

`ApiError`, `NetworkError`, `TimeoutError`, `RetryAfter`, `UnauthorizedError`, `ForbiddenError`,
`NotFoundError`, `BotTokenError`, `DispatcherError`, and the `WebApp*` exceptions
(`WebAppSignatureError`, `WebAppExpiredError`, `WebAppMissingFieldError`, `WebAppParseError`,
`FeatureUnavailableError`) all carry a sensible default hint — override it with `hint=...` on the
raise if you need something more specific.

---

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `MAX_BOT_TOKEN` | ✅ | Bot token from Max |
| `AIOSCAM_ENV` | ❌ | `debug` / `test` / `prod` (default: `prod`) |


---

## License

[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0) — free for personal, educational, and other noncommercial use. Commercial use requires a separate license — contact the author.
