import os
from typing import Dict

USER_SCHEDULES_DIR = os.path.join(os.path.dirname(__file__), "data", "user_schedules")


user_groups: Dict[int, int] = {}
user_notifications: Dict[int, bool] = {}


def ensure_user_dir() -> None:
    os.makedirs(USER_SCHEDULES_DIR, exist_ok=True)


def get_user_schedule_file(user_id: int) -> str:
    ensure_user_dir()
    return os.path.join(USER_SCHEDULES_DIR, f"{user_id}.csv")
