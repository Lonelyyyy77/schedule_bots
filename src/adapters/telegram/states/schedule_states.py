from aiogram.fsm.state import StatesGroup, State


class ScheduleStates(StatesGroup):
    waiting_for_url = State()
