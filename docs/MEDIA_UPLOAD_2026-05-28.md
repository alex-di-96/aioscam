# Media Upload — Реализация 2026-05-28

**Коммит:** `TBD` (после git commit)
**Версия:** v0.1.6.4

---

## Как работает upload в Max API (источник: max-sdk/py/)

Трёхэтапный процесс:

```
1. POST /uploads?access_token=TOKEN&type=image|video|audio|file
   → {"url": "https://upload.server/...", "token": null|"pre_token"}

2. POST multipart к url (field name = "data")
   Ответ зависит от типа:
   - image: {"photos": {"<key>": {"token": "IMAGE_TOKEN"}}}
   - file:  {"token": "FILE_TOKEN"}
   - video: токен был в шаге 1 (pre_token), ответ шага 2 не используется
   - audio: токен был в шаге 1 (pre_token), ответ шага 2 не используется

3. Отправить сообщение с вложением:
   {"attachments": [{"type": "image", "payload": {"token": "IMAGE_TOKEN"}}]}

ВАЖНО: после загрузки ждём 2с перед отправкой (attachment.not.ready ошибка).
При ошибке — до 5 попыток с задержкой 2с.
```

---

## Что было сломано до этого

| Файл | Проблема |
|------|---------|
| `enums/upload.py` | `PHOTO` вместо `image`, `DOCUMENT` вместо `file` |
| `bot/bot.py: get_upload_url()` | GET вместо POST, нет параметра `type` |
| `bot/bot.py: upload_attachment()` | Нерабочий placeholder |
| `types/attachment.py: InputMedia` | Заглушка без логики |
| `client/client.py` | Нет multipart upload, нет download с auth |

---

## Что реализовано

### `aioscam/enums/upload.py`
```python
class UploadType(str, Enum):
    IMAGE = "image"   # было PHOTO
    VIDEO = "video"
    AUDIO = "audio"
    FILE  = "file"    # было DOCUMENT
    # STICKER удалён — нельзя отправить
```

### `aioscam/types/attachment.py` — новые классы

**Для отправки (outgoing):**
```python
class AttachmentPayload(MaxObject):
    token: str

class AttachmentUpload(MaxObject):
    type: str  # "image"|"video"|"audio"|"file"
    payload: AttachmentPayload
    def to_dict(self) -> dict: ...
```

**InputMedia (из файла):**
```python
class InputMedia:
    def __init__(self, path: str, upload_type: Optional[UploadType] = None):
        self.path = path
        self.type = upload_type or _detect_type_by_ext(path)
# Расширения: .jpg/.png/.gif → IMAGE, .mp4/.avi → VIDEO, .mp3/.ogg → AUDIO, всё остальное → FILE
```

**InputMediaBuffer (из памяти):**
```python
class InputMediaBuffer:
    def __init__(self, buffer: bytes, filename: str = "file", upload_type: Optional[UploadType] = None):
        self.buffer = buffer
        self.filename = filename
        self.type = upload_type or _detect_type_by_ext(filename)
```

**Входящие вложения (incoming):**
- `Image` — метод `get_photo_token()` — извлекает токен из `payload.photos[key].token`
- `Video` — метод `get_best_url()` — лучшее из доступных разрешений
- `Audio` — поле `transcription`
- `File` — поля `filename`, `size`
- `Sticker` — метод `get_code()` — бот не может ОТПРАВИТЬ стикер, только получить
- `Contact`, `Location`, `Share` — как были

### `aioscam/client/client.py` — новые методы

```python
async def upload_file(url, path, upload_type) -> str:
    """Multipart POST в upload URL. Возвращает сырой JSON ответ."""

async def upload_file_buffer(url, buffer, filename, upload_type) -> str:
    """То же, но из bytes буфера."""

async def download_file(path, url, token) -> int:
    """GET с Authorization: Bearer {token}. Возвращает HTTP статус."""
```

### `aioscam/utils/media.py` — НОВЫЙ файл

```python
async def process_input_media(bot, att: InputMedia | InputMediaBuffer) -> dict:
    """Полный цикл загрузки → возвращает {"type": "...", "payload": {"token": "..."}}"""
```

### `aioscam/bot/bot.py` — исправлено и добавлено

