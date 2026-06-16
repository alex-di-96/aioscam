AioScam Documentation
=====================

**Async Python framework for Max messenger bots**

.. image:: https://img.shields.io/pypi/v/aioscam
   :target: https://pypi.org/project/aioscam/
   :alt: PyPI

.. image:: https://img.shields.io/badge/python-3.9%2B-blue
   :target: https://www.python.org/
   :alt: Python 3.9+

Installation
------------

.. code-block:: bash

   pip install aioscam

Quick Start
-----------

.. code-block:: python

   from aioscam import Bot, Dispatcher, Router
   from aioscam.filters import Command

   dp = Dispatcher()
   router = Router()

   @router.message_created(Command("start"))
   async def cmd_start(event):
       await event.answer("Привет!")

   dp.include_router(router)

   async def main():
       bot = Bot()  # token from MAX_BOT_TOKEN env var
       await dp.start_polling(bot)

Features
--------

- 🚀 **Fully async** - Built on asyncio and aiohttp
- 🎯 **aiogram-style API** - Familiar decorators and patterns
- 🔄 **Router system** - Modular bot architecture
- 🎭 **Magic Filters** - Declarative event filtering
- 📦 **FSM** - Finite state machine with MemoryStorage
- 🛡️ **StateGuard** - Blocks unauthorized commands during FSM states
- 🌐 **Webhook support** - aiohttp, FastAPI, Litestar
- 📡 **Polling mode** - Long-polling with exponential backoff

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: English

   en/README

.. toctree::
   :maxdepth: 2
   :caption: Русский

   ru/README

Links
-----

- `GitHub <https://github.com/alex-di-96/aioscam>`_
- `PyPI <https://pypi.org/project/aioscam/>`_
- `Issue Tracker <https://github.com/alex-di-96/aioscam/issues>`_
