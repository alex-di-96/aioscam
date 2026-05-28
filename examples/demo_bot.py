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
- I18n (многоязычность)
- SQLAlchemy async (база данных пользователей)
"""

import asyncio
import logging
import time
import sys
import os
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import os
import sys
import fcntl

from aioscam import Bot, Dispatcher, Router, Command, F, StateFilter, BotCommand, I18n
from aioscam.enums import ParseMode, SenderAction
from aioscam.fsm import State, StatesGroup
from aioscam.utils.keyboard import KeyboardBuilder
from aioscam.utils.deep_linking import create_deep_link

# ==================== Deep Link Obfuscation (demo bot only) ====================
# Random shift + hash for secure invite links — NOT part of the framework!

import hashlib
import base64
import random
import time

# Session key — generated at bot start, links expire when bot restarts
_DEEP_LINK_SESSION_KEY = random.randint(1, 255)
_DEEP_LINK_SESSION_START = time.time()
_DEEP_LINK_MAX_AGE = 3600  # 1 hour


def encode_invite_payload(full_name: str, chat_id: int = 0, shift: int = None) -> str:
    """
    Encode invite payload with random shift + hash (demo bot only)
    Returns obfuscated string like "aGVsbG8_42_abc1"
    """
    if shift is None:
        shift = _DEEP_LINK_SESSION_KEY

    # Create hash for integrity check
    hash_input = f"{full_name}:{chat_id}:{shift}"
    short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:4]

    # Combine data with separator that won't appear in names
    data = f"{full_name}:::{chat_id}"

    # Caesar cipher with shift
    encoded_chars = []
    for ch in data:
        encoded_chars.append(chr(ord(ch) + shift))

    encoded = base64.urlsafe_b64encode("".join(encoded_chars).encode()).decode().rstrip("=")
    return f"{encoded}_{shift}_{short_hash}"


def decode_invite_payload(obfuscated: str) -> dict:
    """
    Decode invite payload. Returns {"full_name": str, "chat_id": int, "valid": bool, "reason": str}
    """
    try:
        parts = obfuscated.rsplit("_", 2)
        if len(parts) != 3:
            return {"full_name": None, "chat_id": 0, "valid": False, "reason": "invalid_format"}

        encoded, shift_str, short_hash = parts
        shift = int(shift_str)

        # Decode base64
        padding = 4 - len(encoded) % 4
        encoded += "=" * padding
        decoded_str = base64.urlsafe_b64decode(encoded).decode()

        # Reverse Caesar cipher
        decoded_data = "".join(chr(ord(ch) - shift) for ch in decoded_str)

        # Split data
        if ":::" not in decoded_data:
            return {"full_name": None, "chat_id": 0, "valid": False, "reason": "invalid_format"}

        full_name, chat_id_str = decoded_data.split(":::", 1)
        chat_id = int(chat_id_str) if chat_id_str.isdigit() else 0

        # Verify hash
        hash_input = f"{full_name}:{chat_id}:{shift}"
        expected_hash = hashlib.md5(hash_input.encode()).hexdigest()[:4]

        if expected_hash != short_hash:
            return {"full_name": None, "chat_id": 0, "valid": False, "reason": "tampered"}

        # Check session expiry
        if time.time() - _DEEP_LINK_SESSION_START > _DEEP_LINK_MAX_AGE:
            return {"full_name": None, "chat_id": 0, "valid": False, "reason": "expired"}

        if shift != _DEEP_LINK_SESSION_KEY:
            return {"full_name": None, "chat_id": 0, "valid": False, "reason": "expired_session"}

        return {"full_name": full_name, "chat_id": chat_id, "valid": True, "reason": None}

    except Exception:
        return {"full_name": None, "chat_id": 0, "valid": False, "reason": "decode_error"}

# ==================== SQLAlchemy async (User tracking) ====================
# This is an EXAMPLE for developers — shows how to use async SQLAlchemy with AioScam.
# NOT part of the framework itself.

try:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
    from sqlalchemy import Integer, String, DateTime, func, select, text
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    logger.warning("SQLAlchemy not installed. User tracking disabled. Install: pip install sqlalchemy[asyncio]")

DB_PATH = Path(__file__).parent / "demo_bot.db"
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"

class Base(DeclarativeBase):
    pass

class User(Base):
    """
    Example user model for AioScam developers.
    Demonstrates async SQLAlchemy integration.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(Integer, unique=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True)
    first_name: Mapped[str] = mapped_column(String(255), default="")
    last_name: Mapped[str] = mapped_column(String(255), default="")
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    locale: Mapped[str] = mapped_column(String(10), default="ru")
    created_at = mapped_column(DateTime, server_default=func.now())
    updated_at = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Database:
    """Async database wrapper for demo bot"""

    def __init__(self):
        self.engine = None
        self.session_factory = None

    async def init(self):
        """Initialize database"""
        if not HAS_SQLALCHEMY:
            logger.info("Database: SQLAlchemy not available, skipping")
            return
        self.engine = create_async_engine(DB_URL, echo=False)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"Database: initialized ({DB_PATH})")

    async def add_or_update_user(self, chat_id, user_id, first_name="", last_name="", username="", locale="ru"):
        """Add new user or update existing (tracks new users only)"""
        if not self.session_factory:
            return
        async with self.session_factory() as session:
            async with session.begin():
                result = await session.execute(select(User).where(User.user_id == user_id))
                existing = result.scalar_one_or_none()
                if existing:
                    existing.first_name = first_name
                    existing.last_name = last_name
                    existing.username = username
                    existing.updated_at = func.now()
                else:
                    user = User(
                        chat_id=chat_id,
                        user_id=user_id,
                        first_name=first_name,
                        last_name=last_name,
                        username=username,
                        locale=locale,
                    )
                    session.add(user)
                    logger.info(f"DB: New user added: {first_name} {last_name} (user_id={user_id})")

    async def set_user_locale(self, user_id, locale):
        """Update user locale"""
        if not self.session_factory:
            return
        async with self.session_factory() as session:
            async with session.begin():
                result = await session.execute(select(User).where(User.user_id == user_id))
                user = result.scalar_one_or_none()
                if user:
                    user.locale = locale

    async def get_user_count(self):
        """Get total user count"""
        if not self.session_factory:
            return 0
        async with self.session_factory() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            return result.scalar()

    async def close(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()


# Global database instance
db = Database()

# ==================== I18n ====================

# Load translations from locales/ directory (next to demo_bot.py)
LOCALES_DIR = Path(__file__).parent.parent / "locales"
i18n = I18n(path=str(LOCALES_DIR), default_locale="ru")

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
    waiting_feedback = State()
    waiting_text = State()


# ==================== Middleware ====================

async def cleanup_middleware(event, handler):
    """
    Middleware для одноразовых клавиатур и очистки чата.

    Правило:
    1. Пользователь нажал кнопку → клавиатура исчезает (hide_keyboard)
    2. Бот ответил новым сообщением → предыдущее сообщение бота удаляется
    """
    state = event.data.get('state')
    saved_data = {}
    if state:
        try:
            saved_data = await state.get_data()
        except Exception as e:
            print(f"🧹 get_data error: {e}")
    prev_msg_id = saved_data.get('prev_bot_msg_id')
    quiz_msg_id = saved_data.get('quiz_msg_id')

    # Оборачиваем event.answer для сохранения message_id бота в FSM state
    original_answer = event.answer

    async def answer_with_tracking(text, **kwargs):
        print(f"📝 answer_with_tracking called: text_len={len(text)}")
        result = await original_answer(text, **kwargs)
        if result and isinstance(result, dict):
            msg = result.get('message', result)
            body = msg.get('body', {})
            mid = body.get('mid')
            print(f"📝 answer_with_tracking: extracted mid={mid}")
            if mid and state:
                try:
                    await state.update_data(prev_bot_msg_id=mid)
                    print(f"✅ Saved prev_bot_msg_id={mid} to state")
                except Exception as e:
                    print(f"❌ Failed to save prev_bot_msg_id: {e}")
        return result

    event.answer = answer_with_tracking

    async def hide_keyboard_wrapper(text=None):
        mid = saved_data.get('prev_bot_msg_id')
        print(f"🔒 hide_keyboard_wrapper: mid={mid}, text={text}")
        if not mid:
            return None
        return await event.bot.edit_message(message_id=mid, text=text, keyboard=None)

    async def answer_and_hide_wrapper(text=None, keyboard=None):
        mid = saved_data.get('prev_bot_msg_id')
        if not mid:
            return None
        final_text = text or "✅"
        return await event.bot.edit_message(message_id=mid, text=final_text, keyboard=keyboard)

    event.hide_keyboard = hide_keyboard_wrapper
    event.answer_and_hide_keyboard = answer_and_hide_wrapper

    result = await handler(event)

    # Re-read quiz_msg_id and feedback_msg_id from event.data
    quiz_msg_id = event.data.get('quiz_msg_id') or saved_data.get('quiz_msg_id')
    feedback_msg_id = event.data.get('feedback_msg_id') or saved_data.get('feedback_msg_id')

    # Удаляем предыдущее сообщение бота ПОСЛЕ нового ответа (кроме quiz_msg_id и feedback_msg_id)
    if prev_msg_id and prev_msg_id != quiz_msg_id and prev_msg_id != feedback_msg_id:
        try:
            await event.bot.delete_message(prev_msg_id)
            print(f"🗑️ Deleted prev_msg_id={prev_msg_id}")
        except Exception as e:
            print(f"⚠️ Failed to delete prev_msg_id: {e}")

    return result


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

    # Создаем inline клавиатуру — Главное меню
    # RU: Кнопки главного меню с основными функциями бота
    # EN: Main menu buttons with core bot features
    builder = KeyboardBuilder(inline=True)

    # 📝 Регистрация — FSM: 3-шаговая регистрация (имя, возраст, email)
    # EN: Registration — FSM: 3-step registration (name, age, email)
    builder.callback("📝 Регистрация", "action:register")
    # 🎯 Викторина — FSM: викторина с inline кнопками A/B/C/D (3 вопроса)
    # EN: Quiz — FSM: quiz with inline A/B/C/D buttons (3 questions)
    builder.callback("🎯 Викторина", "action:quiz")
    builder.row()
    # 💬 Обратная связь — FSM: рейтинг 1-5 + текстовый отзыв
    # EN: Feedback — FSM: rating 1-5 + text feedback
    builder.callback("💬 Обратная связь", "action:feedback")
    # 📊 Статистика — показать HTML-форматирование и версию фреймворка
    # EN: Stats — show HTML formatting and framework version
    builder.callback("📊 Статистика", "action:stats")
    builder.row()
    # 🔗 Пригласить друга — генерация диплинка для реферальной программы
    # EN: Invite friend — generate deep link for referral program
    builder.callback("🔗 Пригласить друга", "action:invite")
    builder.row()
    # ⚙️ Настройки — выбор языка (ru/en) для текущего сеанса
    # EN: Settings — language selection (ru/en) for current session
    builder.callback("⚙️ Настройки", "action:settings")
    # ❓ Помощь — справка по командам и возможностям фреймворка
    # EN: Help — help on commands and framework capabilities
    builder.callback("❓ Помощь", "action:help")
    builder.row()
    # ⏹️ Отмена — отмена текущей FSM операции
    # EN: Cancel — cancel current FSM operation
    builder.callback("⏹️ Отмена", "action:cancel")

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
        f"Powered by [aLex Di](https://github.com/alex-di-96/aioscam)"
    )

    await event.answer(welcome_text, keyboard=keyboard.to_dict())


