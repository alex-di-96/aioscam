# Demo Bot — Полная документация пользовательских сценариев

**Файл:** `examples/demo_bot.py` (1784 строки)  
**Назначение:** Демонстрация всех возможностей фреймворка AioScam  
**Дата анализа:** 2026-05-29

---

## Содержание

1. [Архитектурные механизмы](#архитектурные-механизмы)
   - [cleanup_middleware](#cleanup_middleware-строки-331-390)
   - [answer_with_tracking](#answer_with_tracking-строки-356-371)
   - [hide_keyboard](#hide_keyboard-строки-373-380)
   - [FSM States](#fsm-states-строки-241-260)
2. [Deep Link Flow](#deep-link-flow)
   - [Новый пользователь (bot_started)](#новый-пользователь-bot_started)
   - [Существующий пользователь (StartCommand)](#существующий-пользователь-startcommand)
3. [Главное меню (/start)](#главное-меню-start)
4. [Регистрация (FSM: 4 шага)](#регистрация-fsm-4-шага)
5. [Викторина (FSM: 3 вопроса)](#викторина-fsm-3-вопроса)
   - [Текстовый вариант (A/B/C/D)](#текстовый-вариант-abcd)
   - [Callback вариант (inline кнопки)](#callback-вариант-inline-кнопки)
6. [Обратная связь (FSM)](#обратная-связь-fsm)
7. [Обработка изображения (FSM)](#обработка-изображения-fsm)
8. [Настройки (выбор языка)](#настройки-выбор-языка)
9. [Приглашение друга (Deep Link генерация)](#приглашение-друга-deep-link-генерация)
10. [Прочие команды](#прочие-команды)
11. [Catch-all handler](#catch-all-handler)

---

## Архитектурные механизмы

### cleanup_middleware (строки 331-390)

**Назначение:** Автоматическое удаление предыдущих сообщений бота для поддержания чистого чата.

**Алгоритм работы:**

```python
async def cleanup_middleware(event, handler):
    # 1. Извлекаем prev_bot_msg_id из FSM state
    state = event.data.get('state')
    saved_data = await state.get_data()
    prev_msg_id = saved_data.get('prev_bot_msg_id')
    
    # 2. Оборачиваем event.answer для трекинга новых сообщений
    original_answer = event.answer
    async def answer_with_tracking(text, **kwargs):
        result = await original_answer(text, **kwargs)
        # Сохраняем message_id нового сообщения в state
        if result and isinstance(result, dict):
            msg = result.get('message', result)
            mid = msg.get('body', {}).get('mid')
            if mid and state:
                await state.update_data(prev_bot_msg_id=mid)
        return result
    event.answer = answer_with_tracking
    
    # 3. Добавляем вспомогательные функции
    event.hide_keyboard = hide_keyboard_wrapper
    event.answer_and_hide_keyboard = answer_and_hide_wrapper
    
    # 4. Вызываем handler
    result = await handler(event)
    
    # 5. ПОСЛЕ ответа — удаляем предыдущее сообщение бота
    # (кроме quiz_msg_id и feedback_msg_id — они редактируются inline)
    if prev_msg_id and prev_msg_id != quiz_msg_id and prev_msg_id != feedback_msg_id:
        await event.bot.delete_message(prev_msg_id)
    
    return result
```

**Ключевые моменты:**
- Middleware применяется ко ВСЕМ обработчикам `main_router` (строка 1651)
- Удаление происходит ПОСЛЕ нового ответа — пользователь видит плавный переход
- Исключения: `quiz_msg_id` и `feedback_msg_id` — эти сообщения редактируются, а не удаляются
- Если `prev_bot_msg_id` отсутствует — удаление не происходит

---

### answer_with_tracking (строки 356-371)

**Назначение:** Автоматическое сохранение `message_id` каждого нового сообщения бота в FSM.

**Поток данных:**

```
1. event.answer(text, keyboard=...) 
   ↓
2. answer_with_tracking(text, **kwargs)
   ↓
3. original_answer(text, **kwargs) → API call → response
   ↓
4. Извлечение mid из response['message']['body']['mid']
   ↓
5. state.update_data(prev_bot_msg_id=mid)
   ↓
6. return result
```

**Пример использования:**

```python
# Handler отправляет сообщение
await event.answer("Привет!", keyboard=kb)

# answer_with_tracking автоматически:
# 1. Отправляет сообщение через API
# 2. Получает response: {"message": {"body": {"mid": "abc123", ...}}}
# 3. Сохраняет mid="abc123" в state.prev_bot_msg_id

# При следующем вызове handler'а:
# cleanup_middleware удалит сообщение с mid="abc123"
```

---

### hide_keyboard (строки 373-380)

**Назначение:** Скрытие inline-клавиатуры предыдущего сообщения (one-time keyboard поведение).

**Реализация:**

```python
async def hide_keyboard_wrapper(text=None):
    mid = saved_data.get('prev_bot_msg_id')
    if not mid:
        return None
    # Редактируем сообщение: убираем keyboard, опционально меняем текст
    return await event.bot.edit_message(
        message_id=mid, 
        text=text,  # если None — текст не меняется
        keyboard=None  # клавиатура скрывается
    )
```

**Типичный сценарий:**

```python
# 1. Пользователь нажал кнопку "📝 Регистрация"
# 2. Handler вызывает:
await event.hide_keyboard("📝 Регистрация")  # скрывает главное меню
# 3. Затем отправляет новое сообщение:
await event.answer("Введите имя:")  # с новой клавиатурой или без
```

**Почему это важно:**
- Inline-клавиатуры в MAX не исчезают автоматически
- Без `hide_keyboard` все предыдущие кнопки остаются видимыми
- Создаёт "one-time" поведение: кнопка нажата → клавиатура исчезла

---

### FSM States (строки 241-260)

**Определённые состояния:**

```python
class RegistrationState(StatesGroup):
    waiting_name = State()    # Ожидание имени
    waiting_age = State()     # Ожидание возраста
    waiting_email = State()   # Ожидание email
    waiting_phone = State()   # Ожидание телефона (контакт)

class QuizState(StatesGroup):
    question_1 = State()      # Вопрос 1
    question_2 = State()      # Вопрос 2
    question_3 = State()      # Вопрос 3

class FeedbackState(StatesGroup):
    waiting_feedback = State()  # Ожидание текстового отзыва
    waiting_text = State()      # Ожидание текста после рейтинга

class ImageState(StatesGroup):
    waiting_image = State()   # Ожидание изображения
```

**Хранение данных в FSM:**

```python
# Сохранение данных
await state.update_data(name="Иван", age=25, email="ivan@example.com")

# Извлечение данных
data = await state.get_data()
name = data.get('name')  # "Иван"

# Переход между состояниями
await state.set_state(RegistrationState.waiting_age)

# Сброс состояния
await state.set_state(None)
```

**Специальные ключи в FSM data:**
- `prev_bot_msg_id` — message_id последнего сообщения бота (для cleanup_middleware)
- `quiz_msg_id` — message_id сообщения с вопросом викторины (редактируется inline)
- `feedback_msg_id` — message_id сообщения с рейтингом (редактируется inline)
- `score` — текущий счёт в викторине
- `name`, `age`, `email` — данные регистрации
- `feedback_rating` — выбранный рейтинг (1-5)
- `user_locale` — выбранная локаль (ru/en)

---

## Deep Link Flow

### Новый пользователь (bot_started)

**Триггер:** Пользователь переходит по ссылке `https://max.ru/<bot>?start=<payload>`

**Обработчик:** `on_bot_started` (строки 789-877)

**Последовательность:**

```
1. MAX отправляет событие bot_started с payload
   ↓
2. on_bot_started(event, state) вызывается
   ↓
3. Извлечение данных пользователя:
   - chat_id, user_id, first_name, last_name, username, locale
   ↓
4. Сохранение в БД (если SQLAlchemy доступен):
   await db.add_or_update_user(...)
   ↓
5. Проверка payload:
   if event.payload:  # Deep link
       decoded = decode_invite_payload(event.payload)
       
       if decoded["valid"]:
           # Успешная расшифровка
           inviter_name = decoded["full_name"]
           inviter_chat_id = decoded["chat_id"]
           
           # Сообщение новому пользователю
           await event.answer(
               f"🎉 **Добро пожаловать!**\n\n"
               f"Вас пригласил(а) **{inviter_name}**\n\n"
               f"Теперь вы тоже можете пригласить друзей!"
           )
           
           # Уведомление пригласившему
           if inviter_chat_id:
               await event.bot.send_message(
                   chat_id=inviter_chat_id,
                   user_id=user_id,
                   text=f"🔔 **{new_user_name}** перешёл(а) по вашей ссылке!"
               )
       else:
           # Недействительная ссылка
           reason = decoded.get("reason")
           if reason in ("expired", "expired_session"):
               await event.answer("⏰ **Данная ссылка устарела.**")
           else:
               await event.answer("🔗 **Специальная ссылка** (decode failed)")
   else:
       # Обычный запуск без deep link
       await cmd_start(event, state)
```

**Состояние FSM:**
- Не устанавливается (остаётся `None`)
- Данные пользователя сохраняются в БД, не в FSM

**Cleanup middleware:**
- `prev_bot_msg_id` обновляется через `answer_with_tracking`
- При следующем действии пользователя это сообщение будет удалено

---

### Существующий пользователь (StartCommand)

**Триггер:** Существующий пользователь переходит по deep link → MAX отправляет `message_created` с текстом `/start <payload>`

**Обработчик:** `on_repeat_deeplink` (строки 457-515)

**Почему отдельный обработчик:**
- Для существующих пользователей MAX не отправляет `bot_started`
- Вместо этого отправляется `message_created` с текстом `/start ref_123`
- `StartCommand()` фильтр извлекает payload из текста

**Последовательность:**

```
1. Пользователь кликает deep link (уже использует бота)
   ↓
2. MAX отправляет message_created с text="/start <payload>"
   ↓
3. StartCommand() фильтр матчит и извлекает payload
   ↓
4. on_repeat_deeplink(event, state) вызывается
   ↓
5. Извлечение payload:
   text = event.text  # "/start <payload>"
   payload = text[7:].strip()  # "<payload>"
   ↓
6. Расшифровка:
   decoded = decode_invite_payload(payload)
   ↓
7. Сохранение в БД:
   await db.add_or_update_user(...)
   ↓
8. Обработка результата:
   if decoded["valid"]:
       await event.answer(
           f"🎉 **Вы перешли по приглашению!**\n\n"
           f"Вас пригласил(а) **{inviter_name}**"
       )
       
       # Уведомление пригласившему
       if inviter_chat_id:
           await event.bot.send_message(
               chat_id=inviter_chat_id,
               text=f"🔔 **{new_name}** перешёл(а) по вашей ссылке! (повторный вход)"
           )
   else:
       if reason in ("expired", "expired_session"):
           await event.answer("⏰ **Ссылка устарела.**")
       else:
           await event.answer("🔗 **Специальная ссылка** (decode failed)")
```

**Отличие от bot_started:**
- Сообщение немного другое ("Вы перешли по приглашению" vs "Добро пожаловать")
- Уведомление пригласившему: "(повторный вход)"

---

## Главное меню (/start)

**Триггер:** Команда `/start` (без payload) или callback `action:start_menu`

**Обработчик:** `cmd_start` (строки 518-592)

**Последовательность:**

```
1. Пользователь отправляет /start
   ↓
2. cmd_start(event, state) вызывается
   ↓
3. Сброс FSM состояния (если было):
   current_state = await state.get_state()
   if current_state:
       await state.set_state(None)
   ↓
4. Извлечение данных пользователя:
   from_user = event.from_user
   first_name = from_user.first_name
   last_name = from_user.last_name
   username = from_user.username
   name = f"{first_name} {last_name}".strip() or "Пользователь"
   ↓
5. Создание inline-клавиатуры (главное меню):
   builder = KeyboardBuilder(inline=True)
   builder.callback("📝 Регистрация", "action:register")
   builder.callback("🎯 Викторина", "action:quiz")
   builder.row()
   builder.callback("💬 Обратная связь", "action:feedback")
   builder.callback("📊 Статистика", "action:stats")
   builder.row()
   builder.callback("🖼️ Изображение", "action:image")
   builder.callback("🔗 Пригласить друга", "action:invite")
   builder.row()
   builder.callback("⚙️ Параметры", "action:settings")
   builder.callback("❓ Помощь", "action:help")
   builder.row()
   builder.callback("⏹️ Отмена", "action:cancel")
   keyboard = builder.build()
   ↓
6. Формирование приветственного текста:
   welcome_text = (
       f"🎉 **Добро пожаловать в AioScam Framework v{__version__}!**\n\n"
       f"👤 **{name}**\n"
       f"{username_line}"
       f"━━━━━━━━━━━━━━━━━━\n\n"
       f"🤖 **Я Demo Bot** и демонстрирую возможности фреймворка:\n"
       f"• 🤖 Команды и фильтры\n"
       f"• 📝 FSM (машина состояний)\n"
       ...
   )
   ↓
7. Отправка сообщения:
   await event.answer(welcome_text, keyboard=keyboard.to_dict())
   ↓
8. answer_with_tracking сохраняет prev_bot_msg_id
   ↓
9. cleanup_middleware удаляет предыдущее сообщение бота (если было)
```

**Состояние FSM:**
- Сбрасывается в `None`
- `prev_bot_msg_id` обновляется

**Клавиатура:**

```
┌─────────────────────────────────────┐
│ 📝 Регистрация  │  🎯 Викторина     │
├─────────────────────────────────────┤
│ 💬 Обратная связь │ 📊 Статистика   │
├─────────────────────────────────────┤
│ 🖼️ Изображение  │ 🔗 Пригласить    │
├─────────────────────────────────────┤
│ ⚙️ Параметры    │ ❓ Помощь         │
├─────────────────────────────────────┤
│           ⏹️ Отмена                 │
└─────────────────────────────────────┘
```

**Callback'и:**
- `action:register` → регистрация
- `action:quiz` → викторина
- `action:feedback` → обратная связь
- `action:stats` → статистика
- `action:image` → обработка изображения
- `action:invite` → приглашение друга
- `action:settings` → настройки
- `action:help` → справка
- `action:cancel` → отмена операции

---

## Регистрация (FSM: 4 шага)

**Триггер:** Команда `/register` или callback `action:register`

**Обработчики:**
- `cmd_register` (строки 1053-1061) — начало
- `process_name` (строки 1064-1069) — шаг 1
- `process_age` (строки 1072-1082) — шаг 2
- `process_email` (строки 1085-1098) — шаг 3
- `handle_contact` (строки 903-1040) — шаг 4

### Шаг 1: Начало

```
1. Пользователь нажимает "📝 Регистрация" или отправляет /register
   ↓
2. cmd_register(event, state) вызывается
   ↓
3. Установка FSM состояния:
   await state.set_state(RegistrationState.waiting_name)
   ↓
4. Отправка сообщения:
   await event.answer(
       "📝 **Регистрация**\n\n"
       "Шаг 1/4: Введите ваше имя:"
   )
   ↓
5. cleanup_middleware удаляет предыдущее сообщение (главное меню)
```

**Состояние FSM:**
- `state` = `RegistrationState.waiting_name`
- `data` = {} (пусто)

---

### Шаг 2: Ввод имени

```
1. Пользователь отправляет текст (например, "Иван")
   ↓
2. StateFilter(RegistrationState.waiting_name) матчит
   ↓
3. process_name(event, state) вызывается
   ↓
4. Сохранение имени:
   await state.update_data(name=event.text)  # name="Иван"
   ↓
5. Переход к следующему состоянию:
   await state.set_state(RegistrationState.waiting_age)
   ↓
6. Отправка подтверждения:
   await event.answer(
       "✅ Имя сохранено!\n\n"
       "Шаг 2/4: Введите ваш возраст:"
   )
   ↓
7. cleanup_middleware удаляет сообщение "Шаг 1/4: Введите ваше имя:"
```

**Состояние FSM:**
- `state` = `RegistrationState.waiting_age`
- `data` = `{"name": "Иван"}`

---

### Шаг 3: Ввод возраста

```
1. Пользователь отправляет число (например, "25")
   ↓
2. StateFilter(RegistrationState.waiting_age) матчит
   ↓
3. process_age(event, state) вызывается
   ↓
4. Валидация:
   try:
       age = int(event.text)
       if age < 1 or age > 150:
           await event.answer("⚠️ Введите корректный возраст (1-150):")
           return
   ↓
5. Сохранение возраста:
   await state.update_data(age=25)
   ↓
6. Переход к следующему состоянию:
   await state.set_state(RegistrationState.waiting_email)
   ↓
7. Отправка подтверждения:
   await event.answer(
       "✅ Возраст сохранен!\n\n"
       "Шаг 3/4: Введите ваш email:"
   )
   ↓
8. cleanup_middleware удаляет сообщение "Шаг 2/4: Введите ваш возраст:"
```

**Состояние FSM:**
- `state` = `RegistrationState.waiting_email`
- `data` = `{"name": "Иван", "age": 25}`

**Обработка ошибок:**
- Если не число: `"⚠️ Пожалуйста, введите число:"`
- Если вне диапазона 1-150: `"⚠️ Введите корректный возраст (1-150):"`
- Состояние остаётся `waiting_age`, пользователь может повторить ввод

---

### Шаг 4: Ввод email

```
1. Пользователь отправляет email (например, "ivan@example.com")
   ↓
2. StateFilter(RegistrationState.waiting_email) матчит
   ↓
3. process_email(event, state) вызывается
   ↓
4. Валидация:
   if "@" not in event.text:
       await event.answer("⚠️ Введите корректный email:")
       return
   ↓
5. Сохранение email:
   await state.update_data(email="ivan@example.com")
   ↓
6. Переход к следующему состоянию:
   await state.set_state(RegistrationState.waiting_phone)
   ↓
7. Создание клавиатуры для запроса контакта:
   builder = KeyboardBuilder()
   builder.request_contact("📱 Поделиться контактом")
   kb = builder.build()
   ↓
8. Отправка сообщения с клавиатурой:
   await event.answer(
       "✅ Email сохранён!\n\n"
       "Шаг 4/4: Поделитесь номером телефона:",
       keyboard=kb.to_dict()
   )
   ↓
9. cleanup_middleware удаляет сообщение "Шаг 3/4: Введите ваш email:"
```

**Состояние FSM:**
- `state` = `RegistrationState.waiting_phone`
- `data` = `{"name": "Иван", "age": 25, "email": "ivan@example.com"}`

**Клавиатура:**

```
┌─────────────────────────────────────┐
│    📱 Поделиться контактом          │
└─────────────────────────────────────┘
```

(Это one-time keyboard — после нажатия кнопка исчезает)

---

### Шаг 5: Запрос контакта

```
1. Пользователь нажимает "📱 Поделиться контактом"
   ↓
2. MAX отправляет message_created с attachment type="contact"
   ↓
3. handle_contact(event) вызывается (строки 903-1040)
   ↓
4. Проверка FSM состояния:
   state = event.data.get('state')
   current_state_name = await state.get_state()
   if current_state_name == RegistrationState.waiting_phone.full_name:
   ↓
5. Извлечение данных из VCARD:
   for att in attachments:
       if att.get('type') == 'contact':
           payload = att.get('payload', {})
           vcf = payload.get('vcf_info', '')
           # Парсим VCARD
           for line in vcf.split('\r\n'):
               if line.startswith('FN:'):
                   name = line[3:]
               elif line.startswith('TEL'):
                   phone = line.split(':')[-1]
   ↓
6. Извлечение всех данных из FSM:
   reg_data = await state.get_data()
   # reg_data = {"name": "Иван", "age": 25, "email": "ivan@example.com"}
   ↓
7. Сброс FSM состояния:
   await state.set_state(None)
   ↓
8. Отправка финального сообщения:
   await event.answer(
       "✅ **Регистрация завершена!**\n\n"
       f"👤 Имя: {reg_data.get('name', '')}\n"
       f"🔢 Возраст: {reg_data.get('age', '')}\n"
       f"📧 Email: {reg_data.get('email', '')}\n"
       f"📞 Телефон: `{phone_display}`\n\n"
       "⚠️ Мы не храним ваши персональные данные!\n"
       "Это демонстрация работы фреймворка.\n\n"
       "Спасибо за регистрацию! 🎉\n\n"
       "Отправьте /start для возврата в главное меню."
   )
   ↓
9. cleanup_middleware удаляет сообщение "Шаг 4/4: Поделитесь номером телефона:"
```

**Состояние FSM:**
- `state` = `None` (сброшено)
- `data` = `{"name": "Иван", "age": 25, "email": "ivan@example.com", "prev_bot_msg_id": "..."}`

**Итоговое сообщение:**

```
✅ **Регистрация завершена!**

👤 Имя: Иван
🔢 Возраст: 25
📧 Email: ivan@example.com
📞 Телефон: ...1234

⚠️ Мы не храним ваши персональные данные!
Это демонстрация работы фреймворка.

Спасибо за регистрацию! 🎉

Отправьте /start для возврата в главное меню.
```

---

## Викторина (FSM: 3 вопроса)

Викторина имеет **два варианта реализации**:
1. **Текстовый** — пользователь вводит A/B/C/D
2. **Callback** — пользователь нажимает inline-кнопки A/B/C/D

Оба варианта работают параллельно, но callback-вариант предпочтительнее (удобнее для пользователя).

---

### Текстовый вариант (A/B/C/D)

**Триггер:** Команда `/quiz`

**Обработчики:**
- `cmd_quiz` (строки 1103-1115) — начало
- `quiz_q1` (строки 1118-1135) — вопрос 1
- `quiz_q2` (строки 1138-1156) — вопрос 2
- `quiz_q3` (строки 1159-1181) — вопрос 3

#### Начало викторины

```
1. Пользователь отправляет /quiz
   ↓
2. cmd_quiz(event, state) вызывается
   ↓
3. Установка FSM состояния:
   await state.set_state(QuizState.question_1)
   ↓
4. Отправка первого вопроса:
   await event.answer(
       "🎯 **Викторина по AioScam**\n\n"
       "Вопрос 1/3: На каком языке написан фреймворк?\n"
       "A) JavaScript\n"
       "B) Python\n"
       "C) Go\n"
       "D) Rust\n\n"
       "Введите A, B, C или D:"
   )
   ↓
5. cleanup_middleware удаляет предыдущее сообщение
```

**Состояние FSM:**
- `state` = `QuizState.question_1`
- `data` = {}

---

#### Вопрос 1

```
1. Пользователь отправляет "B" (или "b", "B)", и т.д.)
   ↓
2. StateFilter(QuizState.question_1) матчит
   ↓
3. quiz_q1(event, state) вызывается
   ↓
4. Нормализация ответа:
   answer = event.text.strip().upper()  # "B"
   ↓
5. Проверка ответа:
   if answer == "B":
       await state.update_data(score=1, q1="correct")
       await event.answer(
           "✅ Правильно! Python!\n\n"
           "Вопрос 2/3: Сколько API методов реализовано?\n"
           "A) 20\nB) 30\nC) 45\nD) 100"
       )
   else:
       await state.update_data(score=0, q1="wrong")
       await event.answer(
           "❌ Неверно! Правильный ответ: B (Python)\n\n"
           "Вопрос 2/3: Сколько API методов реализовано?\n"
           "A) 20\nB) 30\nC) 45\nD) 100"
       )
   ↓
6. Переход к следующему вопросу:
   await state.set_state(QuizState.question_2)
   ↓
7. cleanup_middleware удаляет сообщение с вопросом 1
```

**Состояние FSM:**
- `state` = `QuizState.question_2`
- `data` = `{"score": 1, "q1": "correct"}` (или `score=0, q1="wrong"`)

---

#### Вопрос 2

```
1. Пользователь отправляет "C"
   ↓
2. StateFilter(QuizState.question_2) матчит
   ↓
3. quiz_q2(event, state) вызывается
   ↓
4. Извлечение текущего счёта:
   data = await state.get_data()
   score = data.get('score', 0)
   ↓
5. Проверка ответа:
   if answer == "C":
       score += 1
       await event.answer(
           "✅ Правильно! 45 методов!\n\n"
           "Вопрос 3/3: Какой security score у фреймворка?\n"
           "A) 7/10\nB) 8/10\nC) 9/10\nD) 10/10"
       )
   else:
       await event.answer(
           "❌ Неверно! Правильный ответ: C (45)\n\n"
           "Вопрос 3/3: Какой security score у фреймворка?\n"
           "A) 7/10\nB) 8/10\nC) 9/10\nD) 10/10"
       )
   ↓
6. Обновление счёта:
   await state.update_data(score=score)
   ↓
7. Переход к следующему вопросу:
   await state.set_state(QuizState.question_3)
```

**Состояние FSM:**
- `state` = `QuizState.question_3`
- `data` = `{"score": 2, "q1": "correct"}`

---

#### Вопрос 3 (финальный)

```
1. Пользователь отправляет "C"
   ↓
2. StateFilter(QuizState.question_3) матчит
   ↓
3. quiz_q3(event, state) вызывается
   ↓
4. Извлечение текущего счёта:
   data = await state.get_data()
   score = data.get('score', 0)
   ↓
5. Проверка ответа:
   if answer == "C":
       score += 1
   ↓
6. Сброс FSM состояния:
   await state.set_state(None)
   ↓
7. Формирование результата:
   if score == 3:
       result_text = "🏆 Отлично! 3/3! Вы эксперт по AioScam!"
   elif score == 2:
       result_text = "👍 Хорошо! 2/3! Почти идеально!"
   elif score == 1:
       result_text = "📚 Неплохо! 1/3! Почитайте документацию!"
   else:
       result_text = "😅 0/3! Не волнуйтесь, попробуйте еще раз!"
   ↓
8. Отправка результата:
   await event.answer(
       f"🎯 **Результаты викторины**\n\n"
       f"{result_text}\n\n"
       f"Ваш счет: **{score}/3**\n\n"
       "Отправьте /start для возврата в главное меню."
   )
   ↓
9. cleanup_middleware удаляет сообщение с вопросом 3
```

**Состояние FSM:**
- `state` = `None` (сброшено)
- `data` = `{"score": 3, "q1": "correct", "prev_bot_msg_id": "..."}`

**Итоговое сообщение:**

```
🎯 **Результаты викторины**

🏆 Отлично! 3/3! Вы эксперт по AioScam!

Ваш счет: **3/3**

Отправьте /start для возврата в главное меню.
```

---

### Callback вариант (inline кнопки)

**Триггер:** Callback `action:quiz` из главного меню

**Обработчик:** `handle_callback` (строки 1467-1497) + `handle_quiz_callback` (строки 1407-1453)

**Отличие от текстового варианта:**
- Сообщение с вопросом **редактируется** (не удаляется и не создаётся новое)
- Inline-кнопки A/B/C/D вместо текстового ввода
- `quiz_msg_id` сохраняется в FSM для редактирования

#### Начало викторины (callback)

```
1. Пользователь нажимает "🎯 Викторина" в главном меню
   ↓
2. handle_callback(event) вызывается с callback_data="action:quiz"
   ↓
3. Установка FSM состояния:
   await state.set_state(QuizState.question_1)
   ↓
4. Получение message_id текущего сообщения (главное меню):
   saved_data = await state.get_data()
   quiz_msg_id = saved_data.get('prev_bot_msg_id')
   ↓
5. Сохранение quiz_msg_id:
   event.data['quiz_msg_id'] = quiz_msg_id  # для middleware
   await state.update_data(quiz_msg_id=quiz_msg_id)
   ↓
6. Создание клавиатуры с вариантами ответа:
   kb = _quiz_keyboard(1)
   # Кнопки: A, B, C, D с callback_data "quiz:1:A", "quiz:1:B", ...
   ↓
7. Редактирование сообщения (замена главного меню на вопрос):
   await event.bot.edit_message(
       message_id=quiz_msg_id,
       text="🎯 **Викторина по AioScam**\n\n"
            "Вопрос 1/3: На каком языке написан фреймворк?\n"
            "A) JavaScript\nB) Python\nC) Go\nD) Rust",
       keyboard=kb,
   )
```

**Состояние FSM:**
- `state` = `QuizState.question_1`
- `data` = `{"quiz_msg_id": "abc123"}`

**Клавиатура:**

```
┌─────────────────────────────────────┐
│  A  │  B  │
├─────────────────────────────────────┤
│  C  │  D  │
└─────────────────────────────────────┘
```

**Важно:** cleanup_middleware **НЕ удаляет** `quiz_msg_id` — это исключение.

---

#### Ответ на вопрос 1 (callback)

```
1. Пользователь нажимает кнопку "B"
   ↓
2. MAX отправляет callback_query с callback_data="quiz:1:B"
   ↓
3. handle_quiz_callback(event, state) вызывается
   (фильтр F.callback_data.startswith("quiz:"))
   ↓
4. Извлечение quiz_msg_id:
   saved_data = await state.get_data()
   msg_id = saved_data.get('quiz_msg_id')
   ↓
5. Парсинг callback_data:
   callback_data = "quiz:1:B"
   parts = callback_data.split(":")  # ["quiz", "1", "B"]
   question = int(parts[1])  # 1
   answer = parts[2]  # "B"
   ↓
6. Проверка ответа:
   correct = {1: "B", 2: "C", 3: "C"}
   if question == 1:
       new_score = 1 if answer == "B" else 0
       await state.update_data(score=new_score, q1_answer=answer)
   ↓
7. Переход к следующему вопросу:
   next_q = question + 1  # 2
   await state.set_state(f"QuizState:question_{next_q}")
   ↓
8. Формирование текста следующего вопроса:
   questions = {
       2: ("✅ Правильно! Python!\n\n" if answer == "B" else "❌ Неверно! ...") +
          "Вопрос 2/3: Сколько API методов реализовано?\n"
          "A) 20\nB) 30\nC) 45\nD) 100",
   }
   text = questions.get(next_q)
   ↓
9. Редактирование сообщения (замена вопроса 1 на вопрос 2):
   await event.bot.edit_message(
       message_id=msg_id,
       text=text,
       keyboard=_quiz_keyboard(next_q),  # кнопки для вопроса 2
   )
```

**Состояние FSM:**
- `state` = `QuizState:question_2`
- `data` = `{"quiz_msg_id": "abc123", "score": 1, "q1_answer": "B"}`

---

#### Финальный ответ (вопрос 3)

```
1. Пользователь нажимает кнопку "C" на вопросе 3
   ↓
2. handle_quiz_callback(event, state) вызывается с callback_data="quiz:3:C"
   ↓
3. Парсинг:
   question = 3
   answer = "C"
   ↓
4. Обновление счёта:
   data = await state.get_data()
   new_score = data.get('score', 0)
   if answer == "C":  # correct[3] == "C"
       new_score += 1
   await state.update_data(score=new_score)
   ↓
5. Сброс FSM состояния:
   await state.set_state(None)
   ↓
6. Формирование результата:
   if new_score == 3:
       result = "🏆 Отлично! 3/3! Вы эксперт по AioScam!"
   ...
   ↓
7. Редактирование сообщения (замена вопроса на результат):
   await event.bot.edit_message(
       message_id=msg_id,
       text=f"🎯 **Результаты викторины**\n\n"
            f"{result}\n\n"
            f"Ваш счет: **{new_score}/3**\n\n"
            f"Отправьте /start для возврата в главное меню.",
       keyboard=None  # клавиатура убирается
   )
```

**Состояние FSM:**
- `state` = `None` (сброшено)
- `data` = `{"quiz_msg_id": "abc123", "score": 3, "q1_answer": "B", ...}`

**Итоговое сообщение (отредактированное):**

```
🎯 **Результаты викторины**

🏆 Отлично! 3/3! Вы эксперт по AioScam!

Ваш счет: **3/3**

Отправьте /start для возврата в главное меню.
```

(Без клавиатуры)

---

## Обратная связь (FSM)

**Триггер:** Команда `/feedback` или callback `action:feedback`

**Обработчики:**
- `cmd_feedback` (строки 1186-1195) — начало (текстовый вариант)
- `process_feedback` (строки 1198-1208) — обработка текста
- `handle_callback` (строки 1515-1530) — начало (callback вариант с рейтингом)
- `handle_feedback_rating` (строки 1393-1405) — обработка рейтинга
- `process_feedback_text` (строки 1233-1256) — обработка текста после рейтинга

### Вариант 1: Текстовый отзыв (команда /feedback)

```
1. Пользователь отправляет /feedback
   ↓
2. cmd_feedback(event, state) вызывается
   ↓
3. Установка FSM состояния:
   await state.set_state(FeedbackState.waiting_feedback)
   ↓
4. Отправка сообщения:
   await event.answer(
       "💬 **Обратная связь**\n\n"
       "Напишите ваш отзыв или предложение:\n\n"
       "(Для отмены используйте /cancel)"
   )
   ↓
5. Пользователь отправляет текст отзыва
   ↓
6. StateFilter(FeedbackState.waiting_feedback) матчит
   ↓
7. process_feedback(event, state) вызывается
   ↓
8. Сброс FSM состояния:
   await state.set_state(None)
   ↓
9. Отправка благодарности:
   await event.answer(
       "✅ Спасибо за ваш отзыв!\n\n"
       f"Мы получили: \"{event.text[:50]}...\"\n\n"
       "Мы обязательно рассмотрим его! 🙏"
   )
```

**Состояние FSM:**
- `state` = `None` (сброшено)

**Итоговое сообщение:**

```
✅ Спасибо за ваш отзыв!

Мы получили: "Отличный фреймворк, очень удобный..."

Мы обязательно рассмотрим его! 🙏
```

---

### Вариант 2: Рейтинг + текст (callback action:feedback)

**Начало:**

```
1. Пользователь нажимает "💬 Обратная связь" в главном меню
   ↓
2. handle_callback(event) вызывается с callback_data="action:feedback"
   ↓
3. Получение message_id текущего сообщения:
   saved_data = await state.get_data()
   feedback_msg_id = saved_data.get('prev_bot_msg_id')
   ↓
4. Сохранение feedback_msg_id:
   event.data['feedback_msg_id'] = feedback_msg_id
   await state.update_data(feedback_msg_id=feedback_msg_id)
   ↓
5. Создание клавиатуры с рейтингом:
   kb = _feedback_rating_keyboard()
   # Кнопки: 🔴 1, 🟤 2, 🟡 3, 🔵 4, 🟢 5
   ↓
6. Редактирование сообщения (замена главного меню на рейтинг):
   await event.bot.edit_message(
       message_id=feedback_msg_id,
       text="💬 **Обратная связь**\n\n"
            "Оцените работу AioScam по 5-бальной шкале:",
       keyboard=kb,
   )
```

**Состояние FSM:**
- `state` = `None` (не устанавливается!)
- `data` = `{"feedback_msg_id": "abc123"}`

**Клавиатура:**

```
┌─────────────────────────────────────┐
│ 🔴 1 │ 🟤 2 │ 🟡 3 │
├─────────────────────────────────────┤
│ 🔵 4 │ 🟢 5 │
└─────────────────────────────────────┘
```

---

**Выбор рейтинга:**

```
1. Пользователь нажимает кнопку "🟢 5"
   ↓
2. MAX отправляет callback_query с callback_data="feedback:5"
   ↓
3. handle_feedback_rating(event, state) вызывается
   (фильтр F.callback_data.startswith("feedback:"))
   ↓
4. Парсинг callback_data:
   callback_data = "feedback:5"
   parts = callback_data.split(":")  # ["feedback", "5"]
   rating = int(parts[1])  # 5
   ↓
5. Сохранение рейтинга:
   await state.update_data(feedback_rating=5)
   ↓
6. Установка FSM состояния:
   await state.set_state(FeedbackState.waiting_text)
   ↓
7. Скрытие клавиатуры (редактирование сообщения):
   saved_data = await state.get_data()
   feedback_msg_id = saved_data.get('feedback_msg_id')
   if feedback_msg_id:
       await event.bot.edit_message(
           message_id=feedback_msg_id,
           text=f"💬 Спасибо! Вы выбрали: 🟢 5/5",
           keyboard=None,
       )
   ↓
8. Отправка нового сообщения с запросом текста:
   await event.answer("✍️ Опишите, что вам понравилось / не понравилось:")
```

**Состояние FSM:**
- `state` = `FeedbackState.waiting_text`
- `data` = `{"feedback_msg_id": "abc123", "feedback_rating": 5}`

---

**Ввод текста отзыва:**

```
1. Пользователь отправляет текст (например, "Очень удобный фреймворк!")
   ↓
2. StateFilter(FeedbackState.waiting_text) матчит
   ↓
3. process_feedback_text(event, state) вызывается
   ↓
4. Извлечение данных:
   saved_data = await state.get_data()
   rating = saved_data.get('feedback_rating', '?')  # 5
   from_user = event.from_user
   name = f"{from_user.first_name} {from_user.last_name}".strip()
   ↓
5. Сброс FSM состояния:
   await state.set_state(None)
   ↓
6. Отправка благодарности:
   await event.answer(
       f"✅ **Спасибо, {name}!**\n\n"
       f"Вы оценили работу AioScam на **{rating}/5**\n\n"
       f"Ваш комментарий: \"{event.text[:100]}...\"\n\n"
       "Мы обязательно учтём ваше мнение! 🙏\n\n"
       "Отправьте /start для начала"
   )
```

**Состояние FSM:**
- `state` = `None` (сброшено)

**Итоговое сообщение:**

```
✅ **Спасибо, Иван Петров!**

Вы оценили работу AioScam на **5/5**

Ваш комментарий: "Очень удобный фреймворк!..."

Мы обязательно учтём ваше мнение! 🙏

Отправьте /start для начала
```

---

## Обработка изображения (FSM)

**Триггер:** Callback `action:image`

**Обработчики:**
- `handle_callback` (строки 1616-1628) — начало
- `handle_contact` (строки 903-970) — обработка изображения

**Требования:**
- PIL (Pillow) должен быть установлен: `pip install pillow`
- Если PIL отсутствует: `await event.answer("⚠️ PIL не установлен.")`

### Начало обработки

```
1. Пользователь нажимает "🖼️ Изображение" в главном меню
   ↓
2. handle_callback(event) вызывается с callback_data="action:image"
   ↓
3. Проверка PIL:
   if not HAS_PIL:
       await event.answer("⚠️ PIL не установлен. Установите: pip install pillow")
       return
   ↓
4. Установка FSM состояния:
   await state.set_state(ImageState.waiting_image)
   ↓
5. Скрытие клавиатуры главного меню:
   await event.hide_keyboard("🖼️ Обработка изображения")
   ↓
6. Отправка инструкции:
   await event.answer(
       "📸 **Пришлите изображение**\n\n"
       "Я его обработаю:\n"
       "• 🔄 Отражу по горизонтали\n"
       "• 📐 Приведу к размеру 800×600\n"
       "• 🏷️ Поставлю водяной знак AioScam\n\n"
       "Или /cancel для отмены."
   )
```

**Состояние FSM:**
- `state` = `ImageState.waiting_image`
- `data` = `{}`

---

### Обработка изображения

```
1. Пользователь отправляет фото
   ↓
2. MAX отправляет message_created с attachment type="image"
   ↓
3. handle_contact(event) вызывается (строки 903-970)
   (этот обработчик проверяет FSM state первым делом)
   ↓
4. Проверка FSM состояния:
   state = event.data.get('state')
   current_state_name = await state.get_state()
   if current_state_name == ImageState.waiting_image.full_name:
   ↓
5. Поиск изображения в attachments:
   image_att = next((a for a in attachments if a.get('type') == 'image'), None)
   if not image_att:
       await event.answer("⚠️ Это не изображение. Пришлите **фото**.")
       return
   ↓
6. Извлечение URL и токена для скачивания:
   payload = image_att.get('payload', {})
   url = payload.get('url')
   token = payload.get('token')
   # Или из photos[key].token структуры
   ↓
7. Отправка статуса:
   await event.answer("⏳ Обрабатываю...")
   ↓
8. Скачивание изображения в память:
   image_bytes = await event.bot.download_file_bytes(url, token)
   if not image_bytes:
       await event.answer("❌ Не удалось скачать изображение.")
       return
   ↓
9. Обработка изображения (PIL):
   try:
       processed = _process_image_demo(image_bytes)
       # 1. Отражение по горизонтали
       # 2. Resize до 800×600
       # 3. Добавление водяного знака "AioScam"
   except RuntimeError as e:
       await event.answer(f"❌ {e}")
       return
   ↓
10. Сброс FSM состояния:
    await state.set_state(None)
    ↓
11. Создание клавиатуры "Вернуться в меню":
    builder = KeyboardBuilder(inline=True)
    builder.callback("↩️ Назад в меню", "action:start_menu")
    kb = builder.build().to_dict()
    ↓
12. Подготовка медиа для отправки:
    from aioscam import InputMediaBuffer, UploadType
    from aioscam.utils.media import process_input_media
    media = InputMediaBuffer(processed, "processed.jpg", UploadType.IMAGE)
    att_dict = await process_input_media(event.bot, media)
    ↓
13. Отправка обработанного изображения:
    try:
        await event.bot.send_message(
            chat_id=event.chat_id,
            user_id=event.user_id,
            text="✅ **Готово!** Вот ваше изображение:",
            attachments=[att_dict],
            keyboard=kb,
        )
    except Exception:
        # Fallback: отправляем изображение и кнопку отдельно
        await event.bot.send_message(..., attachments=[att_dict])
        await event.answer("Нажмите кнопку для возврата в меню:", keyboard=kb)
```

**Состояние FSM:**
- `state` = `None` (сброшено)

**Итоговое сообщение:**

```
✅ **Готово!** Вот ваше изображение:

[Обработанное изображение 800×600 с водяным знаком]

┌─────────────────────────────────────┐
│       ↩️ Назад в меню               │
└─────────────────────────────────────┘
```

**Обработка ошибок:**
- Если пользователь отправил текст вместо фото: `"📸 Жду **изображение**. Отправьте фото, или /cancel для отмены."` (catch-all handler)
- Если PIL не установлен: `"⚠️ PIL не установлен."`
- Если не удалось скачать: `"❌ Не удалось скачать изображение."`
- Если ошибка обработки: `"❌ {error_message}"`

---

## Настройки (выбор языка)

**Триггер:** Callback `action:settings`

**Обработчик:** `handle_callback` (строки 1564-1579) + `lang:` callback (строки 1635-1651)

### Открытие настроек

```
1. Пользователь нажимает "⚙️ Параметры" в главном меню
   ↓
2. handle_callback(event) вызывается с callback_data="action:settings"
   ↓
3. Получение текущей локали:
   saved = await state.get_data() if state else {}
   current_locale = (
       event.data.get('locale')
       or saved.get('user_locale')
       or event.locale  # из MAX API
       or 'ru'
   )
   ↓
4. Создание клавиатуры с отметкой текущего языка:
   kb = _settings_keyboard(current_locale)
   # Если current_locale == "ru":
   #   "🇷🇺 Русский ✅"
   #   "🇺🇸 English"
   ↓
5. Отправка сообщения:
   await event.answer(
       "⚙️ **Параметры**\n\n"
       "Выберите язык интерфейса:\n"
       "🇷🇺 Русский — по умолчанию\n"
       "🇺🇸 English",
       keyboard=kb.build().to_dict(),
   )
```

**Состояние FSM:**
- `state` = `None` (не устанавливается)
- `data` обновляется с `user_locale`

**Клавиатура (если текущий язык — русский):**

```
┌─────────────────────────────────────┐
│ 🇷🇺 Русский ✅ │ 🇺🇸 English │
├─────────────────────────────────────┤
│           🔙 Назад                  │
└─────────────────────────────────────┘
```

---

### Переключение языка

```
1. Пользователь нажимает "🇺🇸 English"
   ↓
2. MAX отправляет callback_query с callback_data="lang:en"
   ↓
3. handle_callback(event) вызывается (строки 1635-1651)
   (фильтр callback_data.startswith("lang:"))
   ↓
4. Извлечение новой локали:
   locale = callback_data.split(":")[1]  # "en"
   event.data['locale'] = locale
   ↓
5. Сохранение в FSM:
   if state:
       await state.update_data(user_locale=locale)
   ↓
6. Сохранение в БД (если SQLAlchemy доступен):
   if HAS_SQLALCHEMY and event.user_id:
       await db.set_user_locale(event.user_id, locale)
   ↓
7. Создание обновлённой клавиатуры:
   kb = _settings_keyboard(locale)
   # Теперь "🇺🇸 English ✅"
   ↓
8. Отправка подтверждения:
   await event.answer(
       f"✅ Язык изменён на **English**\n\n"
       "Выберите язык интерфейса:\n"
       "🇷🇺 Русский — по умолчанию\n"
       "🇺🇸 English",
       keyboard=kb.build().to_dict(),
   )
```

**Состояние FSM:**
- `state` = `None`
- `data` = `{"user_locale": "en", "prev_bot_msg_id": "..."}`

**Обновлённая клавиатура:**

```
┌─────────────────────────────────────┐
│ 🇷🇺 Русский │ 🇺🇸 English ✅ │
├─────────────────────────────────────┤
│           🔙 Назад                  │
└─────────────────────────────────────┘
```

**Примечание:** Фактически i18n не используется в demo_bot — все тексты захардкожены на русском. Сохранение локали — это пример для разработчиков.

---

## Приглашение друга (Deep Link генерация)

**Триггер:** Callback `action:invite`

**Обработчик:** `_handle_invite` (строки 762-786)

### Генерация ссылки

```
1. Пользователь нажимает "🔗 Пригласить друга" в главном меню
   ↓
2. handle_callback(event) вызывается с callback_data="action:invite"
   ↓
3. Скрытие клавиатуры главного меню:
   await event.hide_keyboard("🔗 Приглашение")
   ↓
4. _handle_invite(event) вызывается
   ↓
5. Извлечение данных пользователя:
   full_name = event.from_user.full_name or "Пользователь"
   chat_id = event.chat_id  # НЕ user_id — безопасность!
   ↓
6. Получение username бота:
   bot_me = await event.bot.get_me()
   bot_username = bot_me.get('username', 'my_bot')
   ↓
7. Обфускация payload:
   obfuscated = encode_invite_payload(full_name, chat_id)
   # Пример: "aGVsbG8_42_abc1"
   # Содержит: full_name, chat_id, shift, hash
   ↓
8. Генерация deep link:
   invite_link = create_deep_link(bot_username, obfuscated)
   # Результат: "https://max.ru/my_bot?start=aGVsbG8_42_abc1"
   ↓
9. Отправка ссылки пользователю:
   await event.answer(
       f"📬 **Ваша персональная ссылка:**\n\n"
       f"`{invite_link}`\n\n"
       f"Поделитесь ей с друзьями! Когда они перейдут по ссылке,\n"
       f"бот узнает что их пригласили именно вы."
   )
```

**Состояние FSM:**
- `state` = `None` (не устанавливается)

**Итоговое сообщение:**

```
📬 **Ваша персональная ссылка:**

`https://max.ru/my_bot?start=aGVsbG8_42_abc1`

Поделитесь ей с друзьями! Когда они перейдут по ссылке,
бот узнает что их пригласили именно вы.
```

**Безопасность:**
- Payload обфусцирован (Caesar cipher + MD5 hash)
- `chat_id` используется вместо `user_id` — не раскрывает внутренний ID
- Ссылки истекают через 1 час (`_DEEP_LINK_MAX_AGE = 3600`)
- При перезапуске бота ссылки недействительны (`_DEEP_LINK_SESSION_KEY` меняется)

---

## Прочие команды

### /help (строки 595-628)

```
1. Пользователь отправляет /help
   ↓
2. cmd_help(event) вызывается
   ↓
3. Формирование текста справки (markdown):
   help_text = (
       f"📖 **Справка по AioScam v{__version__}**\n\n"
       "**Меню команд:** нажмите `/` в поле ввода...\n\n"
       "📨 **Форматирование:**\n"
       "• **Markdown**: `**bold**`, `[link](url)`\n"
       ...
   )
   ↓
4. Отправка:
   await event.answer(help_text, format="markdown")
```

**Состояние FSM:** Не изменяется

---

### /stats (строки 631-676)

```
1. Пользователь отправляет /stats
   ↓
2. cmd_stats(event) вызывается
   ↓
3. Формирование текста статистики (HTML):
   stats_text = (
       f"📊 <b>Статистика AioScam Framework</b>\n\n"
       f"🤖 <b>Версия:</b> {__version__}\n"
       f"📦 <b>Модулей:</b> 74 файла\n"
       ...
   )
   ↓
4. Отправка:
   await event.answer(stats_text, format="html")
```

**Состояние FSM:** Не изменяется

**Демонстрация HTML-форматирования:**
- `<b>Жирный</b>` → **Жирный**
- `<i>Курсив</i>` → *Курсив*
- `<u>Подчёркивание</u>` → Подчёркивание
- `<s>Зачёркивание</s>` → Зачёркивание
- `<code>Моноширинный</code>` → `Моноширинный`
- `<a href="url">Ссылка</a>` → Ссылка

---

### /contact (строки 679-688)

```
1. Пользователь отправляет /contact
   ↓
2. cmd_contact(event) вызывается
   ↓
3. Создание клавиатуры запроса контакта:
   builder = KeyboardBuilder()
   builder.request_contact("📱 Поделиться контактом")
   kb = builder.build()
   ↓
4. Отправка:
   await event.answer(
       "📱 **Запрос контакта**\n\n"
       "Нажмите кнопку чтобы поделиться контактом:",
       keyboard=kb.to_dict()
   )
   ↓
5. Пользователь нажимает кнопку
   ↓
6. handle_contact(event) обрабатывает контакт (строки 1000-1040)
   ↓
7. Отправка данных контакта:
   await event.answer(
       f"📱 **Контакт получен!**\n\n"
       f"👤 **Имя:** {name}\n"
       f"📞 **Телефон:** `{phone_display}`\n\n"
       ...
   )
```

**Состояние FSM:** Не изменяется (если не в `RegistrationState.waiting_phone`)

---

### /location (строки 691-700)

```
1. Пользователь отправляет /location
   ↓
2. cmd_location(event) вызывается
   ↓
3. Создание клавиатуры запроса геолокации:
   builder = KeyboardBuilder()
   builder.request_location("📍 Поделиться геолокацией")
   kb = builder.build()
   ↓
4. Отправка:
   await event.answer(
       "📍 **Запрос геолокации**\n\n"
       "Нажмите кнопку чтобы поделиться геолокацией:",
       keyboard=kb.to_dict()
   )
```

**Состояние FSM:** Не изменяется

**Примечание:** Обработка геолокации не реализована в demo_bot — это пример для разработчиков.

---

### /delete (строки 703-723)

```
1. Пользователь отправляет /delete
   ↓
2. cmd_delete(event) вызывается
   ↓
3. Отправка тестового сообщения:
   msg = await event.answer("🗑️ Это сообщение будет удалено через 3 секунды...")
   ↓
4. Ожидание 3 секунды:
   await asyncio.sleep(3)
   ↓
5. Извлечение message_id:
   message_data = msg.get('message', msg)
   message_id = message_data.get('body', {}).get('mid', '')
   ↓
6. Удаление сообщения:
   await event.bot.delete_message(message_id=message_id)
   ↓
7. Подтверждение:
   await event.answer("✅ Сообщение удалено!")
```

**Состояние FSM:** Не изменяется

**Демонстрация:**
- `Bot.delete_message()` — удаление сообщения по message_id
- `asyncio.sleep()` — асинхронное ожидание

---

### /cancel (строки 1259-1266)

```
1. Пользователь отправляет /cancel
   ↓
2. cmd_cancel(event, state) вызывается
   ↓
3. Проверка текущего состояния:
   current_state = await state.get_state()
   ↓
4. Если есть активное состояние:
   if current_state:
       await state.set_state(None)
       await event.answer("❌ Операция отменена.\n\nИспользуйте /start для начала.")
   else:
       await event.answer("ℹ️ У вас нет активной операции.")
```

**Состояние FSM:**
- Сбрасывается в `None` (если было активно)

**Использование:**
- Отмена регистрации на любом шаге
- Отмена викторины
- Отмена обратной связи
- Отмена обработки изображения

---

## Catch-all handler

**Триггер:** Любое сообщение, которое не матчит ни один специфичный обработчик

**Обработчик:** `catch_all_message` (строки 1270-1330)

**Назначение:**
- Логирование всех входящих сообщений
- Отладка deep links
- Обработка edge cases

**Алгоритм:**

```
1. Любое сообщение, не матченное другими обработчиками
   ↓
2. catch_all_message(event) вызывается
   ↓
3. Проверка FSM состояния waiting_image:
   state = event.data.get('state')
   if state:
       current = await state.get_state()
       if current == ImageState.waiting_image.full_name:
           await event.answer(
               "📸 Жду **изображение**. Отправьте фото, или /cancel для отмены."
           )
           return
   ↓
4. Извлечение raw_update данных:
   raw_data = event.data.get('raw_update', {})
   event_type = raw_data.get('event_type', 'N/A')
   update_type = raw_data.get('update_type', 'N/A')
   payload = raw_data.get('payload', 'N/A')
   ...
   ↓
5. Формирование debug-информации:
   debug_lines = [
       f"🔍 **Debug Info:**",
       f"event_type: `{event_type}`",
       f"update_type: `{update_type}`",
       f"payload: `{payload}`",
       ...
   ]
   ↓
6. Проверка deep link:
   if payload and payload not in ('N/A', '', None):
       debug_lines.append(f"🔗 **DEEP LINK DETECTED!**")
       
       # Попытка расшифровки
       decoded = decode_invite_payload(payload)
       if decoded["valid"]:
           debug_lines.append(f"✅ Decoded: full_name=`{decoded['full_name']}`")
           await event.answer("\n".join(debug_lines))
           
           # Уведомление пригласившему
           if decoded["chat_id"]:
               await event.bot.send_message(
                   chat_id=decoded["chat_id"],
                   text=f"🔔 **{new_name}** перешёл(а) по вашей ссылке! (через catch-all)"
               )
       else:
           debug_lines.append(f"❌ Decode failed: reason=`{decoded['reason']}`")
           await event.answer("\n".join(debug_lines))
   else:
       # Не deep link — просто логируем
       logger.info(f"Catch-all: type={event_type}, text='{text[:50]}'")
```

**Когда срабатывает:**
- Пользователь отправляет произвольный текст (не команду)
- Пользователь отправляет сообщение во время `ImageState.waiting_image`, но это текст, а не фото
- Deep link с неизвестным форматом
- Любое сообщение, не матченное специфичными фильтрами

**Важно:** Этот обработчик должен быть **последним** в роутере (строка 1270), иначе он перехватит сообщения у других обработчиков.

---

## Сводная таблица FSM-состояний

| Состояние | Триггер | Следующий шаг | Данные в FSM |
|-----------|---------|---------------|--------------|
| `RegistrationState.waiting_name` | `/register` или `action:register` | Ввод имени | `{}` |
| `RegistrationState.waiting_age` | Ввод имени | Ввод возраста | `{"name": "..."}` |
| `RegistrationState.waiting_email` | Ввод возраста | Ввод email | `{"name": "...", "age": N}` |
| `RegistrationState.waiting_phone` | Ввод email | Запрос контакта | `{"name": "...", "age": N, "email": "..."}` |
| `None` | Контакт получен | — | `{"name": "...", "age": N, "email": "..."}` |
| `QuizState.question_1` | `/quiz` или `action:quiz` | Вопрос 1 | `{}` или `{"quiz_msg_id": "..."}` |
| `QuizState.question_2` | Ответ на вопрос 1 | Вопрос 2 | `{"score": N, "q1": "..."}` |
| `QuizState.question_3` | Ответ на вопрос 2 | Вопрос 3 | `{"score": N, "q1": "...", "q2": "..."}` |
| `None` | Ответ на вопрос 3 | — | `{"score": N, ...}` |
| `FeedbackState.waiting_feedback` | `/feedback` | Ввод текста отзыва | `{}` |
| `None` | Текст отзыва получен | — | `{}` |
| `None` | `action:feedback` | Выбор рейтинга | `{"feedback_msg_id": "..."}` |
| `FeedbackState.waiting_text` | Выбор рейтинга | Ввод текста отзыва | `{"feedback_msg_id": "...", "feedback_rating": N}` |
| `None` | Текст отзыва получен | — | `{"feedback_rating": N}` |
| `ImageState.waiting_image` | `action:image` | Отправка фото | `{}` |
| `None` | Фото обработано | — | `{}` |

---

## Ключевые паттерны

### 1. One-time keyboard (скрытие после нажатия)

```python
# Handler получает callback от inline-кнопки
await event.hide_keyboard("📝 Регистрация")  # скрывает клавиатуру
await event.answer("Новое сообщение")  # отправляет новое
```

**Примеры:**
- Главное меню → регистрация
- Главное меню → настройки
- Главное меню → приглашение

### 2. Inline editing (редактирование сообщения)

```python
# Сохраняем message_id для последующего редактирования
await state.update_data(quiz_msg_id=msg_id)

# Редактируем сообщение (меняем текст и клавиатуру)
await event.bot.edit_message(
    message_id=msg_id,
    text="Новый текст",
    keyboard=new_keyboard,
)
```

**Примеры:**
- Викторина (вопросы меняются inline)
- Обратная связь (рейтинг → текст)

### 3. FSM data flow

```python
# Сохранение данных
await state.update_data(name="Иван", age=25)

# Извлечение данных
data = await state.get_data()
name = data.get('name')  # "Иван"

# Переход между состояниями
await state.set_state(RegistrationState.waiting_age)

# Сброс состояния (завершение flow)
await state.set_state(None)
```

### 4. Cleanup middleware

```python
# Каждое новое сообщение бота автоматически:
# 1. Сохраняет свой message_id в state.prev_bot_msg_id
# 2. При следующем действии пользователя — предыдущее сообщение удаляется

# Исключения:
# - quiz_msg_id — редактируется inline, не удаляется
# - feedback_msg_id — редактируется inline, не удаляется
```

---

## Заключение

Этот документ описывает все пользовательские сценарии demo_bot.py:

- **3 FSM-flow:** регистрация (4 шага), викторина (3 вопроса), обратная связь (рейтинг + текст)
- **1 медиа-flow:** обработка изображения (PIL)
- **2 deep link сценария:** новый пользователь + существующий пользователь
- **6 команд:** /start, /help, /stats, /contact, /location, /delete, /cancel
- **3 callback-действия:** настройки, приглашение, главное меню

Все сценарии используют:
- `cleanup_middleware` для автоматического удаления предыдущих сообщений
- `answer_with_tracking` для трекинга message_id
- `hide_keyboard` для one-time keyboard поведения
- FSM для хранения промежуточных данных

**Для разработчиков:** Используйте этот документ как справочник при создании собственных ботов на AioScam. Все паттерны (FSM, callback, middleware) полностью переносимы.
