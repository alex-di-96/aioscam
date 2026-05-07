#!/usr/bin/env python3
"""Test with correct URL, auth, and endpoints"""

import asyncio
import os
import aiohttp

async def test_api():
    token = os.getenv("MAX_BOT_TOKEN")
    base_url = "https://platform-api.max.ru"
    
    # Токен передаётся БЕЗ "Bearer " префикса!
    headers = {"Authorization": token}
    
    endpoints = [
        ("POST", "/me", {}),
        ("GET", "/me", None),
    ]
    
    async with aiohttp.ClientSession() as session:
        for method, path, body in endpoints:
            url = f"{base_url}{path}"
            print(f"\n{'='*60}")
            print(f"Testing: {method} {url}")
            print(f"Headers: Authorization: {token[:15]}...")
            print(f"{'='*60}")
            
            try:
                kwargs = {
                    "headers": headers,
                    "timeout": aiohttp.ClientTimeout(total=10)
                }
                
                if body is not None:
                    kwargs["json"] = body
                
                async with session.request(method, url, **kwargs) as resp:
                    content_type = resp.content_type
                    data = await resp.text()
                    print(f"Status: {resp.status}")
                    print(f"Content-Type: {content_type}")
                    print(f"Response: {data[:500]}")
                    
                    if resp.status == 200:
                        print("\n✅ SUCCESS!")
                        return True
            except Exception as e:
                print(f"Error: {e}")
    
    return False

asyncio.run(test_api())
