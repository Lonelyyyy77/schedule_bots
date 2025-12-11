import logging
import asyncio
import sys

import discord
from discord.ext import commands

from src.config import settings


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


def create_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(
        command_prefix="!",
        intents=intents,
    )

    return bot


async def load_cogs(bot: commands.Bot):
    """
    Подгружает все когы из src/adapters/discord/cogs
    """
    try:
        await bot.load_extension("src.adapters.discord.cogs.schedule")
    except Exception:
        logging.getLogger("discord.bot").exception("Ошибка загрузки когов")
        raise


async def start_discord_bot() -> None:
    setup_logging(settings.debug)
    log = logging.getLogger("discord.entry")

    if not settings.discord_token:
        raise RuntimeError("DISCORD_TOKEN не задан.")

    bot = create_bot()
    await load_cogs(bot)

    log.info("Discord-бот запускается...")

    try:
        await bot.start(settings.discord_token)
    except Exception:
        log.exception("Ошибка в работе Discord-бота")
        raise


def run_discord_bot() -> None:
    """
    Для запуска через python -m src.ds_bot
    """
    try:
        asyncio.run(start_discord_bot())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger("discord.entry").info("Бот остановлен!")
        sys.exit(0)


if __name__ == "__main__":
    run_discord_bot()
