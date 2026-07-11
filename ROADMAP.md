# AioScam Roadmap

## v0.2.2 — Unreleased

### Миграция Max API v2 (дедлайн Max: 19 июля 2026)

- [x] **Base URL → `platform-api2.max.ru`** — старые `platform-api.max.ru` и `botapi.max.ru`
  отключаются; `/answers` теперь на общем base URL (отдельный callback-домен упразднён)
- [x] **Сертификаты Минцифры в пакете** (`aioscam/certs/`) — Russian Trusted Root CA (до 2032)
  + Sub CA (до 2027) с gosuslugi.ru; клиент строит `TCPConnector` с расширенным `SSLContext`
  автоматически, системное хранилище не затрагивается; переопределение `Bot(ssl_context=...)`
- [x] **Все chat-методы на официальных path-параметрах** — `GET/PATCH/DELETE /chats/{id}`,
  `/chats/{id}/members[/me|/admins[/{uid}]]`, `PUT/GET/DELETE /chats/{id}/pin`; старые плоские
  пути с query/body попадали в удалённый листинговый эндпоинт
- [x] **`ChatAdminPermission`** — enum официальных прав админа
- [x] **`get_chats()` deprecated** — `GET /chats` удалён из API (июнь 2026)
- [x] **`intent` в callback-кнопках** больше не сериализуется (API игнорирует, всегда default)
- [x] Live-верификация на dev-боте против `platform-api2.max.ru` (TLS, чаты, сообщения, pin)

### ChatRegistry + backlog-политики

- [x] **`aioscam.registry.ChatRegistry`** — SQLite-реестр чатов взамен удалённого `GET /chats`:
  авто-пополнение из событий, lazy-discovery, soft-delete, persist polling marker,
  `sync(bot)` (bootstrap + точечная реконсиляция + TTL-обновление прав бота)
- [x] **`Dispatcher(registry=...)`**, интеграция в polling и webhook
- [x] **`start_polling(backlog="skip"|"process"|"collapse")`** — `skip_updates` остался алиасом;
  починен старый skip (пропускал только одно событие из очереди — теперь честный drain);
  collapse схлопывает пользовательский backlog по (chat, user, type), реестровые события
  применяются к базе все по порядку в любом режиме
- [x] **`aioscam/db.py`** — единая база бота `.aioscam/bot.db` для всех компонентов
  (кэш инстансов по пути, refcount close)

### Опросы и квизы

- [x] **Poll types** — в Max Bot API нативных опросов НЕТ (проверено по официальным SDK);
  реализована эмуляция `aioscam.polls.PollManager`: inline-кнопки, голоса в SQLite, live-бары,
  режимы priv/anon/pub, команда `/poll [priv|anon|pub] Вопрос | вар1 | вар2`, bot-driven
  опросы (`creator_id=None`), квизы с пояснением и раскрытием ответа при закрытии,
  StateGuard-allowlist автоматически, локализация подсказок (ru/en; `I18n.translate()` добавлен)
- [x] Примеры: `examples/poll_bot.py`, `examples/registry_bot.py`
- [x] Live-проверено в реальной группе: /poll, голоса с именами (pub), закрытие кнопкой

**Тесты: 714/714** (было 633 в v0.2.1).

## v0.2.1 — Current (2026-06-21)

### `HomePage` — generic landing page for WebApp servers (`aioscam/webapp/homepage.py`)

Мотивация: `WebAppMiddleware` отвечает 401 с одинаковым JSON и на отсутствующий, и на неверный
`initData` — слепой перебор путей (`/api/me`, `/api/auth`, ...) по самому факту структурированного
401 узнаёт, что эндпоинт существует. `HomePage` закрывает корень сервера (`/`) безопасной generic
страницей вместо хардкод `index.html`/raw file response — посетитель без JS видит имя/описание
бота и кнопку "Open in Max" (deep link через `create_deep_link`), ничего не намекает на `/api/*`.
Внутри клиента Max та же страница подгружает Bridge SDK и может быть стартовым экраном мини-приложения.

- `HomePage(bot=None, title=None, description=None, username=None, deep_link_payload="",
  lang="ru", show_open_in_max=True, extra_head="", extra_body="")` — экспортируется из
  `aioscam.webapp.aiohttp` (живёт там же, где `WebAppMiddleware`/`cors_middleware`)
- Имя/описание/username берутся из `bot.get_me()` один раз и кешируются на странице; явные
  параметры конструктора их переопределяют без обращения к боту
