# Demo Bot Fixes — 2026-05-28

**Коммит:** `5de0e11`  
**Тег отката:** `pre-review-2026-05-28` → `e7b902d`

---

## Что было исправлено

### Bug 1: Смена языка в "Параметрах" не работала (КРИТИЧНО)

**Файл:** `examples/demo_bot.py`  
**Функции:** `handle_callback` (ветки `settings` и `lang:`)

**Причина:** `_settings_keyboard()` возвращает `KeyboardBuilder`. При вызове `.build()` получается объект `InlineKeyboard`, а не `dict`. Функция `bot.send_message()` ожидает `keyboard: Optional[Dict]`. Бот получал объект вместо dict и падал без видимой ошибки — locale не менялся.

**Исправление:**
```python
# ❌ Было:
keyboard=kb.build()

# ✅ Стало:
keyboard=kb.build().to_dict()
```

Затронуло два места: открытие настроек (`action:settings`) и подтверждение выбора языка (`lang:ru` / `lang:en`).

---

### Bug 2: После смены языка — при повторном открытии настроек галочка сбрасывалась

**Файл:** `examples/demo_bot.py`  
**Функции:** `handle_callback` (ветка `settings`), `handle_callback` (ветка `lang:`)

**Причина:** Locale сохранялся только в `event.data['locale']` — это dict текущего запроса, он не переживает следующий callback. В БД сохранялось корректно, но при открытии настроек из БД не читали.

**Исправление:** Сохраняем locale в FSM state при переключении:
```python
# В ветке lang:
if state:
    await state.update_data(user_locale=locale)
```

При открытии настроек читаем из FSM state:
```python
saved = await state.get_data() if state else {}
current_locale = (
    event.data.get('locale')          # текущий запрос (только если только что менял)
    or saved.get('user_locale')       # FSM state (персистентно между запросами)
    or event.locale                   # Max API locale (системный)
    or 'ru'                           # fallback
)
```

---

### Feature: Шаг 4/4 — запрос телефона в регистрации

**Файл:** `examples/demo_bot.py`

**Что добавлено:**
1. Новое состояние `RegistrationState.waiting_phone`
2. После шага email (3/4) — показываем кнопку `request_contact`
3. Контакт перехватывается в `handle_contact` (уже существующий хендлер)

**Почему в handle_contact, а не в отдельный хендлер:**  
Router обрабатывает хендлеры в порядке регистрации. `handle_contact` зарегистрирован раньше (`F.message.body.text == ""`). Если добавить отдельный хендлер с `StateFilter(waiting_phone)` ПОСЛЕ `handle_contact` — он никогда не вызовется, т.к. контакт уже перехвачен.

**Решение:** `handle_contact` расширен проверкой FSM состояния:
```python
state = event.data.get('state')
if state:
    current_state_name = await state.get_state()
    if current_state_name == RegistrationState.waiting_phone.full_name:
        reg_data = await state.get_data()
        await state.set_state(None)
        await event.answer("✅ Регистрация завершена!  ...")
        return
# иначе — обычный показ контакта
```

**Шаги регистрации:**
1. `waiting_name` → Введите имя
2. `waiting_age` → Введите возраст
3. `waiting_email` → Введите email → показывает кнопку "📱 Поделиться контактом"
4. `waiting_phone` → пользователь нажимает кнопку → `handle_contact` завершает регистрацию

**Если пользователь не нажал кнопку и написал текст:**  
Сейчас `StateFilter(waiting_phone)` нет как отдельного хендлера — текстовый ввод упадёт в catch-all. Можно добавить напоминание в catch-all или добавить отдельный `StateFilter` хендлер ДО `handle_contact` в файле.

---

## Файлы изменены

| Файл | Изменение |
|------|-----------|
| `examples/demo_bot.py` | bug fixes + phone step |

---

## Что НЕ изменилось (фреймворк)

Все изменения только в `examples/demo_bot.py`. Фреймворк (`aioscam/`) не тронут.

---

## Задачи для Qwen

### Обязательно проверить:
1. **Смена языка** — открыть Параметры → нажать 🇺🇸 English → выйти → снова открыть Параметры → должна быть галочка на EN
2. **Регистрация 4 шага** — `/register` → ввести имя, возраст, email → появляется кнопка 📱 → нажать → регистрация завершена с телефоном

### Открытые вопросы:
- При `waiting_phone` + текстовое сообщение (не контакт) — нет напоминания. Рассмотреть добавление хендлера с `StateFilter(waiting_phone)` ДО `handle_contact` (нужна реорганизация порядка в файле).
- Locale из DB при открытии Settings (сейчас читаем из FSM state, а не из DB) — при рестарте бота FSM в памяти сбрасывается. Если SQLAlchemy включён — можно добавить `db.get_user_locale(user_id)` вызов.
