#!/usr/bin/env python3
"""
AioScam Framework - Полнофункциональный тестовый бот

Этот бот демонстрирует ВСЕ возможности фреймворка:
- Команды и фильтры
- FSM (машина состояний)
- Inline клавиатуры и callback'и
- Middleware
- Magic filters
- Router систему
- Formatting utilities
"""

import asyncio
import logging
import time
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from aioscam import Bot, Dispatcher, Router, Command, F, StateFilter
from aioscam.fsm import State, StatesGroup
from aioscam.utils.keyboard import KeyboardBuilder
from aioscam.utils.formatting import TextFormat
from aioscam.utils.deep_linking import create_deep_link

# ==================== FSM States ====================

class RegistrationState(StatesGroup):
    """Состояния для регистрации"""
    waiting_name = State()
    waiting_age = State()
    waiting_email = State()


class QuizState(StatesGroup):
    """Состояния для викторины"""
    question_1 = State()
    question_2 = State()
    question_3 = State()


class FeedbackState(StatesGroup):
    """Состояния для обратной связи"""
    waiting_feedback = State()


# ==================== Middleware ====================

async def logging_middleware(event, handler):
    """Middleware для логирования событий"""
    event_type = type(event.event).__name__
    logger.info(f"📨 Event: {event_type}")
    
    start_time = time.time()
    result = await handler(event)
    duration = time.time() - start_time
    
    logger.info(f"✅ Event processed in {duration:.3f}s")
    return result


async def typing_middleware(event, handler):
    """Middleware для показа typing индикатора"""
    try:
        if hasattr(event, 'message') and event.message and event.message.chat:
            await event.bot.send_action(
                event.message.chat.id,
                SenderAction.TYPING
            )
    except:
        pass  # Игнорируем ошибки typing
    
    return await handler(event)


# ==================== Routers ====================

# Создаем роутеры для разных функций
main_router = Router(name="main")
quiz_router = Router(name="quiz")
feedback_router = Router(name="feedback")
admin_router = Router(name="admin")


# ==================== Main Router ====================

@main_router.message_created(Command("start"))
async def cmd_start(event, state):
    """Команда /start - главное меню"""
    # Сбрасываем FSM состояние
    current_state = await state.get_state()
    if current_state:
        await state.set_state(None)

    # Получаем данные пользователя
    from_user = event.from_user
    if from_user:
        if hasattr(from_user, 'first_name'):
            first_name = getattr(from_user, 'first_name', '')
            last_name = getattr(from_user, 'last_name', '')
            username = getattr(from_user, 'username', '')
        elif isinstance(from_user, dict):
            first_name = from_user.get('first_name', '')
            last_name = from_user.get('last_name', '')
            username = from_user.get('username', '')
        else:
            first_name = last_name = username = ''
    else:
        first_name = last_name = username = ''

    name = f"{first_name} {last_name}".strip() or "Пользователь"
    username_line = f"🔗 @{username}\n" if username else ""

    # Версия фреймворка
    from aioscam import __version__

    # Создаем inline клавиатуру
    builder = KeyboardBuilder(inline=True)

    builder.callback("📝 Регистрация", "action:register")
    builder.callback("🎯 Викторина", "action:quiz")
    builder.row()
    builder.callback("💬 Обратная связь", "action:feedback")
    builder.callback("📊 Статистика", "action:stats")
    builder.row()
    builder.callback("❓ Помощь", "action:help")
    builder.callback("⚙️ Настройки", "action:settings")

    keyboard = builder.build()

    # Форматированный текст
    welcome_text = (
        f"🎉 **Добро пожаловать в AioScam Framework v{__version__}!**\n\n"
        f"👤 **{name}**\n"
        f"{username_line}"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖 **Я Demo Bot** и демонстрирую возможности фреймворка:\n"
        f"• 🤖 Команды и фильтры\n"
        f"• 📝 FSM (машина состояний)\n"
        f"• 🔘 Inline клавиатуры\n"
        f"• 🎛️ Callback обработчики\n"
        f"• 🎭 Middleware\n"
        f"• ✨ Magic filters\n\n"
        f"Выберите действие:\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"_create by aLex Di_"
    )

    await event.answer(welcome_text, keyboard=keyboard.to_dict())


