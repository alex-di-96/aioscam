#!/usr/bin/env python3
"""Test all keyboard variants"""

import asyncio
import os
import aiohttp

async def test_keyboards():
    token = os.getenv("MAX_BOT_TOKEN")
    headers = {"Authorization": token}
    base_url = "https://platform-api.max.ru/messages"
    params = {"chat_id": 243186798, "user_id": 39068268}

    variants = [
        # 1. Standard inline_keyboard
        {"key": "keyboard", "value": {"inline_keyboard": [[{"text": "Test 1", "callback_data": "1"}]]}},
        # 2. reply_markup key
        {"key": "reply_markup", "value": {"inline_keyboard": [[{"text": "Test 2", "callback_data": "2"}]]}},
        # 3. Simple text keyboard
        {"key": "keyboard", "value": {"keyboard": [["Test 3"], ["Test 4"]]}},
        # 4. Direct array
        {"key": "keyboard", "value": [[{"text": "Test 5", "callback_data": "5"}]]},
        # 5. With type
        {"key": "keyboard", "value": {"inline_keyboard": [[{"text": "Test 6", "type": "callback", "callback_data": "6"}]]}},
    ]

    async with aiohttp.ClientSession() as session:
        for i, var in enumerate(variants):
            print(f"\nTesting variant {i+1}: key='{var['key']}'")
            
            body = {"text": f"Keyboard test {i+1}"}
            body[var["key"]] = var["value"]
            
            async with session.post(
                base_url,
                headers=headers,
                params=params,
                json=body,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                status = resp.status
                print(f"  Status: {status}")
                if status == 200:
                    print(f"  Sent! Check your Max app for message '{i+1}'")
                else:
                    err = await resp.text()
                    print(f"  Error: {err}")
            
            await asyncio.sleep(1)

asyncio.run(test_keyboards())