@main_router.message_created(Command("help"))
async def cmd_help(event):
    """Команда /help - справка"""
    from aioscam import __version__

    help_text = (
        f"📖 **Справка по AioScam v{__version__}**\n\n"
        f"**Меню команд:** нажмите `/` в поле ввода или отправьте `/start`\n\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📨 **Форматирование:**\n"
        f"• **Markdown**: `**bold**`, `[link](url)`\n"
        f"• **HTML**: `<b>bold</b>`, `<a href=url>link</a>`\n"
        f"• Inline клавиатуры с one_time_keyboard\n\n"
        f"📝 **Демо-бот (FSM):**\n"
        f"• Регистрация — /register (3 шага)\n"
        f"• Викторина — кнопка в /start (3 вопроса, inline)\n"
        f"• Обратная связь — /feedback (рейтинг 1-5 + текст)\n\n"
        f"🎛️ **Архитектура:**\n"
        f"• Router + Middleware\n"
        f"• Magic filters (F.text, F.callback)\n"
        f"• StateGuard\n"
        f"• Polling + Webhook (FastAPI, Litestar)\n\n"
        f"📦 **API:** 35/35 методов | **События:** 14 типов\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"**Команды:**\n"
        f"/start — главное меню\n"
        f"/help — эта справка\n"
        f"/stats — статистика + HTML демо\n"
        f"/register — регистрация (3 шага)\n"
        f"/feedback — обратная связь\n"
        f"/cancel — отмена операции\n"
        f"/contact /location — запрос данных\n"
        f"/delete — удаление сообщения\n\n"
        f"**Планируется:**\n"
        f"📷 Фото 🎥 Видео 🎵 Аудио 📎 Файлы\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Powered by [aLex Di](https://github.com/alex-di-96)"
    )

    await event.answer(help_text, format="markdown")


