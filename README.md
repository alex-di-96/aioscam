# AioScam

Async Python framework for building Max messenger bots, inspired by aiogram architecture.

## Version

**v0.2.2** — Latest (2026-07-11)

### What's new in v0.2.2

> ⚠️ **Max API v2 migration** — old API domains shut down on **July 19, 2026**.
> Upgrade to this version to keep your bots alive.

- ✅ **Max API v2** — default base URL is now `platform-api2.max.ru`; all chat methods
  rewritten to the official path-param endpoints (`/chats/{id}/members/...`, `PUT /chats/{id}/pin`, …)
- ✅ **Mintsifry CA bundled** — `platform-api2.max.ru` is signed by the Russian Trusted CA, which
  most non-Russian systems don't trust; aioscam ships the official certificates (`aioscam/certs/`)
  and trusts them **only for bot API connections** — no system-wide certificate install needed
- ✅ **`ChatRegistry`** — Max removed `GET /chats`; the registry rebuilds "which chats am I in?"
  on the bot side: SQLite storage, auto-fill from events, persisted polling marker
  (restart resumes where you stopped), `sync()` reconciliation via per-chat lookups
- ✅ **Backlog policies** — `start_polling(bot, backlog="skip"|"process"|"collapse")`;
  `collapse` turns 50 stale `/start` presses from one user into a single event; fixed `skip_updates`,
  which silently skipped only ONE pending update
- ✅ **`PollManager`** — polls and quizzes for Max (the platform has no native ones): inline-keyboard
  emulation with live result bars, `priv`/`anon`/`pub` visibility, built-in `/poll` command,
  votes in SQLite, localized hints (ru/en)
- ✅ **Shared bot database** — one `.aioscam/bot.db` for all framework components
- ✅ **714/714 tests passing**, live-verified against `platform-api2.max.ru`

### What's new in v0.2.1
- ✅ **`HomePage`** — generic landing page for the server root, so a plain visitor/scanner sees a
  normal-looking page with no hint that `/api/*` exists; mount the real Mini App frontend under
  its own path instead
