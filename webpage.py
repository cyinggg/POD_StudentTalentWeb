# Basic Flask App Setup
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
import os
import pandas as pd
from calendar import monthrange, Calendar
from datetime import datetime, date, timedelta
import calendar

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
                        (rec_df["ID"] == sid) &
                        (rec_df["date"] == d) &
                        (rec_df["shiftPeriod"] == slot["shiftperiod"]) &
                        (rec_df["shiftLevel"] == slot["shiftlevel"])
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
    user = session.get("user")
    if not user or user.get("role") != "student coach":
        return jsonify(success=False, error="Unauthorized"), 403

    date_raw = request.form.get("date")
    shift_period = request.form.get("shiftperiod")
    shift_level = request.form.get("shiftlevel")
    action = request.form.get("action")

    if not all([date_raw, shift_period, shift_level, action]):
        return jsonify(success=False, error="Missing data"), 400

    shift_date = pd.to_datetime(date_raw).date()
    sid = str(user["id"])

    # Load Excel files
    slot_df = load_excel_safe(SLOT_FILE)
    app_df = load_excel_safe(APPLICATION_FILE)

    # Normalize
    slot_df.columns = slot_df.columns.str.strip().str.lower()
    if "date" in slot_df.columns:
        slot_df["date"] = pd.to_datetime(slot_df["date"], errors="coerce").dt.date
    app_df.columns = app_df.columns.str.strip().str.lower()
    if "date" in app_df.columns:
        app_df["date"] = pd.to_datetime(app_df["date"], errors="coerce").dt.date
    if "id" in app_df.columns:
        app_df["id"] = app_df["id"].astype(str)

    # Get shift
    slot = slot_df[
        (slot_df["date"] == shift_date) &
        (slot_df["shiftperiod"] == shift_period) &
        (slot_df["shiftlevel"] == shift_level)
    ]
    if slot.empty:
        return jsonify(success=False, error="Shift not found"), 404
    slot = slot.iloc[0]

    # Check eligibility
    slot_ojt = int(slot.get("onjobtrain", 0))
    slot_night = int(slot.get("nightshift", 0))

    user_ojt = int(user.get("onjobtrain", 0))
    user_night = int(user.get("nightShift", 0))

    eligible = True
    error_msg = ""

    # Night-only slot
    if slot_night == 1 and slot_ojt == 0:
        if user_night != 1:
            eligible = False
            error_msg = "Night shift eligibility required"

    # OJT-only slot
    elif slot_ojt == 1 and slot_night == 0:
        if user_ojt != 1 and user_night != 1:
            eligible = False
            error_msg = "OJT or night eligibility required"

    # OJT + Night slot
    elif slot_ojt == 1 and slot_night == 1:
        if user_ojt != 1 and user_night != 1:
            eligible = False
            error_msg = "OJT or night eligibility required"

    if not eligible:
        return jsonify(success=False, error=error_msg), 403

    # Existing application
    existing_app = app_df[
        (app_df["id"] == sid) &
        (app_df["date"] == shift_date) &
        (app_df["shiftperiod"] == shift_period) &
        (app_df["shiftlevel"] == shift_level)
    ]

    # --- Perform action ---
    if action == "book":
        if not existing_app.empty:
            return jsonify(success=False, error="You already booked this shift"), 400
        new_app = {
            "timestamp": datetime.now(),
            "id": user["id"],
            "name": user["name"],
            "month": shift_date.strftime("%Y-%m"),
            "date": shift_date,
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
        return jsonify(success=True)

    elif action == "cancel":
        if existing_app.empty:
            return jsonify(success=False, error="No booking found"), 404

        current_status = existing_app.iloc[0]["status"].lower()
        idx = existing_app.index[0]

        if current_status == "pending":
            # Remove pending application
            app_df = app_df.drop(idx)
            save_excel_safe(app_df, APPLICATION_FILE)
            return jsonify(success=True)
        elif current_status == "approved":
            # Mark cancel request for admin approval
            app_df.at[idx, "cancelrequest"] = 1
            save_excel_safe(app_df, APPLICATION_FILE)
            return jsonify(success=True, message="Cancel request sent to admin for approval")
        else:
            return jsonify(success=False, error="Cannot cancel this shift"), 400

    else:
        return jsonify(success=False, error="Invalid action"), 400

# Admin apporval into shift_record auto write function
def write_shift_record_if_not_exists(application_row):
    record_df = load_excel_safe(RECORD_FILE)

    # Check duplicate
    duplicate = record_df[
        (record_df["ID"] == application_row["ID"]) &
        (record_df["date"] == application_row["date"]) &
        (record_df["shiftPeriod"] == application_row["shiftPeriod"])
    ]

    if not duplicate.empty:
        return  # already written, DO NOTHING

    new_index = len(record_df) + 1

    new_row = {
        "indexShiftVerify": new_index,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ID": application_row["ID"],
        "name": application_row["name"],
        "month": application_row["month"],
        "date": application_row["date"],
        "day": application_row["day"],
        "shiftPeriod": application_row["shiftPeriod"],
        "shiftLevel": application_row["shiftLevel"],
        "clockIn": "",
        "clockOut": "",
        "remarks": ""
    }

    record_df = pd.concat([record_df, pd.DataFrame([new_row])], ignore_index=True)
    save_excel_safe(record_df, RECORD_FILE)

# Admin approval route Flask
@app.route("/admin/approve_shift", methods=["POST"])
def approve_shift():
    row_index = int(request.form["row_index"])
    decision = request.form["decision"]  # Approved / Rejected
    remarks = request.form.get("remarks", "").strip()

    app_df = load_excel_safe(APPLICATION_FILE)

    # Update application
    app_df.loc[row_index, "adminDecision"] = decision
    app_df.loc[row_index, "status"] = decision
    app_df.loc[row_index, "adminRemarks"] = remarks

    save_excel_safe(app_df, APPLICATION_FILE)

    # Auto-write ONLY if approved
    if decision == "Approved":
        write_shift_record_if_not_exists(app_df.loc[row_index])

    return redirect(url_for("admin_home"))

# Admin review and decision
# @app.route("/admin/review", methods=["GET", "POST"])
# def admin_review():
#     if "user" not in session or session["user"]["role"] != "admin":
#         return redirect(url_for("admin_login"))

#     df = load_excel_safe(APPLICATION_FILE)

#     if request.method == "POST":
#         index = int(request.form["index"])
#         decision = request.form["adminDecision"]
#         remarks = request.form["adminRemarks"]

#         # Update the application row
#         if index >= 0 and index < len(df):
#             df.at[index, "adminDecision"] = decision
#             df.at[index, "adminRemarks"] = remarks
#             # Automatically update status
#             if decision.lower() in ["approved", "excuse in advance", "excuse with valid reason"]:
#                 df.at[index, "status"] = "Approved"
#             elif decision.lower() in ["rejected", "cannot make it"]:
#                 df.at[index, "status"] = "Rejected"

#             # Save applications
#             save_excel_safe(df, APPLICATION_FILE)

#             # Recalculate approved counts live
#             update_approved_counts()

#         return redirect(url_for("admin_review"))

#     # GET request — show all pending or recently applied shifts
#     df = df.fillna("")  # avoid NaN display
#     applications = df.to_dict(orient="records")

#     return render_template("admin_review.html", applications=applications)

# Student coach application
@app.route("/student/my_applications")
def student_my_applications():
    if "user" not in session or session["user"]["role"] != "student":
        return redirect(url_for("student_login"))

    user = session["user"]
    df = load_excel_safe(APPLICATION_FILE)
    df = df.fillna("")  # replace NaN with empty string for display

    # Filter applications by logged-in student
    student_apps = df[df["ID"].astype(str) == str(user["id"])].to_dict(orient="records")

    return render_template("student_my_applications.html", applications=student_apps)

# Count shifts helper
def count_student_shifts(user_id, df, target_date):
    """
    Returns weekly_count, monthly_count for a given student and date.
    Only counts Approved or Pending applications.
    """
    # Filter student
    student_df = df[df["ID"].astype(str) == str(user_id)]

    # Only consider Approved or Pending
    student_df = student_df[student_df["status"].isin(["Pending", "Approved"])]

    # Monthly count
    month_str = target_date.strftime("%Y-%m")
    monthly_count = student_df[student_df["month"] == month_str].shape[0]

    # Weekly count (Monday-Sunday)
    target_week_start = target_date - timedelta(days=target_date.weekday())
    target_week_end = target_week_start + timedelta(days=6)

    weekly_count = student_df[
        (pd.to_datetime(student_df["date"]) >= target_week_start) &
        (pd.to_datetime(student_df["date"]) <= target_week_end)
    ].shape[0]

    return weekly_count, monthly_count

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
                "ID": shift["ID"],
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

    # Only show approved shifts
    df = df[df["adminDecision"] == "Approved"]

    # Convert date column to datetime
    df["date"] = pd.to_datetime(df["date"])

    # Determine month/year to display from query parameters or default to current month
    month = request.args.get("month")
    year = request.args.get("year")

    today = datetime.today()
    if not month or not year:
        month = today.month
        year = today.year
    else:
        month = int(month)
        year = int(year)

    # Create calendar for the month (weeks start on Monday)
    cal = Calendar(firstweekday=calendar.MONDAY)  # Monday=0
    month_days = cal.monthdatescalendar(year, month)

    # Build dictionary with shifts per date
    shifts_per_date = {}
    for _, row in df.iterrows():
        day_str = row["date"].strftime("%Y-%m-%d")
        if day_str not in shifts_per_date:
            shifts_per_date[day_str] = []
        shifts_per_date[day_str].append({
            "name": row["name"],
            "shiftPeriod": row["shiftPeriod"],  # morning / afternoon / night
            "shiftLevel": row["shiftLevel"]
        })

    return render_template(
        "projecthub_duty_calendar.html",
        month=month,
        year=year,
        month_days=month_days,
        shifts_per_date=shifts_per_date
    )

# Update approvedShift counts in slot_control.xlsx from shift_application.xlsx
def update_approved_counts():
    if not os.path.exists(SLOT_FILE) or not os.path.exists(APPLICATION_FILE):
        return

    df_slot = load_excel_safe(SLOT_FILE)
    df_app = load_excel_safe(APPLICATION_FILE).fillna("")

    df_app = df_app[df_app["adminDecision"].str.lower() == "approved"]

    for idx, row in df_slot.iterrows():
        count = df_app[
            (df_app["date"] == row["date"]) &
            (df_app["shiftPeriod"] == row["shiftPeriod"]) &
            (df_app["shiftLevel"] == row["shiftLevel"])
        ].shape[0]

        df_slot.at[idx, "approvedShift"] = count

    save_excel_safe(df_slot, SLOT_FILE)

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