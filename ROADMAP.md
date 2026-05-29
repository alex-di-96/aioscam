# AioScam Roadmap

## v0.1.7 — Current (2026-05-28)

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

### demo_bot.py — UX polish (2026-05-29)
✅ "⏹️ Отмена" удалена из главного меню (орфан, нет кейса применения)
✅ `action:cancel` callback остаётся для ⚙️ Параметры → 🔙 Назад
✅ `/cancel` команда работает для FSM state cancellation
✅ Главное меню: 10 кнопок (было 11)
✅ MyCommands расширены: 3 → 8 команд (start, help, stats, register, quiz, feedback, contact, cancel)
✅ Database auto-recovery — при повреждении SQLite файл удаляется и пересоздаётся

### Тесты
✅ **216 passed, 0 failed** — все тесты проходят (было 211 passed, 5 failed)
- Timeout race condition fix — polling больше не падает каждые 5 минут
- 5 integration тестов исправлены (были сломаны из-за timeout)

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

### Future
- [ ] Plugin system
- [ ] Media download helpers (высокоуровневые)
- [ ] Sticker/animation поддержка