@main_router.message_created(Command("stats"))
async def cmd_stats(event):
    """Команда /stats - статистика + HTML форматирование"""
    from aioscam import __version__

    stats_text = (
        f"📊 <b>Статистика AioScam Framework</b>\n\n"
        f"🤖 <b>Версия:</b> {__version__}\n"
        f"📦 <b>Модулей:</b> 68 файлов\n"
        f"🧪 <b>Тестов:</b> 158/158 passed (100%)\n"
        f"🔒 <b>Security Score:</b> 9/10\n\n"
        f"<b>Реализовано:</b>\n"
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
        f"✅ <b>Framework Production-Ready!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>Демонстрация HTML разметки:</i>\n\n"
        f"<b>Жирный текст</b> — &lt;b&gt;text&lt;/b&gt;\n"
        f"<i>Курсив</i> — &lt;i&gt;text&lt;/i&gt;\n"
        f"<u>Подчёркивание</u> — &lt;u&gt;text&lt;/u&gt;\n"
        f"<s>Зачёркивание</s> — &lt;s&gt;text&lt;/s&gt;\n"
        f"<code>Моноширинный</code> — &lt;code&gt;text&lt;/code&gt;\n"
        f'<a href="https://github.com/alex-di-96/aioscam">Ссылка HTML</a> — &lt;a href="url"&gt;text&lt;/a&gt;\n\n'
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Powered by <a href=\"https://github.com/alex-di-96\">aLex Di</a>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Отправьте</b> /start <b>для начала</b>"
    )

    await event.answer(stats_text, format="html")


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

    # Extract chat_id and user_id from event context
    chat_id = event.chat_id
    user_id = event.user_id

    if chat_id and user_id and msg:
        # msg format: {"message": {"body": {"mid": "...", ...}}}
        message_data = msg.get('message', msg)
        message_id = message_data.get('body', {}).get('mid', '')
        if message_id:
            await event.bot.delete_message(
                message_id=message_id
            )
            await event.answer("✅ Сообщение удалено!")
        else:
            await event.answer("⚠️ Не удалось получить message_id")
    else:
        await event.answer("⚠️ Не удалось получить chat_id/user_id")