- `extra_head`/`extra_body` — точки расширения для собственной разметки/скриптов мини-приложения
  поверх дефолтной обёртки — не хардкод под один проект, а конфигурируемый каркас
- `examples/webapp_bot.py` обновлён: интерактивный демо-фронтенд (`index.html` и т.д.) переехал
  с `/` на `/app` — в Max bot dashboard как Mini App URL регистрируется `WEBAPP_URL + /app`,
  а bare `WEBAPP_URL` отдаёт только `HomePage`
- No-JS ограничение задокументировано как платформенное, не решаемое на уровне фреймворка: Max
  передаёт `initData` только через инжектируемый клиентом JS-объект `window.WebApp`
  (`examples/webapp/max-bridge.js:41`), URL-фрагмент fallback (как `tgWebAppData` у Telegram)
  у Max нет — без выполнения JS сервер не может получить подписанные данные вообще
- Тесты: `tests/test_webapp_homepage.py` (11 тестов, 615/615 всего)

### `WebAppMiddleware` — 404/401 split, `api_prefix`, `WebAppFailGuard` (`aioscam/webapp/aiohttp.py`, `aioscam/webapp/failguard.py`)

Мотивация: после `HomePage` оставалось два открытых пункта маскировки `/api/*` от прямого
исследования — (1) `WebAppMiddleware` отвечал одинаковым 401 и на отсутствующий, и на неверный
`initData`, и (2) путь `/api` сам по себе — из стандартного wordlist'а сканеров. Сделано как
фреймворк-фичи (конфигурируемые параметры/класс), не костыль под пример.

- `WebAppMiddleware`/`webapp_auth_middleware` теперь различают: bare `WebAppDataError`
  (`initData` вообще не пришло — `get_init_data()` поднимает именно базовый класс, не подкласс)
  → 404 "как будто роута нет"; любой подкласс (`WebAppSignatureError`, `WebAppExpiredError`,
  `WebAppMissingFieldError`, `WebAppParseError` — реальная попытка с неверными данными) → 401
- `WebAppMiddleware(bot_token, max_age=86400, api_prefix="/api", fail_guard=None)` — `api_prefix`
  параметризован вместо хардкода `/api`, можно мигрировать API на непредсказуемый путь
  (`secrets.token_hex(8)`); фронтенд должен слать запросы на тот же префикс
- `WebAppFailGuard(max_failures=20, window=60.0, ban_seconds=300.0)` — новый класс
  (`aioscam/webapp/failguard.py`, реэкспорт из `aioscam.webapp.aiohttp`), in-memory sliding-window
  счётчик неудачных попыток по `request.remote`; при превышении порога адрес получает плоский 404
  без попытки валидации до истечения `ban_seconds` — доп. рубеж защиты, не замена HMAC-проверки
- Тесты: `tests/test_webapp_failguard.py` (6), `tests/test_webapp_middleware.py` (12) — ранее
  `WebAppMiddleware`/`webapp_auth_middleware` не имели тестов вообще; итого 633/633
- `examples/webapp_bot.py` доводит `api_prefix` до реальной демонстрации, не только до README:
  `WEBAPP_API_PREFIX` (env, default `/api`) уезжает во все 5 роутов и в `WebAppMiddleware`; сервер
  на лету подменяет `const API_PREFIX = "/api";` в каждой из 4 отдаваемых HTML-страниц
  (`index.html`, `index-vue.html`, `charts.html`, `table.html`), так что фронтенд не дублирует
  префикс вручную и не требует шага сборки. Проверено вручную через `aiohttp.test_utils` с обоими
  значениями префикса (дефолт и кастомный)

---

## v0.2.0 — (2026-06-19)

### `aioscam.webapp` — серверный модуль для Max WebApps (мини-приложений)

Реализовано полностью: двусторонняя связь Bot ↔ WebApp, не только валидация (как планировалось
изначально в Future).

- **`validate_init_data(raw, bot_token, max_age=3600)` → `WebAppInitData`** — HMAC-SHA256 проверка
  подписи (`secret_key = HMAC(b"WebAppData", bot_token)`, `hash = HMAC(secret_key, sorted_check_string)`),
  проверка возраста (`auth_date`)
- **`validate_contact(...)` → `WebAppContact`** — отдельная HMAC-проверка для `requestContact()`
  (`HMAC(bot_token, sorted(authDate, phone_no_plus, userId))`)
