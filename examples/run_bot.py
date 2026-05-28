#!/usr/bin/env python3
"""
AioScam Demo Bot - Production-ready launcher

Usage:
    # Run with .env configuration
    python run_bot.py

    # Override environment mode
    Aioscam_ENV=debug python run_bot.py   # Full debug logging
    Aioscam_ENV=test python run_bot.py    # Test mode (warnings)
    Aioscam_ENV=prod python run_bot.py    # Production (errors only)

    # Or use convenience scripts:
    python run_bot.py --debug    # Same as Aioscam_ENV=debug
    python run_bot.py --test     # Same as Aioscam_ENV=test
    python run_bot.py --prod     # Same as Aioscam_ENV=prod
"""

import argparse
import asyncio
import os
import sys
import fcntl

from demo_bot import main as bot_main, PID_FILE, _check_single_instance


def parse_args():
    parser = argparse.ArgumentParser(description="AioScam Demo Bot")
    parser.add_argument(
        "--env",
        choices=["debug", "test", "prod"],
        help="Environment mode (overrides Aioscam_ENV)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    _check_single_instance()

    args = parse_args()
    
    # Set environment variable if specified
    if args.env:
        import os
        os.environ["Aioscam_ENV"] = args.env
    
    try:
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    finally:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