# ==================== Deep Link Handlers ====================

async def _handle_invite(event):
    """Generate personal invite deep link — obfuscated, no user_id exposed"""
    # Get user's full name and chat_id (NOT user_id — security!)
    full_name = ""
    chat_id = event.chat_id or 0

    if hasattr(event, 'from_user') and event.from_user:
        user = event.from_user
        if hasattr(user, 'full_name') and user.full_name:
            full_name = user.full_name
        else:
            fn = getattr(user, 'first_name', '') or ''
            ln = getattr(user, 'last_name', '') or ''
            full_name = f"{fn} {ln}".strip() or "Пользователь"

    if not full_name:
        full_name = "Пользователь"

    # Get bot username from Bot.get_me() — NO HARDCODE
    bot_me = await event.bot.get_me()
    bot_username = bot_me.get('username', 'my_bot')

    # Encode payload with obfuscation (demo bot only)
    obfuscated = encode_invite_payload(full_name, chat_id)
    invite_link = create_deep_link(bot_username, obfuscated)

    await event.answer(
        f"📬 **Ваша персональная ссылка:**\n\n"
        f"`{invite_link}`\n\n"
        f"Поделитесь ей с друзьями! Когда они перейдут по ссылке,\n"
        f"бот узнает что их пригласили именно вы."
    )


def _settings_keyboard(current_locale: str = "ru") -> KeyboardBuilder:
    """
    RU: Клавиатура настроек — выбор языка (ru/en) с отметкой текущего
    EN: Settings keyboard — language selection (ru/en) with current locale checkmark
    """
    builder = KeyboardBuilder(inline=True)
    # 🇷🇺 Русский — switch session locale to Russian
    ru_label = "🇷🇺 Русский ✅" if current_locale == "ru" else "🇷🇺 Русский"
    # 🇺🇸 English — switch session locale to English (US flag)
    en_label = "🇺🇸 English ✅" if current_locale == "en" else "🇺🇸 English"
    builder.callback(ru_label, "lang:ru")
    builder.callback(en_label, "lang:en")
    builder.row()
    # 🔙 Назад — return to main menu (action:cancel resets state)
    builder.callback("🔙 Назад", "action:cancel")
    return builder


@main_router.bot_started()
async def on_bot_started(event, state):
    """Handle bot_started — check for deep link payload, track user in DB"""
    # Track user in database (example for developers)
    chat_id = event.chat_id or 0
    user_id = event.user_id or 0
    first_name = ""
    last_name = ""
    username = ""

    if hasattr(event, 'from_user') and event.from_user:
        user = event.from_user
        if hasattr(user, 'first_name'):
            first_name = user.first_name or ""
        if hasattr(user, 'last_name'):
            last_name = user.last_name or ""
        if hasattr(user, 'username'):
            username = user.username or ""

    # Detect locale from Max API
    locale = event.locale or "ru"

    if HAS_SQLALCHEMY:
        await db.add_or_update_user(
            chat_id=chat_id,
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            locale=locale,
        )

    if event.payload:
        # Deep link: user came via https://max.ru/<bot>?start=<payload>
        decoded = decode_invite_payload(event.payload)

        if decoded["valid"]:
            inviter_name = decoded["full_name"]
            inviter_chat_id = decoded["chat_id"]

            # Message for the new user
            text = (
                f"🎉 **Добро пожаловать!**\n\n"
                f"Вас пригласил(а) **{inviter_name}**\n\n"
                f"Теперь вы тоже можете пригласить друзей!\n"
                f"Нажмите кнопку **🔗 Пригласить друга** в главном меню."
            )
            await event.answer(text)

            # Send notification to inviter (if chat_id is available)
            if inviter_chat_id:
                bot_me = await event.bot.get_me()
                bot_username = bot_me.get('username', 'my_bot')
                new_user_name = f"{first_name} {last_name}".strip() or "Новый пользователь"
                await event.bot.send_message(
                    chat_id=inviter_chat_id,
                    user_id=user_id,  # use new user's ID for the message
                    text=f"🔔 **{new_user_name}** перешёл(а) по вашей ссылке и начал(а) общение с ботом!",
                )
        else:
            # Expired or invalid link
            reason = decoded.get("reason", "unknown")
            if reason in ("expired", "expired_session"):
                text = (
                    f"⏰ **Данная ссылка устарела.**\n\n"
                    f"Но вы можете сами протестировать бота!\n"
                    f"Нажмите **/start** для начала."
                )
            else:
                text = (
                    f"🔗 **Вы перешли по специальной ссылке!**\n\n"
                    f"Нажмите **🔗 Пригласить друга** чтобы создать свою ссылку."
                )
            await event.answer(text)
    else:
        # Regular start — just show main menu
        await cmd_start(event, state)


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



