import asyncio
import logging
import sys

from aiogram import Dispatcher

from .adapters.telegram.handlers.start import router as start_router
from .adapters.telegram.handlers.schedule import router as schedule_router
from .adapters.telegram.bot_instence import bot
from .config import settings


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


async def main() -> None:
    setup_logging(settings.debug)
    log = logging.getLogger("telegram.entry")

    if not settings.telegram_token:
        raise RuntimeError("TELEGRAM_TOKEN не задан.")

    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(schedule_router)

    log.info("Telegram-бот запускается...")

    try:
        await dp.start_polling(bot)
    except Exception:
        log.exception("Ошибка в поллинге")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger("telegram.entry").info("Бот остановлен!")
        sys.exit(0)
