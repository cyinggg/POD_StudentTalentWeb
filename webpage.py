# Basic Flask App Setup
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash, get_flashed_messages
)
import pandas as pd
import os
from calendar import monthrange, Calendar
from datetime import datetime, date, timedelta
import calendar
from collections import defaultdict
import tempfile
import shutil
from zoneinfo import ZoneInfo
from werkzeug.utils import secure_filename
from flask import send_from_directory
import base64

# Initialize App
app = Flask(__name__)
app.secret_key = "replace_this_with_a_secure_key"

@app.context_processor
def inject_now():
    return {'now': datetime.now}

# Excel Data Folder
DATA_FOLDER = "data"
ACCOUNT_FILE = os.path.join(DATA_FOLDER, "account.xlsx")
SLOT_FILE = os.path.join(DATA_FOLDER, "slot_control.xlsx")
APPLICATION_FILE = os.path.join(DATA_FOLDER, "shift_application.xlsx")
RECORD_FILE = os.path.join(DATA_FOLDER, "shift_record.xlsx")
VERIFY_FILE = os.path.join(DATA_FOLDER, "shift_verify.xlsx")

# Excel Helper
def load_excel_safe(filepath):
    if not os.path.exists(filepath):
        return pd.DataFrame()
    try:
        df = pd.read_excel(filepath, engine="openpyxl")
        # Normalize columns: lowercase and strip
        df.columns = df.columns.astype(str).str.strip()
        return df
    except Exception as e:
        print(f"[load_excel_safe] Error reading {filepath}: {e}")
        return pd.DataFrame()

def save_excel_safe(df: pd.DataFrame, filepath: str):
    if df is None:
        raise ValueError("[save_excel_safe] DataFrame is None")
    directory = os.path.dirname(filepath) or "."
    os.makedirs(directory, exist_ok=True)
    if not filepath.lower().endswith(".xlsx"):
        filepath += ".xlsx"
    with tempfile.NamedTemporaryFile(mode="w+b", suffix=".xlsx", dir=directory, delete=False) as tmp:
        temp_path = tmp.name
    try:
        df.to_excel(temp_path, index=False, engine="openpyxl")
        shutil.move(temp_path, filepath)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise RuntimeError(f"[save_excel_safe] Failed saving {filepath}: {e}")

