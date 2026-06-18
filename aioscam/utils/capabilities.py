"""
Bot capability detection and startup reporting.

Max Platform API does not expose a "capabilities" or "permissions" endpoint —
so we derive what the bot can do from three sources:

  1. Profile (``GET /me``)       — bot name, commands, avatar, etc.
  2. Configuration probe         — check env/settings (webapp URL set?)
  3. API probes (optional)       — verify specific API calls work

Usage::

    caps = await BotCapabilities.probe(bot)
    caps.log_report(logger)

    # Before a handler uses requestContact:
    if not caps.contacts_available:
        raise FeatureUnavailableError("requestContact", "iOS and Android")

PLATFORM NOTES
──────────────
  Bridge features like contacts, biometric, NFC, QR, haptic and screen
  brightness are CLIENT-SIDE and depend on the MAX CLIENT platform
  (iOS / Android / desktop / web). The bot server cannot know which
  platform the user is on — that information comes from the WebApp
  frontend (``bridge.platform``).

  What we CAN detect server-side:
    • Whether a WebApp server URL is configured (has_webapp)
    • Whether the bot token is valid (always — we'd crash otherwise)
    • Whether the bot has any commands registered
    • Whether the bot can send messages (probe, optional)

  What we CANNOT detect server-side:
    • requestContact availability  — depends on MAX client platform
    • biometric / NFC / QR        — depends on device hardware + platform
    • haptic feedback             — depends on platform
    • SSE (server push)           — always available (we serve it)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CommandInfo:
    name: str
    description: str

    def __str__(self) -> str:
        return f"/{self.name} — {self.description}"


@dataclass
class BotCapabilities:
    """
    Snapshot of what this bot instance can do.

    Build via :meth:`probe` at startup, then pass around or store on app state.
    Call :meth:`log_report` to print a structured startup banner to logs.
    """

    # ── From profile ──────────────────────────────────────────────────────────
    user_id: int = 0
    username: str = ""
    name: str = ""
    description: str = ""
    avatar_url: Optional[str] = None
    commands: List[CommandInfo] = field(default_factory=list)

    # ── WebApp ────────────────────────────────────────────────────────────────
    has_webapp: bool = False
    webapp_url: Optional[str] = None

    # ── API probes ────────────────────────────────────────────────────────────
    can_poll: bool = True        # always True if we got here
    poll_verified: bool = False  # set after first successful poll cycle

    # ── Issues found during probe ─────────────────────────────────────────────
    warnings: List[str] = field(default_factory=list)

    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    async def probe(
        cls,
        bot: Any,
        webapp_url: Optional[str] = None,
    ) -> "BotCapabilities":
        """
        Build ``BotCapabilities`` by inspecting the bot profile and optional config.

        Args:
            bot: Initialised :class:`aioscam.Bot` instance (token already set).
            webapp_url: Optional URL of the WebApp server. If provided and the
                        bot has a registered mini-app, ``has_webapp`` is True.

        Returns:
            Populated :class:`BotCapabilities` instance.
        """
        caps = cls()
        caps.warnings = []

        # ── 1. Profile from GET /me ───────────────────────────────────────────
        try:
            me: Dict[str, Any] = await bot.get_me()
        except Exception as exc:
            caps.warnings.append(f"get_me() failed: {exc}")
            return caps

        caps.user_id   = me.get("user_id", 0)
        caps.username  = me.get("username", "")
        caps.name      = me.get("name") or me.get("first_name", "")
        caps.description = me.get("description", "")
        caps.avatar_url  = me.get("avatar_url")

        raw_cmds = me.get("commands") or []
        caps.commands = [
            CommandInfo(name=c["name"], description=c.get("description", ""))
            for c in raw_cmds
            if isinstance(c, dict) and "name" in c
        ]

        if not caps.commands:
            caps.warnings.append(
                "No commands registered. Call bot.set_my_commands([...]) at startup "
                "so users see the command list in the Max UI."
            )

        # ── 2. WebApp availability ────────────────────────────────────────────
        caps.webapp_url = webapp_url

        if webapp_url:
            caps.has_webapp = True
        else:
            caps.warnings.append(
                "WebApp URL not configured (WEBAPP_URL env var is missing). "
                "Users cannot open a mini-app from this bot. "
                "Set WEBAPP_URL and pass it to BotCapabilities.probe() to enable."
            )

        # ── 3. Check: web_app_info from profile (if Max ever exposes it) ──────
        # Currently Max API does not include mini-app registration in GET /me.
        # A bot must be manually registered at business.max.ru/self.
        # We note this as a reminder rather than an error.
        if caps.has_webapp and not me.get("web_app_info"):
            caps.warnings.append(
                "WEBAPP_URL is set but Max API does not confirm mini-app registration. "
                "Register the bot at business.max.ru/self with URL: " + (webapp_url or "")
            )

        return caps

    # ── Reporting ─────────────────────────────────────────────────────────────

    def log_report(self, log: logging.Logger = logger) -> None:
        """Print structured startup report to the given logger."""
        sep = "─" * 52
        log.info(sep)
        log.info(f"  Bot:      @{self.username} (id={self.user_id})")
        log.info(f"  Name:     {self.name}")

        if self.description:
            short = self.description[:80].replace("\n", " ")
            log.info(f"  Desc:     {short}")

        log.info(f"  Avatar:   {'set' if self.avatar_url else 'not set'}")

        # Commands
        if self.commands:
            log.info(f"  Commands: {len(self.commands)}")
            for cmd in self.commands:
                log.info(f"    {cmd}")
        else:
            log.info("  Commands: none")

        # WebApp
        if self.has_webapp:
            log.info(f"  WebApp:   {self.webapp_url}")
        else:
            log.info("  WebApp:   not configured")

        # Client-side features note
        log.info("  Bridge:   contacts/biometric/NFC/QR — platform-dependent")
        log.info("            (check bridge.platform on the frontend)")

        # Warnings
        if self.warnings:
            log.info(sep)
            for w in self.warnings:
                log.warning(f"  ⚠ {w}")

        log.info(sep)

    def require_webapp(self) -> None:
        """
        Assert that WebApp is configured.
        Call before registering /api/* routes or using WebAppMiddleware.

        Raises:
            RuntimeError: If WEBAPP_URL is not set.
        """
        if not self.has_webapp:
            raise RuntimeError(
                "WebApp is not configured. "
                "Set the WEBAPP_URL environment variable to the public HTTPS URL "
                "where your mini-app frontend is hosted, then restart the bot."
            )

    def check_bridge_feature(
        self,
        feature: str,
        required_platforms: str = "iOS and Android",
    ) -> "FeatureAvailability":
        """
        Return availability info for a Bridge SDK feature.

        This CANNOT give a definitive answer server-side — it describes what
        we know statically. Always check ``bridge.platform`` on the client.

        Example::

            fa = caps.check_bridge_feature("requestContact")
            if not fa.always_available:
                logger.warning(fa.guidance)
        """
        return FeatureAvailability(feature=feature, required_platforms=required_platforms)


@dataclass
class FeatureAvailability:
    """
    Static availability description for a Max WebApp Bridge feature.

    Because platform detection is client-side, ``always_available`` is
    always False for hardware/OS features. Use ``guidance`` in error messages.
    """

    feature: str
    required_platforms: str

    always_available: bool = False

    @property
    def guidance(self) -> str:
        return (
            f"'{self.feature}' requires {self.required_platforms}. "
            f"On the frontend: check bridge.platform and bridge.isAvailable "
            f"before calling bridge methods; hide UI elements that are not supported."
        )

    def raise_if_server_side(self) -> None:
        """
        Raise an informative error if someone tries to invoke a client-only
        feature from the server side (which is never correct).
        """
        from aioscam.webapp.init_data import FeatureUnavailableError
        raise FeatureUnavailableError(self.feature, self.required_platforms)