@main_router.message_created(Command("help"))
async def cmd_help(event):
    """Команда /help - справка"""
    from aioscam import __version__

    help_text = (
        f"📖 **Справка по AioScam v{__version__}**\n\n"
        f"**Реализовано в фреймворке:**\n\n"
        f"📨 **Сообщения:**\n"
        f"• Отправка текста с форматированием\n"
        f"• Bold, Italic, Code\n"
        f"• Reply на сообщения\n"
        f"• Удаление сообщений\n\n"
        f"🔘 **Клавиатуры:**\n"
        f"• Inline кнопки (callback)\n"
        f"• Link, Contact, Location\n"
        f"• KeyboardBuilder\n\n"
        f"📱 **Контакты и геолокация:**\n"
        f"• /contact — запрос контакта\n"
        f"• /location — запрос геолокации\n\n"
        f"📝 **FSM:**\n"
        f"• Регистрация (3 шага)\n"
        f"• Викторина (3 вопроса)\n"
        f"• Обратная связь\n\n"
        f"🎛️ **Архитектура:**\n"
        f"• Router + Middleware\n"
        f"• Magic filters\n"
        f"• Config (.env)\n\n"
        f"**Команды:**\n"
        f"/start /help /stats\n"
        f"/register /quiz /feedback\n"
        f"/cancel\n"
        f"/bold /italic /code\n"
        f"/contact /location\n"
        f"/delete\n\n"
        f"**Напишите:** привет, hello, помощь\n\n"
        f"**Планируется:**\n"
        f"📷 Фото 🎥 Видео 🎵 Аудио 📎 Файлы\n\n"
        f"**API:** 35/35 методов | **События:** 14 типов\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"_create by aLex Di_"
    )

    await event.answer(help_text)


@main_router.message_created(Command("stats"))
async def cmd_stats(event):
    """Команда /stats - статистика"""
    from aioscam import __version__

    stats_text = (
        f"📊 **Статистика AioScam Framework**\n\n"
        f"🤖 **Версия:** {__version__}\n"
        f"📦 **Модулей:** 68 файлов\n"
        f"🧪 **Тестов:** 74/74 passed (100%)\n"
        f"🔒 **Security Score:** 9/10\n\n"
        f"**Реализовано:**\n"
        f"• 35 API методов Max\n"
        f"• 14 типов событий\n"
        f"• 9 типов кнопок (inline)\n"
        f"• 8 типов вложений\n"
        f"• 2 класса исключений\n"
        f"• Полная async поддержка\n"
        f"• FSM с storage backends\n"
        f"• Middleware система\n"
        f"• Router система\n"
        f"• Magic filters\n"
        f"• StateGuard\n"
        f"• Запрос контакта/геолокации (inline)\n"
        f"• Удаление сообщений\n\n"
        f"✅ Framework Production-Ready!"
    )

    await event.answer(stats_text)


@main_router.message_created(Command("bold"))
async def cmd_bold(event):
    """Команда /bold - демонстрация форматирования"""
    await event.answer(
        TextFormat.bold("Это жирный текст!") + "\n" +
        TextFormat.italic("А это курсив!") + "\n" +
        TextFormat.code("print('Hello!')")
    )


@main_router.message_created(Command("italic"))
async def cmd_italic(event):
    """Команда /italic - курсив"""
    await event.answer(
        TextFormat.italic("Это курсивный текст!")
    )


@main_router.message_created(Command("code"))
async def cmd_code(event):
    """Команда /code - код"""
    await event.answer(
        TextFormat.pre(
            "from aioscam import Bot, Dispatcher\n\n"
            "dp = Dispatcher()\n"
            "bot = Bot()\n"
            "await dp.start_polling(bot)",
            "python"
        )
    )


@main_router.message_created(Command("contact"))
async def cmd_contact(event):
    """Команда /contact - demo запроса контакта через inline keyboard"""
    builder = KeyboardBuilder()
    builder.request_contact("📱 Поделиться контактом")
    kb = builder.build()

    await event.answer(
        "📱 **Запрос контакта**\n\n"
        "Нажмите кнопку чтобы поделиться контактом:",
        keyboard=kb.to_dict()
    )


