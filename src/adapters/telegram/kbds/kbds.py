from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import timedelta
from ....core.storage import user_notifications, user_groups


def get_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    notif_state = user_notifications.get(user_id, False)
    notif_text = "🔔 Напоминания ВКЛ" if notif_state else "🔕 Напоминания ВЫКЛ"

    group_num = user_groups.get(user_id, 0)
    group_text = "👥 Фильтр: Все группы" if group_num == 0 else f"👥 Фильтр: {group_num} группа"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗓️ Сегодня", callback_data="show_today"),
         InlineKeyboardButton(text="🗓️ Завтра", callback_data="show_tomorrow")],

        [InlineKeyboardButton(text="📅 На этот месяц", callback_data="show_month"),
         InlineKeyboardButton(text="📅 На след месяц", callback_data="show_next_month")],

        [InlineKeyboardButton(text=notif_text, callback_data="toggle_notifications")],
        [InlineKeyboardButton(text=group_text, callback_data="toggle_group")],
        [InlineKeyboardButton(text="🔄 Обновить расписание", callback_data="update_schedule")]
    ])


def get_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])


def get_day_navigation_keyboard(current_date, min_date, max_date) -> InlineKeyboardMarkup:
    nav_buttons = []

    if current_date > min_date:
        prev_day = current_date - timedelta(days=1)
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"day_{prev_day.isoformat()}"
        ))

    if current_date < max_date:
        next_day = current_date + timedelta(days=1)
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"day_{next_day.isoformat()}"
        ))

    keyboard = []
    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton(text="⬅️ Меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
