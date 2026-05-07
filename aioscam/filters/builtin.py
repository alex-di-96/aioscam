"""
Built-in filters
"""

import re
from typing import List, Optional, Union
import logging
from aioscam.filters.base import BaseFilter, FilterResult

logger = logging.getLogger(__name__)


class Command(BaseFilter):
    """
    Filter for bot commands
    
    Usage:
        @router.message_created(Command("start"))
        @router.message_created(Command(["start", "help"]))
    """
    
    def __init__(self, commands: Union[str, List[str]], prefixes: str = "/"):
        if isinstance(commands, str):
            commands = [commands]
        self.commands = [cmd.lower() for cmd in commands]
        self.prefixes = prefixes
    
    async def __call__(self, event) -> FilterResult:
        try:
            # Get text from different possible locations
            text = None
            if hasattr(event, 'text'):
                text = event.text
            elif hasattr(event, 'message') and event.message:
                msg = event.message
                if hasattr(msg, 'body') and msg.body:
                    text = getattr(msg.body, 'text', None)
                elif isinstance(msg, dict):
                    text = msg.get('body', {}).get('text')
            
            if not text:
                return FilterResult(passed=False)
            
            text = text.strip()
            
            if not text.startswith(tuple(self.prefixes)):
                return FilterResult(passed=False)
            
            command_match = re.match(r'^[/\'](\w+)', text)
            if not command_match:
                return FilterResult(passed=False)
            
            command = command_match.group(1).lower()
            
            if command in self.commands:
                return FilterResult(passed=True, data={"command": command})
            
            return FilterResult(passed=False)
        except Exception:
            return FilterResult(passed=False)


class Text(BaseFilter):
    """
    Filter for message text
    
    Usage:
        @router.message_created(Text("hello"))
        @router.message_created(Text(contains=["word1", "word2"]))
        @router.message_created(Text(startswith="prefix"))
    """
    
    def __init__(
        self,
        equals: Optional[str] = None,
        contains: Optional[List[str]] = None,
        startswith: Optional[str] = None,
        endswith: Optional[str] = None,
        regex: Optional[str] = None,
        ignore_case: bool = True,
    ):
        self.equals = equals
        self.contains = contains
        self.startswith = startswith
        self.endswith = endswith
        self.regex = regex
        self.ignore_case = ignore_case
    
    async def __call__(self, event) -> FilterResult:
        try:
            # Get text from different possible locations
            text = None
            if hasattr(event, 'text'):
                text = event.text
            elif hasattr(event, 'message') and event.message:
                msg = event.message
                if hasattr(msg, 'body') and msg.body:
                    text = getattr(msg.body, 'text', None)
                elif isinstance(msg, dict):
                    text = msg.get('body', {}).get('text')
            
            if not text:
                return FilterResult(passed=False)
            
            check_text = text
            if self.ignore_case:
                check_text = text.lower()
            
            if self.equals:
                equals_check = self.equals if not self.ignore_case else self.equals.lower()
                if check_text != equals_check:
                    return FilterResult(passed=False)
            
            if self.contains:
                contains_list = [c if not self.ignore_case else c.lower() for c in self.contains]
                if not any(c in check_text for c in contains_list):
                    return FilterResult(passed=False)
            
            if self.startswith:
                start_check = self.startswith if not self.ignore_case else self.startswith.lower()
                if not check_text.startswith(start_check):
                    return FilterResult(passed=False)
            
            if self.endswith:
                end_check = self.endswith if not self.ignore_case else self.endswith.lower()
                if not check_text.endswith(end_check):
                    return FilterResult(passed=False)
            
            if self.regex:
                flags = re.IGNORECASE if self.ignore_case else 0
                if not re.search(self.regex, text, flags):
                    return FilterResult(passed=False)
            
            return FilterResult(passed=True, data={"text": text})
        except Exception:
            return FilterResult(passed=False)


