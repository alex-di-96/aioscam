# AioScam Roadmap

## v0.1.5.1 — Current (2026-05-19)

✅ Markdown/HTML formatting (`format` param on send_message/edit_message)
✅ `BotCommand` type + `set_my_commands()` — bot command menu
✅ `set_bot_info()` — update bot name/description
✅ one_time_keyboard via middleware pattern
✅ Cleanup middleware — auto-delete previous bot messages
✅ 11 new event decorators
✅ StateGuard configuration in Dispatcher params
✅ ClipboardButton.payload support
✅ 100/100 tests passing

## Planned

### v0.1.6

- [ ] Global rate limiter (queue-based, 429 retry via `Retry-After`)
- [ ] `forward_message()` method
- [ ] `reply_to` parameter in `send_message()`
- [ ] Poll types support (`poll`, `quiz` in API)
- [ ] `delete_messages()` — batch delete

### v0.2.0

- [ ] Webhook documentation (FastAPI, Litestar examples)
- [ ] Scene system (hierarchical FSM)
- [ ] Pagination utilities for `get_chats()`, `get_messages()`
- [ ] Retry decorator with exponential backoff

### Future

- [ ] Plugin system for custom middleware
- [ ] i18n support (localization)
- [ ] Media download helpers
- [ ] Sticker/animation support
- [ ] Admin panel integration

## Done

### v0.1.4.2 (2026-04-27)

- Go SDK signature alignment
- one_time_keyboard concept introduced
- PyPI + TestPyPI publication

### v0.1.3 (2026-04-27)

- Clean public docs
- 35/35 API methods
- 14 event types
