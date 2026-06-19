# Max Bot API — Полная справка

> **Источник:** Официальные SDK max-messenger (Go, TypeScript)
> **Дата обновления:** 2026-05-08
> **Base URL:** `https://platform-api.max.ru`
> **Auth:** `{"Authorization": "<token>"}` (без "Bearer ")

---

## Endpoints

### Bots (`/me`)

| Метод | Endpoint | HTTP | Body | Query | Описание |
|-------|----------|------|------|-------|----------|
| `get_me` | `/me` | GET | — | — | Информация о боте |
| `edit_me` | `/me` | PATCH | `{name, description, photo, ...}` | — | Редактирование бота |
| `set_commands` | `/me` | PATCH | `{commands: [...]}` | — | Установка команд бота |

### Messages (`/messages`)

| Метод | Endpoint | HTTP | Body | Query | Описание |
|-------|----------|------|------|-------|----------|
| `send_message` | `/messages` | POST | `{text, attachments, format, notify}` | `chat_id?`, `user_id?`, `disable_link_preview?` | Отправка сообщения |
| `edit_message` | `/messages` | PUT | `{text, attachments, format}` | `message_id` | Редактирование |
| `delete_message` | `/messages` | DELETE | — | `message_id` | Удаление **только своих** сообщений |
| `get_message` | `/messages/{id}` | GET | — | — | Получить одно сообщение |
| `get_messages` | `/messages` | GET | — | `chat_id?`, `message_ids?`, `from?`, `to?`, `count?` | Список сообщений |

### Callbacks (`/answers`)

| Метод | Endpoint | HTTP | Body | Query | Описание |
|-------|----------|------|------|-------|----------|
| `answer_on_callback` | `/answers` | POST | `{message?, notification?}` | `callback_id` | Ответ на нажатие кнопки |

### Chats (`/chats`)

| Метод | Endpoint | HTTP | Body | Query | Описание |
|-------|----------|------|------|-------|----------|
| `get_chats` | `/chats` | GET | — | `count?`, `marker?` | Список чатов |
| `get_chat` | `/chats/{id}` | GET | — | — | Инфо о чате |
| `get_chat_by_link` | `/chats/by_link` | GET | — | `chat_link` | Поиск по ссылке |
| `edit_chat` | `/chats/{id}` | PATCH | `{title, photo, rules, ...}` | — | Редактирование |
| `get_chat_membership` | `/chats/{id}/members/me` | GET | — | — | Участие бота |
| `get_chat_members` | `/chats/{id}/members` | GET | — | `count?`, `marker?`, `user_ids?` | Участники |
| `get_chat_admins` | `/chats/{id}/members/admin` | GET | — | — | Админы |
| `add_members` | `/chats/{id}/members` | POST | `{user_ids: [...]}` | — | Добавить |
| `remove_member` | `/chats/{id}/members` | DELETE | — | `user_id` | Удалить участника |
| `leave_chat` | `/chats/{id}/members/me` | DELETE | — | — | Выйти из чата |
| `send_action` | `/chats/{id}/actions` | POST | `{action}` | — | Действие (typing, ...) |
| `pin_message` | `/chats/{id}/pin` | PUT | `{message_id, notify?}` | — | Закрепить |
| `unpin_message` | `/chats/{id}/pin` | DELETE | — | — | Открепить |

### Subscriptions (`/subscriptions`)

| Метод | Endpoint | HTTP | Body | Query | Описание |
|-------|----------|------|------|-------|----------|
| `get_subscriptions` | `/subscriptions` | GET | — | — | Список webhook URL |
| `create_webhook` | `/subscriptions` | POST | `{url}` | — | Создать webhook |
| `unsubscribe_webhook` | `/subscriptions` | POST | `{url}` | — | Удалить webhook |

### Uploads (`/upload_url`, `/uploads`)

| Метод | Endpoint | HTTP | Body | Query | Описание |
|-------|----------|------|------|-------|----------|
| `get_upload_url` | `/upload_url` | GET | — | — | URL для загрузки |
| `upload_attachment` | `/uploads` | POST | file | `type`, `chat_id?` | Загрузка файла |

---

## Типы сообщений

### Update Types

