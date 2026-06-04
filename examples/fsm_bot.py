"""
FSM Bot — finite state machine for multi-step conversations

DEMONSTRATES
────────────
  • State, StatesGroup              (aioscam.fsm)
  • state injection in handlers     (add `state` parameter to receive StateContext)
  • state.set_state() / get_state() — transition between states
  • state.update_data() / get_data()— store data between steps
  • StateGuardMiddleware             (aioscam.middleware.manager)
    blocks unknown commands while FSM is active, lets /cancel and /start through

COMMANDS
────────
  /start    — welcome and instructions
  /register — begin 3-step registration (name → age → email)
  /cancel   — cancel active registration at any step
  /status   — show current FSM state (debug info)

VISUAL IN MAX MESSENGER
───────────────────────
  /register → "Введите ваше имя:"
  "Alice"   → "Отлично! Теперь возраст:"
  "25"      → "Теперь email:"
  "/cancel" → "Регистрация отменена" (works at ANY step — StateGuard allows it)
  "/unknown"→ while FSM active: "Сейчас бот ждёт: ваше имя. Для отмены: /cancel"
  "/unknown"→ while FSM idle: handler runs normally (no guard)

SETUP
─────
  export MAX_BOT_TOKEN=your_token_here
  python fsm_bot.py

HOW FSM WORKS
─────────────
  StateContext is injected automatically when the handler declares `state`.
  States are stored per (chat_id, user_id) in memory (MemoryStorage by default).
  StatesGroup.state_name produces a string key like "RegistrationState:waiting_name".
"""

import asyncio
import logging

from aioscam import Bot, Dispatcher, Router, Command
from aioscam.fsm import State, StatesGroup
from aioscam.middleware.manager import StateGuardMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Setup ─────────────────────────────────────────────────────────────────────

dp = Dispatcher()
router = Router()

# StateGuardMiddleware blocks all commands EXCEPT /cancel and /start when FSM
# is active. Custom hints tell the user what input is expected.
guard = StateGuardMiddleware(hints={
    "RegistrationState:waiting_name":  "ваше имя",
    "RegistrationState:waiting_age":   "ваш возраст (число)",
    "RegistrationState:waiting_email": "ваш email",
})
router.add_middleware(guard)

# ── FSM states ─────────────────────────────────────────────────────────────────

class RegistrationState(StatesGroup):
    """3-step registration flow."""
    waiting_name  = State()
    waiting_age   = State()
    waiting_email = State()

# ── Handlers ──────────────────────────────────────────────────────────────────

@router.message_created(Command("start"))
async def cmd_start(event):
    """Welcome — shown when user types /start or opens the bot."""
    await event.answer(
        "👋 Добро пожаловать!\n\n"
        "Попробуй:\n"
        "/register — начать регистрацию\n"
        "/status   — показать текущее состояние\n"
        "/cancel   — отменить регистрацию"
    )


@router.message_created(Command("register"))
async def cmd_register(event, state):
    """
    Start the registration flow.

    `state` is a StateContext injected by the dispatcher. It persists data
    for the current (chat_id, user_id) pair across multiple messages.
    """
    await state.set_state(RegistrationState.waiting_name)
    await event.answer("📝 Регистрация начата.\n\nВведите ваше имя:")


@router.message_created(RegistrationState.waiting_name)
async def process_name(event, state):
    """Step 1: collect name, transition to waiting_age."""
    name = (event.text or "").strip()
    if not name:
        await event.answer("Имя не может быть пустым. Введите ваше имя:")
        return

    await state.update_data(name=name)
    await state.set_state(RegistrationState.waiting_age)
    await event.answer(f"Отлично, {name}! Теперь введите ваш возраст:")


@router.message_created(RegistrationState.waiting_age)
async def process_age(event, state):
    """Step 2: validate age, transition to waiting_email."""
    try:
        age = int((event.text or "").strip())
    except ValueError:
        await event.answer("Пожалуйста, введите число (например: 25):")
        return

    if not 1 <= age <= 150:
        await event.answer("Возраст должен быть от 1 до 150. Попробуйте ещё раз:")
        return

    await state.update_data(age=age)
    await state.set_state(RegistrationState.waiting_email)
    await event.answer("Введите ваш email:")


@router.message_created(RegistrationState.waiting_email)
async def process_email(event, state):
    """Step 3: validate email, finalize registration."""
    email = (event.text or "").strip()
    if "@" not in email:
        await event.answer("Некорректный email. Попробуйте ещё раз:")
        return

    await state.update_data(email=email)
    data = await state.get_data()

    # Clear FSM state — user is no longer in a flow
    await state.set_state(None)

    await event.answer(
        "✅ Регистрация завершена!\n\n"
        f"📛 Имя:    {data['name']}\n"
        f"🔢 Возраст: {data['age']}\n"
        f"📧 Email:  {data['email']}"
    )


@router.message_created(Command("cancel"))
async def cmd_cancel(event, state):
    """
    Cancel active registration.

    StateGuardMiddleware always lets /cancel through, so this handler fires
    regardless of which FSM state is active.
    """
    current = await state.get_state()
    if current:
        await state.set_state(None)
        await event.answer("❌ Регистрация отменена.\n\n/register — начать заново")
    else:
        await event.answer("Нет активной регистрации.")


@router.message_created(Command("status"))
async def cmd_status(event, state):
    """Debug: show current FSM state and stored data."""
    current = await state.get_state()
    data = await state.get_data()
    await event.answer(
        f"🔍 Текущее состояние: `{current or 'нет'}`\n"
        f"📦 Данные: `{data}`"
    )


# ── Router wiring ─────────────────────────────────────────────────────────────

dp.include_router(router)

# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    bot = Bot()
    logger.info("FSM bot started | /start /register /cancel /status")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        pass
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
