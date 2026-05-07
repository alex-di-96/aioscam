#!/usr/bin/env python3
"""Debug updates format"""

import asyncio
import os
import aiohttp
import json

async def test_updates():
    token = os.getenv("MAX_BOT_TOKEN")
    headers = {"Authorization": token}
    
    async with aiohttp.ClientSession() as session:
        # Get updates with small timeout for quick response
        params = {"limit": 1, "timeout": 2}
        
        try:
            async with session.get(
                "https://platform-api.max.ru/updates",
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                print(f"Status: {resp.status}")
                print(f"Content-Type: {resp.content_type}")
                
                data = await resp.text()
                print(f"\nRaw response:\n{data[:1000]}")
                
                try:
                    json_data = json.loads(data)
                    print(f"\nJSON structure:")
                    print(f"Type: {type(json_data)}")
                    if isinstance(json_data, dict):
                        print(f"Keys: {list(json_data.keys())}")
                        for key, value in json_data.items():
                            print(f"  {key}: type={type(value)}, value={str(value)[:200]}")
                    elif isinstance(json_data, list):
                        print(f"List with {len(json_data)} items")
                        if json_data:
                            print(f"First item: {json_data[0]}")
                except Exception as e:
                    print(f"JSON parse error: {e}")
        except Exception as e:
            print(f"Request error: {e}")

asyncio.run(test_updates())
