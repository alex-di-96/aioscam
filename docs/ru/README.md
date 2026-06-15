# AioScam — Документация (RU)

**v0.1.8** | [English](../en/README.md)

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
16. [Конфигурация](#конфигурация)

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
└── utils/        # KeyboardBuilder, formatting, deep_linking, media
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

await dp.start_polling(bot, skip_updates=True)
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
