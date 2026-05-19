# Max API — Шпаргалка

> **Дата:** 2026-05-08
> **SDK репозитории:** `/home/ladm/PythonProjects/max-sdk-go/`, `/home/ladm/PythonProjects/max-sdk-ts/`

---

## Быстрый доступ к SDK

| SDK | Путь |
|-----|------|
| **Go** | `/home/ladm/PythonProjects/max-sdk-go/` |
| **TypeScript** | `/home/ladm/PythonProjects/max-sdk-ts/` |
| **Java** | Приватный (требует авторизации) |
| **Python** | Репозиторий не найден (404) |

---

## Что может/не может бот

### ✅ МОЖЕТ
- Отправлять сообщения (в чат / пользователю)
- Редактировать **свои** сообщения
- Удалять **свои** сообщения
- Закреплять/откреплять сообщения
- Получать список чатов, участников, админов
- Добавлять/удалять участников из чата
- Подписываться на webhook
- Отвечать на callback кнопок
- Загружать файлы (фото, видео, аудио, документы)

### ❌ НЕ МОЖЕТ
- Удалять сообщения **пользователей** (403 access.denied)
- Очищать историю чата (нет endpoint)
- Массовое удаление сообщений (нет endpoint)
- Читать сообщения до начала диалога с ботом
- Отправлять ReplyKeyboard (только inline)

---

## Ключевые ограничения

### 1. delete_message
```
DELETE /messages?message_id=<id>
```
- Только `message_id` — никаких `user_id`, `chat_id`
- Сервер проверяет владельца → 403 если чужое
- **Обход:** удалять только свои, с задержкой

### 2. answer_on_callback
```
POST /answers?callback_id=<id>
Body: { message?: {...}, notification?: string }
```
- `callback_id` обязателен в query
- `message` или `notification` — одно обязательно
- Кнопка НЕ обновляется визуально

### 3. webhook
```
GET    /subscriptions        → {"subscriptions": ["url1", ...]}
POST   /subscriptions {url}  → создать или удалить
```
- Один endpoint для создания И удаления
- Различие по наличию `url` в body

### 4. send_message
```
POST /messages?chat_id=N&user_id=N
Body: {text, attachments?, format?, notify?}
```
- `chat_id` ИЛИ `user_id` — один из них
- Ответ: `{"message": {"body": {"mid": "..."}}}`

---

## Ссылки

- **Официальная документация:** https://dev.max.ru/
- **Business портал:** https://business.max.ru/
- **Go SDK docs:** `/home/ladm/PythonProjects/max-sdk-go/docs/`
- **TS SDK docs:** `/home/ladm/PythonProjects/max-sdk-ts/docs/`
- **Полная API справка:** `docs/MAX_API_REFERENCE.md` (в этом проекте)