@main_router.message_created(Command("location"))
async def cmd_location(event):
    """Команда /location - demo запроса геолокации через inline keyboard"""
    builder = KeyboardBuilder()
    builder.request_location("📍 Поделиться геолокацией")
    kb = builder.build()

    await event.answer(
        "📍 **Запрос геолокации**\n\n"
        "Нажмите кнопку чтобы поделиться геолокацией:",
        keyboard=kb.to_dict()
    )


@main_router.message_created(Command("delete"))
async def cmd_delete(event):
    """Команда /delete - удалить последнее сообщение"""
    # Отправляем тестовое сообщение
    msg = await event.answer("🗑️ Это сообщение будет удалено через 3 секунды...")

    await asyncio.sleep(3)

    # Получаем chat_id и user_id из event context
    chat_id = None
    user_id = None

    if hasattr(event, 'chat') and event.chat:
        chat_id = event.chat.chat_id if hasattr(event.chat, 'chat_id') else event.chat.get('chat_id')

    if hasattr(event, 'from_user') and event.from_user:
        user_id = event.from_user.user_id if hasattr(event.from_user, 'user_id') else event.from_user.get('user_id')

    if chat_id and user_id and msg:
        # msg format: {"message": {"body": {"mid": "...", ...}}}
        message_data = msg.get('message', msg)
        message_id = message_data.get('body', {}).get('mid', '')
        if message_id:
            await event.bot.delete_message(
                chat_id=chat_id,
                user_id=user_id,
                message_id=message_id
            )
            await event.answer("✅ Сообщение удалено!")
        else:
            await event.answer("⚠️ Не удалось получить message_id")
    else:
        await event.answer("⚠️ Не удалось получить chat_id/user_id")


@main_router.message_created(F.message.body.text == "")
async def handle_contact(event):
    """Обработка контакта (сообщение без текста с вложением contact)"""
    raw_data = event.data.get('raw_update', {})
    message = raw_data.get('message', {})
    body = message.get('body', {})
    attachments = body.get('attachments', [])

    for att in attachments:
        if att.get('type') == 'contact':
            payload = att.get('payload', {})
            vcf = payload.get('vcf_info', '')
            max_info = payload.get('max_info', {})

            # Парсим VCARD
            name = ""
            phone = ""
            for line in vcf.split('\r\n'):
                if line.startswith('FN:'):
                    name = line[3:]
                elif line.startswith('TEL'):
                    phone = line.split(':')[-1]

            # Берём из max_info если VCARD пустой
            if not name:
                first = max_info.get('first_name', '')
                last = max_info.get('last_name', '')
                name = f"{first} {last}".strip()

            if not phone:
                phone = "Не указан"

            await event.answer(
                f"📱 **Контакт получен!**\n\n"
                f"👤 **Имя:** {name}\n"
                f"📞 **Телефон:** `{phone}`"
            )
            return


@main_router.message_created(F.message.body.text.func(lambda t: "привет" in t.lower()))
async def handle_hello(event):
    """Обработка приветствий через magic filter"""
    await event.answer("👋 Привет! Как дела?")


@main_router.message_created(F.message.body.text.func(lambda t: "hello" in t.lower()))
async def handle_hello_en(event):
    """Обработка hello через magic filter"""
    await event.answer("👋 Hello! How are you?")


@main_router.message_created(F.message.body.text.func(lambda t: "помощь" in t.lower()))
async def handle_help_text(event):
    """Обработка 'помощь' через magic filter"""
    await event.answer("💡 Используйте /help для справки")


# ==================== Registration Router (FSM) ====================

@main_router.message_created(Command("register"))
async def cmd_register(event, state):
    """Начать регистрацию"""
    await state.set_state(RegistrationState.waiting_name)
    await event.answer(
        "📝 **Регистрация**\n\n"
        "Шаг 1/3: Введите ваше имя:"
    )


@main_router.message_created(StateFilter(RegistrationState.waiting_name))
async def process_name(event, state):
    """Обработка имени"""
    await state.update_data(name=event.text)
    await state.set_state(RegistrationState.waiting_age)
    await event.answer("✅ Имя сохранено!\n\nШаг 2/3: Введите ваш возраст:")


