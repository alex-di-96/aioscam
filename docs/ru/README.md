# AioScam — Документация

## Версия

**v0.1.1** — Production Ready

## Оглавление

1. [Установка](#установка)
2. [Быстрый старт](#быстрый-старт)
3. [Архитектура](#архитектура)
4. [Bot](#bot)
5. [Dispatcher и Router](#dispatcher-и-router)
6. [Фильтры](#фильтры)
7. [FSM](#fsm)
8. [Middleware](#middleware)
9. [Клавиатуры](#клавиатуры)
10. [Webhook](#webhook)
11. [Конфигурация](#конфигурация)

---

## Установка

```bash
# Базовая установка
pip install aioscam

# С поддержкой FastAPI
pip install aioscam[fastapi]

# Для разработки
pip install aioscam[dev]

# Из исходного кода
git clone https://github.com/alex-di-96/aioscam.git
cd aioscam
pip install -e .
```

### Требования

- Python 3.9–3.12
- aiohttp >= 3.9.0
- magic-filter >= 1.0.0
- pydantic >= 2.0.0

---

## Быстрый старт

### Эхо-бот (режим polling)

```python
import asyncio
from aioscam import Bot, Dispatcher, Router
from aioscam.filters import Command

dp = Dispatcher()
router = Router()

@router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer("Привет! Напиши мне что-нибудь!")

@router.message_created()
async def echo(event):
    await event.answer(event.message.body.text)

dp.include_router(router)

async def main():
    bot = Bot()  # Токен из переменной окружения MAX_BOT_TOKEN
    await dp.start_polling(bot)

asyncio.run(main())
```

### Переменная окружения

Создайте файл `.env`:

```env
MAX_BOT_TOKEN=ваш_токен_бота
AIOSCAM_ENV=prod
```

---

## Архитектура

```
aioscam/
├── bot/              # Клиент бота (35 API методов)
├── client/           # HTTP клиент (обёртка aiohttp)
├── dispatcher/       # Dispatcher, Router, EventContext, StateGuard
├── enums/            # Перечисления (12 файлов)
├── exceptions/       # Классы исключений
├── filters/          # BaseFilter, Command, Text, State, Magic Filters
├── fsm/              # State, StatesGroup, MemoryStorage, Scene
├── handler/          # MessageHandler, CallbackHandler, EventHandler
├── methods/          # Обёртки API методов
├── middleware/       # BaseMiddleware, MiddlewareManager
├── types/            # Pydantic модели (User, Chat, Message и др.)
├── utils/            # KeyboardBuilder, форматирование, deep linking
└── webhook/          # Обработчик веб-хуков aiohttp
```

---

## Bot

### Основные методы

#### `send_message()`

Отправка текстового сообщения.

```python
msg = await bot.send_message(
    chat_id=123456,
    text="Привет, мир!",
    user_id=789012
)
```

**Параметры:**
- `chat_id: int | str` — ID чата
- `text: str` — Текст сообщения
- `user_id: int | None` — ID пользователя (для личных сообщений)
- `reply_to_mid: str | None` — ID сообщения для ответа
- `keyboard: dict | None` — Inline клавиатура

**Возвращает:** `dict` — данные отправленного сообщения

#### `edit_message()`

Редактирование сообщения.

```python
await bot.edit_message(
    chat_id=123456,
    message_id="mid.abc123",
    text="Обновлённый текст"
)
```

#### `delete_message()`

Удаление сообщения.

```python
await bot.delete_message(
    chat_id=123456,
    user_id=789012,
    message_id="mid.abc123"
)
```

#### `request_contact()`

Запрос контактной информации.

```python
await bot.request_contact(
    chat_id=123456,
    text="Поделитесь контактом:",
    button_text="📱 Поделиться контактом"
)
```

#### `request_location()`

Запрос геолокации.

```python
await bot.request_location(
    chat_id=123456,
    text="Поделитесь геолокацией:",
    button_text="📍 Поделиться местоположением"
)
```

---

## Dispatcher и Router

### Dispatcher

Центральный компонент обработки обновлений.

```python
from aioscam import Dispatcher

dp = Dispatcher()
await dp.start_polling(bot)  # Режим polling
```

### Router

Маршрутизатор для обработки сообщений.

```python
from aioscam import Router

router = Router()

# Вложенные роутеры
admin_router = Router(name="admin")
user_router = Router(name="user")

router.include_router(admin_router)
router.include_router(user_router)
dp.include_router(router)
```

### EventContext

Контекст события, передаваемый в обработчики.

**Атрибуты:**
- `event` — данные события
- `bot` — экземпляр бота
- `data` — общие данные
- `state` — контекст FSM

---

## Фильтры

### Command

Фильтрация по командам.

```python
from aioscam.filters import Command

@router.message_created(Command("start"))
async def cmd_start(event):
    ...
```

### Text

Фильтрация по тексту.

```python
from aioscam.filters import Text

@router.message_created(Text(contains="привет"))
async def handle_greeting(event):
    ...

@router.message_created(Text(startswith="/"))
async def handle_slash(event):
    ...
```

### Magic Filters

Декларативная фильтрация.

```python
from aioscam.filters import F

@router.message_created(F.message.body.text.func(lambda t: "привет" in t.lower()))
async def handle_hello(event):
    ...

@router.message_created(F.callback.payload.startswith("action:"))
async def handle_callback(event):
    ...
```

---

## FSM

### State и StatesGroup

```python
from aioscam.fsm import State, StatesGroup

class Registration(StatesGroup):
    name = State()
    email = State()
    phone = State()
```

### Использование

```python
@router.message_created(Command("register"))
async def cmd_register(event, state):
    await state.set_state(Registration.name)
    await event.answer("Введите имя:")

@router.message_created(Registration.name)
async def process_name(event, state):
    await state.update_data(name=event.message.body.text)
    await state.set_state(Registration.email)
    await event.answer("Введите email:")

@router.message_created(Registration.email)
async def process_email(event, state):
    data = await state.get_data()
    await event.answer(f"Зарегистрирован: {data['name']}")
    await state.set_state(None)  # Сброс состояния
```

### Методы StateContext

- `get_state()` — получить текущее состояние
- `set_state(state)` — установить состояние
- `get_data()` — получить данные
- `update_data(**kwargs)` — обновить данные
- `clear()` — очистить данные

---

## Middleware

### Создание

```python
from aioscam.middleware import BaseMiddleware

class LoggingMiddleware(BaseMiddleware):
    async def on_message(self, event, handler):
        print(f"Получено: {event.message.body.text}")
        return await handler(event)
```

### Регистрация

```python
router.message.middleware(LoggingMiddleware())
```

---

## Клавиатуры

### KeyboardBuilder

```python
from aioscam.utils import KeyboardBuilder

builder = KeyboardBuilder(inline=True)

# Callback кнопка
builder.callback("Кнопка 1", "action:one")

# Ссылка
builder.link("Открыть сайт", "https://example.com")

# Новый ряд
builder.row()

# Запрос контакта
builder.request_contact("📱 Поделиться контактом")

# Запрос геолокации
builder.request_location("📍 Поделиться местоположением")

# Отправка
await event.answer("Выберите:", keyboard=builder.build().to_dict())
```

### Типы кнопок

| Тип | Описание |
|-----|----------|
| `callback` | Callback-кнопка |
| `link` | Ссылка |
| `chat` | Переход в чат |
| `message` | Переход к сообщению |
| `clipboard` | Копирование в буфер |
| `open_app` | Открыть приложение |
| `request_contact` | Запрос контакта |
| `request_geo_location` | Запрос геолокации |
| `attachment` | Вложение |

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

## Конфигурация

### Переменные окружения

| Переменная | Обязательно | Описание |
|------------|-------------|----------|
| `MAX_BOT_TOKEN` | ✅ | Токен бота из Max Bot API |
| `AIOSCAM_ENV` | ❌ | Окружение: `debug`, `test`, `prod` (по умолчанию: `prod`) |
| `MAX_BASE_URL` | ❌ | URL API (по умолчанию: `https://platform-api.max.ru`) |

### Использование

```python
from aioscam.config import get_config

config = get_config()
print(config.token)
print(config.env)  # debug, test, prod
```

### Режимы

- `debug` — подробное логирование
- `test` — минимальное логирование
- `prod` — production режим
