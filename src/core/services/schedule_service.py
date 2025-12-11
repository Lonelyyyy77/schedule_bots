from datetime import datetime, date
import os
import logging
import pandas as pd

from ..storage import user_groups, get_user_schedule_file
import chardet



def parse_group_info(grupa_val: str) -> str:
    if not isinstance(grupa_val, str):
        return ""
    grupa_val = grupa_val.strip()
    if "WykS" in grupa_val:
        return "Wykład"
    elif "Cw" in grupa_val:
        import re
        match = re.search(r"Cw(\d+)S", grupa_val)
        if match:
            return f"Ćwiczenia (grupa {match.group(1)})"
        else:
            return "Ćwiczenia"
    return grupa_val


def read_schedule(user_id: int) -> pd.DataFrame:
    SCHEDULE_FILE = get_user_schedule_file(user_id)
    df = None

    if not os.path.exists(SCHEDULE_FILE):
        logging.info(f"Файл расписания для пользователя {user_id} не найден")
        return pd.DataFrame()

    try:
        with open(SCHEDULE_FILE, "rb") as f:
            raw = f.read()
            detected = chardet.detect(raw)
            encoding = detected["encoding"] or "utf-8"
            logging.info(f"Определена кодировка файла {SCHEDULE_FILE}: {encoding}")
    except Exception as e:
        logging.error(f"Ошибка определения кодировки: {e}")
        encoding = "utf-8"

    for enc in [encoding, "utf-8", "cp1250", "cp1251"]:
        try:
            df = pd.read_csv(
                SCHEDULE_FILE,
                sep=';',
                skiprows=2,
                header=None,
                skipinitialspace=True,
                encoding=enc,
                engine="python"
            )
            logging.info(f"Файл успешно прочитан с кодировкой: {enc}")
            break
        except Exception as e:
            logging.warning(f"Ошибка чтения с кодировкой {enc}: {e}")
            df = None

    if df is None:
        logging.error(f"❌ Не удалось прочитать CSV для пользователя {user_id}")
        return pd.DataFrame()

    df.dropna(how="all", inplace=True)
    if df.empty:
        return pd.DataFrame()

    default_cols = ["temp0", "Czas od", "Czas do", "Liczba godzin", "Grupy",
                    "Zajecia", "Sala", "Forma zaliczenia", "Uwagi", "temp_extra"]

    if df.shape[1] > len(default_cols):
        extra = [f"temp{idx}" for idx in range(len(default_cols), df.shape[1])]
        cols = default_cols + extra
    else:
        cols = default_cols[:df.shape[1]]

    df.columns = cols

    current_date = None
    dates = []

    for _, row in df.iterrows():
        first_col = str(row.iloc[0]).strip()
        if first_col.startswith("Data Zajec"):
            try:
                parts = first_col.split()
                current_date = datetime.strptime(parts[2], "%Y.%m.%d").date()
            except:
                current_date = None
            dates.append(None)
        else:
            dates.append(current_date)

    df["Data_dt"] = dates

    df = df[df["Data_dt"].notna() & df["Czas od"].notna()]

    return df

def format_schedule(df: pd.DataFrame, title: str, user_id: int) -> str:
    if df.empty:
        return f"{title} пусто 📭"

    group_num = user_groups.get(user_id, 0)
    if group_num > 0:
        df = df[df["Grupy"].astype(str).str.contains(f"Cw{group_num}S") | df["Grupy"].astype(str).str.contains("WykS")]

    if df.empty:
        return f"{title} (после фильтра) пусто 📭"

    days = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
    out = [f"📅 {title}:\n"]

    for date_val, group in df.groupby("Data_dt"):
        out.append(f"🗓️ {days[date_val.weekday()]}, {date_val:%d.%m.%Y}\n")

        group['czas_dt'] = pd.to_datetime(group['Czas od'], format="%H:%M", errors='coerce')

        for _, row in group.sort_values("czas_dt").iterrows():
            zajecia_type = parse_group_info(row["Grupy"])
            out.append(f"⏰ {row['Czas od']} - {row['Czas do']}")
            out.append(f"👥 {zajecia_type}")
            out.append(f"📖 {row['Zajecia']}")
            out.append(f"🏫 {row['Sala']}\n")

    return "\n".join(out)


async def get_schedule_data_for_day(date: date, user_id: int) -> str:
    df = read_schedule(user_id)
    if df.empty:
        return "❌ Ваш файл расписания не найден или пуст."
    df_day = df[df["Data_dt"] == date]
    return format_schedule(df_day, f"Расписание на {date:%d.%m.%Y}", user_id)