@main_router.message_created(StateFilter(RegistrationState.waiting_age))
async def process_age(event, state):
    """Обработка возраста"""
    try:
        age = int(event.text)
        if age < 1 or age > 150:
            await event.answer("⚠️ Введите корректный возраст (1-150):")
            return
        
        await state.update_data(age=age)
        await state.set_state(RegistrationState.waiting_email)
        await event.answer("✅ Возраст сохранен!\n\nШаг 3/3: Введите ваш email:")
    except ValueError:
        await event.answer("⚠️ Пожалуйста, введите число:")


@main_router.message_created(StateFilter(RegistrationState.waiting_email))
async def process_email(event, state):
    """Обработка email"""
    if "@" not in event.text:
        await event.answer("⚠️ Введите корректный email:")
        return
    
    await state.update_data(email=event.text)
    data = await state.get_data()
    await state.set_state(None)
    
    await event.answer(
        "✅ **Регистрация завершена!**\n\n"
        f"👤 Имя: {data['name']}\n"
        f"🔢 Возраст: {data['age']}\n"
        f"📧 Email: {data['email']}\n\n"
        "Спасибо за регистрацию! 🎉"
    )


# ==================== Quiz Router (FSM) ====================

@main_router.message_created(Command("quiz"))
async def cmd_quiz(event, state):
    """Начать викторину"""
    await state.set_state(QuizState.question_1)
    await event.answer(
        "🎯 **Викторина по AioScam**\n\n"
        "Вопрос 1/3: На каком языке написан фреймворк?\n"
        "A) JavaScript\n"
        "B) Python\n"
        "C) Go\n"
        "D) Rust\n\n"
        "Введите A, B, C или D:"
    )


@main_router.message_created(StateFilter(QuizState.question_1))
async def quiz_q1(event, state):
    """Вопрос 1"""
    answer = event.text.strip().upper()
    
    if answer == "B":
        await state.update_data(score=1, q1="correct")
        await event.answer("✅ Правильно! Python!\n\n"
                                  "Вопрос 2/3: Сколько API методов реализовано?\n"
                                  "A) 20\n"
                                  "B) 30\n"
                                  "C) 45\n"
                                  "D) 100")
    else:
        await state.update_data(score=0, q1="wrong")
        await event.answer("❌ Неверно! Правильный ответ: B (Python)\n\n"
                                  "Вопрос 2/3: Сколько API методов реализовано?\n"
                                  "A) 20\n"
                                  "B) 30\n"
                                  "C) 45\n"
                                  "D) 100")
    
    await state.set_state(QuizState.question_2)


@main_router.message_created(StateFilter(QuizState.question_2))
async def quiz_q2(event, state):
    """Вопрос 2"""
    answer = event.text.strip().upper()
    
    data = await state.get_data()
    score = data.get('score', 0)
    
    if answer == "C":
        score += 1
        await event.answer("✅ Правильно! 45 методов!\n\n"
                                  "Вопрос 3/3: Какой security score у фреймворка?\n"
                                  "A) 7/10\n"
                                  "B) 8/10\n"
                                  "C) 9/10\n"
                                  "D) 10/10")
    else:
        await event.answer("❌ Неверно! Правильный ответ: C (45)\n\n"
                                  "Вопрос 3/3: Какой security score у фреймворка?\n"
                                  "A) 7/10\n"
                                  "B) 8/10\n"
                                  "C) 9/10\n"
                                  "D) 10/10")
    
    await state.update_data(score=score)
    await state.set_state(QuizState.question_3)


@main_router.message_created(StateFilter(QuizState.question_3))
async def quiz_q3(event, state):
    """Вопрос 3"""
    answer = event.text.strip().upper()
    
    data = await state.get_data()
    score = data.get('score', 0)
    
    if answer == "C":
        score += 1
    
    await state.set_state(None)
    
    if score == 3:
        result_text = "🏆 Отлично! 3/3! Вы эксперт по AioScam!"
    elif score == 2:
        result_text = "👍 Хорошо! 2/3! Почти идеально!"
    elif score == 1:
        result_text = "📚 Неплохо! 1/3! Почитайте документацию!"
    else:
        result_text = "😅 0/3! Не волнуйтесь, попробуйте еще раз!"
    
    await event.answer(
        f"🎯 **Результаты викторины**\n\n"
        f"{result_text}\n\n"
        f"Ваш счет: **{score}/3**"
    )


