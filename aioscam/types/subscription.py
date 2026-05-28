"""
Subscription type
"""

from typing import Optional
from datetime import datetime
from aioscam.types.base import MaxObject


class Subscription(MaxObject):
    """
    Webhook subscription
    
    Attributes:
        url: Webhook URL
        created_at: Subscription creation time
        last_delivery: Last delivery time
        status: Subscription status
    """
    
    url: str
    created_at: Optional[datetime] = None
    last_delivery: Optional[datetime] = None
    status: Optional[str] = None
