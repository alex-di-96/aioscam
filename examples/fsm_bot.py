"""
FSM example - Registration bot

This example demonstrates a bot with finite state machine for user registration.
"""

import asyncio
import logging
from aioscam import Bot, Dispatcher, Router, Command
from aioscam.fsm import State, StatesGroup

# Setup logging
logging.basicConfig(level=logging.INFO)

# Create dispatcher and router
dp = Dispatcher()
router = Router()


class RegistrationState(StatesGroup):
    """Registration states"""
    waiting_name = State()
    waiting_age = State()
    waiting_email = State()


@router.message_created(Command("register"))
async def cmd_register(event, state):
    """Start registration process"""
    await state.set_state(RegistrationState.waiting_name)
    await event.answer(
        "📝 Регистрация\n\n"
        "Введите ваше имя:"
    )


@router.message_created(RegistrationState.waiting_name)
async def process_name(event, state):
    """Process name input"""
    await state.update_data(name=event.message.text)
    await state.set_state(RegistrationState.waiting_age)
    await event.answer("Отлично! Теперь введите ваш возраст:")


@router.message_created(RegistrationState.waiting_age)
async def process_age(event, state):
    """Process age input"""
    try:
        age = int(event.message.text)
        if age < 1 or age > 150:
            await event.answer("Пожалуйста, введите корректный возраст (1-150):")
            return
        
        await state.update_data(age=age)
        await state.set_state(RegistrationState.waiting_email)
        await event.answer("Теперь введите ваш email:")
    except ValueError:
        await event.answer("Пожалуйста, введите число:")


@router.message_created(RegistrationState.waiting_email)
async def process_email(event, state):
    """Process email input"""
    if "@" not in event.message.text:
        await event.answer("Пожалуйста, введите корректный email:")
        return
    
    await state.update_data(email=event.message.text)
    
    # Get all collected data
    data = await state.get_data()
    
    await state.set_state(None)  # Clear state
    
    await event.answer(
        "✅ Регистрация завершена!\n\n"
        f"📛 Имя: {data['name']}\n"
        f"🔢 Возраст: {data['age']}\n"
        f"📧 Email: {data['email']}"
    )


@router.message_created(Command("cancel"))
async def cmd_cancel(event, state):
    """Cancel registration"""
    current_state = await state.get_state()
    if current_state:
        await state.set_state(None)
        await event.answer("❌ Регистрация отменена.\n\n/ register - начать заново")
    else:
        await event.answer("У вас нет активной регистрации.")


@router.message_created(Command("start"))
async def cmd_start(event):
    """Handle /start command"""
    await event.answer(
        "👋 Добро пожаловать!\n\n"
        "Используйте /register для начала регистрации\n"
        "Используйте /cancel для отмены"
    )


# Include router into dispatcher
dp.include_router(router)


async def main():
    """Main function"""
    bot = Bot()
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\nBot stopped!")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