@main_router.message_created(StateFilter(FeedbackState.waiting_text))
async def process_feedback_text(event, state):
    """Обработка текстового отзыва"""
    saved_data = await state.get_data()
    rating = saved_data.get('feedback_rating', '?')
    from_user = event.from_user
    
    # Get user name
    if from_user:
        if hasattr(from_user, 'first_name'):
            name = f"{getattr(from_user, 'first_name', '')} {getattr(from_user, 'last_name', '')}".strip()
        elif isinstance(from_user, dict):
            name = f"{from_user.get('first_name', '')} {from_user.get('last_name', '')}".strip()
        else:
            name = "Пользователь"
    else:
        name = "Пользователь"
    
    await state.set_state(None)
    
    await event.answer(
        f"✅ **Спасибо, {name}!**\n\n"
        f"Вы оценили работу AioScam на **{rating}/5**\n\n"
        f"Ваш комментарий: \"{event.text[:100]}...\"\n\n"
        "Мы обязательно учтём ваше мнение! 🙏\n\n"
        "Отправьте /start для начала"
    )

@main_router.message_created(Command("cancel"))
async def cmd_cancel(event, state):
    """Отменить текущую операцию"""
    current_state = await state.get_state()

    if current_state:
        await state.set_state(None)
        await event.answer("❌ Операция отменена.\n\nИспользуйте /start для начала.")
    else:
        await event.answer("ℹ️ У вас нет активной операции.")


# ==================== Catch-All Message Handler (Deep Link Debug) ====================

@main_router.message_created()
async def catch_all_message(event):
    """
    Catch-all handler — logs EVERY message with full update structure.
    Must be LAST in the router — catches messages that didn't match any specific handler.
    Used for debugging deep links and understanding what MAX sends.
    """
    # Get raw update data
    raw_data = event.data.get('raw_update', {})

    # Extract all possible fields
    event_type = raw_data.get('event_type', 'N/A')
    update_type = raw_data.get('update_type', 'N/A')
    payload = raw_data.get('payload', 'N/A')
    user_id = raw_data.get('user_id', 'N/A')
    chat_id = raw_data.get('chat_id', 'N/A')

    # Extract message body
    message = raw_data.get('message', {})
    body = message.get('body', {})
    text = body.get('text', '')
    mid = body.get('mid', 'N/A')
    seq = body.get('seq', 'N/A')

    # Check for attachments
    attachments = body.get('attachments', [])
    att_info = []
    for att in attachments:
        att_info.append(f"type={att.get('type')}, payload_keys={list(att.get('payload', {}).keys())}")

    # Check callback
    callback = raw_data.get('callback', 'N/A')

    # Build debug info
    debug_lines = [
        f"🔍 **Debug Info:**",
        f"event_type: `{event_type}`",
        f"update_type: `{update_type}`",
        f"payload: `{payload}`",
        f"user_id: `{user_id}`",
        f"chat_id: `{chat_id}`",
        f"mid: `{mid}`, seq: `{seq}`",
        f"text: `{text[:50]}`",
    ]
    if att_info:
        debug_lines.append(f"attachments: {', '.join(att_info)}")

    # Check if this is a deep link (payload present)
    if payload and payload not in ('N/A', '', None):
        debug_lines.append(f"")
        debug_lines.append(f"🔗 **DEEP LINK DETECTED!**")

        # Try to decode
        decoded = decode_invite_payload(payload)
        if decoded["valid"]:
            debug_lines.append(f"✅ Decoded: full_name=`{decoded['full_name']}`, chat_id=`{decoded['chat_id']}`")
            await event.answer("\n".join(debug_lines))

            # Notify the inviter
            if decoded["chat_id"]:
                user_info = event.from_user
                if user_info:
                    fn = getattr(user_info, 'first_name', '') or ''
                    ln = getattr(user_info, 'last_name', '') or ''
                    new_name = f"{fn} {ln}".strip() or "Пользователь"
                    await event.bot.send_message(
                        chat_id=decoded["chat_id"],
                        user_id=event.user_id,
                        text=f"🔔 **{new_name}** перешёл(а) по вашей ссылке! (через catch-all)",
                    )
        else:
            debug_lines.append(f"❌ Decode failed: reason=`{decoded['reason']}`")
            await event.answer("\n".join(debug_lines))
    else:
        # Not a deep link — just log
        logger.info(f"Catch-all: type={event_type}, text='{text[:50]}', payload='{payload}'")


