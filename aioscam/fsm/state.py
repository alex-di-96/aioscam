"""
State and StatesGroup
"""

from typing import Optional


class State:
    """
    Represents a single state in FSM
    
    Usage:
        class MyState(StatesGroup):
            waiting_name = State()
            waiting_age = State()
    """
    
    def __init__(self, name: Optional[str] = None):
        self.name = name
        self._group: Optional['StatesGroup'] = None
    
    def set_group(self, group: 'StatesGroup') -> None:
        """Set parent group (can be class or instance)"""
        self._group = group

    @property
    def full_name(self) -> str:
        """Get full state name"""
        if self._group:
            # Handle both class and instance
            group_cls = self._group if isinstance(self._group, type) else self._group.__class__
            return f"{group_cls.__name__}:{self.name}"
        return self.name or "unknown"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, State):
            return self.full_name == other.full_name
        if isinstance(other, str):
            return self.full_name == other
        return False
    
    def __hash__(self) -> int:
        return hash(self.full_name)
    
    def __repr__(self) -> str:
        return f"State({self.full_name})"


class StatesGroup:
    """
    Base class for state groups

    Usage:
        class MyState(StatesGroup):
            waiting_name = State()
            waiting_age = State()
    """

    def __init_subclass__(cls, **kwargs):
        """Automatically setup states when subclass is defined"""
        super().__init_subclass__(**kwargs)
        cls._setup_states()

    def __init__(self):
        self._setup_states()

    @classmethod
    def _setup_states(cls) -> None:
        """Setup states in group"""
        for attr_name, attr_value in cls.__dict__.items():
            if isinstance(attr_value, State):
                attr_value.name = attr_name
                attr_value.set_group(cls)
    
    def __class_getitem__(cls, key):
        """Allow indexing for state access"""
        return getattr(cls, key, None)
