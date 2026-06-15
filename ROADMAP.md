# AioScam Roadmap

## Unreleased

### Telemetry + auto_telemetry flag (2026-06-15)

`Bot(auto_telemetry=True)` (default on, independent from `auto_brand`):
fire-and-forget anonymous usage ping `POST https://yasvc.ru/cgi-bin/botlog`
on `start_polling()` / `handle_webhook()` start.

- Payload: `{"event": "polling_start"|"webhook_start", "version": __version__, "bot_id": <int|None>}`
  (`bot_id` only included if `_me` already cached, e.g. via `_ensure_branding`)
- `Bot._send_telemetry()` (`aioscam/bot/bot.py`): `timeout=5s`, `allow_redirects=False`,
  all exceptions (connection errors, timeouts) silently swallowed — never affects bot operation
- Sent via `asyncio.create_task()` (not awaited) from `Dispatcher.start_polling`/`handle_webhook`
  (`aioscam/dispatcher/dispatcher.py`), wrapped in `try/except TypeError` for mocked bots in tests
- Opt-out: `Bot(auto_telemetry=False)`
- No new dependencies — reuses `aiohttp` session via `AioScamClient._get_session()`
- Tests: `tests/test_bot_send.py::TestSendTelemetry` (5 tests)

## v0.1.8 — Current (2026-06-04)

### Live testing session — bugs found (2026-06-04)

**Bug 5 — `send_action` wrong API path (HTTP 404)**
`SEND_ACTION = "/actions"` → Max API returns 404 on every call.
Correct path per official Max SDK: `POST /chats/{chat_id}/actions`.
The bug caused any handler that called `send_action` to crash before sending a reply.
Fix: path built dynamically `f"/chats/{chat_id}/actions"`, `chat_id` moved from body to URL.
> Files: `aioscam/enums/api_path.py`, `aioscam/bot/bot.py`

**Bug 6 — `SenderAction` enum values didn't match Max API**
Our values: `TYPING="typing"`, `UPLOAD_PHOTO`, `RECORD_VIDEO`, `RECORD_AUDIO`, ...
Max API values (per max-sdk): `TYPING_ON="typing_on"`, `SENDING_PHOTO`, `SENDING_VIDEO`,
`SENDING_AUDIO`, `SENDING_FILE`, `MARK_SEEN`.
Fix: enum rewritten to match max-sdk/py/maxapi/enums/sender_action.py.
> File: `aioscam/enums/sender_action.py`

Discovered by: live echo_bot.py test — every message echo crashed with HTTP 404.

---

## v0.1.8 — Previous state (2026-06-03)

### Code Review #2 — 3 bugs + 94 new unit tests (commit pending)

#### Bugs fixed

**Bug 1 — `Update.event` returned `None` for lifecycle event types (CRITICAL)**
All event handlers for `bot_stopped`, `user_added`, `user_removed`, `message_edited`,
`message_removed`, `message_chat_created`, `chat_title_changed`, `dialog_cleared`,
`dialog_muted`, `dialog_unmuted`, `bot_added`, `bot_removed` **never fired** in production.
`_process_update()` checks `if not event_type or not event: return` — and `Update.event`
was `None` for all event types except the three "main" ones.
Fix: `if self.update_type: return self`
> File: `aioscam/types/update.py`

**Bug 2 — `I18n.gettext` fallback to default locale was broken**
When a key was missing in the requested locale, the code tried to look up the
default locale name (`"en"`) as a key inside the current locale dict — not in
`self._translations`. Result: always fell through to returning the raw key string
instead of the default locale translation.
Fix: `text = translations.get(key); if text is None: text = self._translations.get(self.default_locale, {}).get(key, key)`
> File: `aioscam/i18n/i18n.py`

**Bug 3 — `create_group_deep_link` didn't URL-encode the payload**
`create_deep_link()` uses `quote(payload, safe='')` but `create_group_deep_link()`
with a payload just did f-string interpolation — payload with `=`, `&`, spaces
would produce malformed URLs and fail to round-trip through `parse_deep_link()`.
Fix: added `quote(payload, safe='')` to the group deep link URL.
> File: `aioscam/utils/deep_linking.py`

#### New unit tests (+94 tests, 463 total)

- `tests/test_dispatcher_routing.py` — `Update.event` for all 13 event types,
  `Update` properties (text, sender, recipient), `Dispatcher._process_update`
  routing for all event types, state injection, StateGuard blocking/allowing,
  `stop_polling` / `stop_webhook` controls
- `tests/test_filters_scene_webhook.py` — `StartCommand` (all 5 match modes),
  `ContentType`, `AllFilter`, `Scene` class (6 tests), `StateGuardMiddleware`
  standalone with hint logic, `I18n` fallback locale (bug fix coverage),
  `create_group_deep_link` URL encoding (bug fix coverage),
  `AiohttpWebhookHandler` (secret token, no-secret, invalid, exception→500),
  `Bot.request_contact/request_location`, `Bot.send_action`, `Bot.delete_message`,
  `Bot.get_messages`, `Bot.get_message`, context manager, aliases,
  `delete_webhook()` deprecation warning

