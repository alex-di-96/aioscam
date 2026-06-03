# Code Review #2 — Bug Fixes (2026-06-03)

Second deep code review of the entire AioScam framework.
3 bugs fixed, 94 new unit tests added. Total: 463 passing.

---

## Bug 1 — `Update.event` returned `None` for lifecycle event types (CRITICAL)

**File:** `aioscam/types/update.py`

**Symptom:** All lifecycle event handlers registered via
`@router.bot_stopped()`, `@router.user_added()`, `@router.message_edited()`,
`@router.chat_title_changed()`, etc. **never fired** in a running bot.

**Root cause:**
```python
# Before (broken):
@property
def event(self):
    if self.update_type in ("message_created", "message_callback", "bot_started"):
        return self
    return None  # ← all other 10 event types returned None
```

In `Dispatcher._process_update()`:
```python
event = update.event
if not event_type or not event:
    logger.warning(f"Unknown update type: {update}")
    return  # ← immediately skipped for all lifecycle events
```

**Fix:**
```python
@property
def event(self):
    if self.update_type:
        return self
    return None
```

**Affected event types (previously silently dropped):**
- `bot_stopped`, `bot_added`, `bot_removed`
- `user_added`, `user_removed`
- `message_edited`, `message_removed`
- `message_chat_created`, `chat_title_changed`
- `dialog_cleared`, `dialog_muted`, `dialog_unmuted`

---

## Bug 2 — `I18n.gettext` fallback to default locale was broken

**File:** `aioscam/i18n/i18n.py`

**Symptom:** When a translation key existed in the default locale (`en`) but was
missing in the user's locale (`ru`), `gettext()` returned the raw key string
instead of the English fallback.

**Root cause:**
```python
# Before (broken):
text = translations.get(
    key,
    translations.get(self.default_locale, {}).get(key, key)
    #  ^^^ translations is the RU dict, e.g. {"greeting": "Привет!"}
    #  Looking for "en" as a KEY in the RU dict → always {} → returns key
)
```

`translations` is the locale-specific dict, not `self._translations` (the top-level
dict mapping locale codes to dicts). So the fallback was essentially a no-op.

**Fix:**
```python
text = translations.get(key)
if text is None:
    text = self._translations.get(self.default_locale, {}).get(key, key)
```

---

## Bug 3 — `create_group_deep_link` didn't URL-encode the payload

**File:** `aioscam/utils/deep_linking.py`

**Symptom:** `create_group_deep_link("bot", 99, "a=1&b=2")` produced a malformed URL:
`https://max.ru/bot?add_to_group=99&start=a=1&b=2` — the `&` breaks the query string,
and `parse_deep_link()` would not recover the original payload.

**Root cause:**
```python
# Before (broken) — no quote() call:
return f"https://max.ru/{bot_username}?add_to_group={group_id}&start={payload}"

# create_deep_link() had this right:
return f"https://max.ru/{bot_username}?start={quote(payload, safe='')}"
```

**Fix:**
```python
return f"https://max.ru/{bot_username}?add_to_group={group_id}&start={quote(payload, safe='')}"
```

---

## New tests (+94)

### `tests/test_dispatcher_routing.py` (37 tests)

| Class | Coverage |
|---|---|
| `TestUpdateEventProperty` | All 13 event types return self; None update_type returns None |
| `TestUpdateProperties` | `.text`, `.sender`, `.recipient`, `.update_id`, `.event_type` |
| `TestDispatcherProcessUpdate` | Routing for `message_created`, `message_callback`, `bot_started`, `bot_stopped`, `user_added`, `message_edited`; unknown/None event types don't crash |
| `TestDispatcherStateInjection` | State injected into event.data; StateGuard blocks unauthorized commands; StateGuard allows /cancel |
| `TestDispatcherControls` | `stop_polling`, `stop_webhook`, no-event no-crash |

### `tests/test_filters_scene_webhook.py` (57 tests)

| Class | Coverage |
|---|---|
| `TestStartCommandFilter` | All 5 match modes: any, equals, startswith, contains, regex; payload from `/start <text>` message; bare `/start` fails |
| `TestContentTypeFilter` | text type, no-text, list of types, no-message |
| `TestAllFilter` | Always passes for text, no-text, empty event |
| `TestScene` | name, handler decorator, start(), update_data(), get_data() copy, next() no-op |
| `TestStateGuardMiddleware` | Non-command pass-through; allowed commands; unknown command with/without active state; custom/default hints |
| `TestI18nFallback` | Existing key, fallback to default locale (bug fix), missing everywhere → key, async reload hot-update |
| `TestGroupDeepLinkEncoding` | Without payload, URL encoding (bug fix), special chars, roundtrip |
| `TestAiohttpWebhookHandler` | Valid request, valid secret, invalid secret → 401, no secret, exception → 500 |
| `TestBotRequestContactLocation` | Keyboard structure, button type, custom button text |
| `TestBotMiscMethods` | send_action, delete_message, get_messages (empty/list), get_message, context manager, aliases, deprecation warning |
