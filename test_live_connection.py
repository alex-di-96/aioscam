#!/usr/bin/env python3
"""
Test script for real Max API connection
Run this manually: python test_live_connection.py
"""

import asyncio
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

from aioscam import Bot, Dispatcher, Router, Command, F
from aioscam.types.user import User
from aioscam.types.chat import Chat, ChatType as ChatTypeEnum
from aioscam.types.message import Message, MessageBody


async def test_1_connection():
    """Test 1: Bot connection to Max API"""
    print("\n" + "="*60)
    print("TEST 1: Подключение к Max API")
    print("="*60)
    
    bot = Bot()
    print(f"✅ Bot token установлен: {bot.token[:15]}...")
    
    try:
        me = await bot.get_me()
        print(f"✅ ПОДКЛЮЧЕНИЕ УСПЕШНО!")
        print(f"📋 Bot info: {me}")
        await bot.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        await bot.close()
        return False


async def test_2_get_chats():
    """Test 2: Get bot chats"""
    print("\n" + "="*60)
    print("TEST 2: Получение списка чатов")
    print("="*60)
    
    bot = Bot()
    
    try:
        chats = await bot.get_chats()
        print(f"✅ Получено чатов: {len(chats)}")
        for chat in chats[:3]:  # Show first 3
            print(f"  - {chat}")
        await bot.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await bot.close()
        return False


async def test_3_send_message():
    """Test 3: Send test message"""
    print("\n" + "="*60)
    print("TEST 3: Отправка тестового сообщения")
    print("="*60)
    
    bot = Bot()
    
    try:
        # Get first chat
        chats = await bot.get_chats()
        if not chats:
            print("❌ Нет доступных чатов для отправки")
            await bot.close()
            return False
        
        # Use first chat
        chat_id = chats[0].get('id') or chats[0].get('chat_id')
        
        print(f"📤 Отправка сообщения в chat_id: {chat_id}")
        result = await bot.send_message(
            chat_id=chat_id,
            text="🤖 Это тестовое сообщение от AioScam Framework!"
        )
        print(f"✅ Сообщение отправлено: {result}")
        await bot.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        await bot.close()
        return False


async def test_4_dispatcher():
    """Test 4: Dispatcher event processing"""
    print("\n" + "="*60)
    print("TEST 4: Обработка событий Dispatcher")
    print("="*60)
    
    dp = Dispatcher()
    router = Router()
    
    @router.message_created(Command("start"))
    async def cmd_start(event):
        print(f"✅ Обработана команда /start")
        return "start_handled"
    
    @router.message_created()
    async def handle_message(event):
        print(f"✅ Обработано сообщение: {event.message.text}")
        return "message_handled"
    
    dp.include_router(router)
    
    # Simulate /start command
    chat = Chat(id=1, type=ChatTypeEnum.PRIVATE)
    body = MessageBody(text="/start")
    message = Message(id=1, chat=chat, body=body)
    
    from unittest.mock import MagicMock
    event = MagicMock()
    event.message = message
    
    result = await dp.process_message(event)
    print(f"✅ Результат обработки: {result}")
    
    return result == "start_handled"


async def test_5_fsm():
    """Test 5: FSM state management"""
    print("\n" + "="*60)
    print("TEST 5: Управление состояниями FSM")
    print("="*60)
    
    from aioscam.fsm import MemoryStorage, State, StatesGroup
    
    class TestState(StatesGroup):
        step1 = State()
        step2 = State()
    
    storage = MemoryStorage()
    
    # Test state operations
    await storage.set_state(chat_id=1, state="TestState:step1")
    state = await storage.get_state(chat_id=1)
    print(f"✅ State установлен: {state}")
    
    await storage.set_data(chat_id=1, data={"test": "value"})
    data = await storage.get_data(chat_id=1)
    print(f"✅ Data установлен: {data}")
    
    await storage.update_data(chat_id=1, data={"test2": "value2"})
    data = await storage.get_data(chat_id=1)
    print(f"✅ Data обновлен: {data}")
    
    await storage.close()
    
    return True


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 AioScam Framework - LIVE TESTS")
    print("="*60)
    
    # Check if token is available
    if not os.getenv("MAX_BOT_TOKEN"):
        print("\n❌ ERROR: MAX_BOT_TOKEN не установлен!")
        print("\nЗапустите скрипт так:")
        print("  export MAX_BOT_TOKEN=\"your-token-here\"")
        print("  python test_live_connection.py")
        return
    
    results = {}
    
    # Test 1: Connection
    results["connection"] = await test_1_connection()
    
    # Test 2: Get chats
    results["get_chats"] = await test_2_get_chats()
    
    # Test 3: Send message (optional, may fail without proper chats)
    results["send_message"] = await test_3_send_message()
    
    # Test 4: Dispatcher (offline)
    results["dispatcher"] = await test_4_dispatcher()
    
    # Test 5: FSM (offline)
    results["fsm"] = await test_5_fsm()
    
    # Summary
    print("\n" + "="*60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТОВ")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print(f"\n🎯 ИТОГО: {passed}/{total} тестов прошли успешно")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