---

## v0.1.7 — (2026-05-28)

### Async integrity + Webhook fixes (коммит da9e787)
✅ **I18n** — убран блокирующий `open()` в `__init__`, добавлен `async def reload()` через `aiofiles`
✅ **I18n `lazy=True`** — пропуск синхронной загрузки при создании внутри event loop
✅ **`AiohttpWebhookHandler`** — добавлена валидация `X-Max-Secret-Token` (было полностью отсутствовала)
✅ **`Dispatcher.handle_webhook()`** — `shutdown_event` заменён на `SIGINT`/`SIGTERM` signal handlers (раньше зависал навечно)
✅ **`Dispatcher.stop_webhook()`** — программная остановка webhook-сервера
✅ **`examples/webhook_bot.py`** — `WEBHOOK_SECRET` из env, signal shutdown, убран `while True: sleep(3600)`
> Ролбэк: `git checkout pre-async-fixes` | Подробности: `docs/FIXES_ASYNC_2026-05-28.md`

### Media upload / download
✅ `InputMedia(path)` — авто-определение типа по расширению (image/video/audio/file)
✅ `InputMediaBuffer(buffer, filename)` — загрузка из памяти без temp-файла
✅ `bot.send_photo()`, `bot.send_video()`, `bot.send_audio()`, `bot.send_document()`, `bot.send_media()`
✅ `bot.get_upload_url(type)` — исправлен (был сломан: GET вместо POST, нет type)
✅ `bot.download_file(path, url, token)` — скачать в файл
✅ `bot.download_file_bytes(url, token)` — скачать в память (bytes)
✅ `Bot.make_temp_path(ext)` — уникальные datetime-имена для temp-файлов
✅ `attachment.not.ready` retry-логика (5 попыток, задержка 2с)
✅ `UploadType` enum исправлен: `IMAGE` (было `PHOTO`), `FILE` (было `DOCUMENT`)
✅ Sticker — только приём (API не позволяет боту отправлять стикеры)
✅ Новая зависимость: `aiofiles>=23.0.0`

### Deep links (подтверждено 2026-05-28)
✅ `bot_started` + `payload` работает для ВСЕХ пользователей (новые + существующие)
✅ Polling marker fix — `Bot.get_updates()` использует `marker` из API, не `body.seq`
✅ `StartCommand` фильтр — fallback для `/start <payload>` из `message_created`
✅ Obfuscation: Caesar cipher + MD5 hash (уровень demo_bot, не фреймворк)
✅ Referral system — `encode_invite_payload()` / `decode_invite_payload()`
> Подробности: `docs/FIXES_DEEPLINK_2026-05-28.md`

### demo_bot.py — UX fixes (коммит df1e448+)
✅ "⚙️ Настройки" → "⚙️ Параметры" — убрана коллизия с sidebar MAX мессенджера
✅ `Bot.send_callback()` — добавлен `keyboard` параметр (inline keyboard support)
✅ Phone masking — показ только последние 4 цифры (`...0279`)
✅ Privacy notice — "Мы не храним и не собираем ваши персональные данные!"
✅ `/start` подсказка — после регистрации, викторины, обратной связи
✅ **"⚙️ Параметры" inline keyboard** — работает через `event.answer(keyboard=kb.build())`
  - 🇷🇺 Русский ✅ / 🇺🇸 English — переключение + галочка (подтверждено 2026-05-29 через Playwright)

### demo_bot.py — Image FSM
✅ `ImageState` с состоянием `waiting_image`
✅ Кнопка `🖼️ Изображение` в главном меню
✅ Флоу: отправить фото → скачать в память → PIL (отражение + 800×600 + водяной знак) → вернуть с кнопкой «Назад»

### demo_bot.py — Регистрация + телефон
✅ Шаг 4/4: запрос телефона через `RequestContactButton`
✅ Контакт обрабатывается в `handle_contact` с проверкой FSM состояния

### demo_bot.py — Параметры / Локаль
✅ Исправлена смена языка (`kb.build()` → `event.answer()` вместо `send_callback()`)
✅ Локаль сохраняется в FSM state (`user_locale`) — не сбрасывается между запросами
✅ Inline keyboard при открытии параметров — работает (подтверждено 2026-05-29)

### Тесты
✅ 211 passed, 5 failed (integration tests) — +53 новых: type detection, FSM, PIL, temp paths, methods

> Подробности: `docs/MEDIA_UPLOAD_2026-05-28.md`, `docs/FIXES_DEMOBOT_2026-05-28.md`, `docs/FIXES_DEEPLINK_2026-05-28.md`

---

## Done

### v0.1.6.3 (2026-05-28)
✅ `EventContext.payload` — диплинк-пэйлоад доступен в хендлерах
✅ `EventContext.answer()` — исправлен для `bot_started` событий
✅ `Router.message_callback()` — добавлен алиас
✅ `StartCommand` фильтр — повторные входы через диплинк (`/start payload`)
✅ `Command` фильтр — захватывает аргументы в `command_args`
✅ `parse_deep_link` — переведён на `urllib.parse`

