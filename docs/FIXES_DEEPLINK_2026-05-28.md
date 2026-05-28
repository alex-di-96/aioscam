# Исправления: диплинки и архитектурные баги (2026-05-28)

Этот документ описывает все изменения, внесённые в ходе code review.
Создан как ориентир для следующих сессий работы с кодом.

---

## Точка отката (git tag)

```
pre-deeplink-fix  →  commit 8df7e78
```

Для отката: `git checkout pre-deeplink-fix`

---

## Что было сломано — краткий список

| # | Файл | Симптом |
|---|------|---------|
| 1 | `dispatcher/event.py` | `event.payload` → `AttributeError` в любом хендлере |
| 2 | `dispatcher/event.py` | `event.answer()` кидает `ValueError` на `bot_started` событиях |
| 3 | `dispatcher/router.py` | `@router.message_callback(...)` → `AttributeError` (метод не существовал) |
| 4 | `dispatcher/router.py` | `bot_started` / `bot_stopped` определены дважды (мёртвый код) |
| 5 | `dispatcher/dispatcher.py` | Двойная инъекция `state` для `message_callback` событий |
| 6 | `dispatcher/dispatcher.py` | `import json` дважды (в модуле и внутри цикла) |
| 7 | `utils/deep_linking.py` | Ручной парсинг URL ломался на значениях с символом `=` (base64 и др.) |
| 8 | `filters/builtin.py` | `Command` фильтр отбрасывал аргументы команды (`/start ref_123` → args терялись) |
| 9 | `filters/builtin.py` | `StartCommand` не работал совсем: искал `event.payload` → `False`, fallback тоже None |

---

## Детальное описание каждого фикса

### Фикс 1 — `EventContext.payload` (`dispatcher/event.py`)

**Проблема:** `EventContext` не имел свойства `payload`. Все хендлеры вида:
```python
async def on_started(event):
    if event.payload:   # AttributeError!
```
падали с `AttributeError`. `StartCommand` фильтр тоже не работал по той же причине.

**Решение:** добавлено свойство:
```python
@property
def payload(self) -> Optional[str]:
    """Deep link payload (bot_started ?start= parameter)"""
    if hasattr(self.event, 'payload'):
        return self.event.payload
    if isinstance(self.event, dict):
        return self.event.get('payload')
    return None
```

---

### Фикс 2 — `EventContext.answer()` (`dispatcher/event.py`)

**Проблема:** метод заново вычислял `user_id` и `chat_id` через `self.from_user` и `self.chat`,
без fallback на `event.user_id` / `event.chat_id`. Для `bot_started` событий, где
`Update.user = None` но `Update.user_id` задан, `answer()` кидал `ValueError`.

**Решение:** заменено на использование уже готовых свойств `self.user_id` и `self.chat_id`,
которые содержат правильные fallback-цепочки для всех типов событий.

---

### Фикс 3 — `Router.message_callback()` (`dispatcher/router.py`)

**Проблема:** `@router.message_callback(...)` → `AttributeError`. В Router был только
`callback_query()`, а `message_callback` — официальное имя события в Max API.

**Решение:** добавлен алиас:
```python
def message_callback(self, *filters) -> Callable:
    """Alias for callback_query — matches Max API event name."""
    return self.callback_query(*filters)
```

---

### Фикс 4 — дублирование `bot_started` / `bot_stopped` (`dispatcher/router.py`)

**Проблема:** методы `bot_started` и `bot_stopped` были определены дважды:
- строки ~147-167: inline-реализации
- строки ~309-315: делегаты к `on_event()` — переопределяли первые

Вторые определения стирали первые. Мёртвый код вводил в заблуждение.

**Решение:** удалены дублирующие определения снизу. Остались inline-реализации
(строки ~147-167), которые функционально корректны.

---

### Фикс 5 — двойная инъекция `state` (`dispatcher/dispatcher.py`)

**Проблема:** для `message_callback` событий `_process_update` вручную создавал
`StateContext` и клал в `context.data['state']`, после чего вызывал
`process_callback()`, который делал то же самое второй раз.

**Решение:** ручной блок убран, вызывается только `process_callback()`.

---

