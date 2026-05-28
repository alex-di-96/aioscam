#!/usr/bin/env python3
"""
Simple Deep Link Test Bot — catch ALL updates and log raw data.
"""
import asyncio, logging, sys
from aioscam import Bot, Dispatcher, Router

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

router = Router()

@router.bot_started()
async def on_started(event, state):
    logger.info(f"bot_started: user_id={event.user_id}, payload={event.payload}")
    if event.payload:
        await event.answer(f"Deep link received: {event.payload}")
    else:
        await event.answer("Hello! Click https://max.ru/id3900000111_bot?start=test123")

@router.message_created()
async def on_message(event):
    raw = event.data.get('raw_update', {})
    payload = raw.get('payload', 'none')
    text = event.text or ''
    logger.info(f"message: text='{text}', payload={payload}")
    logger.info(f"  raw_keys={list(raw.keys())}")
    if payload and payload != 'none':
        await event.answer(f"Message with payload: {payload}")

async def main():
    bot = Bot()
    dp = Dispatcher()
    dp.include_router(router)
    me = await bot.get_me()
    logger.info(f"Bot: {me.get('first_name')} (@{me.get('username')})")
    logger.info("Polling started...")
    await dp.start_polling(bot, skip_updates=False, timeout=3, limit=20)

if __name__ == "__main__":
    asyncio.run(main())
