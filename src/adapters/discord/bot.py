from __future__ import annotations

import logging
import discord
from discord.ext import commands

from src.config import settings


def create_discord_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True  

    bot = commands.Bot(
        command_prefix="/",
        intents=intents
    )
    return bot


async def start_discord_bot():
    logging.getLogger("discord.entry").info("Запуск Discord-бота...")

    bot = create_discord_bot()

    from .cogs.schedule import ScheduleCog
    await bot.add_cog(ScheduleCog(bot))

    token = settings.require_discord()

    await bot.start(token)
