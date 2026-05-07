#!/usr/bin/env python3
"""Test keyboard formats"""

import asyncio
import os
import aiohttp

async def test_keyboard():
    token = os.getenv("MAX_BOT_TOKEN")
    headers = {"Authorization": token}
    
    # Получим user_id из последнего update
    async with aiohttp.ClientSession() as session:
        # Get updates to find user_id
        async with session.get(
            "https://platform-api.max.ru/updates",
            headers=headers,
            params={"limit": 1, "timeout": 2},
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            data = await resp.json()
            print(f"Updates: {data}")
            
            # Try different keyboard formats
            keyboard_formats = {
                "format_1_inline_keyboard": {
                    "inline_keyboard": [
                        [{"text": "Button 1", "callback_data": "btn1"}],
                        [{"text": "Button 2", "callback_data": "btn2"}]
                    ]
                },
                "format_2_keyboard": {
                    "keyboard": [
                        ["Button 1", "Button 2"],
                        ["Button 3"]
                    ]
                },
                "format_3_buttons_array": {
                    "buttons": [
                        {"text": "Button 1", "callback_data": "btn1"},
                        {"text": "Button 2", "callback_data": "btn2"}
                    ]
                }
            }
            
            for name, keyboard in keyboard_formats.items():
                print(f"\n{'='*60}")
                print(f"Testing: {name}")
                print(f"Keyboard: {keyboard}")
                print(f"{'='*60}")
                
                # Send with chat_id and user_id
                body = {"text": f"Test keyboard: {name}"}
                
                async with session.post(
                    "https://platform-api.max.ru/messages",
                    headers=headers,
                    params={"chat_id": 243186798, "user_id": 39068268},
                    json={**body, "keyboard": keyboard},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    response = await resp.json()
                    print(f"Status: {resp.status}")
                    print(f"Response: {response}")
                    
                    if resp.status == 200:
                        print(f"✅ SUCCESS with {name}!")
                        return

asyncio.run(test_keyboard())
