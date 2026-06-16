"""
Max WebApp initData validation and Pydantic models.

When a user opens a mini-app via OpenAppButton, Max injects
``window.WebApp.initData`` — a URL-encoded query string containing
user info, chat context, and an HMAC-SHA256 signature.

Always validate initData server-side before trusting user fields.

Algorithm (mirrors Telegram WebApp):
    1. Parse initData as URL query string
    2. Pop the ``hash`` field
    3. Sort remaining ``key=value`` pairs, join with ``\\n``
    4. ``secret_key = HMAC_SHA256(key=b"WebAppData", msg=bot_token)``
    5. ``expected = HMAC_SHA256(key=secret_key, msg=check_string).hexdigest()``
    6. Compare ``expected == hash`` in constant time
"""

import hashlib
import hmac
import json
import time
from typing import Optional
from urllib.parse import parse_qsl, unquote_plus

from pydantic import BaseModel


class WebAppDataError(ValueError):
    """Raised when initData is missing, invalid, or expired."""


class WebAppUser(BaseModel):
    """User info embedded in initData."""

    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    photo_url: Optional[str] = None


class WebAppChat(BaseModel):
    """Chat context embedded in initData (DIALOG | CHAT | CHANNEL)."""

    id: int
    type: str


class WebAppInitData(BaseModel):
    """Parsed and validated initData from Max WebApp."""

    query_id: Optional[str] = None
    user: Optional[WebAppUser] = None
    chat: Optional[WebAppChat] = None
    auth_date: int
    hash: str
    start_param: Optional[str] = None
    ip: Optional[str] = None


def validate_init_data(
    init_data_raw: str,
    bot_token: str,
    max_age: int = 86400,
) -> WebAppInitData:
    """
    Validate Max WebApp initData and return a parsed model.

    Args:
        init_data_raw: Raw string from ``window.WebApp.initData``
        bot_token: Bot token (``MAX_BOT_TOKEN``)
        max_age: Maximum allowed age in seconds (default 24 h). Pass 0 to skip.

    Returns:
        Validated :class:`WebAppInitData`

    Raises:
        WebAppDataError: If signature is invalid, data is expired, or parsing fails
    """
    try:
        params: dict[str, str] = dict(parse_qsl(init_data_raw, keep_blank_values=True))
    except Exception as exc:
        raise WebAppDataError("Failed to parse initData query string") from exc

    received_hash = params.pop("hash", None)
    if not received_hash:
        raise WebAppDataError("initData is missing the 'hash' field")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise WebAppDataError("initData signature is invalid")

    try:
        auth_date = int(params["auth_date"])
    except (KeyError, ValueError) as exc:
        raise WebAppDataError("initData missing or invalid 'auth_date'") from exc

    if max_age and (time.time() - auth_date) > max_age:
        raise WebAppDataError(f"initData expired (age > {max_age}s)")

    user: Optional[WebAppUser] = None
    if "user" in params:
        try:
            user = WebAppUser(**json.loads(unquote_plus(params["user"])))
        except Exception:
            pass

    chat: Optional[WebAppChat] = None
    if "chat" in params:
        try:
            chat = WebAppChat(**json.loads(unquote_plus(params["chat"])))
        except Exception:
            pass

    return WebAppInitData(
        query_id=params.get("query_id"),
        user=user,
        chat=chat,
        auth_date=auth_date,
        hash=received_hash,
        start_param=params.get("start_param"),
        ip=params.get("ip"),
    )