### v0.1.6.2 (2026-05-28)
✅ Markdown/HTML formatting (`format` param)
✅ `BotCommand` + `set_my_commands()` — меню команд бота
✅ `set_bot_info()` — обновление описания бота
✅ `one_time_keyboard` через middleware
✅ Cleanup middleware — авто-удаление предыдущих сообщений бота
✅ 11 новых декораторов событий
✅ StateGuard — конфигурируется в параметрах Dispatcher
✅ `ClipboardButton.payload`
✅ Rate limiter — token bucket, 429 retry, exponential backoff
✅ Methods API — `Bot.execute(GetMe())`, `Bot.execute(SendMessage(...))`
✅ `send_callback` — SDK-aligned (botapi.max.ru, JSON, NewMessageBody)
✅ Type dedup — единый источник для User/Message/MessageBody
✅ EventContext — `user_id`, `chat_id` convenience properties
✅ 158/158 тестов (+58 новых)
✅ 13 примеров ботов (4 новых)
✅ **I18n** — JSON-переводы, авто-определение локали из `user_locale`

### v0.1.6.1 (2026-05-20)
- Поддержка deep link (StartCommand filter)
- Update class с payload для bot_started

### v0.1.6 (2026-05-19)
- Initial v0.1.6
- 35/35 API методов
- 14 типов событий

### v0.1.4.2 (2026-04-27)
- Go SDK signature alignment
- one_time_keyboard concept
- PyPI + TestPyPI

### v0.1.3 (2026-04-27)
- Clean public docs
- 35/35 API методов
- 14 типов событий

---

## Planned

### v0.1.8
- [ ] `forward_message()` метод
- [ ] `reply_to` параметр в `send_message()`
- [ ] Poll types (`poll`, `quiz` в API)
- [ ] `delete_messages()` — batch delete
- [ ] CI/CD (GitHub Actions)

### v0.2.0
- [ ] Scene system (иерархический FSM)
- [ ] Webhook документация (FastAPI, Litestar примеры)
- [ ] Пагинация для `get_chats()`, `get_messages()`
- [x] **StateGuard — regex/like/and-or для `state_guard_callbacks`** (найдено в ToirBot 2026-06-10, реализовано 2026-06-15)

  Было: `process_callback` сравнивал **полный** `event.callback_data` с `state_guard_callbacks`
  только через exact match. Реальные callback'и часто несут параметр через `|`, например
  `confirm_yes|52507`, который не матчился с `{"confirm_yes"}`.

  **Реализовано** (аддитивно, обратная совместимость сохранена):
  `_guard_allowed_callbacks` теперь принимает элементы двух видов:
  - `str` — exact match как раньше (`"action:cancel"`)
  - `magic_filter.F` выражение — резолвится против полного payload, поддерживает
    `.startswith()`, `.contains()`, `.regexp()` и комбинации `&` / `|` / `~`:

    ```python
    from magic_filter import F

    dp = Dispatcher(state_guard_callbacks=[
        "action:cancel",
        F.startswith("confirm_"),
        F.regexp(r"^nav:(back|next)$"),
        F.startswith("menu_") & ~F.contains("admin"),
    ])
    ```

  Матчер: `Dispatcher._callback_guard_allowed(payload, allowed)` (`dispatcher/dispatcher.py`).
  Тесты: `tests/test_v015.py::TestCallbackGuardMatcher` (6 тестов).

  **Важно:** `state_guard_callbacks` со смешанными типами (`str` + `F`) нельзя передавать как `set`
  (`MagicFilter` нехэшируем) — использовать `list`.

### Future
- [ ] Plugin system
- [ ] Media download helpers (высокоуровневые)
- [ ] Sticker/animation поддержка
- [ ] AI агенты — интеграция с LLM (OpenAI, Claude, GigaChat) для умных ответов в ботах

### Technical Debt — минимум зависимостей
**Принцип:** тащить как можно меньше зависимостей — каждая лишняя зависимость = риск для пользователей

- [ ] **`python-dotenv`** — убрать побочный эффект `load_dotenv()` на уровне модуля в `aioscam/config.py:18`. Варианты:
  - Ленивая загрузка внутри `Config.__init__()` — пользователь сам решает
  - Убрать совсем — пользователь вызывает `load_dotenv()` если нужно
  - Сделать optional dependency: `pip install aioscam[dotenv]`
- [ ] **Аудит зависимостей** — проверить каждую: действительно ли нужна? Есть ли stdlib аналог?
  - `aiohttp` ✅ — нужен (async HTTP)
  - `aiofiles` ✅ — нужен (async file I/O для I18n)
  - `pydantic` ✅ — нужен (валидация типов)
  - `magic-filter` ✅ — нужен (aiogram-style фильтры)
  - `python-dotenv` ⚠️ — сомнительно, можно `os.getenv()` + пользователь сам загружает

### Community
- [ ] ☕ **Buy me a cookie** — добавить Boosty/Patreon ссылку в README ✅ (done)
- [ ] GitHub Sponsors
- [ ] Open Collective