- ✅ **`WebAppMiddleware` 404/401 split** — a request with no `initData` at all now gets a plain 404
  (looks like the route doesn't exist); only a present-but-wrong signature gets 401
- ✅ **`api_prefix`** — move the API off the well-known `/api` path; `examples/webapp_bot.py` wires
  it through `WEBAPP_API_PREFIX` end to end, including server-side template rewriting for all 4
  frontend pages
- ✅ **`WebAppFailGuard`** — in-memory sliding-window per-IP ban for repeat failed-auth probing
- ✅ **633/633 tests passing**

### What's new in v0.2.0
- ✅ **`aioscam.webapp`** — server-side module for Max WebApps (mini apps): `validate_init_data()` /
  `validate_contact()` (HMAC-SHA256), `EventStreamManager` (SSE push, Bot → WebApp), `WebAppMiddleware`
  (validates `initData` on `/api/*` requests, static files stay public)
- ✅ **`BotCapabilities`** — `BotCapabilities.probe(bot)` reports what the bot can actually do at
  startup, since `GET /me` carries no permissions field; `caps.log_report(logger)` prints a banner
- ✅ **Hint-based exceptions everywhere** — every framework exception now carries a `.hint` with a
  concrete cause/fix, appended automatically to `str(exc)` (`ApiError`, `NetworkError`, `RetryAfter`,
  `UnauthorizedError`, `BotTokenError`, `DispatcherError`, and the new `WebApp*` exceptions)
- ✅ **`examples/webapp_bot.py` + `examples/webapp/*.html`** — working bot with a REST+SSE API and
  4 frontend pages (native Bridge SDK reference, Vue 3 demo, Chart.js, sortable table)
- ✅ **604/604 tests passing**

### What's new in v0.1.8.1
- ✅ **`AIOSCAM_ENV` / `AIOSCAM_API_URL`** — исправлен регистр env-переменных (`Aioscam_ENV` → `AIOSCAM_ENV`), на Linux mixed-case переменные не работали
- ✅ **PolyForm Noncommercial License 1.0.0** — смена лицензии с MIT

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
- 🪟 **WebApp (Mini Apps)** — `initData`/contact validation, SSE push (Bot → WebApp), `/api/*` middleware
- 📊 **`BotCapabilities`** — capability/permission report logged at startup
- 💡 **Hint-based exceptions** — every error tells you what to actually do about it
- 📇 **ChatRegistry** — bot-side chat list (Max removed `GET /chats`), persisted polling marker
- 🗳️ **Polls & Quizzes** — `PollManager` emulation with `/poll` command (no native polls in Max API)
- 🔐 **Mintsifry CA bundled** — works with `platform-api2.max.ru` out of the box, no system cert install
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

`aioscam.webapp` (WebApp/Mini App support — `validate_init_data`, `EventStreamManager`,
`WebAppMiddleware`) needs **no extra install** — it only uses `aiohttp` and `pydantic`, both
already required by the base package. A plain `pip install aioscam` is enough.

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

## WebApp (Max Mini Apps)

Server-side helpers for two-way communication between your bot and a Max WebApp (mini app) running
in the client's WebView:

```python
from aioscam.webapp import validate_init_data, EventStreamManager
from aioscam.webapp.aiohttp import WebAppMiddleware
from aioscam.utils.capabilities import BotCapabilities

# Validate the signed initData a WebApp page sends you
data = validate_init_data(raw_init_data, bot_token)  # -> WebAppInitData (HMAC-SHA256 checked)

# Push events from the bot to a connected WebApp over SSE
events = EventStreamManager()
await events.publish(user_id, {"type": "bot_message", "text": "hi from the bot"})

# Protect your /api/* routes (static files stay public)
app.middlewares.append(WebAppMiddleware(bot_token=bot.token))

# Log what this bot can actually do at startup
caps = await BotCapabilities.probe(bot, webapp_url="https://example.com/webapp")
caps.log_report(logger)
```

Serve the server's HTTP root with a generic landing page instead of a hand-written `index.html` —
works with no JS (plain "Open in Max" link) and gives a scanner/plain visitor no hint that `/api/*`
exists. Mount your actual Mini App frontend under its own path (e.g. `/app`) and register
*that* path in the Max bot dashboard, not the bare root:

```python
from aioscam.webapp.aiohttp import HomePage

app.router.add_get("/", HomePage(bot).handler)
```

`WebAppMiddleware` already returns 404 (not 401) when a request carries no `initData` at all, so
blind probing of `/api/*` paths looks identical to a route that doesn't exist — only requests with
a (wrong) signature get a 401. For stronger masking, move the API off the well-known `/api` prefix
and add a `WebAppFailGuard` to flat-404 repeat offenders instead of letting them keep guessing:

```python
from aioscam.webapp.aiohttp import WebAppFailGuard, WebAppMiddleware

guard = WebAppFailGuard(max_failures=20, window=60, ban_seconds=300)
app.middlewares.append(
    WebAppMiddleware(bot_token=bot.token, api_prefix="/a8f3e1", fail_guard=guard)
)
```

Full working example with a REST+SSE backend and 4 frontend pages (native Bridge SDK reference,
Vue 3, Chart.js, sortable table): `examples/webapp_bot.py` + `examples/webapp/*.html` — run it with
`WEBAPP_API_PREFIX=/your-secret` to see `api_prefix` move the whole API and have the frontend pick
it up automatically (the server rewrites `const API_PREFIX = "/api";` in each served page).

## Rate Limiter

```python
from aioscam import Bot
from aioscam.limiter import RateLimitConfig

bot = Bot(rate_limit=RateLimitConfig.strict())   # 5 req/s, burst 10
bot = Bot(rate_limit=RateLimitConfig.relaxed())  # 30 req/s, burst 50
```

## Max API v2 (July 2026 migration)

Max shuts down the old API domains on **July 19, 2026**. aioscam ≥0.2.2 talks to
`platform-api2.max.ru` by default and bundles the Mintsifry (Russian Trusted) CA
certificates the new server is signed with — trust is scoped to the bot's HTTPS
connections only, your system trust store is never touched:

```python
bot = Bot()                          # just works on platform-api2.max.ru
bot = Bot(ssl_context=my_context)    # override if you need a custom trust chain
```

## Chat Registry

Max removed `GET /chats` — a bot can no longer ask the server which chats it is in.
`ChatRegistry` rebuilds that knowledge bot-side and persists it in SQLite:

```python
from aioscam import Bot, Dispatcher, ChatRegistry

registry = ChatRegistry()               # .aioscam/bot.db
dp = Dispatcher(registry=registry)

# backlog policy: what to do with updates accumulated while the bot was down
#   "skip"     — drop them (registry is still updated from ALL of them, in order)
#   "process"  — dispatch everything
#   "collapse" — 50 stale /start presses from one user become one event
await dp.start_polling(bot, backlog="collapse")

groups = await registry.groups()        # local, zero API calls
chats  = await registry.chats()
stats  = await registry.sync(bot)       # reconcile against live API + refresh bot permissions
```

The long-polling marker is persisted too: a restart resumes exactly where the bot
stopped, so `bot_added` events from downtime are not lost.

## Polls & Quizzes

Max Bot API has no native polls — `PollManager` emulates them over inline keyboards
with votes in SQLite and live result bars in the message:

```python
from aioscam import PollManager

polls = PollManager()                   # same .aioscam/bot.db
polls.attach(dp, command="poll")        # users get: /poll [priv|anon|pub] Вопрос | вар1 | вар2

# bot-driven poll (creator_id=None → no control buttons, close via code only)
poll_id = await polls.send_poll(bot, chat_id, "Deploy on Friday?", ["Yes", "No"],
                                visibility="pub", creator_id=admin_id)

await polls.send_quiz(bot, chat_id, "2+2?", ["3", "4"], correct_option=1,
                      explanation="Arithmetic.")

results = await polls.results(poll_id)
await polls.close_poll(bot, poll_id)
```

Visibility: `pub` shows voter names, `anon` shows aggregate bars, `priv` hides
everything — the creator reads the breakdown via a private "📊 Results" button.
Hint strings are localized (bundled ru/en): notifications follow the clicking
user's client locale, the shared message follows the creator's.

## API Coverage

| Category | Methods |
|----------|---------|
| **Bot Info** | `get_me`, `get_me_from_chat`, `change_info`, `set_bot_info`, `set_my_commands` |
| **Messages** | `send_message`, `edit_message`, `delete_message`, `get_message`, `get_messages`, `pin_message`, `delete_pin_message`, `get_pin_message` |
| **Media** | `send_photo`, `send_video`, `send_audio`, `send_document`, `send_media`, `download_file`, `download_file_bytes`, `get_upload_url`, `get_video` |
| **Callbacks** | `send_callback`, `send_action` |
| **Chats** | `get_chat_by_id`, `get_chat_by_link`, `edit_chat`, `delete_chat`, `add_chat_members`, `remove_member_chat`, `add_list_admin_chat`, `remove_admin`, `get_chat_members`, `get_chat_member`, `get_list_admin_chat`, `delete_me_from_chat`; ~~`get_chats`~~ (removed from Max API June 2026 — use `ChatRegistry`) |
| **Updates** | `get_updates`, `get_last_marker` |
| **Webhooks** | `subscribe_webhook`, `unsubscribe_webhook`, `get_subscriptions` |

**14 event types:** `message_created`, `message_callback`, `message_edited`, `message_removed`, `bot_started`, `bot_stopped`, `bot_added`, `bot_removed`, `chat_title_changed`, `dialog_cleared`, `dialog_muted`, `dialog_unmuted`, `user_added`, `user_removed`

**8 button types:** `CallbackButton`, `LinkButton`, `ChatButton`, `MessageButton`, `ClipboardButton`, `OpenAppButton`, `RequestContactButton`, `RequestGeoLocationButton`

## Project Structure

```
aioscam/
├── bot/          # Bot client — all API methods
├── certs/        # Bundled Mintsifry CA (platform-api2.max.ru TLS)
├── client/       # HTTP client (aiohttp, rate-limited, file upload/download)
├── db.py         # Shared SQLite bot database (.aioscam/bot.db)
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
├── polls/        # PollManager — polls/quizzes over inline keyboards
├── registry/     # ChatRegistry — bot-side chat list, persisted marker
├── types/        # Pydantic models — User, Chat, Message, Attachment, etc.
├── utils/        # KeyboardBuilder, formatting, deep_linking, media, BotCapabilities
└── webapp/       # validate_init_data, validate_contact, EventStreamManager, WebAppMiddleware
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

**714/714 tests passing (100%)**

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
| `webapp_bot.py` | WebApp REST+SSE backend — `examples/webapp/*.html` frontends |
| `poll_bot.py` | Polls & quizzes — `/poll` command, bot-driven polls, priv/anon/pub |
| `registry_bot.py` | ChatRegistry — `/chats` from local registry, `/sync`, backlog policies |

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