# ==================== Callback Handlers ====================



def _feedback_rating_keyboard() -> dict:
    """
    RU: Клавиатура рейтинга обратной связи — кнопки 1-5 с цветовыми индикаторами
    EN: Feedback rating keyboard — buttons 1-5 with color indicators
    """
    builder = KeyboardBuilder(inline=True)
    # 🔴 1 — Poor rating (red)
    builder.callback("🔴 1", "feedback:1")
    # 🟤 2 — Below average (brown)
    builder.callback("🟤 2", "feedback:2")
    # 🟡 3 — Average (yellow)
    builder.callback("🟡 3", "feedback:3")
    builder.row()
    # 🔵 4 — Good (blue)
    builder.callback("🔵 4", "feedback:4")
    # 🟢 5 — Excellent (green)
    builder.callback("🟢 5", "feedback:5")
    return builder.build().to_dict()


def _quiz_keyboard(question: int) -> dict:
    """
    RU: Клавиатура викторины — варианты ответа A/B/C/D для указанного вопроса
    EN: Quiz keyboard — answer options A/B/C/D for given question
    """
    builder = KeyboardBuilder(inline=True)
    builder.callback("A", f"quiz:{question}:A")
    builder.callback("B", f"quiz:{question}:B")
    builder.row()
    builder.callback("C", f"quiz:{question}:C")
    builder.callback("D", f"quiz:{question}:D")
    return builder.build().to_dict()



@main_router.callback_query(F.callback_data.startswith("feedback:"))
async def handle_feedback_rating(event, state):
    """Handle feedback rating button clicks (feedback:1-5)"""
    callback_data = event.callback_data or ""
    parts = callback_data.split(":")
    if len(parts) != 2:
        return
    rating = int(parts[1])
    
    await state.update_data(feedback_rating=rating)
    await state.set_state(FeedbackState.waiting_text)
    
    # Hide keyboard (one_time)
    saved_data = await state.get_data()
    feedback_msg_id = saved_data.get('feedback_msg_id')
    if feedback_msg_id:
        await event.bot.edit_message(
            message_id=feedback_msg_id,
            text=f"💬 Спасибо! Вы выбрали: {'🔴🟤🟡🔵🟢'[rating-1]} {rating}/5",
            keyboard=None,
        )
    
    # Send new message asking for text feedback
    await event.answer("✍️ Опишите, что вам понравилось / не понравилось:")


@main_router.callback_query(F.callback_data.startswith("quiz:"))
async def handle_quiz_callback(event, state):
    """Handle quiz button clicks (quiz:Q:A/B/C/D)"""
    saved_data = await state.get_data()
    msg_id = saved_data.get('quiz_msg_id')

    callback_data = event.callback_data or ""
    parts = callback_data.split(":")
    if len(parts) != 3:
        return

    question = int(parts[1])
    answer = parts[2]
    correct = {1: "B", 2: "C", 3: "C"}

    if question == 1:
        new_score = 1 if answer == "B" else 0
        await state.update_data(score=new_score, q1_answer=answer)
    else:
        data = await state.get_data()
        new_score = data.get('score', 0)
        if answer == correct.get(question):
            new_score += 1
        await state.update_data(score=new_score)

    if question < 3:
        next_q = question + 1
        await state.set_state(f"QuizState:question_{next_q}")
        prev_answer = data.get('q1_answer', '') if question == 2 else ''
        questions = {
            2: ("✅ Правильно! Python!\n\n" if answer == "B" else "❌ Неверно! Правильный: B (Python)\n\n") +
               "Вопрос 2/3: Сколько API методов реализовано?\n"
               "A) 20\nB) 30\nC) 45\nD) 100",
            3: ("✅ Правильно! 45 методов!\n\n" if answer == "C" else "❌ Неверно! Правильный: C (45)\n\n") +
               "Вопрос 3/3: Какой security score у фреймворка?\n"
               "A) 7/10\nB) 8/10\nC) 9/10\nD) 10/10",
        }
        text = questions.get(next_q, "Викторина завершена")
        await event.bot.edit_message(
            message_id=msg_id,
            text=text,
            keyboard=_quiz_keyboard(next_q),
        )
    else:
        await state.set_state(None)
        if new_score == 3:
            result = "🏆 Отлично! 3/3! Вы эксперт по AioScam!"
        elif new_score == 2:
            result = "👍 Хорошо! 2/3! Почти идеально!"
        elif new_score == 1:
            result = "📚 Неплохо! 1/3! Почитайте документацию!"
        else:
            result = "😅 0/3! Не волнуйтесь, попробуйте еще раз!"

        await event.bot.edit_message(
            message_id=msg_id,
            text=f"🎯 **Результаты викторины**\n\n{result}\n\nВаш счет: **{new_score}/3**",
        )


