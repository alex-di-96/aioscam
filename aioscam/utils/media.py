"""
Media upload helpers — process InputMedia/InputMediaBuffer into sendable attachment dicts
"""

import json
import logging
from typing import Union

from aioscam.enums.upload import UploadType
from aioscam.types.attachment import InputMedia, InputMediaBuffer

logger = logging.getLogger(__name__)


async def process_input_media(
    bot,
    att: Union[InputMedia, InputMediaBuffer],
) -> dict:
    """
    Upload a local file or buffer to Max servers and return a ready attachment dict.

    Flow (per Max API docs):
        1. POST /uploads?type=... → {url, token?}
        2. POST multipart to url → JSON with token info
        3. Extract token (format depends on type)
        4. Return {"type": "...", "payload": {"token": "..."}}

    Args:
        bot: Bot instance
        att: InputMedia (path) or InputMediaBuffer (bytes)

    Returns:
        Attachment dict ready for send_message attachments list
    """
    upload_info = await bot.get_upload_url(att.type)
    upload_url = upload_info.get("url") or upload_info.get("upload_url", "")
    pre_token = upload_info.get("token")  # only present for video/audio

    if not upload_url:
        raise ValueError(f"get_upload_url returned no url: {upload_info}")

    # Upload the file
    if isinstance(att, InputMedia):
        raw_response = await bot._client.upload_file(upload_url, att.path, att.type.value)
    else:
        raw_response = await bot._client.upload_file_buffer(
            upload_url, att.buffer, att.filename, att.type.value
        )

    logger.debug(f"Upload response for {att.type}: {raw_response[:200]}")

    # Extract token by type
    token = _extract_token(att.type, raw_response, pre_token)

    return {"type": att.type.value, "payload": {"token": token}}


def _extract_token(upload_type: UploadType, raw_response: str, pre_token: str) -> str:
    """Extract upload token from raw server response based on type."""
    if upload_type in (UploadType.VIDEO, UploadType.AUDIO):
        # Token was returned by /uploads endpoint before the actual upload
        if pre_token:
            return pre_token
        # Fallback — try parsing response
        try:
            return json.loads(raw_response).get("token", "")
        except Exception:
            return ""

    try:
        data = json.loads(raw_response)
    except Exception as e:
        raise ValueError(f"Cannot parse upload response as JSON: {raw_response[:200]}") from e

    if upload_type == UploadType.IMAGE:
        # {"photos": {"<key>": {"token": "..."}}}
        photos = data.get("photos", {})
        if photos and isinstance(photos, dict):
            key = next(iter(photos))
            token = photos[key].get("token", "")
            if token:
                return token
        # Some image uploads return token directly
        return data.get("token", "")

    if upload_type == UploadType.FILE:
        # {"token": "..."}
        return data.get("token", "")

    # Generic fallback
    return data.get("token", "")
