# Async / Webhook Fixes — 2026-05-28

**Коммит:** `da9e787`
**Ролбэк тег:** `pre-async-fixes` → `6e88c84`

---

## Контекст

Аудит выявил три места потери асинхронности и нарушения безопасности:

| # | Файл | Проблема | Приоритет |
|---|------|----------|-----------|
| 1 | `i18n/i18n.py` | `open()` + `json.load()` — блокирующий I/O | MEDIUM |
| 2 | `webhook/aiohttp.py` | Нет валидации `X-Max-Secret-Token` | MEDIUM |
| 3 | `dispatcher/dispatcher.py` | `shutdown_event` никогда не сигналится → вечный hang | LOW→HIGH |

---

## Fix 1 — I18n: блокирующий файловый I/O

**Файл:** `aioscam/i18n/i18n.py`

**Проблема:** `_load_translations()` вызывался из `__init__` с обычным `open()` + `json.load()`.
Если `I18n` создаётся внутри уже запущенного event loop — блокирует цикл.

**Исправление:**

```python
# БЫЛО:
def _load_translations(self):
    with open(file, "r") as f:
        self._translations[locale] = json.load(f)

# СТАЛО — три варианта использования:

# 1. Старый способ (обратно совместим):
i18n = I18n(path="locales", default_locale="ru")
# → _load_translations_sync() через Path.read_text() + json.loads()

# 2. Ленивый async (внутри event loop):
i18n = I18n(path="locales", default_locale="ru", lazy=True)
async def main():
    await i18n.reload()   # aiofiles — полностью async
    await dp.start_polling(bot)

# 3. Горячая перезагрузка без рестарта:
await i18n.reload()
```

**Новые методы:**
- `_load_translations_sync()` — sync загрузка через `Path.read_text()` (вызывается из `__init__` без `lazy=True`)
- `async def reload()` — async загрузка через `aiofiles.open()`
- `__init__(lazy=True)` — пропуск sync загрузки

**Обратная совместимость:** полная — `I18n(path=..., default_locale=...)` работает как раньше.

---

## Fix 2 — Webhook: отсутствующая валидация secret token

**Файл:** `aioscam/webhook/aiohttp.py`

**Проблема:** `AiohttpWebhookHandler.handle_request()` принимал **любые** запросы без проверки
токена. Злоумышленник мог слать произвольные updates в бот.

```python
# БЫЛО:
class AiohttpWebhookHandler(BaseWebhookHandler):
    async def handle_request(self, request):
        data = await request.json()
        # Сразу обрабатывает — без проверки!
```

**Исправление:**

```python
# СТАЛО:
handler = AiohttpWebhookHandler(
    bot, dp,
    path="/webhook",
    secret_token="my_secret",  # новый параметр
)

# handle_request() теперь:
# 1. Проверяет X-Max-Secret-Token header
# 2. Возвращает 401 при несовпадении
# 3. Логирует IP отклонённого запроса
```

**Примечание:** `Dispatcher.handle_webhook()` уже имел эту валидацию — теперь оба пути защищены.

---

## Fix 3 — Dispatcher: зависание shutdown_event

**Файл:** `aioscam/dispatcher/dispatcher.py`

**Проблема:** `handle_webhook()` создавал `asyncio.Event()`, но никогда его не устанавливал.
`await shutdown_event.wait()` ждал вечно. `except KeyboardInterrupt` в async контексте
не срабатывает — asyncio отменяет через `CancelledError`, а не KeyboardInterrupt.

```python
# БЫЛО — зависает навсегда:
shutdown_event = asyncio.Event()
await site.start()
await shutdown_event.wait()  # ← никто не вызовет .set()
```

**Исправление — signal handlers:**

```python
# СТАЛО:
stop_event = asyncio.Event()

def _signal_handler():
    stop_event.set()

loop.add_signal_handler(signal.SIGINT, _signal_handler)
loop.add_signal_handler(signal.SIGTERM, _signal_handler)

await site.start()
await stop_event.wait()  # ← корректно завершится по Ctrl+C или systemd stop
```

**Новые методы:**
- `dp.stop_webhook()` — программная остановка (например, по таймеру)
- `_webhook_stop_event` — инициализируется в `__init__` (не None → нет AttributeError)

**Windows:** `NotImplementedError` от `add_signal_handler` перехватывается, сервер
продолжает работу (на Windows используйте `webhook_bot.py`).

---

## Исправленный пример

**Файл:** `examples/webhook_bot.py`

| Было | Стало |
|------|-------|
| `while True: await asyncio.sleep(3600)` | `await stop_event.wait()` + signal handlers |
| Нет secret token | `WEBHOOK_SECRET` из env, передаётся в handler |
| `except KeyboardInterrupt` | Правильный signal-based cleanup |

---

## Как откатиться

```bash
git checkout pre-async-fixes
# или
git revert da9e787
```

---

## Что проверить при тестировании

1. **I18n:** `I18n(path="locales")` — переводы загружаются, `i18n.gettext(event, "key")` работает
2. **I18n lazy:** `I18n(lazy=True)` + `await i18n.reload()` — переводы пустые до reload, после полные
3. **Webhook secret:** запрос без заголовка → 401; запрос с правильным заголовком → 200
4. **Shutdown:** `Ctrl+C` останавливает webhook без зависания, unsubscribe вызывается
5. **stop_webhook():** `dp.stop_webhook()` корректно завершает работающий webhook сервер