- **`EventStreamManager`** (`aioscam/webapp/events.py`) — push-уведомления Bot → WebApp через
  Server-Sent Events: per-`user_id` очереди, `publish()`, `broadcast()`, `active_users()`,
  `connection_count()`, `stream()` (long-lived handler с heartbeat)
- **`WebAppMiddleware`** (`aioscam/webapp/aiohttp.py`) — валидирует `initData` на каждый `/api/*`
  запрос; пропускает всё что не начинается с `/api` и `/static` — статика остаётся публичной
- initData принимается тремя способами: `Authorization: MaxWebApp <raw>`, `X-Webapp-Init-Data`
  header, или `?initData=` query param — последнее нужно для `EventSource` (SSE), который не
  умеет ставить кастомные заголовки
- **`cors_middleware`** — настраиваемый `allow_origins`

### `BotCapabilities` — отчёт о возможностях бота при старте (`aioscam/utils/capabilities.py`)

Max API не отдаёт поле permissions/capabilities в `GET /me` (проверено живым пробником — только
`user_id, first_name, username, is_bot, last_activity_time, description, avatar_url,
full_avatar_url, commands, name`). `BotCapabilities.probe(bot, webapp_url=...)` собирает картину
из профиля + конфигурации + warnings, чтобы не вводить пользователя в заблуждение о том, что
доступно. `caps.log_report(logger)` печатает структурированный баннер при старте бота.
Bridge-фичи (haptic/biometric/NFC/QR/contacts) явно документированы как клиентские —
сервер не может знать платформу пользователя, это видно только на фронтенде (`bridge.platform`).

### Информативные исключения — `.hint` на каждом exception (`aioscam/exceptions/exceptions.py`)

Каждое исключение фреймворка теперь несёт `.hint` — конкретную причину/фикс, автоматически
добавляется в `str(exc)`. Раньше `str(ApiError(...))` отдавал только сырое сообщение API;
теперь `ApiError`, `NetworkError`, `TimeoutError`, `RetryAfter`, `UnauthorizedError`,
`ForbiddenError`, `NotFoundError`, `BotTokenError`, `DispatcherError` — у каждого свой дефолтный
hint (например `RetryAfter` прямо говорит сколько секунд подождать и предлагает понизить
`rate_limit=`). Тот же паттерн используется в исключениях `aioscam.webapp`
(`WebAppSignatureError`, `WebAppExpiredError`, `WebAppMissingFieldError`, `WebAppParseError`,
`FeatureUnavailableError`).

### Примеры — `examples/webapp_bot.py` + `examples/webapp/*.html`

Полноценный рабочий бот с REST API (`GET /health`, `GET /api/me`, `POST /api/auth`,
`POST /api/contact`, `POST /api/send`, `GET /api/events`) и 4 фронтенд-страницы:

| Файл | Назначение |
|------|-----------|
| `index.html` | Канонический справочник нативного Max Bridge SDK (vanilla JS): haptic, QR, biometric, NFC, storage, навигация, SSE, отправка сообщений |
| `index-vue.html` | Vue 3 (по CDN, без build step) — bot↔webapp чат через SSE, без дублирования Bridge-контролов |
| `charts.html` | Chart.js — графики (линейный + донат), которых в Max нет нативно; питаются тем же SSE-потоком |
| `table.html` | Сортируемая/фильтруемая таблица (vanilla JS) — тоже расширенный контрол сверх Max |
| `max-bridge.js` | Promise-обёртка над `window.WebApp.*`, общая для всех страниц |

Принцип разделения: нативные Bridge-контролы — только в `index.html`; примеры для других
фреймворков показывают только bot↔webapp связь; расширенные UI-компоненты (графики, таблицы),
которых в Max нет — отдельные файлы со своей библиотекой.

> Тесты: 604/604 (было 569 на v0.1.8.1). Зависимостей не добавлено (только stdlib `hmac`/`hashlib` + существующий `aiohttp`).

---

## v0.1.8.1 — (2026-06-16)

### Hotfix: env var names + license (2026-06-16)
- `Aioscam_ENV` → `AIOSCAM_ENV`, `Aioscam_API_URL` → `AIOSCAM_API_URL` в `aioscam/config.py`
  (на Linux mixed-case имена не работали — env vars регистро-зависимы)
- `.env.example` обновлён до v0.1.8.1, исправлены имена переменных
- Смена лицензии MIT → PolyForm Noncommercial License 1.0.0
- Удалены внутренние dev-логи из `docs/` (FIXES_*.md, MEDIA_UPLOAD, MAX_BUTTON_FORMATTING)

