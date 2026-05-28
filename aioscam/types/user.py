"""
User type
"""

from typing import Optional
from pydantic import Field
from aioscam.types.base import MaxObject


class User(MaxObject):
    """
    Represents a Max user

    Attributes:
        id: User ID (also accepts 'user_id' from raw API)
        username: Username
        first_name: First name
        last_name: Last name
        display_name: Display name
        is_bot: Whether user is a bot
        is_premium: Whether user has premium
        language_code: User language
        name: Alias for display_name (raw API compat)
        last_activity_time: Last activity timestamp (raw API compat)
    """

    id: Optional[int] = Field(default=None, alias="user_id")
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    is_bot: bool = False
    is_premium: Optional[bool] = None
    language_code: Optional[str] = None
    # Raw API compat fields
    name: Optional[str] = None
    last_activity_time: Optional[int] = None
    
    @property
    def full_name(self) -> str:
        """Get full user name"""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) or self.display_name or self.username or f"User#{self.id}"
    
    def mention(self) -> str:
        """Get user mention"""
        if self.username:
            return f"@{self.username}"
        return self.full_name
