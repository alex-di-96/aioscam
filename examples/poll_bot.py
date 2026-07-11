"""
Poll Bot — опросы и квизы поверх inline-клавиатур

Max Bot API не имеет нативных опросов (в отличие от Telegram) — ни в одном
официальном SDK их нет. PollManager эмулирует их inline-кнопками: голоса
хранятся в SQLite (переживают рестарт), сообщение обновляется live-барами.

DEMONSTRATES
────────────
  • PollManager                          (aioscam.polls)
  • polls.attach(dp, command="poll")     — /poll из коробки + StateGuard allowlist
  • Режимы видимости: priv / anon / pub
  • send_poll() / send_quiz()            — опросы от имени бота (bot-driven)
  • close_poll() / results()             — программное управление
  • Локализация подсказок (ru/en из клиента, контент не переводится)
  • Общая база бота .aioscam/bot.db      (одна на PollManager + ChatRegistry)

COMMANDS
────────
  /poll [priv|anon|pub] Вопрос | вар1 | вар2   — создать опрос (встроенная)
  /quiz    — бот отправит демо-квиз (правильный ответ + пояснение)
  /botpoll — bot-driven опрос без владельца (нет кнопок управления,
             закрыть можно только кодом)
  /start   — справка

VISUAL IN MAX MESSENGER
───────────────────────
  /poll pub Куда обедать? | Кафе | Столовая
      → сообщение с кнопками; после голосов — бары ▓▓░ и имена (pub)
      → у автора есть «⏹ Завершить», в priv ещё «📊 Результаты»
  /poll        → подсказка по формату (на языке клиента)
  /quiz        → клик по ответу даёт «✅ Верно!» / «❌ Неверно…» только вам

SETUP
─────
  export MAX_BOT_TOKEN=your_token_here
  python poll_bot.py
"""

import asyncio
import logging

from aioscam import Bot, BotCommand, Command, Dispatcher, PollManager, Router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Setup ─────────────────────────────────────────────────────────────────────

dp = Dispatcher()
router = Router()

# Все компоненты по умолчанию делят одну базу .aioscam/bot.db
polls = PollManager()

# Регистрирует: обработчик голосов (только payload-префикс "apoll:", чужие
# callback-хендлеры не затрагиваются), команду /poll и StateGuard-allowlist,
# чтобы пользователь внутри FSM-диалога тоже мог голосовать.
polls.attach(dp, command="poll")

# ── Handlers ──────────────────────────────────────────────────────────────────

@router.message_created(Command("start"))
async def cmd_start(event):
    await event.answer(
        "📊 Poll Bot — опросы и квизы для Max\n\n"
        "/poll Вопрос | вар1 | вар2 — создать опрос\n"
        "/poll priv … — результаты видит только автор\n"
        "/poll pub …  — видно, кто как проголосовал\n"
        "/quiz — демо-квиз\n"
        "/botpoll — опрос от имени бота (без владельца)"
    )


@router.message_created(Command("quiz"))
async def cmd_quiz(event):
    """
    Квиз: один правильный ответ, ответить можно один раз.
    Распределение голосов скрыто до закрытия, правильный ответ
    раскрывается в сообщении после close_poll().
    """
    await polls.send_quiz(
        event.bot,
        event.chat_id,
        question="Какой домен Max Bot API актуален с июля 2026?",
        options=["botapi.max.ru", "platform-api.max.ru", "platform-api2.max.ru"],
        correct_option=2,
        explanation="Старые домены отключены; сертификат Минцифры уже вшит в aioscam.",
        creator_id=event.user_id,          # автор сможет завершить квиз кнопкой
        user_id=event.user_id,
    )


@router.message_created(Command("botpoll"))
async def cmd_botpoll(event):
    """
    Bot-driven опрос: creator_id=None — «ничейный» опрос от имени бота.
    Кнопок управления в сообщении нет вообще; завершить можно только
    программно: await polls.close_poll(bot, poll_id).
    """
    poll_id = await polls.send_poll(
        event.bot,
        event.chat_id,
        question="Опрос от имени бота — управляется только кодом",
        options=["Понятно", "Покажи ещё раз"],
        visibility="anon",
        creator_id=None,
        user_id=event.user_id,
    )
    logger.info(f"Bot-driven poll created: {poll_id}")
    # Пример программного доступа к результатам в любой момент:
    #   results = await polls.results(poll_id)
    #   await polls.close_poll(event.bot, poll_id)


# ── Router wiring ─────────────────────────────────────────────────────────────

dp.include_router(router)

# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    bot = Bot()
    await bot.set_my_commands([
        BotCommand(name="start",   description="Справка по боту"),
        BotCommand(name="poll",    description="Создать опрос: /poll Вопрос | вар1 | вар2"),
        BotCommand(name="quiz",    description="Демо-квиз"),
        BotCommand(name="botpoll", description="Опрос от имени бота"),
    ])
    logger.info("Poll bot started. Send /poll in Max Messenger.")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        pass
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