### Фикс 6 — `import json` дважды (`dispatcher/dispatcher.py`)

**Проблема:** `json` импортирован на уровне модуля (строка 7) и повторно
внутри цикла поллинга (строка 275).

**Решение:** убран inline-импорт из цикла.

---

### Фикс 7 — `parse_deep_link` (`utils/deep_linking.py`)

**Проблема:** ручной парсинг `p.split("=")` падал при значениях с символом `=`
(base64, URL-encoded данные и т.п.).

**Решение:** заменено на `urllib.parse.urlparse` + `parse_qs`:
```python
parsed = urlparse(url)
params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
```

---

### Фикс 8 — `Command` фильтр не сохранял аргументы (`filters/builtin.py`)

**Проблема:** регекс `r'^[/\'](\w+)'` захватывал только имя команды.
При `/start ref_12345` аргумент `ref_12345` терялся.

**Решение:** добавлено в `FilterResult.data`:
```python
args = text[command_match.end():].strip() or None
return FilterResult(passed=True, data={"command": command, "command_args": args})
```

Теперь хендлер может получить аргументы через параметр `command_args`:
```python
async def on_start(event, command_args: str = None):
    print(command_args)  # "ref_12345" или None
```

---

### Фикс 9 — `StartCommand` для повторных входов (`filters/builtin.py`)

**Проблема:** `StartCommand` искал пэйлоад только в `event.payload`.
После фикса 1 это заработало для первого входа (`bot_started`).
Но при повторных кликах на диплинк Max API присылает `message_created`
с текстом `/start ref_12345` — пэйлоад приходил в тексте сообщения, не в `payload`.

**Решение:** `StartCommand` теперь проверяет оба источника:
1. `event.payload` (для `bot_started`)
2. `event.text` вида `/start <payload>` (для `message_created`)

---

## Паттерн для полной поддержки диплинков (для примеров и документации)

```python
# Первый вход — Max API присылает bot_started с payload
@router.bot_started(StartCommand())
async def on_first_deeplink(event):
    payload = event.payload  # теперь работает
    await handle_referral(event, payload)

# Повторные входы — Max API присылает message_created: "/start ref_123"
@router.message_created(StartCommand())
async def on_repeat_deeplink(event):
    # StartCommand фильтр парсит payload из текста /start <payload>
    text = event.text or ''
    payload = text[7:].strip() if text.startswith('/start ') else None
    await handle_referral(event, payload)

# Обычный /start без диплинка (должен быть ПОСЛЕ StartCommand-хендлера)
@router.message_created(Command("start"))
async def on_plain_start(event):
    await event.bot.send_message(event.chat_id, "Добро пожаловать!")
```

> **Важно:** порядок регистрации хендлеров имеет значение. Хендлер с `StartCommand()`
> должен быть зарегистрирован раньше хендлера с `Command("start")`, иначе
> `/start ref_123` будет перехвачен вторым хендлером без разбора пэйлоада.

---

## Что ещё требует внимания (не исправлено в этой сессии)

| Проблема | Файл | Приоритет |
|----------|------|-----------|
| `get_me()` кэширует навсегда — при смене имени бота данные устаревают | `bot/bot.py:103` | Низкий |
| `send_callback()` создаёт raw aiohttp-сессию в обход клиентской абстракции | `bot/bot.py:527` | Средний |
| Polling маркер берётся из `body.seq`/`timestamp`, а не из ответа API (`marker`). Ломается для событий без `message.body` (bot_started, callback) | `dispatcher/dispatcher.py:289-295` | Средний |
| `MessageBody` не имеет поля `payload` — пэйлоад из `/start payload` не моделируется в типах | `types/message.py` | Низкий |

---

## Файлы изменены

```
aioscam/dispatcher/event.py       — +payload свойство, fix answer()
aioscam/dispatcher/router.py      — +message_callback alias, убрано дублирование
aioscam/dispatcher/dispatcher.py  — убрана двойная state-инъекция, fix import json
aioscam/filters/builtin.py        — Command захватывает args, StartCommand для repeat entries
aioscam/utils/deep_linking.py     — fix URL парсинга
examples/deep_link_bot.py         — добавлен хендлер для повторных входов
```
