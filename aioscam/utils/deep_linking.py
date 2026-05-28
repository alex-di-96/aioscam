"""
Deep linking utilities
"""


def create_deep_link(bot_username: str, payload: str) -> str:
    """
    Create deep link for bot
    
    Usage:
        link = create_deep_link("my_bot", "ref_12345")
        # Returns: https://max.ru/my_bot?start=ref_12345
    
    Args:
        bot_username: Bot username (without @)
        payload: Deep link payload
    
    Returns:
        Deep link URL
    """
    return f"https://max.ru/{bot_username}?start={payload}"


def create_group_deep_link(bot_username: str, group_id: int, payload: str = "") -> str:
    """
    Create deep link for adding bot to group
    
    Args:
        bot_username: Bot username
        group_id: Group ID
        payload: Optional payload
    
    Returns:
        Deep link URL
    """
    if payload:
        return f"https://max.ru/{bot_username}?add_to_group={group_id}&start={payload}"
    return f"https://max.ru/{bot_username}?add_to_group={group_id}"


def parse_deep_link(url: str) -> dict:
    """
    Parse deep link and extract payload
    
    Args:
        url: Deep link URL
    
    Returns:
        Dict with bot_username, payload, group_id (if present)
    """
    result = {
        "bot_username": None,
        "payload": None,
        "group_id": None,
    }
    
    if not url.startswith("https://max.ru/"):
        return result
    
    # Extract parts
    path_query = url.replace("https://max.ru/", "")
    parts = path_query.split("?", 1)
    
    if len(parts) == 2:
        result["bot_username"] = parts[0]
        query = parts[1]
        
        # Parse query parameters
        params = dict(p.split("=") for p in query.split("&") if "=" in p)
        
        if "start" in params:
            result["payload"] = params["start"]
        if "add_to_group" in params:
            result["group_id"] = int(params["add_to_group"])
    
    return result
