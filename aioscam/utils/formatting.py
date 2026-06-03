"""
Text formatting utilities
"""

from typing import Optional


class TextFormat:
    """
    Text formatting helpers
    """
    
    @staticmethod
    def bold(text: str) -> str:
        """Make text bold"""
        return f"**{text}**"
    
    @staticmethod
    def italic(text: str) -> str:
        """Make text italic"""
        return f"_{text}_"
    
    @staticmethod
    def underline(text: str) -> str:
        """Underline text"""
        return f"__{text}__"
    
    @staticmethod
    def strikethrough(text: str) -> str:
        """Strikethrough text"""
        return f"~~{text}~~"
    
    @staticmethod
    def code(text: str) -> str:
        """Inline code"""
        return f"`{text}`"
    
    @staticmethod
    def pre(text: str, language: Optional[str] = None) -> str:
        """Code block"""
        if language:
            return f"```{language}\n{text}\n```"
        return f"```\n{text}\n```"
    
    @staticmethod
    def link(text: str, url: str) -> str:
        """Text link"""
        return f"[{text}]({url})"
    
    @staticmethod
    def mention(text: str, user_id: int) -> str:
        """User mention"""
        return f"[{text}](user://{user_id})"


# Short aliases
Bold = TextFormat.bold
Italic = TextFormat.italic
Code = TextFormat.code
Pre = TextFormat.pre
Link = TextFormat.link
Mention = TextFormat.mention
