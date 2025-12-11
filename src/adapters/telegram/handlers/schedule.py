from aiogram import Router, types
from aiogram import F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import os

from ..bot_instence import bot
from ....core.storage import user_groups, get_user_schedule_file
from ..states.schedule_states import ScheduleStates
from ..kbds.kbds import get_main_keyboard, get_day_navigation_keyboard
from ....core.services.schedule_service import get_schedule_data_for_day
from ....core.parser import download_schedule
from .start import send_welcome
from ....core.url_store import load_urls, set_user_url
from ....core.storage import user_notifications


router = Router()

@router.message(F.document)
async def handle_file_upload(message: Message):
    user_id = message.from_user.id # type: ignore
    doc = message.document

    if not doc.file_name.lower().endswith(".csv"): # type: ignore
        return await message.answer("❗ Отправьте файл в формате .csv")

    try:
        file = await bot.get_file(doc.file_id)
        save_path = get_user_schedule_file(user_id)
        await bot.download_file(file.file_path, save_path)

        await message.answer("✅ Файл расписания обновлён!")
        await send_welcome(message)

    except Exception as e:
        await message.answer(f"❌ Ошибка сохранения файла:\n{e}")


@router.callback_query(F.data.startswith("show_"))
async def show_schedule_callback(callback: types.CallbackQuery):
    timeframe = callback.data[5:]
    user_id = callback.from_user.id
    today = datetime.now().date()

    await callback.answer()

    if timeframe == "today":
        date = today
    elif timeframe == "tomorrow":
        date = today + timedelta(days=1)
    elif timeframe == "month":
        date = today.replace(day=1)
    elif timeframe == "next_month":
        if today.month == 12:
            date = today.replace(year=today.year+1, month=1, day=1)
        else:
            date = today.replace(month=today.month+1, day=1)
    else:
        return await callback.message.edit_text("⚠️ Неверный timeframe")

    text = await get_schedule_data_for_day(date, user_id)

    # границы месяца для кнопок
    min_d = date.replace(day=1)
    if date.month == 12:
        max_d = date.replace(year=date.year+1, month=1, day=1) - timedelta(days=1)
    else:
        max_d = date.replace(month=date.month+1, day=1) - timedelta(days=1)

    keyboard = get_day_navigation_keyboard(date, min_d, max_d)

    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "update_schedule")
async def process_update(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    links = load_urls()

    if str(user_id) in links:
        url = links[str(user_id)]
        file_path = get_user_schedule_file(user_id)

        loading = await callback.message.edit_text("⏳ Обновляю расписание...")

        try:
            if os.path.exists(file_path):
                os.remove(file_path)

            await download_schedule(url, file_path)

            await loading.edit_text("✅ Расписание обновлено!", 
                                    reply_markup=get_main_keyboard(user_id))
        except Exception as e:
            await loading.edit_text(f"❌ Ошибка:\n{e}")

        return

    # --- Если ссылки нет — просим ввести ---
    await callback.message.edit_text("Вставь ссылку на расписание:")
    await state.set_state(ScheduleStates.waiting_for_url)



@router.message(ScheduleStates.waiting_for_url)
async def get_schedule_url(message: Message, state: FSMContext):
    url = message.text.strip()
    user_id = message.from_user.id

    set_user_url(user_id, url)

    loading = await message.answer("⏳ Загружаю расписание...")

    try:
        file_path = get_user_schedule_file(user_id)
        if os.path.exists(file_path):
            os.remove(file_path)

        await download_schedule(url, file_path)

        await loading.edit_text("✅ Расписание обновлено!", reply_markup=get_main_keyboard(user_id))
    except Exception as e:
        await loading.edit_text(f"❌ Ошибка:\n{e}")

    await state.clear()



@router.callback_query(F.data == "toggle_group")
async def toggle_group(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    new_group = (user_groups.get(user_id, 0) + 1) % 4
    user_groups[user_id] = new_group

    await callback.answer(f"Группа: {new_group or 'Все'}")
    await callback.message.edit_reply_markup(get_main_keyboard(user_id))


@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_notifications[user_id] = not user_notifications.get(user_id, False)

    await callback.answer(
        "Напоминания включены" if user_notifications[user_id] else "Напоминания выключены"
    )
    await callback.message.edit_reply_markup(get_main_keyboard(user_id))


@router.callback_query(F.data.startswith("day_"))
async def navigate_day(callback: types.CallbackQuery):
    date_val = datetime.fromisoformat(callback.data.split("_")[1]).date()
    user_id = callback.from_user.id

    text = await get_schedule_data_for_day(date_val, user_id)

    min_d = date_val.replace(day=1)
    if date_val.month == 12:
        max_d = date_val.replace(year=date_val.year+1, month=1, day=1) - timedelta(days=1)
    else:
        max_d = date_val.replace(month=date_val.month+1, day=1) - timedelta(days=1)

    keyboard = get_day_navigation_keyboard(date_val, min_d, max_d)

    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text(
        "👋 Привет! Выберите опцию ниже.",
        reply_markup=get_main_keyboard(user_id)
    )