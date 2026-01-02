# Basic Flask App Setup
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
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
        return pd.read_excel(filepath)
    except:
        return pd.DataFrame()

def save_excel_safe(df, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_excel(filepath, index=False)

def save_excel_atomic(df, filepath):
    """
    Transaction-safe Excel write:
    prevents partial writes / corruption
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        temp_path = tmp.name

    try:
        df.to_excel(temp_path, index=False)
        shutil.move(temp_path, filepath)  # atomic replace
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

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
        user_id = request.form["id"].strip()
        contact = request.form["contact"].strip()

        df = load_excel_safe(ACCOUNT_FILE)

        # Normalize data
        df["ID"] = df["ID"].astype(str).str.strip()
        df["Contact"] = df["Contact"].astype(str).str.replace(".0", "", regex=False).str.strip()
        df["role"] = df["role"].astype(str).str.strip().str.lower()

        user = df[
            (df["ID"] == user_id) &
            (df["Contact"] == contact) &
            (df["role"] == "student coach")
        ]

        if user.empty:
            return render_template("student_login.html", error="Invalid ID or Contact")

        session["user"] = {
            "id": user.iloc[0]["ID"],
            "name": user.iloc[0]["name"],
            "role": "student coach",
            "onjobtrain": int(user.iloc[0]["onjobtrain"]),
            "nightShift": int(user.iloc[0]["nightShift"])
        }

        return redirect(url_for("student_home"))

    return render_template("student_login.html")

# Admin login
@app.route("/login/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user_id = request.form["id"].strip()
        contact = request.form["contact"].strip()

        df = load_excel_safe(ACCOUNT_FILE)

        df["ID"] = df["ID"].astype(str).str.strip()
        df["Contact"] = df["Contact"].astype(str).str.replace(".0", "", regex=False).str.strip()
        df["role"] = df["role"].astype(str).str.strip().str.lower()

        user = df[
            (df["ID"] == user_id) &
            (df["Contact"] == contact) &
            (df["role"] == "admin")
        ]

        if user.empty:
            return render_template("admin_login.html", error="Invalid ID or Contact")

        session["user"] = {
            "id": user.iloc[0]["ID"],
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
    # --- ALWAYS define view ---
    view_type = request.args.get("view", "table")
    month = int(request.args.get("month", datetime.today().month))
    year = int(request.args.get("year", datetime.today().year))

    # --- Load slot dataframe ---
    slot_df = load_excel_safe(SLOT_FILE)
    slot_df.columns = slot_df.columns.str.strip()  # keep original case for display

    # --- Ensure required columns ---
    required_cols = [
        "month","date","day","shiftPeriod","shiftLevel",
        "approvedShift","isOpen","remarks","onjobtrain","nightShift"
    ]
    for col in required_cols:
        if col not in slot_df.columns:
            slot_df[col] = 0 if col in ["approvedShift","isOpen","onjobtrain","nightShift"] else ""

    # --- Normalize types ---
    slot_df["date"] = pd.to_datetime(slot_df["date"], errors="coerce")
    slot_df["isOpen"] = slot_df["isOpen"].fillna(0).astype(int)
    slot_df["approvedShift"] = slot_df["approvedShift"].fillna(0).astype(int)
    slot_df["onjobtrain"] = slot_df["onjobtrain"].fillna(0).astype(int)
    slot_df["nightShift"] = slot_df["nightShift"].fillna(0).astype(int)

    # --- Filter for selected month ---
    slot_df_month = slot_df[
        (slot_df["date"].dt.year == year) &
        (slot_df["date"].dt.month == month)
    ].copy()

    # --- Auto-create missing slots (non-destructive) ---
    shift_types = ["Morning", "Afternoon", "Night"]
    shift_levels = ["L3", "L4", "L6"]
    first_day = datetime(year, month, 1)
    last_day = datetime(year, month, calendar.monthrange(year, month)[1])
    all_dates = pd.date_range(first_day, last_day)

    new_rows = []
    for d in all_dates:
        for stype in shift_types:
            for slevel in shift_levels:
                exists = (
                    (slot_df_month["date"] == d) &
                    (slot_df_month["shiftPeriod"] == stype) &
                    (slot_df_month["shiftLevel"] == slevel)
                ).any()
                if not exists:
                    new_rows.append({
                        "month": f"{year}-{month:02d}",
                        "date": d,
                        "day": d.strftime("%A"),
                        "shiftPeriod": stype,
                        "shiftLevel": slevel,
                        "approvedShift": 0,
                        "isOpen": 0,
                        "remarks": "",
                        "onjobtrain": 0,
                        "nightShift": 1 if stype == "Night" else 0
                    })

    if new_rows:
        slot_df = pd.concat([slot_df, pd.DataFrame(new_rows)], ignore_index=True)
        save_excel_safe(slot_df, SLOT_FILE)
        slot_df_month = slot_df[
            (slot_df["date"].dt.year == year) &
            (slot_df["date"].dt.month == month)
        ].copy()

    # --- Load application dataframe and compute approved shifts ---
    app_df = load_excel_safe(APPLICATION_FILE)
    if not app_df.empty:
        app_df.columns = app_df.columns.str.strip().str.lower()  # lowercase for safety
        app_df["date"] = pd.to_datetime(app_df["date"], errors="coerce")
        if "admindecision" in app_df.columns:
            app_df["approvedshift"] = app_df["admindecision"].apply(
                lambda x: 1 if str(x).lower() == "approved" else 0
            )
            approved_counts = (
                app_df.groupby(["date","shiftperiod","shiftlevel"])["approvedshift"]
                .sum()
                .to_dict()
            )
            # Map approved counts to slot_df_month
            slot_df_month["approvedShift"] = slot_df_month.apply(
                lambda r: approved_counts.get(
                    (r["date"], r["shiftPeriod"], r["shiftLevel"]), 0
                ),
                axis=1
            )
        else:
            # if column missing, default to 0
            slot_df_month["approvedShift"] = 0
    else:
        slot_df_month["approvedShift"] = 0

    # --- Calendar structure (Monday start) ---
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        week_data = []
        for d in week:
            shifts = (
                slot_df_month[slot_df_month["date"] == pd.Timestamp(d)]
                .to_dict("records") if d.month == month else []
            )
            week_data.append({"date": d, "shifts": shifts})
        weeks.append(week_data)

    return render_template(
        "admin_slot_control.html",
        view=view_type,
        month=month,
        year=year,
        weeks=weeks,                       # calendar view
        slots=slot_df_month.to_dict("records"),  # table view
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

    # --- Normalize date (CRITICAL) ---
    target_date = pd.to_datetime(date_str).normalize()
    slot_df["date"] = pd.to_datetime(slot_df["date"], errors="coerce").dt.normalize()

    mask = (
        (slot_df["date"] == target_date) &
        (slot_df["shiftPeriod"] == shiftPeriod) &
        (slot_df["shiftLevel"] == shiftLevel)
    )

    if not mask.any():
        return jsonify({"success": False, "error": "Slot not found"}), 404

    slot_df.loc[mask, "isOpen"] = isOpen
    slot_df.loc[mask, "onjobtrain"] = onjobtrain
    slot_df.loc[mask, "nightShift"] = nightShift
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
    app_df = load_excel_safe(APPLICATION_FILE)
    acc_df = load_excel_safe(ACCOUNT_FILE)

    if app_df.empty or acc_df.empty:
        print("skipping totals update — empty Excel")
        return

    # Normalize
    app_df["id"] = app_df["id"].astype(str)
    app_df["admindecision"] = app_df["admindecision"].astype(str).str.lower()
    app_df["status"] = app_df["status"].astype(str).str.lower()

    acc_df["ID"] = acc_df["ID"].astype(str)

    # Reset totals
    acc_df["totalApprovedShift"] = 0
    acc_df["totalPendingShift"] = 0

    # Count per user
    for user_id in acc_df["ID"]:
        acc_df.loc[acc_df["ID"] == user_id, "totalApprovedShift"] = (
            (app_df["id"] == user_id) &
            (app_df["admindecision"] == "approved")
        ).sum()

        acc_df.loc[acc_df["ID"] == user_id, "totalPendingShift"] = (
            (app_df["id"] == user_id) &
            (app_df["status"] == "pending")
        ).sum()

    save_excel_safe(acc_df, ACCOUNT_FILE)
    print("account.xlsx totals updated")

# --- Eligibility check function ---
def check_booking_eligibility(user, slot):
    """
    Returns (eligible: bool, reason: str)
    Enforces:
        - onjobtrain=1 user can book onjobtrain or onjobtrain+night
        - nightShift=1 user can book onjobtrain, onjobtrain+night, or night
    """
    eligible = True
    reasons = []

    user_onjob = int(user.get("onjobtrain", 0))
    user_night = int(user.get("nightShift", 0))

    slot_onjob = int(slot.get("onjobtrain", 0))
    slot_night = int(slot.get("nightshift", 0))

    if slot_onjob == 1 and slot_night == 0:
        if user_onjob != 1:
            eligible = False
            reasons.append("OJT required")
    elif slot_night == 1 and slot_onjob == 0:
        if user_night != 1:
            eligible = False
            reasons.append("Night shift not eligible")
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

    # Load Excel files
    slot_df = load_excel_safe(SLOT_FILE)
    app_df = load_excel_safe(APPLICATION_FILE)
    rec_df = load_excel_safe(RECORD_FILE)
    app_df.columns = app_df.columns.str.strip()

    # Normalize columns
    slot_df.columns = slot_df.columns.str.strip().str.lower()
    for col in ["isopen", "onjobtrain", "nightshift"]:
        if col not in slot_df.columns:
            slot_df[col] = 0
        slot_df[col] = slot_df[col].fillna(0).astype(int)

    for df in [app_df, rec_df]:
        if not df.empty:
            df.columns = df.columns.str.strip().str.lower()
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.date
            if "id" in df.columns:
                df["id"] = df["id"].astype(str)

    # Normalize slot_df date FIRST (CRITICAL)
    if "date" in slot_df.columns:
        slot_df["date"] = pd.to_datetime(slot_df["date"], errors="coerce").dt.date

    # Filter for current month AND open shifts
    slot_df = slot_df[
        (slot_df["date"].notna()) &
        (slot_df["date"].apply(lambda d: d.year == year and d.month == month)) &
        (slot_df["isopen"] == 1)
    ]

    # Build calendar
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    weeks = []

    for week in cal.monthdatescalendar(year, month):
        days = []
        for d in week:
            day_shifts = []
            if d.month == month:
                shifts = slot_df[slot_df["date"] == d]
                for _, slot in shifts.iterrows():
                    # Eligibility
                    eligible = True
                    reasons = []

                    slot_ojt = int(slot.get("onjobtrain", 0))
                    slot_night = int(slot.get("nightshift", 0))

                    user_ojt = int(user.get("onjobtrain", 0))
                    user_night = int(user.get("nightShift", 0))

                    # Case 1: Night-only slot → ONLY night users
                    if slot_night == 1 and slot_ojt == 0:
                        if user_night != 1:
                            eligible = False
                            reasons.append("Night shift eligibility required")

                    # Case 2: OJT-only slot → OJT OR night users allowed
                    elif slot_ojt == 1 and slot_night == 0:
                        if user_ojt != 1 and user_night != 1:
                            eligible = False
                            reasons.append("OJT or night eligibility required")

                    # Case 3: OJT + Night slot → OJT OR night users allowed
                    elif slot_ojt == 1 and slot_night == 1:
                        if user_ojt != 1 and user_night != 1:
                            eligible = False
                            reasons.append("OJT or night eligibility required")

                    # Case 4: Open slot → everyone allowed
                    # (no check needed)

                    reason = "; ".join(reasons)

                    # Check if already booked
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
            days.append({"date": d, "shifts": day_shifts})
        weeks.append(days)

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
        # -------------------------
        # AUTH
        # -------------------------
        user = session.get("user")
        if not user or user.get("role") != "student coach":
            return jsonify(success=False, error="Unauthorized"), 403

        # -------------------------
        # INPUT
        # -------------------------
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

        # -------------------------
        # LOAD EXCEL FILES
        # -------------------------
        slot_df = load_excel_safe(SLOT_FILE)
        app_df = load_excel_safe(APPLICATION_FILE)

        # -------------------------
        # NORMALIZE SLOT FILE
        # -------------------------
        slot_df.columns = slot_df.columns.str.strip().str.lower()

        if "date" in slot_df.columns:
            slot_df["date"] = pd.to_datetime(
                slot_df["date"], errors="coerce"
            ).dt.date

        for col in ["onjobtrain", "nightshift"]:
            if col not in slot_df.columns:
                slot_df[col] = 0
            slot_df[col] = slot_df[col].fillna(0).astype(int)

        # -------------------------
        # NORMALIZE APPLICATION FILE
        # -------------------------
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
        app_df["date"] = pd.to_datetime(
            app_df["date"], errors="coerce"
        ).dt.date

        # -------------------------
        # FIND SLOT
        # -------------------------
        slot = slot_df[
            (slot_df["date"] == shift_date) &
            (slot_df["shiftperiod"] == shift_period) &
            (slot_df["shiftlevel"] == shift_level)
        ]

        if slot.empty:
            return jsonify(success=False, error="Shift not found"), 404

        slot = slot.iloc[0]

        # -------------------------
        # ELIGIBILITY (UNCHANGED LOGIC)
        # -------------------------
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

        # -------------------------
        # EXISTING APPLICATION
        # -------------------------
        existing_app = app_df[
            (app_df["id"] == sid) &
            (app_df["date"] == shift_date) &
            (app_df["shiftperiod"] == shift_period) &
            (app_df["shiftlevel"] == shift_level)
        ]

        # -------------------------
        # ACTIONS (UNCHANGED LOGIC)
        # -------------------------
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

            save_excel_atomic(app_df, APPLICATION_FILE)
            recalculate_account_shift_totals()

            return jsonify(success=True)

        elif action == "cancel":
            if existing_app.empty:
                return jsonify(success=False, error="No booking found"), 404

            idx = existing_app.index[0]
            current_status = existing_app.iloc[0]["status"].lower()

            if current_status == "pending":
                app_df = app_df.drop(idx)
                save_excel_atomic(app_df, APPLICATION_FILE)
                recalculate_account_shift_totals()
                return jsonify(success=True)

            elif current_status == "approved":
                app_df.at[idx, "cancelrequest"] = 1
                save_excel_atomic(app_df, APPLICATION_FILE)
                recalculate_account_shift_totals()
                return jsonify(
                    success=True,
                    message="Cancel request sent to admin for approval"
                )

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
    # --- Load application data ---
    app_df = load_excel_safe(APPLICATION_FILE)

    # --- Get current month/year or from query params ---
    today = datetime.today()
    month = request.args.get("month", default=today.month, type=int)
    year = request.args.get("year", default=today.year, type=int)

    # --- Prepare month_days for calendar view (Monday-first) ---
    cal = calendar.Calendar(firstweekday=0)  # Monday=0 in Python
    month_days = []
    for week in cal.monthdatescalendar(year, month):
        month_days.append(week)

    # --- If application data is empty, return template safely ---
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
    app_df["id"] = app_df["id"].astype(str)

    # Ensure admin columns exist
    for col in ["admindecision", "adminremarks", "status"]:
        if col not in app_df.columns:
            app_df[col] = ""

    # Normalize date
    app_df["date"] = pd.to_datetime(app_df["date"], errors="coerce")

    # =============================== Merge account.xlsx ===============================
    acc_df = load_excel_safe(ACCOUNT_FILE)
    if not acc_df.empty:
        acc_df.columns = acc_df.columns.str.strip()
        acc_df["ID"] = acc_df["ID"].astype(str)

        # Ensure required account columns
        for col in ["onjobtrain", "nightShift", "totalApprovedShift", "totalPendingShift"]:
            if col not in acc_df.columns:
                acc_df[col] = 0

        # Merge application and account data
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

    # ---------------- Build calendar data ----------------
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

    # ------------------ Pass to template ----------------
    return render_template(
        "admin_shift_application.html",
        application=app_df.to_dict("records"),
        calendar_data=calendar_data,
        today=today.date(),
        month=month,
        year=year,
        month_days=month_days,
        # today=datetime.today().date(),
        datetime=datetime,       # pass datetime to template
        timedelta=timedelta      # pass timedelta to template
    )

# Admin shift application approve reject AJAX update
@app.route("/admin/shift_application/update", methods=["POST"])
def update_shift_application():
    try:
        # ------------------ GET FORM DATA ------------------
        timestamp = request.form.get("timestamp", "").strip()  # original timestamp
        key = request.form.get("key", "").strip()              # composite key: id_date_shift_shiftlevel
        admindecision = request.form.get("admindecision", "").strip()
        adminremarks = request.form.get("adminremarks", "").strip()
        status = request.form.get("status", "").strip()

        if not key:
            return jsonify(success=False, error="Missing key"), 400

        try:
            id_, date_str, shift, level = key.split("_")
        except ValueError:
            return jsonify(success=False, error="Invalid key format"), 400

        # ------------------ LOAD APPLICATION DATA ------------------
        app_df = load_excel_safe(APPLICATION_FILE)
        app_df.columns = [c.strip() for c in app_df.columns]

        # Ensure necessary columns exist
        for col in ["admindecision", "adminremarks", "status", "adminUpdateTimestamp", "timestamp_str"]:
            if col not in app_df.columns:
                app_df[col] = ""

        # Normalize columns for matching
        app_df["id"] = app_df["id"].astype(str)
        app_df["date"] = pd.to_datetime(app_df["date"], errors="coerce")
        app_df["shiftperiod"] = app_df["shiftperiod"].str.lower()
        app_df["shiftlevel"] = app_df["shiftlevel"].str.lower()
        app_df["timestamp_str"] = app_df["timestamp_str"].astype(str).str.strip()

        # ------------------ CREATE MASK ------------------
        mask = (
            (app_df["id"] == id_) &
            (app_df["date"].dt.strftime("%Y-%m-%d") == date_str) &
            (app_df["shiftperiod"] == shift.lower()) &
            (app_df["shiftlevel"] == level.lower())
        )

        if not mask.any():
            return jsonify(success=False, error="Application not found"), 404

        # ------------------ UPDATE ROW ------------------
        app_df.loc[mask, ["admindecision", "adminremarks", "status"]] = [
            admindecision, adminremarks, status
        ]
        app_df.loc[mask, "adminUpdateTimestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Keep original timestamp for logging
        if timestamp:
            app_df.loc[mask, "timestamp_str"] = timestamp

        save_excel_safe(app_df, APPLICATION_FILE)

        # ---- UPDATE ACCOUNT TOTALS ----
        recalculate_account_shift_totals()

        # ------------------ WRITE APPROVED SHIFT TO RECORD ------------------
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
    # Load shift applications
    df = load_excel_safe(APPLICATION_FILE)
    if df.empty:
        return "No shift application data found"

    df.columns = df.columns.str.strip()  # Remove extra spaces

    # Only show approved shifts (case-insensitive)
    df["admindecision"] = df["admindecision"].astype(str)
    df = df[df["admindecision"].str.lower() == "approved"]

    if df.empty:
        return "No approved shifts found"

    # Convert date column to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])  # Drop rows with invalid dates

    # Determine month/year to display
    today = datetime.today()
    month = request.args.get("month", type=int) or today.month
    year = request.args.get("year", type=int) or today.year

    # Calendar weeks (Monday first)
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_days = cal.monthdatescalendar(year, month)

    # Build dictionary of approved shifts per date
    shifts_per_date = {}
    for _, row in df.iterrows():
        day_str = row["date"].strftime("%Y-%m-%d")
        shifts_per_date.setdefault(day_str, []).append({
            "name": row["name"],
            "shiftperiod": str(row.get("shiftperiod", "")).lower(),  # morning/afternoon/night
            "shiftlevel": str(row.get("shiftlevel", "")).lower(),
            "adminremarks": str(row.get("adminremarks", ""))  # show remarks
        })

    # Pass to template
    return render_template(
        "projecthub_duty_calendar.html",
        month=month,
        year=year,
        month_days=month_days,
        shifts_per_date=shifts_per_date,
        today=today.date()
    )

# Upload
@app.route("/admin/upload_excel", methods=["POST"])
def admin_upload_excel():
    file = request.files.get("excel_file")
    if not file:
        flash("No file selected", "error")
        return redirect(url_for("admin_manage_excels"))

    filename = file.filename
    save_path = os.path.join(DATA_FOLDER, filename)
    os.makedirs(DATA_FOLDER, exist_ok=True)
    file.save(save_path)
    flash(f"{filename} uploaded successfully", "success")
    return redirect(url_for("admin_manage_excels"))

# Download
@app.route("/admin/download/<filename>")
def admin_download_excel(filename):
    try:
        return send_from_directory(DATA_FOLDER, filename, as_attachment=True)
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