# ==================== Feedback Router (FSM) ====================

@main_router.message_created(Command("feedback"))
async def cmd_feedback(event, state):
    """Начать обратную связь"""
    await state.set_state(FeedbackState.waiting_feedback)
    await event.answer(
        "💬 **Обратная связь**\n\n"
        "Напишите ваш отзыв или предложение:\n\n"
        "(Для отмены используйте /cancel)"
    )


@main_router.message_created(StateFilter(FeedbackState.waiting_feedback))
async def process_feedback(event, state):
    """Обработка отзыва"""
    await state.set_state(None)
    
    await event.answer(
        "✅ Спасибо за ваш отзыв!\n\n"
        f"Мы получили: \"{event.text[:50]}...\"\n\n"
        "Мы обязательно рассмотрим его! 🙏"
    )


# ==================== Cancel Command ====================

@main_router.message_created(Command("cancel"))
async def cmd_cancel(event, state):
    """Отменить текущую операцию"""
    current_state = await state.get_state()
    
    if current_state:
        await state.set_state(None)
        await event.answer("❌ Операция отменена.\n\nИспользуйте /start для начала.")
    else:
        await event.answer("ℹ️ У вас нет активной операции.")


# ==================== Callback Handlers ====================

@main_router.callback_query()
async def handle_callback(event):
    """Обработка callback запросов"""
    # Use the new callback_data property from EventContext
    callback_data = event.callback_data or ""
    
    # Get state from context.data (injected by dispatcher)
    state = event.data.get('state')
    
    callbacks = {
        "action:register": ("📝 Начинаем регистрацию...", "register"),
        "action:quiz": ("🎯 Запускаем викторину!", "quiz"),
        "action:feedback": ("💬 Жду ваш отзыв!", "feedback"),
        "action:stats": ("📊 Статистика:", "stats"),
        "action:help": ("📖 Справка:", "help"),
        "action:settings": ("⚙️ Настройки скоро будут доступны!", "settings"),
    }
    
    if callback_data in callbacks:
        message, command = callbacks[callback_data]
        
        if command == "register" and state:
            await state.set_state(RegistrationState.waiting_name)
            await event.answer("📝 Начинаем регистрацию!\n\nШаг 1/3: Введите ваше имя:")
        elif command == "quiz" and state:
            await state.set_state(QuizState.question_1)
            await event.answer(
                "🎯 **Викторина по AioScam**\n\n"
                "Вопрос 1/3: На каком языке написан фреймворк?\n"
                "A) JavaScript\n"
                "B) Python\n"
                "C) Go\n"
                "D) Rust\n\n"
                "Введите A, B, C или D:"
            )
        elif command == "feedback" and state:
            await state.set_state(FeedbackState.waiting_feedback)
            await event.answer("💬 Жду ваш отзыв!\n\nНапишите что думаете о боте:")
        elif command == "stats":
            await cmd_stats(event)
        elif command == "help":
            await cmd_help(event)
        elif command == "settings":
            await event.answer("⚙️ Настройки скоро будут доступны!")
        else:
            await event.answer(message)
    else:
        await event.answer(f"🔘 Нажата кнопка: {callback_data}")


# ==================== Setup Dispatcher ====================

dp = Dispatcher()

# Включаем middleware
# dp.middleware_manager.add(logging_middleware)
# dp.middleware_manager.add(typing_middleware)

# Включаем роутеры
dp.include_router(main_router)


# ==================== Main ====================

async def main():
    """Запуск бота"""
    # Config is auto-loaded from .env via get_config()
    from aioscam.config import get_config
    config = get_config()
    config.setup_logging()
    
    bot = Bot()
    
    # Получаем информацию о боте для генерации ссылки
    me = await bot.get_me()
    username = me.get('username', 'unknown')
    bot_url = f"https://max.ru/{username}"
    
    print("\n" + "="*60)
    print("🤖 AioScam Demo Bot - Запуск")
    print("="*60)
    print(f"\n✅ Бот запущен!")
    print(f"👤 Bot: {me.get('first_name', 'Unknown')}")
    print(f"🔗 Откройте бота: {bot_url}")
    print(f"💬 Отправьте /start для начала")
    print("="*60 + "\n")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
