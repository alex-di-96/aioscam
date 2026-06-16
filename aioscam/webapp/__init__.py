"""
aioscam.webapp — Server-side helpers for Max WebApp mini-applications.

Quick start::

    from aioscam.webapp import validate_init_data, WebAppDataError

    try:
        init_data = validate_init_data(raw_string, bot_token=BOT_TOKEN)
        print(init_data.user.id, init_data.start_param)
    except WebAppDataError as e:
        print("invalid:", e)

For aiohttp servers::

    from aioscam.webapp.aiohttp import get_init_data, WebAppMiddleware
"""

from aioscam.webapp.init_data import (
    WebAppChat,
    WebAppDataError,
    WebAppInitData,
    WebAppUser,
    validate_init_data,
)

__all__ = [
    "WebAppUser",
    "WebAppChat",
    "WebAppInitData",
    "WebAppDataError",
    "validate_init_data",
]
