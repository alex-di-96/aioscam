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
    """
    Base error for all WebApp initData validation failures.

    Always catch this base class in production to handle all variants::

        try:
            init_data = validate_init_data(raw, bot_token)
        except WebAppDataError as e:
            # e.hint explains what to check
            return web.json_response({"ok": False, "error": str(e)}, status=401)

    For fine-grained handling catch specific subclasses:
        WebAppSignatureError  — wrong token or tampered data
        WebAppExpiredError    — session too old, user must re-open app
        WebAppMissingFieldError — incomplete initData string
        WebAppParseError      — malformed input (not a real Max client)
    """

    hint: str = ""

    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.hint = hint

    def __str__(self) -> str:
        if self.hint:
            return f"{super().__str__()} — {self.hint}"
        return super().__str__()


class WebAppSignatureError(WebAppDataError):
    """
    initData HMAC signature does not match.

    Most common causes:
    - Wrong ``bot_token`` on the server
    - initData was tampered with (e.g., injected by attacker)
    - Token was rotated after the WebApp session was opened

    Security: always return HTTP 401, never reveal which field is wrong.
    """

    def __init__(self) -> None:
        super().__init__(
            "initData signature is invalid",
            hint="verify that MAX_BOT_TOKEN matches the token of the bot that opened this WebApp",
        )


class WebAppExpiredError(WebAppDataError):
    """
    initData is older than the configured ``max_age``.

    The user must close and re-open the mini-app to get fresh initData.
    Typical lifetime: 24 h (default). For high-security apps use 1 h.
    """

    def __init__(self, age_seconds: int, max_age: int) -> None:
        super().__init__(
            f"initData expired (age {age_seconds}s > max_age {max_age}s)",
            hint="user should close and re-open the mini-app; or increase max_age if this is a long-lived session",
        )
        self.age_seconds = age_seconds
        self.max_age = max_age


class WebAppMissingFieldError(WebAppDataError):
    """
    A required field is absent from initData.

    ``hash`` and ``auth_date`` are mandatory — their absence means
    this request did not come from a real Max WebApp client.
    """

    def __init__(self, field: str) -> None:
        super().__init__(
            f"initData missing required field: '{field}'",
            hint="this request was not sent by a Max WebApp client (Bridge SDK was not loaded, or initData was not passed)",
        )
        self.field = field


class WebAppParseError(WebAppDataError):
    """
    initData could not be parsed as a URL-encoded query string.

    Indicates garbage input — not a real Max WebApp session.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(
            f"initData parse error: {detail}",
            hint="ensure the client sends window.WebApp.initData unchanged, URL-encoded",
        )


class FeatureUnavailableError(WebAppDataError):
    """
    A WebApp Bridge feature is not available on the current platform.

    Client-side features (contacts, biometric, NFC) depend on the platform
    the user is running Max on. Check ``bridge.isAvailable`` and
    ``bridge.platform`` on the frontend before calling platform-only methods.
    """

    def __init__(self, feature: str, platforms: str = "iOS and Android") -> None:
        super().__init__(
            f"feature '{feature}' is not available",
            hint=f"'{feature}' requires {platforms}; check bridge.platform on the frontend and hide the UI element when not supported",
        )
        self.feature = feature


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


class WebAppContact(BaseModel):
    """Validated contact returned by window.WebApp.requestContact()."""

    phone: str
    auth_date: str
    hash: str


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
        params = dict(parse_qsl(init_data_raw, keep_blank_values=True))
    except Exception as exc:
        raise WebAppParseError(str(exc)) from exc

    received_hash = params.pop("hash", None)
    if not received_hash:
        raise WebAppMissingFieldError("hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise WebAppSignatureError()

    if "auth_date" not in params:
        raise WebAppMissingFieldError("auth_date")
    try:
        auth_date = int(params["auth_date"])
    except ValueError as exc:
        raise WebAppParseError(f"'auth_date' is not an integer: {params['auth_date']!r}") from exc

    if max_age:
        age = int(time.time()) - auth_date
        if age > max_age:
            raise WebAppExpiredError(age_seconds=age, max_age=max_age)

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


def validate_contact(
    phone: str,
    auth_date: str,
    contact_hash: str,
    user_id: int,
    bot_token: str,
) -> WebAppContact:
    """
    Validate the contact returned by ``window.WebApp.requestContact()``.

    Algorithm (per Max Bridge SDK docs):
        params = {authDate, phone (no leading +), userId}
        check_string = sorted key=value pairs joined by ``\\n``
        hash = HMAC_SHA256(key=bot_token, msg=check_string).hexdigest()

    Args:
        phone: Phone number as returned by requestContact (may have leading +)
        auth_date: authDate string from requestContact result
        contact_hash: hash string from requestContact result
        user_id: User ID from validated initData (``init_data.user.id``)
        bot_token: Bot token (``MAX_BOT_TOKEN``)

    Returns:
        :class:`WebAppContact` with the validated phone number

    Raises:
        WebAppDataError: If the hash does not match
    """
    phone_stripped = phone.lstrip("+")
    params = {
        "authDate": str(auth_date),
        "phone": phone_stripped,
        "userId": str(user_id),
    }
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    expected = hmac.new(bot_token.encode(), check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, contact_hash):
        raise WebAppSignatureError()

    return WebAppContact(phone=phone, auth_date=auth_date, hash=contact_hash)
