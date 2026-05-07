#!/usr/bin/env python3
"""Debug script - test different HTTP methods and URLs"""

import asyncio
import os
import aiohttp

async def test_api():
    token = os.getenv("MAX_BOT_TOKEN")
    print(f"Token: {token[:15]}...\n")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test different URLs and methods
    tests = [
        # (method, url, body)
        ("GET", "https://max.ru/api/bot/getMe", None),
        ("POST", "https://max.ru/api/bot/getMe", {}),
        ("GET", "https://api.max.ru/bot/getMe", None),
        ("POST", "https://api.max.ru/bot/getMe", {}),
        ("GET", "https://max.ru/api/v1/bot/getMe", None),
        ("POST", "https://max.ru/api/v1/bot/getMe", {}),
        ("POST", "https://max.ru/bot/getMe", {}),
        ("GET", "https://max.ru/bot/getMe", None),
    ]
    
    async with aiohttp.ClientSession() as session:
        for method, url, body in tests:
            print(f"\n{'='*60}")
            print(f"Testing: {method} {url}")
            print(f"{'='*60}")
            
            try:
                kwargs = {
                    "headers": headers,
                    "timeout": aiohttp.ClientTimeout(total=5)
                }
                
                if body is not None:
                    kwargs["json"] = body
                
                async with session.request(
                    method,
                    url,
                    **kwargs
                ) as resp:
                    data = await resp.text()
                    print(f"Status: {resp.status}")
                    print(f"Response: {data[:200]}")
                    
                    if resp.status == 200:
                        print("\n✅ SUCCESS!")
                        return
            except Exception as e:
                print(f"Error: {e}")

asyncio.run(test_api())
