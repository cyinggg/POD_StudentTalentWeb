# Basic Flask App Setup
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash, get_flashed_messages
)
import pandas as pd
import os
import pandas as pd
from calendar import monthrange, Calendar
from datetime import datetime, date, timedelta
import calendar
from collections import defaultdict
import tempfile
import shutil

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
    # Load Excel files safely
    # -----------------------------
    slot_df = normalize_shift_df(load_excel_safe(SLOT_FILE))
    app_df = normalize_shift_df(load_excel_safe(APPLICATION_FILE))
    rec_df = normalize_shift_df(load_excel_safe(RECORD_FILE))

    # -----------------------------
    # Normalize slot_df columns/types
    # -----------------------------
    slot_df.columns = slot_df.columns.str.strip().str.lower()
    for col in ["isopen", "onjobtrain", "nightshift"]:
        if col not in slot_df.columns:
            slot_df[col] = 0
        slot_df[col] = slot_df[col].fillna(0).astype(int)

    if "date" in slot_df.columns:
        slot_df["date"] = pd.to_datetime(slot_df["date"], errors="coerce").dt.date

    # -----------------------------
    # Filter slots for current month & open
    # -----------------------------
    slot_df = slot_df[
        (slot_df["date"].notna()) &
        (slot_df["date"].apply(lambda d: d.year == year and d.month == month)) &
        (slot_df["isopen"] == 1)
    ]

    # -----------------------------
    # Normalize application dataframe
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

    # Fill missing timestamps for old rows
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if "timestamp" not in app_df.columns:
        app_df["timestamp"] = now_str
    else:
        app_df["timestamp"] = app_df["timestamp"].fillna(now_str).replace("", now_str)

    # -----------------------------
    # Normalize record dataframe
    # -----------------------------
    rec_df.columns = rec_df.columns.str.strip().str.lower()
    rec_df["id"] = rec_df["id"].astype(str)
    if "date" in rec_df.columns:
        rec_df["date"] = pd.to_datetime(rec_df["date"], errors="coerce").dt.date

    # -----------------------------
    # Build calendar weeks
    # -----------------------------
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    weeks = []

    for week in cal.monthdatescalendar(year, month):
        week_days = []
        for d in week:
            day_shifts = []
            if d.month == month:
                shifts = slot_df[slot_df["date"] == d]
                for _, slot in shifts.iterrows():
                    # Eligibility checks
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

                    reason = "; ".join(reasons)

                    # Existing booking checks
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
                        "reason": reason,
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

        # -----------------------------
        # Input data
        # -----------------------------
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

        # -----------------------------
        # Load Excel files safely
        # -----------------------------
        slot_df = load_excel_safe(SLOT_FILE)
        app_df = load_excel_safe(APPLICATION_FILE)

        # Normalize columns
        slot_df.columns = slot_df.columns.str.strip().str.lower()
        if "date" in slot_df.columns:
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

        # Fill missing timestamps for old rows
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        app_df["timestamp"] = app_df.get("timestamp", now_str).replace("", now_str).fillna(now_str)

        # -----------------------------
        # Find slot
        # -----------------------------
        slot = slot_df[
            (slot_df["date"] == shift_date) &
            (slot_df["shiftperiod"] == shift_period) &
            (slot_df["shiftlevel"] == shift_level)
        ]
        if slot.empty:
            return jsonify(success=False, error="Shift not found"), 404
        slot = slot.iloc[0]

        # -----------------------------
        # Eligibility checks
        # -----------------------------
        slot_ojt = int(slot.get("onjobtrain", 0))
        slot_night = int(slot.get("nightshift", 0))
        user_ojt = int(user.get("onjobtrain", 0))
        user_night = int(user.get("nightShift", 0))

        if slot_night == 1 and slot_ojt == 0 and user_night != 1:
            return jsonify(success=False, error="Night shift eligibility required"), 403
        if slot_ojt == 1 and slot_night == 0 and user_ojt != 1 and user_night != 1:
            return jsonify(success=False, error="OJT or night eligibility required"), 403
        if slot_ojt == 1 and slot_night == 1 and user_ojt != 1 and user_night != 1:
            return jsonify(success=False, error="OJT or night eligibility required"), 403

        # -----------------------------
        # Existing application check
        # -----------------------------
        existing_app = app_df[
            (app_df["id"] == sid) &
            (app_df["date"] == shift_date) &
            (app_df["shiftperiod"] == shift_period) &
            (app_df["shiftlevel"] == shift_level)
        ]

        # -----------------------------
        # Book / Cancel logic
        # -----------------------------
        if action == "book":
            if not existing_app.empty:
                return jsonify(success=False, error="You already booked this shift"), 400

            new_app = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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

        elif action == "cancel":
            if existing_app.empty:
                return jsonify(success=False, error="No booking found"), 404

            idx = existing_app.index[0]
            current_status = existing_app.iloc[0]["status"].lower()

            if current_status == "pending":
                app_df = app_df.drop(idx)
                save_excel_safe(app_df, APPLICATION_FILE)
                recalculate_account_shift_totals()
                return jsonify(success=True)

            elif current_status == "approved":
                app_df.at[idx, "cancelrequest"] = 1
                save_excel_safe(app_df, APPLICATION_FILE)
                recalculate_account_shift_totals()
                return jsonify(success=True, message="Cancel request sent to admin for approval")

            return jsonify(success=False, error="Cannot cancel this shift"), 400

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
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app_df["timestamp_str"] = app_df["timestamp_str"].replace("", now_str).fillna(now_str)
    if "timestamp" not in app_df.columns:
        app_df["timestamp"] = now_str
    else:
        app_df["timestamp"] = app_df["timestamp"].fillna(now_str).replace("", now_str)

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
            "shift": row.get("shiftperiod") or row.get("shiftPeriod"),
            "level": row.get("shiftlevel") or row.get("shiftLevel"),
            "admindecision": row.get("admindecision", ""),
            "status": row.get("status", ""),
            "onjobtrain": row.get("onjobtrain", 0),
            "nightShift": row.get("nightShift", 0),
            "adminremarks": row.get("adminremarks", "")
        })

    return render_template(
        "admin_shift_application.html",
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
        # Get form data
        timestamp = request.form.get("timestamp", "").strip()
        key = request.form.get("key", "").strip()  # id_date_shift_shiftlevel
        admindecision = request.form.get("admindecision", "").strip()
        adminremarks = request.form.get("adminremarks", "").strip()
        status = request.form.get("status", "").strip()

        if not key:
            return jsonify(success=False, error="Missing key"), 400

        try:
            id_, date_str, shift, level = key.split("_")
        except ValueError:
            return jsonify(success=False, error="Invalid key format"), 400

        # Load application data
        app_df = load_excel_safe(APPLICATION_FILE)
        app_df.columns = [c.strip() for c in app_df.columns]

        # Ensure required columns exist
        for col in ["admindecision", "adminremarks", "status", "adminUpdateTimestamp", "timestamp_str"]:
            if col not in app_df.columns:
                app_df[col] = ""
        
        # Fill missing timestamps
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        app_df["timestamp_str"] = app_df["timestamp_str"].replace("", now_str).fillna(now_str)
        app_df["timestamp"] = app_df["timestamp"].replace("", now_str).fillna(now_str)

        # Normalize for matching
        app_df["id"] = app_df["id"].astype(str).str.strip()
        app_df["date"] = pd.to_datetime(app_df["date"], errors="coerce")
        app_df["shiftperiod"] = app_df.get("shiftperiod", "").astype(str).str.lower()
        app_df["shiftlevel"] = app_df.get("shiftlevel", "").astype(str).str.lower()
        app_df["timestamp_str"] = app_df.get("timestamp_str", "").astype(str).str.strip()

        # Create mask to identify row
        mask = (
            (app_df["id"] == id_) &
            (app_df["date"].dt.strftime("%Y-%m-%d") == date_str) &
            (app_df["shiftperiod"] == shift.lower()) &
            (app_df["shiftlevel"] == level.lower())
        )

        if not mask.any():
            return jsonify(success=False, error="Application not found"), 404

        # Update row
        app_df.loc[mask, ["admindecision", "adminremarks", "status"]] = [
            admindecision, adminremarks, status
        ]
        app_df.loc[mask, "adminUpdateTimestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if timestamp:
            app_df.loc[mask, "timestamp_str"] = timestamp

        # Save safely
        save_excel_safe(app_df, APPLICATION_FILE)

        # Recalculate totals in account.xlsx
        recalculate_account_shift_totals()

        # Write approved shifts to record file if not exists
        if admindecision.lower() == "approved":
            write_shift_record_if_not_exists(app_df.loc[mask].iloc[0].to_dict())

        return jsonify(success=True, message=f"Application {admindecision} successfully updated")

    except Exception as e:
        print("update_shift_application ERROR:", e)
        return jsonify(success=False, error=str(e)), 500

# Student coach clockIn clockOut
@app.route("/student/attendance", methods=["GET", "POST"])
def student_attendance():
    if "user" not in session or session["user"]["role"] != "student":
        return redirect(url_for("student_login"))

    user = session["user"]
    df = load_excel_safe(RECORD_FILE)  # shift_record.xlsx
    df = df.fillna("")

    if request.method == "POST":
        date = request.form["date"]
        shiftPeriod = request.form["shiftPeriod"]

        # Check if record exists
        mask = (df["ID"].astype(str) == str(user["id"])) & \
               (df["date"] == date) & \
               (df["shiftPeriod"] == shiftPeriod)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if mask.any():
            # Update clockOut
            df.loc[mask, "clockOut"] = now_str
            df.loc[mask, "remarks"] = request.form.get("remarks", "")
        else:
            # New record: Clock In
            new_row = {
                "indexShiftVerify": len(df)+1,
                "timestamp": now_str,
                "ID": user["id"],
                "name": user["name"],
                "month": date[:7],
                "date": date,
                "day": datetime.strptime(date, "%Y-%m-%d").strftime("%A"),
                "shiftPeriod": shiftPeriod,
                "shiftLevel": request.form.get("shiftLevel", "L3"),
                "clockIn": now_str,
                "clockOut": "",
                "remarks": request.form.get("remarks", "")
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        save_excel_safe(df, RECORD_FILE)
        return render_template("student_attendance.html", success="Attendance recorded!", records=df.to_dict(orient="records"))

    return render_template("student_attendance.html", records=df.to_dict(orient="records"))

# Student coach / Admin verification
@app.route("/admin/verify", methods=["GET", "POST"])
def admin_verify():
    if "user" not in session or session["user"]["role"] != "admin":
        return redirect(url_for("admin_login"))

    df = load_excel_safe(VERIFY_FILE).fillna("")
    record_df = load_excel_safe(RECORD_FILE).fillna("")

    if request.method == "POST":
        index = int(request.form["index"])
        studentCoachName = request.form.get("studentCoachName", "")
        studentCoachIn = request.form.get("studentCoachIn", "")
        studentCoachOut = request.form.get("studentCoachOut", "")
        staffName = session["user"]["name"]
        staffSignature = request.form.get("staffSignature", "")
        staffRemarks = request.form.get("staffRemarks", "")

        if index >= 0 and index < len(record_df):
            shift = record_df.iloc[index]
            new_row = {
                "indexShiftRecord": index+1,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ID": shift["id"],
                "name": shift["name"],
                "month": shift["month"],
                "date": shift["date"],
                "day": shift["day"],
                "shiftPeriod": shift["shiftPeriod"],
                "shiftLevel": shift["shiftLevel"],
                "studentCoachName": studentCoachName,
                "studentCoachIn": studentCoachIn,
                "studentCoachOut": studentCoachOut,
                "staffName": staffName,
                "staffSignature": staffSignature,
                "staffRemarks": staffRemarks
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_excel_safe(df, VERIFY_FILE)

        return redirect(url_for("admin_verify"))

    return render_template("admin_verify.html", records=record_df.to_dict(orient="records"))

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
    file = request.files.get("excel_file")

    if not file or file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("admin_manage_excels"))

    # Sanitize filename (CRITICAL for security)
    filename = secure_filename(file.filename)

    # Optional: only allow Excel files
    if not filename.lower().endswith((".xlsx", ".xls")):
        flash("Only Excel files are allowed", "error")
        return redirect(url_for("admin_manage_excels"))

    os.makedirs(DATA_FOLDER, exist_ok=True)
    save_path = os.path.join(DATA_FOLDER, filename)

    file.save(save_path)

    flash(f"{filename} uploaded successfully", "success")
    return redirect(url_for("admin_manage_excels"))

# Download
@app.route("/admin/download/<path:filename>")
def admin_download_excel(filename):
    try:
        return send_from_directory(
            DATA_FOLDER,
            filename,
            as_attachment=True
        )
    except FileNotFoundError:
        flash(f"{filename} not found", "error")
        return redirect(url_for("admin_manage_excels"))

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