| Тип | Описание |
|-----|----------|
| `message_created` | Новое сообщение |
| `message_callback` | Нажатие inline кнопки |
| `message_edited` | Сообщение отредактировано |
| `message_removed` | Сообщение удалено |
| `bot_started` | Пользователь начал диалог |
| `bot_stopped` | Пользователь остановил бота |
| `bot_added` | Бот добавлен в чат |
| `bot_removed` | Бот удалён из чата |
| `chat_title_changed` | Название чата изменено |
| `dialog_cleared` | История чата очищена |
| `dialog_muted` | Чат замьючен |
| `dialog_unmuted` | Чат размьючен |
| `user_added` | Пользователь добавлен |
| `user_removed` | Пользователь удалён |

### Sender Actions

`typing`, `upload_photo`, `record_video`, `upload_video`, `record_audio`, `upload_audio`, `upload_document`, `finding_location`, `choosing_sticker`

### Button Types (Inline)

| Тип | Поля | Описание |
|-----|------|----------|
| `callback` | `label`, `payload` | Кнопка с callback |
| `link` | `label`, `url` | Внешняя ссылка |
| `message` | `label`, `text` | Отправка текста |
| `chat` | `label`, `chat_id` | Переход в чат |
| `clipboard` | `label`, `clipboard_text` | Копировать в буфер |
| `open_app` | `label`, `web_app`, `contact_id?`, `payload?` | Открыть мини-приложение (WebApp) |
| `request_contact` | `label` | Запрос контакта |
| `request_geo_location` | `label` | Запрос геолокации |

---

## WebApp (мини-приложения)

Мини-приложения Max — отдельная подсистема: открываются клиентом как HTML/CSS/JS в WebView через
кнопку `OpenAppButton` (`web_app`/`contact_id`/`payload`, см. таблицу выше) или диплинк
`https://max.ru/<botName>?startapp=<payload>`. На стороне фронтенда работает MAX Bridge JS SDK
(`window.WebApp.*`, подключается через `<script src="https://st.max.ru/js/max-web-app.js">`) —
это НЕ часть Bot HTTP API выше, а отдельный браузерный JS API, описанный на
https://dev.max.ru/docs/webapps/bridge.

Серверная валидация того, что присылает WebApp (`initData`, контакты) — модуль `aioscam.webapp`,
задокументирован в `docs/ru/README.md` / `docs/en/README.md` (разделы WebApp / BotCapabilities).

---

## ⚠️ Ограничения API

### Удаление сообщений

**Бот может удалять ТОЛЬКО свои сообщения.**

```
DELETE /messages?message_id=<id>
```

- Никаких `user_id` или `chat_id` в параметрах
- Сервер определяет владельца по `message_id`
- При попытке удалить чужое → `403 access.denied`

**Из Go SDK:**
```go
func (a *messages) DeleteMessage(ctx context.Context, messageID string)
```

**Из TypeScript SDK:**
```typescript
delete = async ({ message_id }: DeleteMessageDTO) => {
    return this._delete('messages', { query: { message_id } });
}
```

**Вывод:** Ограничение на стороне сервера Max API. SDK не предоставляют `force_delete` или `clear_history`.

### Callback ответ

```
POST /answers?callback_id=<id>
Body: { message?: {...}, notification?: string }
```

- `callback_id` — **обязательный** query параметр
- `message` или `notification` — одно из них обязательно в body
- Визуальное обновление кнопки ("✅") **не работает** — API не обновляет состояние

### Webhook

- `POST /subscriptions` — создание: `{"url": "https://..."}`
- `POST /subscriptions` — удаление: `{"url": "https://..."}` (тот же endpoint!)
- `GET /subscriptions` — возвращает `{"subscriptions": ["url1", "url2"]}`

---

## Формат ответа send_message

```json
{
  "message": {
    "body": {
      "mid": "mid.abc123",
      "text": "...",
      ...
    },
    ...
  }
}
```

Для получения `message_id`: `response.message.body.mid`

---

## Сравнение с aioscam

| Max API | aioscam | Соответствует? |
|---------|---------|----------------|
| `DeleteMessage(messageID)` | `delete_message(message_id)` | ✅ Да |
| `AnswerOnCallback(callback_id, body)` | `send_callback(callback_id, message, notification)` | ✅ Да |
| `SendMessage(body, query)` | `send_message(chat_id, text, ...)` | ✅ Да |
| `GET /subscriptions` | `get_subscriptions()` → list | ✅ Да |
| `POST /subscriptions {url}` | `unsubscribe_webhook(url)` | ✅ Да |
