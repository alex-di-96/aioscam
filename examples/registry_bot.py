"""
Registry Bot — реестр чатов и политики обработки backlog

Max API удалил GET /chats (июнь 2026): бот больше не может спросить сервер
«в каких чатах я состою?». ChatRegistry восстанавливает это знание на стороне
бота: SQLite-реестр пополняется из событий (bot_added, bot_started, любое
сообщение — lazy-discovery), polling-marker сохраняется между рестартами,
а sync() сверяет реестр с живым API точечными GET /chats/{id}.

DEMONSTRATES
────────────
  • ChatRegistry                         (aioscam.registry)
  • Dispatcher(registry=...)             — авто-пополнение из событий
  • backlog="skip" | "process" | "collapse"
      skip     — накопленное за даунтайм отбрасывается (реестр всё равно
                 обновляется ВСЕМИ событиями по порядку!)
      process  — обработать всё накопленное
      collapse — 50 старых /start от одного юзера → один последний
  • Persist marker: рестарт продолжает с места остановки
  • registry.sync(bot)                   — ручная реконсиляция + права бота
  • Общая база .aioscam/bot.db           (одна на ChatRegistry + PollManager)

COMMANDS
────────
  /chats — известные чаты из реестра (группы, каналы, диалоги)
  /sync  — реконсиляция с живым API (title, статус, права бота)
  /start — справка

VISUAL IN MAX MESSENGER
───────────────────────
  Добавьте бота в группу → напишите /chats — группа уже в списке
  (событие bot_added попало в реестр автоматически).
  Выключите бота, добавьте его в ещё одну группу, включите — после
  рестарта /chats покажет и её: marker сохранён, событие не потерялось.

SETUP
─────
  export MAX_BOT_TOKEN=your_token_here
  python registry_bot.py
"""

import asyncio
import logging

from aioscam import Bot, BotCommand, ChatRegistry, Command, Dispatcher, Router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Setup ─────────────────────────────────────────────────────────────────────

registry = ChatRegistry()          # .aioscam/bot.db — общая база бота
dp = Dispatcher(registry=registry)
router = Router()

_TYPE_ICONS = {"chat": "👥", "channel": "📢", "dialog": "💬"}

# ── Handlers ──────────────────────────────────────────────────────────────────

@router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer(
        "📇 Registry Bot — реестр чатов без GET /chats\n\n"
        "/chats — что бот знает о своих чатах\n"
        "/sync  — сверить реестр с живым API\n\n"
        "Добавьте бота в группу и снова вызовите /chats — "
        "она появится в списке автоматически."
    )


@router.message_created(Command("chats"))
async def cmd_chats(event):
    """
    Список чатов из ЛОКАЛЬНОГО реестра — ни одного запроса к API.
    Реестр пополняется сам: bot_added/bot_started обрабатываются даже при
    backlog="skip", а любое сообщение из неизвестного чата регистрирует его.
    """
    chats = await registry.chats()
    if not chats:
        await event.answer("Реестр пуст. Добавьте бота в группу или напишите ему.")
        return

    lines = [f"Известно чатов: {len(chats)}\n"]
    for chat in chats:
        icon = _TYPE_ICONS.get(chat["type"], "❔")
        title = chat["title"] or f"id {chat['chat_id']}"
        extra = ""
        if chat["bot_is_admin"]:
            extra = " · бот админ"
        lines.append(f"{icon} {title} ({chat['type']}){extra}")
    await event.answer("\n".join(lines))


@router.message_created(Command("sync"))
async def cmd_sync(event):
    """
    Ручная реконсиляция:
    1) best-effort bootstrap через deprecated GET /chats (пока Max его не отключил);
    2) точечный GET /chats/{id} по каждому известному чату — 403/404 помечает
       чат удалённым (soft-delete), успех обновляет title/статус/участников;
    3) права бота через GET /chats/{id}/members/me (TTL-кэш 1 час) — у Max НЕТ
       события «права изменились», периодическая сверка — единственный способ.
    """
    stats = await registry.sync(event.bot)
    await event.answer(
        "🔄 Синхронизация завершена\n"
        f"bootstrap: {stats['bootstrapped']} · проверено: {stats['checked']}\n"
        f"обновлено: {stats['updated']} · удалено: {stats['removed']}"
    )


# ── Router wiring ─────────────────────────────────────────────────────────────

dp.include_router(router)

# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    bot = Bot()
    await bot.set_my_commands([
        BotCommand(name="start", description="Справка по боту"),
        BotCommand(name="chats", description="Известные чаты из реестра"),
        BotCommand(name="sync",  description="Сверить реестр с API"),
    ])

    # Стартовая сверка: подтягивает чаты, о которых бот узнал бы только
    # по событиям — полезно на первом запуске.
    stats = await registry.sync(bot)
    logger.info(f"Startup sync: {stats}")

    logger.info("Registry bot started. Send /chats in Max Messenger.")
    try:
        # collapse: события даунтайма не теряются, но 50 старых /start от
        # одного пользователя схлопнутся в один; реестровые события
        # (bot_added/bot_removed) применяются к базе ВСЕ по порядку.
        await dp.start_polling(bot, backlog="collapse")
    except KeyboardInterrupt:
        pass
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
