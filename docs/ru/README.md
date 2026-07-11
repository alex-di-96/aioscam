# AioScam — Документация (RU)

**v0.2.1** | [English](../en/README.md)

## Оглавление

1. [Установка](#установка)
2. [Быстрый старт](#быстрый-старт)
3. [Архитектура](#архитектура)
4. [Bot — методы](#bot)
5. [Медиафайлы](#медиафайлы)
6. [Dispatcher и Router](#dispatcher-и-router)
7. [EventContext](#eventcontext)
8. [Фильтры](#фильтры)
9. [FSM](#fsm)
10. [Middleware](#middleware)
11. [Клавиатуры](#клавиатуры)
12. [Deep links](#deep-links)
13. [I18n](#i18n)
14. [Rate Limiter](#rate-limiter)
15. [Webhook](#webhook)
16. [WebApp (мини-приложения)](#webapp-мини-приложения)
17. [BotCapabilities](#botcapabilities)
18. [ChatRegistry — реестр чатов](#chatregistry--реестр-чатов)
19. [Опросы и квизы (PollManager)](#опросы-и-квизы-pollmanager)
20. [Миграция Max API v2 и сертификаты](#миграция-max-api-v2-и-сертификаты)
21. [Исключения и hint](#исключения-и-hint)
22. [Конфигурация](#конфигурация)

---

## Установка

```bash
# Из исходного кода (разработка)
git clone https://github.com/alex-di-96/aioscam.git
cd aioscam
pip install -e .

# С поддержкой FastAPI
pip install aioscam[fastapi]

# С поддержкой Litestar
pip install aioscam[litestar]

# Режим разработки (pytest, ruff, mypy)
pip install aioscam[dev]
```

`aioscam.webapp` (поддержка WebApp/мини-приложений) **не требует** отдельной установки — он
использует только `aiohttp` и `pydantic`, которые уже обязательны для базового пакета.
Отдельного `aioscam[webapp]` нет и не нужен: обычный `pip install aioscam` уже даёт
`validate_init_data`, `EventStreamManager` и `WebAppMiddleware`.

**Требования:** Python 3.9–3.12, aiohttp>=3.9, aiofiles>=23.0, pydantic>=2.0, magic-filter>=1.0

---

## Быстрый старт

```python
import asyncio
from aioscam import Bot, Dispatcher, Router
from aioscam.filters import Command

dp = Dispatcher()
router = Router()

@router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer("Привет! Напиши мне что-нибудь.")

@router.message_created()
async def echo(event):
    await event.answer(event.text)

dp.include_router(router)

async def main():
    bot = Bot()  # Токен из MAX_BOT_TOKEN
    await dp.start_polling(bot)

asyncio.run(main())
```

`.env`:
```env
MAX_BOT_TOKEN=ваш_токен
AIOSCAM_ENV=prod   # debug | test | prod
```

---

## Архитектура

```
aioscam/
├── bot/          # Bot — все API методы
├── client/       # HTTP клиент (aiohttp + rate limiter + upload/download)
├── dispatcher/   # Dispatcher, Router, EventContext, StateGuard
├── enums/        # 15 enum-файлов
├── exceptions/   # 12 классов исключений
├── filters/      # Command, Text, StartCommand, StateFilter, ContentType, F
├── fsm/          # State, StatesGroup, MemoryStorage
├── handler/      # MessageHandler, CallbackHandler, EventHandler
├── i18n/         # I18n — JSON-переводы, авто-локаль
├── limiter/      # RateLimiter, RateLimitConfig
├── methods/      # BaseMethod, GetMe, SendMessage, GetUpdates
├── middleware/   # BaseMiddleware, MiddlewareManager
├── types/        # Pydantic-модели (User, Chat, Message, Attachment, …)
├── utils/        # KeyboardBuilder, formatting, deep_linking, media, BotCapabilities
└── webapp/       # validate_init_data, validate_contact, EventStreamManager, WebAppMiddleware
```

---

## Bot

### Сообщения

```python
await bot.send_message(chat_id=123, user_id=456, text="Привет!", format="markdown")
await bot.edit_message(message_id="mid.abc", text="Новый текст")
await bot.delete_message(message_id="mid.abc")
await bot.send_action(chat_id=123, action=SenderAction.TYPING_ON)
```

### Медиафайлы

```python
# Отправка по пути (тип определяется по расширению)
await bot.send_photo(chat_id=123, user_id=456, photo="photo.jpg", caption="Фото!")
await bot.send_video(chat_id=123, user_id=456, video="video.mp4")
await bot.send_audio(chat_id=123, user_id=456, audio="song.mp3")
await bot.send_document(chat_id=123, user_id=456, document="report.pdf")
await bot.send_media(chat_id=123, user_id=456, media="file.ext")  # авто-тип

# Отправка из буфера памяти (без файла на диске)
from aioscam import InputMediaBuffer, UploadType
media = InputMediaBuffer(image_bytes, "photo.jpg", UploadType.IMAGE)
await bot.send_photo(chat_id=123, user_id=456, photo=media)

# Скачивание в память
data = await bot.download_file_bytes(url, token)  # → bytes | None

# Скачивание в файл
path = Bot.make_temp_path(".jpg")  # уникальное имя по datetime
await bot.download_file(path, url, token)          # → HTTP status code
```

### Callback и действия

```python
await bot.send_callback(callback_id=..., message="Ответ", notification="Попап")
await bot.send_action(chat_id=123, action=SenderAction.TYPING_ON)
```

### Чаты и пользователи

```python
me = await bot.get_me()
chats = await bot.get_chats()
chat = await bot.get_chat_by_id(chat_id=123)
members = await bot.get_chat_members(chat_id=123)
await bot.add_chat_members(chat_id=123, user_ids=[456, 789])
await bot.remove_member_chat(chat_id=123, user_id=456)
```

### Команды и информация бота

```python
from aioscam.types.command import BotCommand
await bot.set_my_commands([
    BotCommand(name="start", description="Запустить бота"),
    BotCommand(name="help", description="Справка"),
])
await bot.set_bot_info(name="Мой бот", description="Описание бота")
```

---

## Медиафайлы

### InputMedia — из файла

```python
from aioscam import InputMedia, UploadType

m = InputMedia("photo.jpg")       # → UploadType.IMAGE
m = InputMedia("video.mp4")       # → UploadType.VIDEO
m = InputMedia("song.mp3")        # → UploadType.AUDIO
m = InputMedia("doc.pdf")         # → UploadType.FILE
m = InputMedia("file", UploadType.IMAGE)  # явный тип
```

**Авто-определение по расширению:**
- `.jpg .jpeg .png .gif .webp .bmp` → IMAGE
- `.mp4 .mov .avi .mkv .webm` → VIDEO
- `.mp3 .ogg .wav .m4a .flac .aac .opus` → AUDIO
- всё остальное → FILE

### InputMediaBuffer — из памяти

```python
from aioscam import InputMediaBuffer, UploadType

b = InputMediaBuffer(bytes_data, "photo.jpg")            # тип из расширения
b = InputMediaBuffer(bytes_data, "file", UploadType.FILE)  # явный тип
```

### Скачивание входящих медиа

```python
# Из raw_update в хендлере:
raw = event.data.get("raw_update", {})
attachments = raw.get("message", {}).get("body", {}).get("attachments", [])

for att in attachments:
    payload = att.get("payload", {})
    url = payload.get("url")
    token = payload.get("token")

    if url and token:
        # Режим 1: в память (для обработки PIL, конвертации и т.д.)
        data = await event.bot.download_file_bytes(url, token)

        # Режим 2: в файл с уникальным именем
        from aioscam import Bot
        path = Bot.make_temp_path(".jpg")
        await event.bot.download_file(path, url, token)
```

### Стикеры

Боты **не могут отправлять** стикеры через Max Bot API. При получении:
```python
if att.get("type") == "sticker":
    code = att.get("payload", {}).get("code")   # код стикера
    url  = att.get("payload", {}).get("url")    # URL картинки
```

---

## Dispatcher и Router

```python
from aioscam import Dispatcher, Router

dp = Dispatcher(
    storage=MemoryStorage(),
    state_guard_commands={'/cancel', '/start'},
    state_guard_callbacks={'action:cancel'},
)

# Вложенные роутеры
admin_router = Router(name="admin")
user_router  = Router(name="user")
dp.include_router(admin_router)
dp.include_router(user_router)

# Политика обработки накопленных за даунтайм событий:
#   "skip"     — отбросить (по умолчанию; = устаревшему skip_updates=True)
#   "process"  — обработать все
#   "collapse" — схлопнуть повторы: 50 старых /start от одного юзера → один
await dp.start_polling(bot, backlog="collapse")
```

---

## EventContext

Контекст события — передаётся первым аргументом в каждый хендлер.

| Свойство | Тип | Описание |
|----------|-----|----------|
| `event` | Any | Сырой объект события |
| `bot` | Bot | Экземпляр бота |
| `data` | dict | Общие данные запроса |
| `user_id` | int\|None | ID пользователя |
| `chat_id` | int\|None | ID чата |
| `text` | str\|None | Текст сообщения |
| `payload` | str\|None | Deep link payload |
| `locale` | str\|None | Локаль пользователя |
| `callback_data` | str\|None | Данные callback-кнопки |
| `callback_id` | str\|None | ID callback (для send_callback) |
| `from_user` | User\|None | Отправитель |
| `message` | Message\|None | Объект сообщения |

**Методы:**
```python
await event.answer("Текст", keyboard=kb, format="markdown")
await event.hide_keyboard("Новый текст")
await event.answer_and_hide_keyboard("Текст", keyboard=new_kb)
```

---

## Фильтры

### Command

```python
@router.message_created(Command("start"))
@router.message_created(Command(["start", "help"]))  # несколько команд
```

Аргументы команды доступны через `command_args`:
```python
@router.message_created(Command("photo"))
async def cmd_photo(event, command_args: str = None):
    # /photo /path/to/file.jpg → command_args = "/path/to/file.jpg"
```

### StartCommand (Deep link)

```python
from aioscam import StartCommand

@router.bot_started(StartCommand())           # любой payload
@router.bot_started(StartCommand("ref_123"))  # точное совпадение
@router.bot_started(StartCommand(startswith="ref_"))  # префикс
@router.message_created(StartCommand())       # повторный вход через диплинк
```

Payload доступен через `start_payload`:
```python
async def handler(event, start_payload: str = None):
    print(start_payload)  # значение ?start=
```

### Text

```python
@router.message_created(Text("привет"))
@router.message_created(Text(contains=["слово1", "слово2"]))
@router.message_created(Text(startswith="prefix"))
@router.message_created(Text(regex=r"\d{4}"))
```

### StateFilter

```python
from aioscam import StateFilter

@router.message_created(StateFilter(MyState.waiting_name))
```

### Magic Filter

```python
from aioscam import F

@router.message_created(F.message.body.text.func(lambda t: "привет" in t.lower()))
@router.callback_query(F.callback_data.startswith("action:"))
@router.message_created(F.message.body.text == "")  # пустой текст (вложения)
```

---

## FSM

```python
from aioscam.fsm import State, StatesGroup

class MyState(StatesGroup):
    waiting_name  = State()
    waiting_age   = State()
    waiting_email = State()
    waiting_phone = State()

# В хендлере:
await state.set_state(MyState.waiting_name)
await state.update_data(name="Иван")
data = await state.get_data()    # {"name": "Иван"}
current = await state.get_state()  # "MyState:waiting_name"
await state.set_state(None)      # сброс
```

**StateGuard** — блокирует команды и callback-кнопки во время активного FSM состояния:
```python
from magic_filter import F

dp = Dispatcher(
    state_guard_commands={'/cancel', '/start'},
    state_guard_callbacks=[
        'action:cancel',                # exact match
        F.startswith('confirm_'),       # "confirm_yes|52507" — тоже пройдёт
        F.regexp(r'^nav:(back|next)$'),
    ],
    state_guard_hint_func=lambda s: "имя пользователя",
)
```
`state_guard_callbacks` — список из строк (exact match) и/или `magic_filter.F` выражений
(`.startswith()`, `.contains()`, `.regexp()`, комбинируются через `&` / `|` / `~`).
Список, а не `set` — `F`-выражения нехэшируемы.

---

## Middleware

```python
async def logging_middleware(event, handler):
    print(f"In: {event.text}")
    result = await handler(event)
    print(f"Done")
    return result

router.middleware()(logging_middleware)
```

---

## Клавиатуры

```python
from aioscam.utils.keyboard import KeyboardBuilder

builder = KeyboardBuilder(inline=True)

builder.callback("Кнопка", "action:click")
builder.link("Сайт", "https://example.com")
builder.request_contact("📱 Телефон")
builder.request_location("📍 Геолокация")
builder.clipboard("Копировать", "текст для копирования")
builder.row()  # новая строка

keyboard = builder.build().to_dict()
await event.answer("Выберите:", keyboard=keyboard)
```

**Типы кнопок:** `callback`, `link`, `chat`, `message` (switch), `clipboard`, `open_app`, `request_contact`, `request_geo_location`

---

## Deep links

```python
from aioscam.utils.deep_linking import create_deep_link, parse_deep_link

link = create_deep_link("mybot", "ref_123")
# → "https://max.ru/mybot?start=ref_123"

info = parse_deep_link(link)
# → {"bot_username": "mybot", "start": "ref_123"}
```

**Обработка первого входа:**
```python
@router.bot_started(StartCommand())
async def on_deeplink(event, start_payload: str = None):
    print(f"Payload: {start_payload}")
    print(f"event.payload: {event.payload}")  # то же самое
```

**Повторный вход** — Max присылает `message_created` с текстом `/start <payload>`:
```python
@router.message_created(StartCommand())
async def on_repeat_deeplink(event, start_payload: str = None):
    print(f"Repeat visit with payload: {start_payload}")
```

---

## I18n

```python
from aioscam import I18n

i18n = I18n(path="locales/", default_locale="ru")

@router.message_created(Command("start"))
async def cmd_start(event):
    locale = event.locale or "ru"
    text = i18n.get("welcome", locale=locale)
    await event.answer(text)
```

Файл `locales/ru.json`:
```json
{
  "welcome": "Добро пожаловать!",
  "help": "Справка"
}
```

---

## Rate Limiter

```python
from aioscam import Bot
from aioscam.limiter import RateLimitConfig

bot = Bot(rate_limit=RateLimitConfig(
    rate=10.0,      # запросов в секунду
    burst=20,       # максимальный burst
    max_retries=3,  # попыток при 429
    backoff_base=1.0,
))

# Пресеты:
bot = Bot(rate_limit=RateLimitConfig.strict())   # 5 req/s
bot = Bot(rate_limit=RateLimitConfig.relaxed())  # 30 req/s
```

---

## Webhook

```python
await dp.handle_webhook(
    bot=bot,
    host="0.0.0.0",
    port=8080,
    path="/webhook",
    secret_token="your_secret",
)
```

---

## WebApp (мини-приложения)

Max открывает мини-приложения (WebApp) как обычный HTML/CSS/JS внутри WebView клиента.
`aioscam.webapp` — серверная часть: проверка того, что присылает страница, и push-уведомления
обратно через SSE.

### Валидация `initData`

Каждая страница мини-приложения получает подписанную строку `initData` из `window.WebApp.initData`.
Проверяйте её на сервере перед тем как доверять содержимому:

```python
from aioscam.webapp import validate_init_data, WebAppSignatureError, WebAppExpiredError

try:
    data = validate_init_data(raw_init_data, bot_token, max_age=3600)
except WebAppSignatureError:
    ...  # подпись не совпала — данные подделаны или не тот bot_token
except WebAppExpiredError:
    ...  # auth_date старше max_age

print(data.user.id, data.start_param)
```

`validate_contact(...)` — аналогичная HMAC-проверка для payload из `requestContact()`.

### Push-уведомления в WebApp (SSE)

```python
from aioscam.webapp import EventStreamManager

events = EventStreamManager()

# в хендлере роута /api/events:
async def sse_handler(request):
    return await events.stream(request, user_id=data.user.id)

# в любом другом месте бота:
await events.publish(user_id=123, {"type": "bot_message", "text": "привет из бота"})
await events.broadcast({"type": "announcement", "text": "деплой завершён"})
```

`EventSource` (браузерный API под SSE) не умеет ставить кастомные заголовки, поэтому страница
передаёт `initData` через query-параметр: `GET /api/events?initData=<raw>`.
`WebAppMiddleware` принимает `initData` из `Authorization: MaxWebApp <raw>`, заголовка
`X-Webapp-Init-Data` или `?initData=` — именно в этом порядке.

### Защита `/api/*` роутов

```python
from aioscam.webapp.aiohttp import WebAppMiddleware

app.middlewares.append(WebAppMiddleware(bot_token=bot.token))
```

Middleware валидирует только запросы с путём, начинающимся на `/api`; всё остальное (включая
`/static/*` и HTML-страницы) остаётся без проверки и доступно публично. Коды ошибок разделены
намеренно: если `initData` вообще не было в запросе — middleware отвечает обычным 404
(неотличимым от незарегистрированного роута), а если `initData` пришло, но не прошло проверку
(неверная подпись, истёк срок, повреждённый формат) — 401. Слепой перебор путей, который не
отправляет `initData`, не может отличить `/api/me` от 404 на несуществующем пути.

### Главная страница

`HomePage` даёт корню сервера безопасный контент вместо хардкод `index.html`: имя/описание бота
(из `bot.get_me()`) и кнопку "Open in Max" — без JS, без намёка на `/api/*`. Реальный фронтенд
мини-приложения монтируйте под отдельным путём и именно его регистрируйте как Mini App URL в
Max bot dashboard — не голый корень:

```python
from aioscam.webapp.aiohttp import HomePage

app.router.add_get("/", HomePage(bot).handler)              # публичная landing-страница
app.router.add_get("/app", serve_index)                     # Mini App URL из dashboard
app.router.add_static("/app", path=str(STATIC_DIR))
```

`HomePage(bot, title=..., description=..., extra_head=..., extra_body=...)` позволяет переопределить
текст или добавить свою разметку/скрипты поверх дефолтного каркаса — см. `examples/webapp_bot.py`.

### Маскировка `/api/*` от сканеров

Разделение 404/401 уже скрывает факт существования роута от тех, кто не отправляет `initData`.
Чтобы поднять планку против сканеров по словарю (которые пробуют типовые имена `/api`, `/api/me`,
`/api/auth`), уберите API с известного префикса `/api` через `api_prefix` и добавьте
`WebAppFailGuard`, чтобы вовсе перестать отвечать адресам, которые систематически не проходят
проверку:

```python
from aioscam.webapp.aiohttp import WebAppFailGuard, WebAppMiddleware

guard = WebAppFailGuard(max_failures=20, window=60, ban_seconds=300)
app.middlewares.append(
    WebAppMiddleware(bot_token=bot.token, api_prefix="/a8f3e1", fail_guard=guard)
)
```

После `max_failures` неудачных проверок за `window` секунд каждый запрос с этого адреса получает
плоский 404 на `ban_seconds` — проверка подписи даже не выполняется. Это доп. рубеж защиты против
автоматического перебора, а не замена самой HMAC-проверки. Не забудьте, что запросы фронтенда
(`fetch`/`EventSource`) должны идти на тот же `api_prefix` — см. как это сделано в
`examples/webapp_bot.py` ниже.

Полный рабочий пример — REST-эндпоинты (`/api/auth`, `/api/contact`, `/api/send`), SSE-эндпоинт
и 4 фронтенд-страницы — в `examples/webapp_bot.py` + `examples/webapp/*.html`. Запустите его с
`WEBAPP_API_PREFIX=/your-secret`, и весь API переедет на новый префикс целиком: сервер на лету
подменяет строку `const API_PREFIX = "/api";` в каждой отдаваемой странице, так что фронтенд
узнаёт реальный префикс без шага сборки и без дублирования значения вручную.

---

## BotCapabilities

`GET /me` в Max API не отдаёт поле permissions/capabilities, поэтому `BotCapabilities` собирает
картину из профиля бота и конфигурации, чтобы не дать вам предположить наличие функций, которые
на самом деле не настроены:

```python
from aioscam.utils.capabilities import BotCapabilities

caps = await BotCapabilities.probe(bot, webapp_url="https://example.com/webapp")
caps.log_report(logger)  # структурированный баннер при старте, включая warnings
```

Фичи Bridge SDK (haptic, биометрия, NFC, QR, контакты) — клиентские: сервер не может знать
платформу пользователя, поэтому они не входят в этот отчёт; проверяйте `window.WebApp.platform`
на фронтенде.

---

## ChatRegistry — реестр чатов

В июне 2026 Max удалил `GET /chats`: бот больше не может спросить сервер, в каких чатах он
состоит. `ChatRegistry` восстанавливает это знание на стороне бота и хранит в SQLite
(`.aioscam/bot.db` — общая база всех компонентов фреймворка):

```python
from aioscam import Bot, Dispatcher, ChatRegistry

registry = ChatRegistry()
dp = Dispatcher(registry=registry)
await dp.start_polling(bot, backlog="collapse")

await registry.chats()      # все известные чаты — без единого API-запроса
await registry.groups()     # только группы (type="chat")
await registry.dialogs()    # диалоги
await registry.get(chat_id) # один чат
```

**Как реестр пополняется:**
- события `bot_added` / `bot_started` / `chat_title_changed` применяются автоматически;
  `bot_removed` / `dialog_removed` помечают чат удалённым (soft-delete, строка остаётся);
- **lazy-discovery** — любое событие из неизвестного чата регистрирует его;
- **persist marker** — позиция long polling сохраняется: после рестарта бот продолжает с
  места остановки, и события даунтайма (например, добавление в группу) не теряются;
- реестровые события применяются к базе **во всех** backlog-режимах, даже при `"skip"`.

**Ручная сверка** (у Max нет события «права изменились» — только периодическая проверка):

```python
stats = await registry.sync(bot)
# {'bootstrapped': N, 'checked': N, 'updated': N, 'removed': N}
```

`sync()` делает best-effort bootstrap через deprecated `GET /chats` (пока Max его не отключил),
затем точечные `GET /chats/{id}` по каждому известному чату (403/404 → removed) и обновляет
права бота через `GET /chats/{id}/members/me` с TTL-кэшем (по умолчанию час).

Пример: `examples/registry_bot.py`.

---

## Опросы и квизы (PollManager)

В Max Bot API **нет нативных опросов** (в отличие от Telegram). `PollManager` эмулирует их
inline-кнопками: голоса в SQLite (переживают рестарт), live-бары в сообщении, локализованные
подсказки (ru/en в комплекте — уведомления на языке кликающего, текст сообщения на языке
создателя; сам контент опроса не переводится).

```python
from aioscam import PollManager

polls = PollManager()               # та же .aioscam/bot.db
polls.attach(dp, command="poll")    # хендлер голосов + команда /poll + StateGuard-allowlist
```

Пользователи создают опросы прямо из чата:

```
/poll Куда идём обедать? | Кафе | Столовая | Останемся
/poll priv Оценка релиза? | 5 | 4 | 3
/poll pub Кто за пятницу? | За | Против
```

Режимы видимости:

| Режим | Что видно в сообщении |
|-------|----------------------|
| `pub` | бары + имена проголосовавших под каждым вариантом |
| `anon` | только бары и цифры (по умолчанию) |
| `priv` | только «Проголосовало: N»; раскладку видит автор по кнопке «📊 Результаты» (privates-уведомление) |

Программно (bot-driven):

```python
poll_id = await polls.send_poll(bot, chat_id, "Вопрос?", ["Да", "Нет"],
                                visibility="pub", creator_id=admin_id)
# creator_id=None → «ничейный» опрос: кнопок управления нет, закрыть можно только кодом

await polls.send_quiz(bot, chat_id, "2+2?", ["3", "4"], correct_option=1,
                      explanation="Арифметика.")   # ✅/❌ мгновенно, приватно

results = await polls.results(poll_id)   # счётчики в любой момент
await polls.close_poll(bot, poll_id)     # завершить: клавиатура убирается,
                                         # квиз раскрывает правильный ответ
```

Механика голосования: одиночный выбор — голос можно перенести; `multiple=True` — тумблер;
квиз — один ответ навсегда. `attach()` добавляет payload-префикс опросов и команду `/poll`
в allowlist StateGuard — пользователь внутри FSM-диалога всё равно может голосовать.

Пример: `examples/poll_bot.py`.

---

## Миграция Max API v2 и сертификаты

**До 19 июля 2026** все боты обязаны переехать на `platform-api2.max.ru` — старые домены
(`platform-api.max.ru`, `botapi.max.ru`) отключаются. aioscam ≥0.2.2 делает это из коробки:

- дефолтный base URL — `platform-api2.max.ru`; `/answers` (ответы на callback) теперь на том
  же домене, отдельного callback-домена больше нет;
- новый сервер подписан сертификатом **Минцифры** (Russian Trusted CA), которого нет в
  системных хранилищах большинства не-российских ОС. Фреймворк **включает официальные
  сертификаты в пакет** (`aioscam/certs/`, скачаны с gosuslugi.ru) и доверяет им только для
  соединений бота — системное хранилище не затрагивается, ничего устанавливать не нужно;
- переопределение: `Bot(ssl_context=...)` / `AioScamClient(ssl_context=...)`;
- лимит нового сервера — 30 запросов/сек (дефолт RateLimiter — 10/с, с запасом);
- `GET /chats` удалён из API — `Bot.get_chats()` помечен deprecated, используйте
  [ChatRegistry](#chatregistry--реестр-чатов).

---

## Исключения и hint

Каждое исключение фреймворка несёт `.hint` — конкретную причину или фикс — он автоматически
добавляется при `str()`:

```python
try:
    bot = Bot()
except BotTokenError as e:
    print(e)  # "Bot token is not provided — pass token=... to Bot(), or set the MAX_BOT_TOKEN environment variable"
    print(e.hint)  # только hint
```

`ApiError`, `NetworkError`, `TimeoutError`, `RetryAfter`, `UnauthorizedError`, `ForbiddenError`,
`NotFoundError`, `BotTokenError`, `DispatcherError` и исключения `WebApp*`
(`WebAppSignatureError`, `WebAppExpiredError`, `WebAppMissingFieldError`, `WebAppParseError`,
`FeatureUnavailableError`) несут дефолтный hint — переопределяется через `hint=...` при raise,
если нужна более конкретная подсказка.

---

## Конфигурация

| Переменная | Обязательно | Описание |
|------------|-------------|----------|
| `MAX_BOT_TOKEN` | ✅ | Токен бота |
| `AIOSCAM_ENV` | ❌ | `debug` / `test` / `prod` (умолч. `prod`) |

```python
from aioscam.config import get_config
config = get_config()
print(config.token, config.env)
```

---

## Лицензия

[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0) — бесплатно для личного, образовательного и некоммерческого использования. Коммерческое использование требует отдельного соглашения — свяжитесь с автором.
