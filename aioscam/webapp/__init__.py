"""
aioscam.webapp — Server-side helpers for Max WebApp mini-applications.

Quick start::

    from aioscam.webapp import validate_init_data, validate_contact, WebAppDataError

    # Validate initData from window.WebApp.initData
    try:
        init_data = validate_init_data(raw_string, bot_token=BOT_TOKEN)
        print(init_data.user.id, init_data.start_param)
    except WebAppDataError as e:
        print("invalid:", e)

    # Validate contact from window.WebApp.requestContact()
    contact = validate_contact(
        phone=result["phone"],
        auth_date=result["authDate"],
        contact_hash=result["hash"],
        user_id=init_data.user.id,
        bot_token=BOT_TOKEN,
    )
    print(contact.phone)

For aiohttp servers::

    from aioscam.webapp.aiohttp import cors_middleware, get_init_data, WebAppMiddleware
"""

from aioscam.webapp.init_data import (
    WebAppChat,
    WebAppContact,
    WebAppDataError,
    WebAppInitData,
    WebAppUser,
    validate_contact,
    validate_init_data,
)

__all__ = [
    "WebAppUser",
    "WebAppChat",
    "WebAppInitData",
    "WebAppContact",
    "WebAppDataError",
    "validate_init_data",
    "validate_contact",
]
