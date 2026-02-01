import pandas as pd
from datetime import date
from zoneinfo import ZoneInfo
import os

SG_TZ = ZoneInfo("Asia/Singapore")
RECORD_FILE = os.path.join("data", "shift_record.xlsx")

def load_approved_shifts(target_date: date):
    if not os.path.exists(RECORD_FILE):
        return []

    df = pd.read_excel(RECORD_FILE, engine="openpyxl")
    df.columns = df.columns.str.strip().str.lower()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    day_df = df[df["date"] == target_date]

    shifts = []
    for _, r in day_df.iterrows():
        shifts.append({
            "name": r.get("name", ""),
            "shift": r.get("shiftperiod", ""),
            "level": r.get("shiftlevel", "")
        })

    return shifts