# Normalize account.xlsx
def normalize_account_df(df):
    if df.empty:
        return df

    df.columns = df.columns.str.strip()

    required_cols = [
        "ID", "onjobtrain", "nightShift",
        "totalApprovedShift", "totalPendingShift"
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = 0

    df["ID"] = df["ID"].astype(str)
    return df

def normalize_shift_df(df):
    """Normalize columns, types, and dates for shift DataFrames."""
    if df.empty:
        return df
    df.columns = df.columns.str.strip().str.lower()
    if "id" in df.columns:
        df["id"] = df["id"].astype(str)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    for col in ["status", "admindecision", "adminremarks"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()
    return df

# Home Page Route
@app.route("/")
def home():
    return render_template("home.html")

# Role Selection Page
@app.route("/select_role")
def select_role():
    return render_template("select_role.html")

# Student coach login
# GET show login page, POST validate login
@app.route("/login/student", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        user_id = request.form.get("id", "").strip()
        contact = request.form.get("contact", "").strip()

        df = load_excel_safe(ACCOUNT_FILE)

        if df.empty:
            return render_template("student_login.html", error="No account data found")

        # Normalize all columns safely
        df.columns = df.columns.str.strip().str.lower()  # lowercase everything
        df = df.fillna("")  # prevent NaN issues

        # Ensure columns exist
        for col in ["id", "name", "contact", "role", "onjobtrain", "nightshift"]:
            if col not in df.columns:
                df[col] = "" if col in ["id", "name", "contact", "role"] else 0

        # Convert to string and strip
        df["id"] = df["id"].astype(str).str.strip()
        df["contact"] = df["contact"].astype(str).str.replace(".0", "", regex=False).str.strip()
        df["role"] = df["role"].astype(str).str.strip().str.lower()
        df["name"] = df["name"].astype(str).str.strip()
        df["onjobtrain"] = df["onjobtrain"].fillna(0).astype(int)
        df["nightshift"] = df["nightshift"].fillna(0).astype(int)

        # Filter for student coach
        user = df[
            (df["id"] == user_id) &
            (df["contact"] == contact) &
            (df["role"] == "student coach")
        ]

        if user.empty:
            return render_template("student_login.html", error="Invalid ID or Contact")

        session["user"] = {
            "id": user.iloc[0]["id"],
            "name": user.iloc[0]["name"],
            "role": "student coach",
            "onjobtrain": int(user.iloc[0]["onjobtrain"]),
            "nightShift": int(user.iloc[0]["nightshift"])
        }

        return redirect(url_for("student_home"))

    return render_template("student_login.html")

# Admin login
@app.route("/login/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user_id = request.form.get("id", "").strip()
        contact = request.form.get("contact", "").strip()

        df = load_excel_safe(ACCOUNT_FILE)

        if df.empty:
            return render_template("admin_login.html", error="No account data found")

        # Normalize all columns safely
        df.columns = df.columns.str.strip().str.lower()
        df = df.fillna("")

        for col in ["id", "name", "contact", "role"]:
            if col not in df.columns:
                df[col] = ""

        df["id"] = df["id"].astype(str).str.strip()
        df["contact"] = df["contact"].astype(str).str.replace(".0", "", regex=False).str.strip()
        df["role"] = df["role"].astype(str).str.strip().str.lower()
        df["name"] = df["name"].astype(str).str.strip()

        # Filter for admin
        user = df[
            (df["id"] == user_id) &
            (df["contact"] == contact) &
            (df["role"] == "admin")
        ]

        if user.empty:
            return render_template("admin_login.html", error="Invalid ID or Contact")

        session["user"] = {
            "id": user.iloc[0]["id"],
            "name": user.iloc[0]["name"],
            "role": "admin"
        }

        return redirect(url_for("admin_home"))

    return render_template("admin_login.html")

# Student coach home
@app.route("/student/home")
def student_home():
    if "user" not in session or session["user"]["role"] != "student coach":
        return redirect(url_for("student_login"))

    return render_template("student_home.html", user=session["user"])

# Admin home
@app.route("/admin/home")
def admin_home():
    if "user" not in session or session["user"]["role"] != "admin":
        return redirect(url_for("admin_login"))

    return render_template("admin_home.html", user=session["user"])

# Projecthub calendar public accessable
# @app.route("/projecthub")
# def projecthub():
#     return render_template("projecthub.html")

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# Admin slot control
@app.route("/admin/slot_control")
def admin_slot_control():
    view_type = request.args.get("view", "table")
    month = int(request.args.get("month", datetime.today().month))
    year = int(request.args.get("year", datetime.today().year))

    # --- Load slot data safely ---
    slot_df = load_excel_safe(SLOT_FILE)

    # Normalize column names
    slot_df.columns = slot_df.columns.astype(str).str.strip()

    # Ensure required columns exist
    required_cols = [
        "month", "date", "day", "shiftperiod", "shiftlevel",
        "approvedshift", "isopen", "remarks", "onjobtrain", "nightshift"
    ]
    for col in required_cols:
        if col not in slot_df.columns:
            slot_df[col] = 0 if col in ["approvedshift", "isopen", "onjobtrain", "nightshift"] else ""

    # Normalize types
    slot_df["date"] = pd.to_datetime(slot_df["date"], errors="coerce")
    slot_df["isopen"] = slot_df["isopen"].fillna(0).astype(int)
    slot_df["approvedshift"] = slot_df["approvedshift"].fillna(0).astype(int)
    slot_df["onjobtrain"] = slot_df["onjobtrain"].fillna(0).astype(int)
    slot_df["nightshift"] = slot_df["nightshift"].fillna(0).astype(int)

    # Filter slots for selected month
    slot_df_month = slot_df[
        (slot_df["date"].dt.year == year) & (slot_df["date"].dt.month == month)
    ].copy()

    # --- Auto-create missing slots ---
    shift_types = ["Morning", "Afternoon", "Night"]
    shift_levels = ["L3", "L4", "L6"]
    first_day = datetime(year, month, 1)
    last_day = datetime(year, month, calendar.monthrange(year, month)[1])
    all_dates = pd.date_range(first_day, last_day)

    new_rows = []
    for d in all_dates:
        for stype in shift_types:
            for slevel in shift_levels:
                # Check if slot already exists
                exists = (
                    (slot_df_month["date"] == d) &
                    (slot_df_month["shiftperiod"] == stype) &
                    (slot_df_month["shiftlevel"] == slevel)
                ).any()
                if not exists:
                    new_rows.append({
                        "month": f"{year}-{month:02d}",
                        "date": d,
                        "day": d.strftime("%A"),
                        "shiftperiod": stype,
                        "shiftlevel": slevel,
                        "approvedshift": 0,
                        "isopen": 0,
                        "remarks": "",
                        "onjobtrain": 0,
                        "nightshift": 1 if stype == "Night" else 0
                    })

    # Append new slots if any
    if new_rows:
        slot_df = pd.concat([slot_df, pd.DataFrame(new_rows)], ignore_index=True)
        # Remove duplicate columns just in case
        slot_df = slot_df.loc[:, ~slot_df.columns.duplicated()]
        save_excel_safe(slot_df, SLOT_FILE)
        slot_df_month = slot_df[
            (slot_df["date"].dt.year == year) & (slot_df["date"].dt.month == month)
        ].copy()

    # --- Build calendar (Monday first) ---
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        week_data = []
        for d in week:
            shifts = slot_df_month[slot_df_month["date"] == pd.Timestamp(d)].to_dict("records") if d.month == month else []
            week_data.append({"date": d, "shifts": shifts})
        weeks.append(week_data)

    return render_template(
        "admin_slot_control.html",
        view=view_type,
        month=month,
        year=year,
        weeks=weeks,
        slots=slot_df_month.to_dict("records"),
        current_year=datetime.today().year,
        today=date.today()
    )

# Admin slot control update
@app.route("/admin/slot_control/update", methods=["POST"])
def update_shift():
    date_str = request.form.get("date")
    shiftPeriod = request.form.get("shiftPeriod")
    shiftLevel = request.form.get("shiftLevel")

    def to_int(val, default=0):
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    isOpen = to_int(request.form.get("isOpen"))
    onjobtrain = to_int(request.form.get("onjobtrain"))
    nightShift = to_int(request.form.get("nightShift"))
    remarks = request.form.get("remarks", "")

    slot_df = load_excel_safe(SLOT_FILE)
    slot_df.columns = slot_df.columns.astype(str).str.strip()

    # Normalize date
    target_date = pd.to_datetime(date_str).normalize()
    slot_df["date"] = pd.to_datetime(slot_df["date"], errors="coerce").dt.normalize()

    # Create mask
    mask = (
        (slot_df["date"] == target_date) &
        (slot_df["shiftperiod"] == shiftPeriod) &
        (slot_df["shiftlevel"] == shiftLevel)
    )

    if not mask.any():
        return jsonify({"success": False, "error": "Slot not found"}), 404

    # Update slot
    slot_df.loc[mask, "isopen"] = isOpen
    slot_df.loc[mask, "onjobtrain"] = onjobtrain
    slot_df.loc[mask, "nightshift"] = nightShift
    slot_df.loc[mask, "remarks"] = remarks

    save_excel_safe(slot_df, SLOT_FILE)

    return jsonify({
        "success": True,
        "isOpen": isOpen,
        "onjobtrain": onjobtrain,
        "nightShift": nightShift
    })

# Update totalApprovedShift and totalPendingShift
def recalculate_account_shift_totals():

    # Load Excel files safely
    app_df = load_excel_safe(APPLICATION_FILE)
    acc_df = load_excel_safe(ACCOUNT_FILE)

    if app_df.empty or acc_df.empty:
        print("Skipping totals update — empty Excel")
        return

    # --- Normalize columns ---
    app_df.columns = app_df.columns.str.strip().str.lower()
    acc_df.columns = acc_df.columns.str.strip()

    app_df["id"] = app_df["id"].astype(str).str.strip()
    app_df["admindecision"] = app_df.get("admindecision", "").astype(str).str.lower()
    app_df["status"] = app_df.get("status", "").astype(str).str.lower()

    acc_df["ID"] = acc_df["ID"].astype(str).str.strip()

    # --- Reset totals ---
    acc_df["totalApprovedShift"] = 0
    acc_df["totalPendingShift"] = 0

    # --- Count per user ---
    for user_id in acc_df["ID"]:
        approved_count = ((app_df["id"] == user_id) & (app_df["admindecision"] == "approved")).sum()
        pending_count = ((app_df["id"] == user_id) & (app_df["status"] == "pending")).sum()

        acc_df.loc[acc_df["ID"] == user_id, "totalApprovedShift"] = approved_count
        acc_df.loc[acc_df["ID"] == user_id, "totalPendingShift"] = pending_count

    # --- Save safely ---
    save_excel_safe(acc_df, ACCOUNT_FILE)
    print("ACCOUNT_FILE totals updated successfully")

# --- Eligibility check function ---
def check_booking_eligibility(user, slot):

    eligible = True
    reasons = []

    user_onjob = int(user.get("onjobtrain", 0))
    user_night = int(user.get("nightShift", 0))

    slot_onjob = int(slot.get("onjobtrain", 0))
    slot_night = int(slot.get("nightshift", 0))

    # OJT-only slot
    if slot_onjob == 1 and slot_night == 0:
        if user_onjob != 1:
            eligible = False
            reasons.append("OJT required")

    # Night-only slot
    elif slot_night == 1 and slot_onjob == 0:
        if user_night != 1:
            eligible = False
            reasons.append("Night shift eligibility required")

    # OJT + Night slot
    elif slot_onjob == 1 and slot_night == 1:
        if user_onjob != 1 and user_night != 1:
            eligible = False
            reasons.append("OJT or Night shift required")

    return eligible, "; ".join(reasons)

# Student coach shift booking page
@app.route("/student_coach/shifts")
def student_coach_shifts():
    user = session.get("user")
    if not user or user.get("role") != "student coach":
        return redirect(url_for("student_login"))

    month = int(request.args.get("month", date.today().month))
    year = int(request.args.get("year", date.today().year))
    sid = str(user["id"])

    # -----------------------------
    # Load Excel safely
    # -----------------------------
    slot_df = load_excel_safe(SLOT_FILE)
    app_df = load_excel_safe(APPLICATION_FILE)
    rec_df = load_excel_safe(RECORD_FILE)

    # -----------------------------
    # Normalize SLOT
    # -----------------------------
    slot_df.columns = slot_df.columns.str.strip().str.lower()

    for col in ["isopen", "onjobtrain", "nightshift"]:
        if col not in slot_df.columns:
            slot_df[col] = 0
        slot_df[col] = slot_df[col].fillna(0).astype(int)

    slot_df["date"] = pd.to_datetime(slot_df.get("date"), errors="coerce").dt.date

    # -----------------------------
    # Normalize APPLICATION
    # -----------------------------
    app_df.columns = app_df.columns.str.strip().str.lower()

    required_cols = [
        "timestamp", "id", "name", "month", "date", "day",
        "shiftperiod", "shiftlevel", "status",
        "admindecision", "adminremarks", "cancelrequest"
    ]
    for col in required_cols:
        if col not in app_df.columns:
            app_df[col] = ""

    app_df["id"] = app_df["id"].astype(str)
    app_df["date"] = pd.to_datetime(app_df["date"], errors="coerce").dt.date

    # 🔒 HARD FIX: NEVER NaN TIMESTAMP
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app_df["timestamp"] = (
        app_df["timestamp"]
        .astype(str)
        .replace("nan", "")
        .replace("", now_str)
        .fillna(now_str)
    )

    # -----------------------------
    # Normalize RECORD
    # -----------------------------
    rec_df.columns = rec_df.columns.str.strip().str.lower()
    rec_df["id"] = rec_df.get("id", "").astype(str)
    rec_df["date"] = pd.to_datetime(rec_df.get("date"), errors="coerce").dt.date

    # -----------------------------
    # FILTER SLOT MONTH (OPEN ONLY)
    # -----------------------------
    slot_df = slot_df[
        (slot_df["date"].notna()) &
        (slot_df["date"].apply(lambda d: d.year == year and d.month == month)) &
        (slot_df["isopen"] == 1)
    ]

    # -----------------------------
    # 🔥 INCLUDE OLD APPLICATIONS EVEN IF SLOT MISSING
    # -----------------------------
    user_apps = app_df[
        (app_df["id"] == sid) &
        (app_df["date"].notna()) &
        (app_df["date"].apply(lambda d: d.year == year and d.month == month))
    ]

    for _, row in user_apps.iterrows():
        exists = (
            (slot_df["date"] == row["date"]) &
            (slot_df["shiftperiod"] == row["shiftperiod"]) &
            (slot_df["shiftlevel"] == row["shiftlevel"])
        )
        if not exists.any():
            slot_df = pd.concat([
                slot_df,
                pd.DataFrame([{
                    "date": row["date"],
                    "shiftperiod": row["shiftperiod"],
                    "shiftlevel": row["shiftlevel"],
                    "isopen": 0,
                    "onjobtrain": 0,
                    "nightshift": 0
                }])
            ], ignore_index=True)

    # -----------------------------
    # BUILD CALENDAR
    # -----------------------------
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    weeks = []

    for week in cal.monthdatescalendar(year, month):
        week_days = []
        for d in week:
            day_shifts = []

            shifts = slot_df[slot_df["date"] == d]

            for _, slot in shifts.iterrows():
                eligible = True
                reasons = []

                slot_ojt = int(slot.get("onjobtrain", 0))
                slot_night = int(slot.get("nightshift", 0))
                user_ojt = int(user.get("onjobtrain", 0))
                user_night = int(user.get("nightShift", 0))

                if slot_night == 1 and slot_ojt == 0 and user_night != 1:
                    eligible = False
                    reasons.append("Night shift eligibility required")
                elif slot_ojt == 1 and slot_night == 0 and user_ojt != 1 and user_night != 1:
                    eligible = False
                    reasons.append("OJT or night eligibility required")
                elif slot_ojt == 1 and slot_night == 1 and user_ojt != 1 and user_night != 1:
                    eligible = False
                    reasons.append("OJT or night eligibility required")

                status = "open"

                app = app_df[
                    (app_df["id"] == sid) &
                    (app_df["date"] == d) &
                    (app_df["shiftperiod"] == slot["shiftperiod"]) &
                    (app_df["shiftlevel"] == slot["shiftlevel"])
                ]

                rec = rec_df[
                    (rec_df["id"] == sid) &
                    (rec_df["date"] == d) &
                    (rec_df["shiftperiod"] == slot["shiftperiod"]) &
                    (rec_df["shiftlevel"] == slot["shiftlevel"])
                ]

                if not rec.empty:
                    status = "approved"
                elif not app.empty:
                    status = app.iloc[0]["status"].lower()

                day_shifts.append({
                    "shiftperiod": slot["shiftperiod"],
                    "shiftlevel": slot["shiftlevel"],
                    "status": status,
                    "iseligible": eligible,
                    "reason": "; ".join(reasons),
                    "date": d
                })

            week_days.append({"date": d, "shifts": day_shifts})
        weeks.append(week_days)

    return render_template(
        "student_coach_shift.html",
        user=user,
        weeks=weeks,
        month=month,
        year=year,
        today=date.today(),
        view=request.args.get("view", "calendar")
    )

# Student coach book / cancel
@app.route("/student_coach/shift_action", methods=["POST"])
def student_coach_shift_action():
    try:
        user = session.get("user")
        if not user or user.get("role") != "student coach":
            return jsonify(success=False, error="Unauthorized"), 403

        date_raw = request.form.get("date")
        shift_period = request.form.get("shiftperiod")
        shift_level = request.form.get("shiftlevel")
        action = request.form.get("action")

        if not all([date_raw, shift_period, shift_level, action]):
            return jsonify(success=False, error="Missing data"), 400

        shift_date = pd.to_datetime(date_raw, errors="coerce")
        if pd.isna(shift_date):
            return jsonify(success=False, error="Invalid date"), 400
        shift_date = shift_date.date()

        sid = str(user["id"])

        slot_df = load_excel_safe(SLOT_FILE)
        app_df = load_excel_safe(APPLICATION_FILE)

        slot_df.columns = slot_df.columns.str.strip().str.lower()
        slot_df["date"] = pd.to_datetime(slot_df["date"], errors="coerce").dt.date

        for col in ["onjobtrain", "nightshift"]:
            if col not in slot_df.columns:
                slot_df[col] = 0
            slot_df[col] = slot_df[col].fillna(0).astype(int)

        app_df.columns = app_df.columns.str.strip().str.lower()

        required_cols = [
            "timestamp", "id", "name", "month", "date", "day",
            "shiftperiod", "shiftlevel", "status",
            "admindecision", "adminremarks", "cancelrequest"
        ]
        for col in required_cols:
            if col not in app_df.columns:
                app_df[col] = ""

        app_df["id"] = app_df["id"].astype(str)
        app_df["date"] = pd.to_datetime(app_df["date"], errors="coerce").dt.date

        # 🔒 HARD FIX
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        app_df["timestamp"] = (
            app_df["timestamp"]
            .astype(str)
            .replace("nan", "")
            .replace("", now_str)
            .fillna(now_str)
        )

        existing_app = app_df[
            (app_df["id"] == sid) &
            (app_df["date"] == shift_date) &
            (app_df["shiftperiod"] == shift_period) &
            (app_df["shiftlevel"] == shift_level)
        ]

        if action == "book":
            if not existing_app.empty:
                return jsonify(success=False, error="You already booked this shift"), 400

            new_app = {
                "timestamp": now_str,
                "id": sid,
                "name": user["name"],
                "month": shift_date.strftime("%Y-%m"),
                "date": shift_date.strftime("%Y-%m-%d"),
                "day": shift_date.strftime("%A"),
                "shiftperiod": shift_period,
                "shiftlevel": shift_level,
                "status": "pending",
                "admindecision": "",
                "adminremarks": "",
                "cancelrequest": 0
            }

            app_df = pd.concat([app_df, pd.DataFrame([new_app])], ignore_index=True)
            save_excel_safe(app_df, APPLICATION_FILE)
            recalculate_account_shift_totals()
            return jsonify(success=True)

        if action == "cancel":
            if existing_app.empty:
                return jsonify(success=False, error="No booking found"), 404

            idx = existing_app.index[0]
            status = existing_app.iloc[0]["status"].lower()

            if status == "pending":
                app_df = app_df.drop(idx)
            elif status == "approved":
                app_df.at[idx, "cancelrequest"] = 1
            else:
                return jsonify(success=False, error="Cannot cancel"), 400

            save_excel_safe(app_df, APPLICATION_FILE)
            recalculate_account_shift_totals()
            return jsonify(success=True)

        return jsonify(success=False, error="Invalid action"), 400

    except Exception as e:
        print("student_coach_shift_action ERROR:", e)
        return jsonify(success=False, error="Internal server error"), 500

# Write approved shift to shift_record.xlsx
def write_shift_record_if_not_exists(application_row):
    """
    Writes an approved shift application to shift_record.xlsx if it doesn't already exist.
    Duplicate check is based on ID + date + shiftperiod.
    """

    # Load existing shift record
    record_df = load_excel_safe(RECORD_FILE)

    # Normalize columns to lowercase and strip whitespace
    record_df.columns = [c.strip().lower() for c in record_df.columns]

    # Define canonical columns
    REQUIRED_COLUMNS = [
        "indexshiftverify", "timestamp", "applicationtimestamp",
        "id", "name", "month", "date", "day",
        "shiftperiod", "shiftlevel",
        "clockin", "clockout", "remarks"
    ]

    # Ensure all required columns exist
    for col in REQUIRED_COLUMNS:
        if col not in record_df.columns:
            record_df[col] = ""

    # Ensure types for comparison
    record_df["id"] = record_df["id"].astype(str)
    record_df["date"] = pd.to_datetime(record_df["date"], errors="coerce")
    app_date = pd.to_datetime(application_row.get("date"), errors="coerce")

    # Duplicate check
    duplicate = record_df[
        (record_df["id"] == str(application_row.get("id"))) &
        (record_df["date"] == app_date) &
        (record_df["shiftperiod"] == application_row.get("shiftperiod"))
    ]
    if not duplicate.empty:
        return  # Already exists, do nothing

    # Prepare new row
    new_row = {
        "indexshiftverify": len(record_df) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "applicationtimestamp": application_row.get("timestamp_str") or application_row.get("timestamp"),
        "id": str(application_row.get("id")),
        "name": application_row.get("name", ""),
        "month": application_row.get("month", ""),
        "date": app_date,
        "day": application_row.get("day", ""),
        "shiftperiod": application_row.get("shiftperiod", ""),
        "shiftlevel": application_row.get("shiftlevel", ""),
        "clockin": "",
        "clockout": "",
        "remarks": ""
    }

    # Append new row safely
    record_df = pd.concat([record_df, pd.DataFrame([new_row])], ignore_index=True)

    # Save only canonical columns, in correct order
    save_excel_safe(record_df[REQUIRED_COLUMNS], RECORD_FILE)

# Admin shift application page
@app.route("/admin/shift_application")
def admin_shift_application():
    # Load application data
    app_df = load_excel_safe(APPLICATION_FILE)

    # Current month/year or query params
    today = datetime.today()
    month = request.args.get("month", default=today.month, type=int)
    year = request.args.get("year", default=today.year, type=int)

    # Calendar month (Monday-first)
    cal = calendar.Calendar(firstweekday=0)  # Monday=0
    month_days = [week for week in cal.monthdatescalendar(year, month)]

    if app_df.empty:
        return render_template(
            "admin_shift_application.html",
            application=[],
            calendar_data={},
            today=today.date(),
            month=month,
            year=year,
            month_days=month_days
        )

    # --- Normalize columns ---
    app_df.columns = app_df.columns.str.strip()
    app_df["id"] = app_df["id"].astype(str).str.strip()
    app_df["date"] = pd.to_datetime(app_df["date"], errors="coerce")

    # Ensure admin-related columns exist
    for col in ["admindecision", "adminremarks", "status", "timestamp_str"]:
        if col not in app_df.columns:
            app_df[col] = ""
    
    # Fill missing timestamps for old rows
    # now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # app_df["timestamp_str"] = app_df["timestamp_str"].replace("", now_str).fillna(now_str)
    # if "timestamp" not in app_df.columns:
    #     app_df["timestamp"] = now_str
    # else:
    #     app_df["timestamp"] = app_df["timestamp"].fillna(now_str).replace("", now_str)

    # Ensure columns exist but DO NOT modify values
    for col in ["admindecision", "adminremarks", "status", "timestamp_str", "timestamp"]:
        if col not in app_df.columns:
            app_df[col] = ""

    # Merge with account data for eligibility info
    acc_df = load_excel_safe(ACCOUNT_FILE)
    if not acc_df.empty:
        acc_df.columns = acc_df.columns.str.strip()
        acc_df["ID"] = acc_df["ID"].astype(str).str.strip()

        # Ensure required account columns
        for col in ["onjobtrain", "nightShift", "totalApprovedShift", "totalPendingShift"]:
            if col not in acc_df.columns:
                acc_df[col] = 0

        # Merge application and account
        app_df = app_df.merge(
            acc_df[["ID", "onjobtrain", "nightShift", "totalApprovedShift", "totalPendingShift"]],
            left_on="id",
            right_on="ID",
            how="left"
        )
        app_df.drop(columns=["ID"], inplace=True, errors="ignore")

    # Fill missing values
    for col in ["onjobtrain", "nightShift", "totalApprovedShift", "totalPendingShift"]:
        if col in app_df.columns:
            app_df[col] = app_df[col].fillna(0).astype(int)

    # Build calendar data dict
    calendar_data = defaultdict(list)
    for _, row in app_df.iterrows():
        if pd.isna(row["date"]):
            continue
        date_str = row["date"].strftime("%Y-%m-%d")
        calendar_data[date_str].append({
            "id": row["id"],
            "name": row["name"],
            # "shift": row.get("shiftperiod") or row.get("shiftPeriod"),
            "shift": str(row.get("shiftperiod") or row.get("shiftPeriod") or "").lower(),
            "level": row.get("shiftlevel") or row.get("shiftLevel"),
            "admindecision": row.get("admindecision", ""),
            "status": row.get("status", ""),
            "onjobtrain": row.get("onjobtrain", 0),
            "nightShift": row.get("nightShift", 0),
            "adminremarks": row.get("adminremarks", "")
        })

    return render_template(
        "admin_shift_application.html",
        user=session.get("user"),
        application=app_df.to_dict("records"),
        calendar_data=calendar_data,
        today=today.date(),
        month=month,
        year=year,
        month_days=month_days,
        datetime=datetime,
        timedelta=timedelta
    )

# Admin shift application approve reject AJAX update
@app.route("/admin/shift_application/update", methods=["POST"])
def update_shift_application():
    try:
        # -----------------------------
        # Get form data
        # -----------------------------
        timestamp = (request.form.get("timestamp") or "").strip()
        key = (request.form.get("key") or "").strip()
        admindecision = (request.form.get("admindecision") or "").strip()
        adminremarks = (request.form.get("adminremarks") or "").strip()
        status = (request.form.get("status") or "").strip()

        if not key:
            return jsonify(success=False, error="Missing key"), 400

        try:
            id_, date_str, shift, level = key.split("_")
        except ValueError:
            return jsonify(success=False, error="Invalid key format"), 400

        # -----------------------------
        # Load application file safely
        # -----------------------------
        app_df = load_excel_safe(APPLICATION_FILE)
        app_df.columns = app_df.columns.str.strip().str.lower()

        # -----------------------------
        # Ensure required columns (NO mutation)
        # -----------------------------
        for col in [
            "timestamp", "timestamp_str",
            "admindecision", "adminremarks", "status",
            "adminupdatetimestamp"
        ]:
            if col not in app_df.columns:
                app_df[col] = ""

        # -----------------------------
        # Normalize matching columns
        # -----------------------------
        app_df["id"] = app_df["id"].astype(str).str.strip()
        app_df["date"] = pd.to_datetime(app_df["date"], errors="coerce")
        app_df["shiftperiod"] = app_df["shiftperiod"].astype(str).str.lower()
        app_df["shiftlevel"] = app_df["shiftlevel"].astype(str).str.lower()
        app_df["timestamp_str"] = app_df["timestamp_str"].astype(str).str.strip()

        # -----------------------------
        # Build row match (SAFE)
        # -----------------------------
        mask = None

        if timestamp:
            mask = (app_df["timestamp_str"] == timestamp)

        if mask is None or not mask.any():
            mask = (
                (app_df["id"] == id_) &
                (app_df["date"].dt.strftime("%Y-%m-%d") == date_str) &
                (app_df["shiftperiod"] == shift.lower()) &
                (app_df["shiftlevel"] == level.lower())
            )

        if not mask.any():
            return jsonify(success=False, error="Application not found"), 404

        # -----------------------------
        # Apply update (ONLY target row)
        # -----------------------------
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        app_df.loc[mask, "admindecision"] = admindecision
        app_df.loc[mask, "adminremarks"] = adminremarks
        app_df.loc[mask, "status"] = status
        app_df.loc[mask, "adminupdatetimestamp"] = now_str

        # Fill timestamp_str ONLY if missing (old rows)
        app_df.loc[mask & (app_df["timestamp_str"] == ""), "timestamp_str"] = now_str

        # -----------------------------
        # Save safely
        # -----------------------------
        save_excel_safe(app_df, APPLICATION_FILE)

        # -----------------------------
        # Recalculate totals
        # -----------------------------
        recalculate_account_shift_totals()

        # -----------------------------
        # Write approved record once
        # -----------------------------
        if admindecision.lower() == "approved":
            write_shift_record_if_not_exists(
                app_df.loc[mask].iloc[0].to_dict()
            )

        return jsonify(success=True, message="Application updated successfully")

    except Exception as e:
        print("update_shift_application ERROR:", e)
        return jsonify(success=False, error="Internal server error"), 500

# Student coach attendance page
SG_TZ = ZoneInfo("Asia/Singapore")
def now_sg():
    return datetime.now(SG_TZ).strftime("%Y-%m-%d %H:%M:%S")

@app.route("/student/attendance")
def student_attendance():
    user = session.get("user")
    if user is None or user.get("role") != "student coach":
        return redirect(url_for("student_login"))

    sid = str(user["id"])

    # Load Excel safely
    df = load_excel_safe(RECORD_FILE)

    # Ensure all required columns exist
    required_cols = [
        "indexshiftverify", "timestamp", "applicationtimestamp",
        "id", "name", "month", "date", "day",
        "shiftperiod", "shiftlevel",
        "clockin", "clockout",
        "shiftstart", "shiftend", "shifthours", "remarks"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = "" if col in ["clockin", "clockout", "shiftstart", "shiftend", "remarks"] else 0

    # Normalize
    df.columns = df.columns.str.strip().str.lower()
    df["id"] = df["id"].astype(str)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    # Filter shifts for this student
    my_shifts = df[df["id"] == sid].copy()

    # --- CRITICAL: CLEAN NaN / NaT ---
    for col in ["clockin", "clockout", "shiftstart", "shiftend", "remarks"]:
        if col not in my_shifts.columns:
            my_shifts[col] = ""
        else:
            # Replace any NaN / NaT with empty string
            my_shifts[col] = my_shifts[col].where(my_shifts[col].notna(), "")
            my_shifts[col] = my_shifts[col].astype(str).str.strip()

    if "shifthours" not in my_shifts.columns:
        my_shifts["shifthours"] = ""

    # --- Render template ---
    return render_template(
        "student_attendance.html",
        user=user,
        shifts=my_shifts.to_dict("records"),
        now_time=now_sg()  # returns current SG time string
    )

# Student coach clockIn clockOut
@app.route("/student/attendance/clock", methods=["POST"])
def student_clock_action():
    user = session.get("user")
    if user is None or user.get("role") != "student coach":
        return jsonify(success=False, error="Unauthorized"), 403

    sid = str(user["id"])
    action = request.form.get("action")  # clockin / clockout
    key = request.form.get("key")
    remarks = (request.form.get("remarks") or "").strip()

    if not action or not key:
        return jsonify(success=False, error="Missing data"), 400

    try:
        _, date_str, shift, level = key.split("_")
    except ValueError:
        return jsonify(success=False, error="Invalid key"), 400

    df = load_excel_safe(RECORD_FILE)
    if df.empty:
        return jsonify(success=False, error="No shift records found"), 404

    df.columns = df.columns.str.strip().str.lower()
    df["id"] = df["id"].astype(str)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    mask = (
        (df["id"] == sid) &
        (df["date"] == date_str) &
        (df["shiftperiod"].astype(str).str.lower() == shift.lower()) &
        (df["shiftlevel"].astype(str).str.lower() == level.lower())
    )

    if not mask.any():
        return jsonify(success=False, error="Shift record not found"), 404

    now_time = now_sg()

    if action == "clockin":
        if df.loc[mask, "clockin"].notna().any():
            return jsonify(success=False, error="Already clocked in"), 400
        df.loc[mask, "clockin"] = now_time

    elif action == "clockout":
        if df.loc[mask, "clockin"].isna().any():
            return jsonify(success=False, error="Clock in first"), 400
        if df.loc[mask, "clockout"].notna().any():
            return jsonify(success=False, error="Already clocked out"), 400
        df.loc[mask, "clockout"] = now_time

    else:
        return jsonify(success=False, error="Invalid action"), 400

    if remarks:
        df.loc[mask, "remarks"] = remarks

    save_excel_safe(df, RECORD_FILE)

    return jsonify(success=True, time=now_time)

# Student coach attendance clock in clock out save without page
@app.route("/student/attendance/save", methods=["POST"])
def student_attendance_save():
    user = session.get("user")
    if user is None or user.get("role") != "student coach":
        return jsonify(success=False, error="Unauthorized"), 403

    sid = str(user["id"])
    key = request.form.get("key")
    shiftstart = request.form.get("shiftstart", "").strip()
    shiftend = request.form.get("shiftend", "").strip()
    remarks = request.form.get("remarks", "").strip()

    try:
        _, date_str, shift, level = key.split("_")
    except Exception:
        return jsonify(success=False, error="Invalid key"), 400

    df = load_excel_safe(RECORD_FILE)
    df.columns = df.columns.str.strip().str.lower()
    df["id"] = df["id"].astype(str)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    mask = (
        (df["id"] == sid) &
        (df["date"] == date_str) &
        (df["shiftperiod"] == shift) &
        (df["shiftlevel"] == level)
    )

    if not mask.any():
        return jsonify(success=False, error="Shift not found"), 404

    # Save fields
    df.loc[mask, "shiftstart"] = shiftstart
    df.loc[mask, "shiftend"] = shiftend
    df.loc[mask, "remarks"] = remarks

    # Auto calculate shift hours
    try:
        if shiftstart and shiftend:
            start = datetime.strptime(shiftstart, "%H:%M")
            end = datetime.strptime(shiftend, "%H:%M")
            hours = (end - start).seconds / 3600
            df.loc[mask, "shifthours"] = round(hours, 2)
    except Exception:
        pass  # never crash user input

    save_excel_safe(df, RECORD_FILE)
    return jsonify(success=True)

# Admin verify student coach shift
SG_TZ = ZoneInfo("Asia/Singapore")

def now_sg():
    return datetime.now(SG_TZ).strftime("%Y-%m-%d %H:%M:%S")
# Admin AJAX verify and save sign
@app.route("/admin/verify_shifts")
def admin_verify_shifts():
    user = session.get("user")
    if not user or user.get("role") != "admin":
        return redirect(url_for("admin_login"))

    rec_df = load_excel_safe(RECORD_FILE)
    if rec_df.empty:
        shifts = []
    else:
        rec_df.columns = rec_df.columns.str.strip().str.lower()
        rec_df["date"] = pd.to_datetime(rec_df["date"], errors="coerce")
        
        # Sort by date ascending
        rec_df = rec_df.sort_values(by="date", ascending=True)

        # Merge verification info
        verify_df = load_excel_safe(VERIFY_FILE)
        if not verify_df.empty:
            verify_df.columns = verify_df.columns.str.strip().str.lower()
            # Create set of verified keys
            verified_keys = set(
                f"{row['studentcoachid']}_{row['date']}_{row['shiftperiod']}_{row['shiftlevel']}"
                for idx, row in verify_df.iterrows()
            )
            rec_df["is_verified"] = rec_df.apply(
                lambda r: f"{r['id']}_{r['date'].strftime('%Y-%m-%d')}_{r['shiftperiod']}_{r['shiftlevel']}" in verified_keys,
                axis=1
            )
        else:
            rec_df["is_verified"] = False

        shifts = rec_df.to_dict("records")

    return render_template("admin_verify_shifts.html", user=user, shifts=shifts, now_sg=now_sg())

# --- Admin AJAX verify save ---
@app.route("/admin/verify_shifts/save", methods=["POST"])
def admin_verify_shift_save():
    user = session.get("user")
    if not user or user.get("role") != "admin":
        return jsonify(success=False, error="Unauthorized"), 403

    key = (request.form.get("key") or "").strip()
    staffname = (request.form.get("staffname") or "").strip()
    remarks = (request.form.get("remarks") or "").strip()
    canvas_data = request.form.get("canvasData")
    file = request.files.get("staffsign")

    if not key:
        return jsonify(success=False, error="Missing key"), 400

    if not staffname:
        return jsonify(success=False, error="Staff name required"), 400

    try:
        sid, date_str, shift, level = key.split("_", 3)
    except ValueError:
        return jsonify(success=False, error="Invalid key format"), 400

    rec_df = load_excel_safe(RECORD_FILE)
    if rec_df.empty:
        return jsonify(success=False, error="No records found"), 404

    rec_df.columns = rec_df.columns.str.strip().str.lower()
    rec_df["id"] = rec_df["id"].astype(str)
    rec_df["date"] = pd.to_datetime(rec_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    mask = (
        (rec_df["id"] == sid) &
        (rec_df["date"] == date_str) &
        (rec_df["shiftperiod"] == shift) &
        (rec_df["shiftlevel"] == level)
    )

    if not mask.any():
        return jsonify(success=False, error="Shift not found"), 404

    row = rec_df.loc[mask].iloc[0]

    # ---------- SIGNATURE ----------
    os.makedirs("static/signatures", exist_ok=True)
    sign_filename = ""

    if canvas_data and canvas_data.startswith("data:image"):
        try:
            img_data = canvas_data.split(",", 1)[1]
            if len(img_data) < 1000:
                return jsonify(success=False, error="Signature too small"), 400

            sign_filename = f"{sid}_{date_str}_{shift}_{level}.png"
            with open(os.path.join("static/signatures", sign_filename), "wb") as f:
                f.write(base64.b64decode(img_data))
        except Exception:
            return jsonify(success=False, error="Invalid canvas signature"), 400

    elif file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        sign_filename = f"{sid}_{date_str}_{shift}_{level}{ext}"
        file.save(os.path.join("static/signatures", sign_filename))

    else:
        return jsonify(success=False, error="Signature required"), 400

    verify_df = load_excel_safe(VERIFY_FILE)

    if verify_df.empty:
        verify_df = pd.DataFrame(columns=[
            "indexshiftrecord", "timestamp", "month", "date", "day",
            "shiftperiod", "shiftlevel",
            "studentcoachid", "studentcoachname",
            "clockin", "clockout",
            "shiftstart", "shiftend", "shifthour",
            "staffname", "staffsign", "staffremarks"
        ])
    else:
        verify_df.columns = verify_df.columns.str.strip().str.lower()

    verify_df.loc[len(verify_df)] = {
        "indexshiftrecord": len(verify_df) + 1,
        "timestamp": now_sg(),
        "month": row.get("month", ""),
        "date": row.get("date", ""),
        "day": row.get("day", ""),
        "shiftperiod": row.get("shiftperiod", ""),
        "shiftlevel": row.get("shiftlevel", ""),
        "studentcoachid": row.get("id", ""),
        "studentcoachname": row.get("name", ""),
        "clockin": row.get("clockin", ""),
        "clockout": row.get("clockout", ""),
        "shiftstart": row.get("shiftstart", ""),
        "shiftend": row.get("shiftend", ""),
        "shifthour": row.get("shifthour", ""),
        "staffname": staffname,
        "staffsign": sign_filename,
        "staffremarks": remarks
    }

    save_excel_safe(verify_df, VERIFY_FILE)

    return jsonify(success=True)

# Projecthub duty calendar
@app.route("/projecthub_duty_calendar")
def projecthub_duty_calendar():
    # ------------------------------
    # Date / navigation setup
    # ------------------------------
    today = date.today()
    month = request.args.get("month", today.month, type=int)
    year = request.args.get("year", today.year, type=int)

    # Monday-first calendar
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_days = cal.monthdatescalendar(year, month)

    # ------------------------------
    # Load application data safely
    # ------------------------------
    df = load_excel_safe(APPLICATION_FILE)

    shifts_per_date = defaultdict(list)

    if not df.empty:
        # Normalize columns
        df.columns = df.columns.str.strip()

        # Ensure required columns exist (never break old files)
        for col in ["admindecision", "date", "name", "shiftperiod", "shiftlevel", "adminremarks"]:
            if col not in df.columns:
                df[col] = ""

        # Approved only (case-insensitive)
        df["admindecision"] = df["admindecision"].astype(str).str.lower()
        df = df[df["admindecision"] == "approved"]

        # Parse dates safely
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])

        # Build calendar data
        for _, row in df.iterrows():
            date_str = row["date"].strftime("%Y-%m-%d")

            shifts_per_date[date_str].append({
                "name": str(row["name"]),
                "shiftperiod": str(row["shiftperiod"]).lower(),
                "shiftlevel": str(row["shiftlevel"]).lower(),
                "adminremarks": str(row.get("adminremarks", ""))
            })

    # ------------------------------
    # ALWAYS render calendar
    # ------------------------------
    return render_template(
        "projecthub_duty_calendar.html",
        month=month,
        year=year,
        month_days=month_days,
        shifts_per_date=shifts_per_date,  # empty dict is OK
        today=today
    )

# Mange excel file
# --- Whitelist of allowed Excel files ---
ALLOWED_EXCEL_FILES = {
    "account.xlsx",
    "slot_control.xlsx",
    "shift_application.xlsx",
    "shift_record.xlsx",
    "shift_verify.xlsx",
}

@app.route("/admin/manage_excels")
def admin_manage_excels():
    user = session.get("user")

    # --- Admin guard ---
    if not user or user.get("role") != "admin":
        flash("Unauthorized access", "error")
        return redirect(url_for("admin_login"))

    os.makedirs(DATA_FOLDER, exist_ok=True)

    # --- List Excel files only ---
    excel_files = [
        f for f in os.listdir(DATA_FOLDER)
        if f.lower().endswith((".xlsx", ".xls"))
    ]

    # --- Collect flash messages ---
    flash_messages = [
        {"category": category, "message": message}
        for category, message in get_flashed_messages(with_categories=True)
    ]

    return render_template(
        "admin_manage_excel.html",
        excel_files=excel_files,
        flash_messages=flash_messages
    )

# Upload
@app.route("/admin/upload_excel", methods=["POST"])
def admin_upload_excel():
    user = session.get("user")

    # --- Admin guard ---
    if not user or user.get("role") != "admin":
        flash("Unauthorized access", "error")
        return redirect(url_for("admin_login"))

    file = request.files.get("excel_file")

    if not file or file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("admin_manage_excels"))

    filename = secure_filename(file.filename)

    # --- Extension check ---
    if not filename.lower().endswith((".xlsx", ".xls")):
        flash("Only Excel files are allowed", "error")
        return redirect(url_for("admin_manage_excels"))

    # --- System file whitelist (IMPORTANT) ---
    if filename not in ALLOWED_EXCEL_FILES:
        flash("This Excel file is not allowed to be uploaded", "error")
        return redirect(url_for("admin_manage_excels"))

    os.makedirs(DATA_FOLDER, exist_ok=True)
    save_path = os.path.join(DATA_FOLDER, filename)

    try:
        file.save(save_path)
        flash(f"{filename} uploaded successfully", "success")
    except Exception as e:
        flash(f"Upload failed: {e}", "error")

    return redirect(url_for("admin_manage_excels"))

# Download
@app.route("/admin/download_excel/<filename>")
def admin_download_excel(filename):
    user = session.get("user")

    # --- Admin guard ---
    if not user or user.get("role") != "admin":
        flash("Unauthorized access", "error")
        return redirect(url_for("admin_login"))

    filename = secure_filename(filename)

    # --- Only allow known Excel files ---
    if filename not in ALLOWED_EXCEL_FILES:
        flash("Invalid file request", "error")
        return redirect(url_for("admin_manage_excels"))

    file_path = os.path.join(DATA_FOLDER, filename)

    if not os.path.exists(file_path):
        flash("File not found", "error")
        return redirect(url_for("admin_manage_excels"))

    return send_from_directory(
        DATA_FOLDER,
        filename,
        as_attachment=True
    )

# ==========================
# Debug print all routes
# ==========================
# for rule in app.url_map.iter_rules():
#     print(rule)

# ==========================
# Flask app for Replit
# ==========================
# Health Check for UptimeRobot
@app.route("/health")
def health():
    return "UptimeRobot ok."

# ==========================
# RUN
# ==========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)