### Bug fix: OpenAppButton — правильные поля API (2026-06-16)

`OpenAppButton` имел поле `app_id: str` которого нет в Max API. Исправлено по официальной документации:
- `web_app: Optional[str]` — username бота, чьё мини-приложение открыть
- `contact_id: Optional[int]` — user_id того же бота
- `payload: Optional[str]` — данные, передаваемые в мини-приложение как `start_param` (макс 512 символов)

`Button.to_dict()` обновлён для сериализации новых полей.
`KeyboardBuilder.open_app()` — новая сигнатура `(text, web_app=None, contact_id=None, payload=None)`.
`InlineKeyboard.serialize_button()` уже корректно использовал `web_app`/`contact_id` через `getattr` — изменений не требовалось.
> Files: `aioscam/types/keyboard.py`, `aioscam/utils/keyboard.py`

## v0.1.8 — (2026-06-15)

### StateGuard regex/like/and-or callbacks (2026-06-15)

`state_guard_callbacks` now accepts `magic_filter.F` expressions
(`.startswith()`, `.contains()`, `.regexp()`, `& | ~`) alongside exact-match
strings — found via ToirBot (`confirm_yes|52507` didn't match `{"confirm_yes"}`).
Additive, backward compatible. Matcher: `Dispatcher._callback_guard_allowed()`.
Tests: `tests/test_v015.py::TestCallbackGuardMatcher` (6 tests).
Documented in `docs/ru/README.md` and `docs/en/README.md` (FSM/StateGuard section).

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
✅ `send_callback` — SDK-aligned (POST /answers, JSON, NewMessageBody)
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

### v0.2.0
- [x] **StateGuard — magic_filter для `state_guard_commands`** (2026-06-16) — `state_guard_commands`
  теперь принимает `Iterable` из строк (exact match) и `F`-выражений (`.startswith`, `.regexp`, `& | ~`).
  Добавлен `_command_guard_allowed()`. Backward-compatible. Тесты: `TestCommandGuardMatcher` (8 тестов, 577/577).

- [ ] `forward_message()` метод
- [ ] `reply_to` параметр в `send_message()`
- [x] Poll types — нативных в Max API нет; эмуляция `PollManager` (см. v0.2.2)
- [ ] `delete_messages()` — batch delete
- [ ] CI/CD (GitHub Actions)
- [ ] Scene system (иерархический FSM)
- [ ] Webhook документация (FastAPI, Litestar примеры)
- ~~Пагинация для `get_chats()`~~ — `GET /chats` удалён из Max API, замена: `ChatRegistry`; пагинация `get_messages()` — [ ]
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
- [ ] **AI-интеграция** — готовый клиент для подключения LLM к боту "из коробки"
  - Timeweb Cloud AI Gateway (унифицированный доступ к нескольким моделям)
  - GigaChat (Sber)
  - Архитектура: отдельный модуль (`aioscam.ai` или extra `aioscam[ai]`), не тащить SDK провайдеров
    в core-зависимости
- [ ] **`aioscam.webapp` — серверный модуль для мини-приложений Max**
  Max WebApps — обычные веб-приложения (HTML/CSS/JS) на HTTPS-хостинге разработчика, открываемые
  в WebView клиента через `OpenAppButton`. Бот-сторона нужна только для:
  - Валидации `initData` (HMAC-SHA256 по `botToken`) — стандарт, аналогичный Telegram WebApp
  - Pydantic-модели `WebAppInitData` (query_id, user, chat, start_param, auth_date, hash)
  - Хелпера для webhook/REST endpoint (FastAPI/aiohttp handler)

  **Не входит в scope фреймворка:** выбор UI-стека (Flutter Web, React, Svelte, ванильный JS —
  на усмотрение разработчика), хостинг, Bridge JS SDK.

  Приоритетный UI для примера: **Flutter Web** (компилируется в static HTML/JS, богатый нативный UI)
  или **Svelte** (< 5 КБ runtime, самодостаточный бандл без CDN).
  > Зависимость: нет новых (только stdlib `hmac`, `hashlib`)
  > Docs: https://dev.max.ru/docs/webapps/introduction

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
- [x] ☕ **Buy me a cookie** — Boosty-ссылка в README (2026-06-15: исправлена на реальный профиль `boosty.to/alex.di/donate`)
- [ ] GitHub Sponsors
- [ ] Open Collective
