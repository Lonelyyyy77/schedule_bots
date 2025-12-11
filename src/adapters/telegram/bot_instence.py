from aiogram import Bot
from aiogram.enums import ParseMode
from src.config import settings

bot = Bot(
    token=settings.require_telegram()
)