@main_router.callback_query()
async def handle_callback(event):
    """
    RU: Главный обработчик callback-кнопок меню
    EN: Main menu callback handler
    """
    callback_data = event.callback_data or ""
    state = event.data.get('state')

    # RU: Маппинг callback_id → действие
    # EN: callback_id → action mapping
    callbacks = {
        # action:register — запустить FSM регистрацию (3 шага)
        "action:register": ("register",),
        # action:quiz — запустить викторину с inline кнопками
        "action:quiz": ("quiz",),
        # action:feedback — запустить обратную связь (рейтинг + текст)
        "action:feedback": ("feedback",),
        # action:stats — показать статистику в HTML-формате
        "action:stats": ("stats",),
        # action:settings — открыть настройки (выбор языка ru/en)
        "action:settings": ("settings",),
        # action:help — показать справку по командам
        "action:help": ("help",),
        # action:cancel — отменить текущую FSM операцию
        "action:cancel": ("cancel",),
        # action:invite — сгенерировать диплинк для реферальной программы
        "action:invite": ("invite",),
    }

    if callback_data in callbacks:
        command = callbacks[callback_data][0]

        if command == "register" and state:
            # RU: Начать регистрацию — очистить FSM, запустить шаг 1 (имя)
            # EN: Start registration — clear FSM, start step 1 (name)
            await state.set_state(RegistrationState.waiting_name)
            # 1. Убираем клавиатуру (одноразовая)
            # EN: Hide keyboard (one_time)
            await event.hide_keyboard("📝 Регистрация")
            # 2. Отправляем новый ответ
            await event.answer("📝 Начинаем регистрацию!\n\nШаг 1/3: Введите ваше имя:")

        elif command == "quiz" and state:
            # RU: Начать викторину — редактировать сообщение с inline кнопками A/B/C/D
            # EN: Start quiz — edit message with inline A/B/C/D buttons
            await state.set_state(QuizState.question_1)
            saved_data = await state.get_data()
            quiz_msg_id = saved_data.get('prev_bot_msg_id')
            print(f"🎯 quiz handler: quiz_msg_id={quiz_msg_id}")
            if quiz_msg_id:
                event.data['quiz_msg_id'] = quiz_msg_id  # For middleware
                await state.update_data(quiz_msg_id=quiz_msg_id)
                kb = _quiz_keyboard(1)
                print(f"🎯 quiz keyboard: {kb}")
                await event.bot.edit_message(
                    message_id=quiz_msg_id,
                    text="🎯 **Викторина по AioScam**\n\n"
                         "Вопрос 1/3: На каком языке написан фреймворк?\n"
                         "A) JavaScript\n"
                         "B) Python\n"
                         "C) Go\n"
                         "D) Rust",
                    keyboard=kb,
                )
            else:
                await event.answer("⚠️ Не удалось начать викторину.")

        elif command == "feedback" and state:
            # RU: Начать обратную связь — показать рейтинг 1-5 с цветовыми кнопками
            # EN: Start feedback — show rating 1-5 with color buttons
            saved_data = await state.get_data()
            feedback_msg_id = saved_data.get('prev_bot_msg_id')
            if feedback_msg_id:
                event.data['feedback_msg_id'] = feedback_msg_id
                await state.update_data(feedback_msg_id=feedback_msg_id)
                kb = _feedback_rating_keyboard()
                await event.bot.edit_message(
                    message_id=feedback_msg_id,
                    text="💬 **Обратная связь**\n\n"
                         "Оцените работу AioScam по 5-бальной шкале:",
                    keyboard=kb,
                )
            else:
                await event.answer("⚠️ Не удалось начать обратную связь.")

        elif command == "stats":
            # RU: Показать статистику — HTML-форматирование, версия, API методы
            # EN: Show stats — HTML formatting, version, API methods
            await event.hide_keyboard("📊 Статистика")
            await cmd_stats(event)

        elif command == "settings":
            # RU: Открыть настройки — выбор языка с отметкой текущего
            # EN: Open settings — language selection with current locale checkmark
            user_id = event.user_id or 0
            current_locale = event.data.get('locale', event.locale or 'ru')
            kb = _settings_keyboard(current_locale)
            await event.bot.send_callback(
                callback_id=event.callback_id,
                message="⚙️ **Настройки**\n\n"
                        "Выберите язык интерфейса:\n"
                        "🇷🇺 Русский — по умолчанию\n"
                        "🇺🇸 English",
                keyboard=kb.build(),
            )

        elif command == "help":
            # RU: Показать справку по командам
            # EN: Show help on commands
            await event.hide_keyboard("📖 Справка")
            await cmd_help(event)

        elif command == "cancel":
            # RU: Отменить FSM — сбросить состояние, скрыть клавиатуру
            # EN: Cancel FSM — reset state, hide keyboard
            if state:
                current = await state.get_state()
                if current:
                    await state.set_state(None)
                    await event.hide_keyboard("⏹️ Отмена")
                    await event.answer("❌ Операция отменена.")
                else:
                    await event.hide_keyboard()
                    await event.answer("ℹ️ У вас нет активной операции.")
            else:
                await event.hide_keyboard()
                await event.answer("❌ Операция отменена.")

        elif command == "invite":
            # RU: Сгенерировать диплинк для реферальной программы
            # EN: Generate deep link for referral program
            await event.hide_keyboard("🔗 Приглашение")
            await _handle_invite(event)
        else:
            await event.hide_keyboard()
            await event.answer(f"🔘 Нажата кнопка: {callback_data}")

    # RU: Переключение языка (lang:ru / lang:en) — вне основного меню
    # EN: Language switching (lang:ru / lang:en) — outside main menu
    elif callback_data.startswith("lang:"):
        locale = callback_data.split(":")[1]
        event.data['locale'] = locale
        # Save to DB if user exists — RU: сохранить в БД если пользователь есть
        if HAS_SQLALCHEMY and event.user_id:
            await db.set_user_locale(event.user_id, locale)

        # Show settings again with updated checkmark
        kb = _settings_keyboard(locale)
        lang_name = "Русский" if locale == "ru" else "English"
        await event.bot.send_callback(
            callback_id=event.callback_id,
            message=f"✅ Язык изменён на **{lang_name}**",
            keyboard=kb.to_dict(),
        )

    else:
        await event.hide_keyboard()
        await event.answer(f"🔘 Неизвестная кнопка: {callback_data}")


