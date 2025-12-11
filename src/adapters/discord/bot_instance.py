import discord
from discord.ext import commands

from src.config import settings


def create_discord_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(
        command_prefix="!",
        intents=intents,
    )

    return bot


bot = create_discord_bot()