class ContentType(BaseFilter):
    """
    Filter for message content type
    
    Usage:
        @router.message_created(ContentType("text"))
        @router.message_created(ContentType(["photo", "video"]))
    """
    
    def __init__(self, content_types: Union[str, List[str]]):
        if isinstance(content_types, str):
            content_types = [content_types]
        self.content_types = content_types
    
    async def __call__(self, event) -> FilterResult:
        try:
            message = getattr(event, 'message', None)
            if not message:
                return FilterResult(passed=False)
            
            has_attachments = hasattr(message, 'attachments') and message.attachments
            
            if "text" in self.content_types:
                text = getattr(message, 'text', None) or getattr(getattr(message, 'body', None), 'text', None)
                if text:
                    return FilterResult(passed=True, data={"content_type": "text"})
            
            if has_attachments:
                for attachment in message.attachments:
                    if attachment.type.value in self.content_types:
                        return FilterResult(passed=True, data={"content_type": attachment.type.value})
            
            return FilterResult(passed=False)
        except Exception:
            return FilterResult(passed=False)


class ChatType(BaseFilter):
    """
    Filter for chat type
    
    Usage:
        @router.message_created(ChatType("private"))
    """
    
    def __init__(self, chat_types: Union[str, List[str]]):
        if isinstance(chat_types, str):
            chat_types = [chat_types]
        self.chat_types = chat_types
    
    async def __call__(self, event) -> FilterResult:
        try:
            message = getattr(event, 'message', None)
            if not message:
                return FilterResult(passed=False)
            
            chat = getattr(message, 'chat', None)
            if not chat:
                return FilterResult(passed=False)
            
            chat_type = chat.type.value if hasattr(chat.type, 'value') else str(chat.type)
            
            if chat_type in self.chat_types:
                return FilterResult(passed=True, data={"chat_type": chat_type})
            
            return FilterResult(passed=False)
        except Exception:
            return FilterResult(passed=False)


class StateFilter(BaseFilter):
    """
    Filter for FSM state

    Usage:
        @router.message_created(StateFilter(MyState.waiting_name))
    """

    def __init__(self, state):
        self.state = state

    async def __call__(self, event) -> FilterResult:
        try:
            # Skip state filtering for commands (text starting with /)
            text = getattr(event, 'text', '') or ''
            if text.startswith('/'):
                logger.debug(f"StateFilter: skipping command {text!r}")
                return FilterResult(passed=False)
            
            current_state = None
            
            data = getattr(event, 'data', {})
            logger.debug(f"StateFilter: event.data keys={list(data.keys()) if isinstance(data, dict) else 'N/A'}")

            # Try via event.data['state'] (StateContext from dispatcher)
            if isinstance(data, dict) and 'state' in data:
                state_ctx = data['state']
                logger.debug(f"StateFilter: found state_ctx type={type(state_ctx).__name__}")
                if hasattr(state_ctx, 'get_state'):
                    current_state = await state_ctx.get_state()
                    logger.debug(f"StateFilter: got current_state={current_state!r}")

            if current_state is not None:
                # Compare: current_state (str) vs self.state (State or str)
                if hasattr(self.state, 'full_name'):
                    # self.state is a State object, compare full_name
                    expected = self.state.full_name
                    logger.debug(f"StateFilter: current={current_state!r}, expected={expected!r}")
                    matches = current_state == expected
                else:
                    # self.state is a string
                    expected = self.state
                    logger.debug(f"StateFilter: current={current_state!r}, expected={expected!r}")
                    matches = current_state == expected

                if matches:
                    logger.debug(f"StateFilter: PASSED")
                    return FilterResult(passed=True, data={"state": self.state})
                else:
                    logger.debug(f"StateFilter: FAILED")
            else:
                logger.debug(f"StateFilter: current_state is None")

            return FilterResult(passed=False)
        except Exception as e:
            logger.error(f"StateFilter: exception {e}")
            return FilterResult(passed=False)


class AllFilter(BaseFilter):
    """
    Filter that always passes (catch-all)
    
    Usage:
        @router.message_created(AllFilter())
    """
    
    async def __call__(self, event) -> FilterResult:
        return FilterResult(passed=True)


# Alias for backward compatibility
State = StateFilter