# ==================== Deep Link Middleware ====================

async def deep_link_middleware(event, handler):
    """
    Middleware to handle deep links for existing users.
    When an existing user clicks on a deep link, MAX sends message_created with payload.
    This middleware intercepts and processes the deep link before the normal message handler.
    """
    # Check if this update has a payload (deep link)
    if hasattr(event, 'payload') and event.payload:
        decoded = decode_invite_payload(event.payload)
        if decoded["valid"]:
            inviter_name = decoded["full_name"]
            inviter_chat_id = decoded["chat_id"]

            # Show welcome message with referrer info
            text = (
                f"🎉 **Вы перешли по приглашению!**\n\n"
                f"Вас пригласил(а) **{inviter_name}**\n\n"
                f"Теперь вы тоже можете пригласить друзей!\n"
                f"Нажмите кнопку **🔗 Пригласить друга** в глав меню."
            )
            await event.answer(text)

            # Notify the inviter
            if inviter_chat_id:
                user_info = event.from_user
                if user_info:
                    fn = getattr(user_info, 'first_name', '') or ''
                    ln = getattr(user_info, 'last_name', '') or ''
                    new_name = f"{fn} {ln}".strip() or "Новый пользователь"
                    await event.bot.send_message(
                        chat_id=inviter_chat_id,
                        user_id=event.user_id,
                        text=f"🔔 **{new_name}** перешёл(а) по вашей ссылке!",
                    )
            return  # Don't pass to normal handler

    # No deep link — proceed normally
    return await handler(event)


# ==================== Setup Dispatcher ====================

dp = Dispatcher()

# Включаем middleware на роутер
main_router.middleware()(cleanup_middleware)
main_router.middleware()(deep_link_middleware)

# Включаем роутеры
dp.include_router(main_router)


# ==================== Main ====================

async def main():
    """Запуск бота"""
    from aioscam import __version__
    from aioscam.config import get_config
    config = get_config()
    config.setup_logging()

    # Initialize database (SQLAlchemy async example)
    await db.init()

    bot = Bot(parse_mode=ParseMode.MARKDOWN)
    
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
    
    # Register bot commands (shown in menu button)
    commands = [
        BotCommand(name="start", description="Запустить бота"),
        BotCommand(name="help", description="Справка по командам"),
        BotCommand(name="stats", description="Статистика фреймворка"),
    ]
    await bot.set_my_commands(commands)
    print(f"✅ Зарегистрировано {len(commands)} команд: {[c.name for c in commands]}")
    
    # Update bot description with version (avoid duplicates)
    current_desc = me.get("description", "")
    if f"v{__version__}" not in current_desc:
        await bot.set_bot_info(description=current_desc + f"\n\nv{__version__}")
    print(f"✅ Описание бота: v{__version__}")
    
    try:
        await dp.start_polling(bot, skip_updates=False)
    except KeyboardInterrupt:
        print("\n\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        await bot.close()
        await db.close()


PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.demo_bot.pid')


def _check_single_instance():
    """Check that only one demo_bot is running"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            print(f"❌ Demo bot already running (PID {old_pid}). Stop it first.")
            sys.exit(1)
        except (ProcessLookupError, ValueError):
            os.remove(PID_FILE)
    with open(PID_FILE, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        f.write(str(os.getpid()))


if __name__ == "__main__":
    _check_single_instance()
    try:
        asyncio.run(main())
    finally:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
