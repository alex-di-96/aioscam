# AioScam Roadmap

## v0.1.6.3 — Current (2026-05-28)

✅ `EventContext.payload` — диплинк-пэйлоад доступен в хендлерах (`event.payload`)
✅ `EventContext.answer()` — исправлен для `bot_started` событий (fallback на `user_id`/`chat_id`)
✅ `Router.message_callback()` — добавлен алиас под официальное имя события Max API
✅ Убрано дублирование `bot_started`/`bot_stopped` в Router
✅ Убрана двойная инъекция `state` для `message_callback` в Dispatcher
✅ `StartCommand` фильтр — теперь работает и для повторных входов через диплинк (`message_created: /start payload`)
✅ `Command` фильтр — захватывает аргументы команды в `command_args`
✅ `parse_deep_link` — переведён на `urllib.parse` (корректная обработка `=` в значениях)
> Подробности: `docs/FIXES_DEEPLINK_2026-05-28.md`

## v0.1.6.2 — (2026-05-28)

✅ Markdown/HTML formatting (`format` param on send_message/edit_message)
✅ `BotCommand` type + `set_my_commands()` — bot command menu
✅ `set_bot_info()` — update bot name/description
✅ one_time_keyboard via middleware pattern
✅ Cleanup middleware — auto-delete previous bot messages
✅ 11 new event decorators
✅ StateGuard configuration in Dispatcher params
✅ ClipboardButton.payload support
✅ Rate limiter — token bucket, 429 retry, exponential backoff
✅ methods/ API — `Bot.execute(GetMe())`, `Bot.execute(SendMessage(...))`
✅ send_callback — SDK-aligned (botapi.max.ru, JSON, NewMessageBody)
✅ Type dedup — single source truth for User/Message/MessageBody
✅ EventContext — `user_id`, `chat_id` convenience properties
✅ 158/158 tests passing (+58 new)
✅ 13 example bots (4 new)
✅ **I18n** — JSON-based translations, auto locale detection from `user_locale`

## Planned

### v0.1.7

- [ ] `forward_message()` method
- [ ] `reply_to` parameter in `send_message()`
- [ ] Poll types support (`poll`, `quiz` in API)
- [ ] `delete_messages()` — batch delete
- [ ] CI/CD pipeline (GitHub Actions)

### v0.2.0

- [ ] Webhook documentation (FastAPI, Litestar examples)
- [ ] Scene system (hierarchical FSM)
- [ ] Pagination utilities for `get_chats()`, `get_messages()`
- [ ] Retry decorator with exponential backoff

### Future

- [ ] Plugin system for custom middleware
- [ ] Media download helpers
- [ ] Sticker/animation support
- [ ] Admin panel integration

## Done

### v0.1.6.1 (2026-05-20)

- Deep link support (StartCommand filter)
- Update class with bot_started payload

### v0.1.6 (2026-05-19)

- Initial v0.1.6 release
- 35/35 API methods
- 14 event types

### v0.1.4.2 (2026-04-27)

- Go SDK signature alignment
- one_time_keyboard concept introduced
- PyPI + TestPyPI publication

### v0.1.3 (2026-04-27)

- Clean public docs
- 35/35 API methods
- 14 event types
