"""
Configuration module for AioScam framework

Supports 3 environment modes via .env file or environment variables:
- debug: Full detailed logging (DEBUG level)
- test: All errors shown (WARNING level)
- prod: Only critical errors (ERROR level)
"""

import logging
import os
from enum import Enum
from typing import Optional

from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


class EnvMode(str, Enum):
    """Environment modes"""
    DEBUG = "debug"
    TEST = "test"
    PROD = "prod"


# Log level mapping
LOG_LEVELS = {
    EnvMode.DEBUG: logging.DEBUG,
    EnvMode.TEST: logging.WARNING,
    EnvMode.PROD: logging.ERROR,
}

# Log format per mode
LOG_FORMATS = {
    EnvMode.DEBUG: "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    EnvMode.TEST: "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    EnvMode.PROD: "%(asctime)s - %(levelname)s - %(message)s",
}


class Config:
    """
    Framework configuration
    
    Usage:
        config = Config()
        print(config.env_mode)  # debug | test | prod
        print(config.bot_token)  # token from env
        
        # Setup logging
        config.setup_logging()
    """
    
    def __init__(
        self,
        env_mode: Optional[str] = None,
        log_level: Optional[int] = None,
        bot_token: Optional[str] = None,
        api_url: Optional[str] = None,
    ):
        self._env_mode = self._get_env_mode(env_mode)
        self._log_level = log_level or LOG_LEVELS[self._env_mode]
        self._log_format = LOG_FORMATS[self._env_mode]
        
        # Required
        self.bot_token = bot_token or os.getenv("MAX_BOT_TOKEN", "")
        if not self.bot_token:
            raise ValueError(
                "MAX_BOT_TOKEN is not set!\n"
                "Please set it in .env file or MAX_BOT_TOKEN environment variable"
            )
        
        # Optional
        self.api_url = api_url or os.getenv("Aioscam_API_URL", "https://platform-api.max.ru")
    
    @property
    def env_mode(self) -> EnvMode:
        """Get current environment mode"""
        return self._env_mode
    
    @property
    def log_level(self) -> int:
        """Get configured log level"""
        return self._log_level
    
    @property
    def log_format(self) -> str:
        """Get configured log format"""
        return self._log_format
    
    def _get_env_mode(self, env_mode: Optional[str] = None) -> EnvMode:
        """Determine environment mode"""
        mode = env_mode or os.getenv("Aioscam_ENV", "prod").lower()
        
        try:
            return EnvMode(mode)
        except ValueError:
            logging.warning(f"Invalid Aioscam_ENV={mode!r}, defaulting to 'prod'")
            return EnvMode.PROD
    
    def setup_logging(self, logger_name: str = "aioscam") -> logging.Logger:
        """
        Setup logging for the framework
        
        Args:
            logger_name: Root logger name (default: 'aioscam')
            
        Returns:
            Configured logger
        """
        logger = logging.getLogger(logger_name)
        logger.setLevel(self._log_level)
        
        # Only add handler if no handlers exist
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(self._log_level)
            formatter = logging.Formatter(self._log_format)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def __repr__(self) -> str:
        return (
            f"Config(env_mode={self._env_mode.value!r}, "
            f"log_level={logging.getLevelName(self._log_level)}, "
            f"api_url={self.api_url!r})"
        )


# Global config instance (lazy loaded)
_config: Optional[Config] = None


def get_config(
    env_mode: Optional[str] = None,
    bot_token: Optional[str] = None,
) -> Config:
    """
    Get or create global configuration
    
    Args:
        env_mode: Override environment mode
        bot_token: Override bot token
        
    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(env_mode=env_mode, bot_token=bot_token)
    return _config
