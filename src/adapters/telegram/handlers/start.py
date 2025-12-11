from aiogram.filters.command import CommandStart
from aiogram.types import Message
from aiogram import Router

from ..kbds.kbds import get_main_keyboard


router = Router()

@router.message(CommandStart())
async def send_welcome(message: Message):
    user_id = message.from_user.id # type: ignore
    text = (
        "👋 Привет! Я ваш бот для просмотра расписания.\n\n"
        "Выберите опцию ниже.\n\n"
        "Для обновления данных отправьте новый файл `Plany.csv`."
    )
    await message.answer(text, reply_markup=get_main_keyboard(user_id))