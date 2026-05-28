"""
Middleware example - Logging and timing

This example demonstrates how to use middleware for logging and timing.
"""

import asyncio
import logging
import time
from aioscam import Bot, Dispatcher, Router, Command

# Setup logging
logging.basicConfig(level=logging.INFO)

# Create dispatcher and router
dp = Dispatcher()
router = Router()


@router.middleware()
async def logging_middleware(event, handler):
    """Log all events"""
    event_type = type(event.event).__name__
    logging.info(f"📨 Received event: {event_type}")
    
    result = await handler(event)
    
    logging.info(f"✅ Event processed: {event_type}")
    return result


@router.middleware()
async def timing_middleware(event, handler):
    """Measure handler execution time"""
    start_time = time.time()
    
    result = await handler(event)
    
    execution_time = time.time() - start_time
    logging.info(f"⏱️ Handler executed in {execution_time:.3f}s")
    
    return result


@router.message_created(Command("start"))
async def cmd_start(event):
    """Handle /start command"""
    await event.answer("👋 Привет! Я бот с middleware.")


@router.message_created(Command("slow"))
async def cmd_slow(event):
    """Simulate slow operation"""
    await asyncio.sleep(2)  # Simulate work
    await event.answer("⏳ Готово! Это заняло 2 секунды.")


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