```python
# Исправлено:
async def get_upload_url(self, upload_type) -> dict:
    # POST /uploads?type=... (было GET без type)

# Новое:
async def download_file(self, path, url, token) -> int: ...

async def send_photo(self, chat_id, user_id, photo, caption="", **kwargs): ...
async def send_video(self, chat_id, user_id, video, caption="", **kwargs): ...
async def send_audio(self, chat_id, user_id, audio, caption="", **kwargs): ...
async def send_document(self, chat_id, user_id, document, caption="", **kwargs): ...
async def send_media(self, chat_id, user_id, media, caption="", **kwargs): ...
# send_media — авто-определение типа по расширению

# Исправлено:
async def send_message(..., attachments: Optional[List[Dict]] = None, ...):
    # Добавлен явный параметр attachments
```

---

## Использование (примеры)

### Отправка файла
```python
# По пути:
await bot.send_photo(chat_id=chat_id, user_id=user_id, photo="photo.jpg")
await bot.send_video(chat_id=chat_id, user_id=user_id, video="video.mp4", caption="Смотри!")
await bot.send_document(chat_id=chat_id, user_id=user_id, document="report.pdf")
await bot.send_audio(chat_id=chat_id, user_id=user_id, audio="song.mp3")

# Авто-определение типа:
await bot.send_media(chat_id=chat_id, user_id=user_id, media="anyfile.ext")

# Из буфера:
data = open("photo.jpg", "rb").read()
await bot.send_photo(chat_id=chat_id, user_id=user_id, photo=data)

# InputMedia явно:
from aioscam import InputMedia, UploadType
media = InputMedia("photo.jpg", UploadType.IMAGE)
await bot.send_media(chat_id=chat_id, user_id=user_id, media=media, caption="Фото!")
```

### Скачивание входящего файла
```python
@router.message_created(F.message.body.text == "")
async def handle_media(event):
    raw = event.data.get("raw_update", {})
    attachments = raw.get("message", {}).get("body", {}).get("attachments", [])
    for att in attachments:
        payload = att.get("payload", {})
        url = payload.get("url")
        token = payload.get("token")
        if url and token:
            await event.bot.download_file("/tmp/received_file", url, token)
```

### Низкоуровневое использование
```python
from aioscam.utils.media import process_input_media
from aioscam import InputMedia, UploadType

media = InputMedia("photo.jpg")
att_dict = await process_input_media(bot, media)
# att_dict = {"type": "image", "payload": {"token": "..."}}

await bot.send_message(
    chat_id=chat_id, user_id=user_id,
    text="Фото!",
    attachments=[att_dict],
)
```

---

## Стикеры

Боты **не могут отправлять** стикеры через Max Bot API.
Тип `sticker` отсутствует в `UploadType` (нет endpoint для загрузки).

При получении стикера в событии:
```python
att_type = att.get("type")  # == "sticker"
payload = att.get("payload", {})
code = payload.get("code")   # код стикера
url = payload.get("url")     # картинка стикера
```

---

## Файлы изменены

| Файл | Изменение |
|------|-----------|
| `aioscam/enums/upload.py` | Исправлены значения enum |
| `aioscam/types/attachment.py` | Полная переработка |
| `aioscam/client/client.py` | +upload_file, +upload_file_buffer, +download_file |
| `aioscam/utils/media.py` | НОВЫЙ: process_input_media |
| `aioscam/bot/bot.py` | +send_photo/video/audio/document/media, fix get_upload_url |
| `aioscam/__init__.py` | +InputMedia, InputMediaBuffer, UploadType экспорты; версия 0.1.6.4 |
| `pyproject.toml` | +aiofiles зависимость; версия 0.1.6.4 |
| `examples/media_bot.py` | НОВЫЙ пример |

---

## Задачи для Qwen

### Обязательно протестировать:
1. `bot.send_photo(chat_id, user_id, "photo.jpg")` — изображение должно прийти
2. `bot.send_document(chat_id, user_id, "file.pdf")` — документ  
3. `bot.send_audio(chat_id, user_id, "audio.mp3")` — аудио (VIDEO/AUDIO получают pre_token)
4. `bot.download_file(path, url, token)` — скачать входящий файл

### Открытые вопросы:
- Точный формат ответа `/uploads` для VIDEO и AUDIO — SDK говорит что токен возвращается в upload URL ответе (`pre_token`), но нужно подтвердить. Если нет — смотреть `_extract_token()` в `utils/media.py`.
- `get_video()` метод — `/videos?video_token=...` — нужно проверить правильность endpoint.
