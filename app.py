from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import openpyxl
from datetime import datetime, timedelta
from pytz import timezone
import calendar
import os
import pandas as pd

app = Flask(__name__)

# ==========================
# SESSION CONFIGURATION
# ==========================
app.secret_key = "change_this_to_a_random_secret_in_production"
app.permanent_session_lifetime = timedelta(minutes=30)

# ==========================
# FILE PATHS
# ==========================
DATA_DIR = "data"
STUDENTCOACH_FILE = os.path.join(DATA_DIR, "StudentCoach.xlsx")
APPLICATIONS_FILE = os.path.join(DATA_DIR, "applications.xlsx")
NOTIFICATIONS_FILE = os.path.join(DATA_DIR, "notifications.xlsx")
COMMITTEE_FILE = os.path.join(DATA_DIR, "committee_calendar.xlsx")

# ==========================
# CONTEXT PROCESSORS
# ==========================
@app.context_processor
def inject_current_time():
    return {'current_time': datetime.now()}

# ==========================
# HELPER FUNCTIONS
# ==========================
def load_students_dict():
    """Load students into dict keyed by Student ID"""
    students = {}
    if not os.path.exists(STUDENTCOACH_FILE):
        return students

    wb = openpyxl.load_workbook(STUDENTCOACH_FILE)
    ws = wb.active
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[1]:
            continue
        sid = str(row[1]).strip()
        div = str(row[9]).strip() if row[9] else ""
        students[sid] = {
            "full_name": str(row[0]).strip() if row[0] else "",
            "student_id": sid,
            "cluster": str(row[2]).strip() if row[2] else "",
            "degree": str(row[3]).strip() if row[3] else "",
            "current_year": str(row[4]).strip() if row[4] else "",
            "contact": str(row[5]).strip() if row[5] else "",
            "telegram": str(row[6]).strip() if row[6] else "",
            "can_id": str(row[7]).strip() if row[7] else "",
            "birthday": str(row[8]).strip() if row[8] else "",
            "division": div
        }
    return students

def validate_contact(student_id, contact):
    """Validate student contact number"""
    students = load_students_dict()
    student = students.get(student_id)
    if not student:
        return False
    # Remove spaces, dashes, +65 prefix etc.
    input_contact = ''.join(filter(str.isdigit, contact))
    stored_contact = ''.join(filter(str.isdigit, student.get("contact", "")))
    return input_contact == stored_contact

# Normalize contact number
def normalize_contact(v):
    return "".join(filter(str.isdigit, str(v)))

# Normalize division
def normalize_contact(v):
    return str(v).strip()

def ensure_applications_file():
    # Ensure applications.xlsx exists
    if os.path.exists(APPLICATIONS_FILE):
        return

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "Timestamp", "Division", "StudentID", "StudentName",
        "Date", "ShiftType", "SlotLevel", "SlotNumber",
        "Preference", "Type", "Details",
        "Status", "WaitingCount",
        "AdminDecision", "AdminRemark", "DecisionTimestamp"
    ])
    wb.save(APPLICATIONS_FILE)

def ensure_committee_file():
    if os.path.exists(COMMITTEE_FILE):
        return
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "Timestamp","Division","StudentID","StudentName","Date",
        "Type","Details","Status"
    ])
    wb.save(COMMITTEE_FILE)

def append_application(record):
    ensure_applications_file()
    wb = openpyxl.load_workbook(APPLICATIONS_FILE)
    ws = wb.active
    ws.append(record)
    wb.save(APPLICATIONS_FILE)

def append_committee_entry(record):
    ensure_committee_file()
    wb = openpyxl.load_workbook(COMMITTEE_FILE)
    ws = wb.active
    ws.append(record)
    wb.save(COMMITTEE_FILE)

def update_application_status(date, shift, level, slot, student_id, status):
    if status not in {"Approved", "Rejected"}:
        raise ValueError(f"Invalid status: {status}")
    ensure_applications_file()
    wb = openpyxl.load_workbook(APPLICATIONS_FILE)
    ws = wb.active
    found = False
    approved_exists = False
    # First pass: check if Approved already exists
    for row in ws.iter_rows(min_row=2):
        if (
            row[1].value == "Student Coach" and
            row[4].value == date and
            row[5].value == shift and
            row[6].value == level and
            row[7].value == slot
        ):
            if str(row[11].value).strip() == "Approved":
                approved_exists = True
    # Block duplicate approvals
    if status == "Approved" and approved_exists:
        return False
    # Second pass: update target row
    for row in ws.iter_rows(min_row=2):
        if (
            row[1].value == "Student Coach" and
            row[2].value == student_id and
            row[4].value == date and
            row[5].value == shift and
            row[6].value == level and
            row[7].value == slot
        ):
            row[11].value = status
            found = True
            break
    if found:
        wb.save(APPLICATIONS_FILE)
    return found

def update_application_decision(
    date, shift, level, slot, student_id,
    decision, remark=""
):
    ensure_applications_file()
    wb = openpyxl.load_workbook(APPLICATIONS_FILE)
    ws = wb.active
    found = False

    for row in ws.iter_rows(min_row=2):
        if (
            row[1].value == "Student Coach" and
            row[2].value == student_id and
            row[4].value == date and
            row[5].value == shift and
            row[6].value == level and
            row[7].value == slot
        ):
            # Status update (update_application_status logic preserved)
            if decision == "Approved":
                row[11].value = "Approved"
            elif decision == "Rejected":
                row[11].value = "Rejected"
            else:
                row[11].value = "Approved"

            # New fields
            row[13].value = decision
            row[14].value = remark
            row[15].value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            found = True
            break

    if found:
        wb.save(APPLICATIONS_FILE)
    return found

def load_committee_entries(division):
    ensure_committee_file()
    wb = openpyxl.load_workbook(COMMITTEE_FILE)
    ws = wb.active
    entries = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[1] != division:
            continue
        entries.append({
            "timestamp": row[0],
            "division": row[1],
            "student_id": row[2],
            "student_name": row[3],
            "date": row[4],
            "type": row[5],
            "details": row[6],
            "status": row[7]
        })
    return entries

# ==========================
# ROUTES
# ==========================
@app.route("/")
def start_page():
    return render_template("start.html")

@app.route("/select_division")
def select_division():
    divisions = [
        "POD Staff and Administration",
        "Student Talent Committee and Ambassador",
        "Student Coach",
        "Student Technologist",
        "Student Project Engineer",
        "Student Project Executive"
    ]
    # session.clear()
    return render_template("select_division.html", divisions=divisions)

@app.route("/start_login/<path:division>")
def start_login(division):
    session.clear()
    session["division"] = division
    return render_template("login.html", division=division)

@app.route("/verify_id", methods=["POST"])
def verify_id():
    student_id = request.form["student_id"].strip()
    students = load_students_dict()
    student = students.get(student_id)

    if not student:
        return render_template(
            "login.html",
            division=session.get("division"),
            error="Invalid Student ID"
        )

    session["student_id"] = student_id
    session["student_name"] = student.get("full_name", "")

    return render_template(
        "login.html",
        division=session.get("division"),
        student_name=session.get("student_name")
    )

@app.route("/login", methods=["POST"])
def login():
    if "student_id" not in session:
        return redirect(url_for("select_division"))

    contact_input = request.form.get("contact", "").strip()

    students = load_students_dict()
    student = students.get(session["student_id"])

    if not student:
        return redirect(url_for("select_division"))

    # ---- NORMALIZE CONTACT ----
    excel_contact = "".join(filter(str.isdigit, str(student["contact"])))
    input_contact = "".join(filter(str.isdigit, contact_input))

    if excel_contact != input_contact:
        return render_template(
            "login.html",
            division=session.get("division"),
            student_name=session.get("student_name"),
            error="Invalid contact number"
        )

    # ---- SET ROLE FROM EXCEL (NOT FROM URL) ----
    role = str(student.get("division", "")).strip()
    session["role"] = role

    print("LOGIN OK → ROLE:", role)

    # ---- REDIRECT BY ROLE ----
    if role == "POD Staff and Administration":
        return redirect(url_for("admin_home"))

    if role in [
        "Student Coach",
        "Student Talent Committee and Ambassador"
    ]:
        return redirect(url_for("calendar_view"))

    return redirect(url_for("select_division"))

@app.route("/calendar")
def calendar_view():
    # Not logged in go back to division selection
    if "student_id" not in session:
        return redirect(url_for("select_division"))

    # Admin is NOT allowed to see calendar force admin home
    if session.get("role") == "POD Staff and Administration":
        return redirect(url_for("admin_home"))

    # Only now prepare calendar data
    sg = datetime.now(timezone("Asia/Singapore"))
    year = sg.year
    month = sg.month
    month_name = calendar.month_name[month]
    cal = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)

    role = session.get("role", "")
    is_pod = False  # admin never reaches here
    is_committee = role == "Student Talent Committee and Ambassador"
    is_coach = role == "Student Coach"

    return render_template(
        "calendar.html",
        year=year,
        month=month,
        month_name=month_name,
        cal=cal,
        role=role,
        is_pod=is_pod,
        is_committee=is_committee,
        is_coach=is_coach,
        student_name=session.get("student_name")
    )

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("select_division"))

@app.route("/projecthub")
def projecthub_home():
    return render_template("projecthub_home.html")

@app.route("/projecthub/student_coach_schedule")
def projecthub_duty_calendar():

    ensure_applications_file()  # Make sure applications.xlsx exists

    # Load Excel into DataFrame
    df = pd.read_excel(APPLICATIONS_FILE)

    # Build approved_bookings dict for template
    approved_bookings = {}

    for _, row in df.iterrows():
        # Only consider rows where AdminDecision == "Approved"
        if str(row.get("AdminDecision", "")).strip() != "Approved":
            continue

        date_str = row.get("Date")
        if not isinstance(date_str, str):
            # Ensure date is in YYYY-MM-DD format
            date_str = pd.to_datetime(date_str).strftime("%Y-%m-%d")

        shift = str(row.get("ShiftType"))
        level = str(row.get("SlotLevel"))
        slot = int(row.get("SlotNumber", 1))
        student_name = str(row.get("StudentName"))

        key = (date_str, shift, level, slot)
        approved_bookings[key] = student_name

    # Get current month/year for calendar display
    sg = datetime.now()
    year = sg.year
    month = sg.month
    month_name = calendar.month_name[month]
    cal = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)

    # Extract unique slot levels from current approved bookings for display
    levels = sorted(df["SlotLevel"].dropna().unique())

    return render_template(
        "projecthub_duty_calendar.html",
        approved_bookings=approved_bookings,
        year=year,
        month=month,
        month_name=month_name,
        cal=cal,
        levels=levels  # pass levels for template loop
    )

# ==========================
# COMMITTEE APIs
# ==========================
@app.route("/api/committee/calendar")
def api_committee_calendar():
    if session.get("role") not in ["Student Talent Committee and Ambassador",
                                   "POD Staff and Administration"]:
        return jsonify([])
    return jsonify(load_committee_entries(session.get("role")))

@app.route("/api/committee/submit", methods=["POST"])
def api_committee_submit():
    if session.get("role") != "Student Talent Committee and Ambassador":
        return jsonify({"message": "Unauthorized"}), 403
    data = request.get_json()
    entry_type = data.get("type")
    status = "Approved" if entry_type == "Availability" else "Pending"
    ts = datetime.now(timezone("Asia/Singapore")).strftime("%Y-%m-%d %H:%M:%S")
    record = [
        ts,
        session.get("role"),
        session.get("student_id"),
        session.get("student_name"),
        data.get("date"),
        entry_type,
        data.get("details", ""),
        status
    ]
    append_committee_entry(record)
    return jsonify({"message": f"{entry_type} submitted ({status})"})

# ==========================
# STUDENT COACH APIs
# ==========================
@app.route("/api/applications")
def api_applications():
    ensure_applications_file()
    wb = openpyxl.load_workbook(APPLICATIONS_FILE)
    ws = wb.active
    rows = []
    waiting_map = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[1] != "Student Coach":
            continue
        if r[11] != "Pending":
            continue
        key = (r[4], r[5], r[6], r[7])
        waiting_map[key] = waiting_map.get(key, 0) + 1
    for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if row[1] != "Student Coach":
            continue
        status = row[11]
        rows.append({
            "timestamp": row[0],
            "division": row[1],
            "student_id": row[2],
            "student_name": row[3],
            "date": row[4],
            "shift_type": row[5],
            "slot_level": row[6],
            "slot_number": row[7],
            "preference": row[8],
            "type": row[9],
            "details": row[10],
            "status": status,
            "waiting_count": waiting_map.get((row[4], row[5], row[6], row[7]), 0)
        })
    return jsonify(rows)

@app.route("/api/submit", methods=["POST"])
def api_submit():
    if session.get("role") != "Student Coach":
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    data = request.get_json()
    date = data.get("date")
    shift_type = data.get("shift_type")
    slot_level = data.get("slot_level")
    slot_number = data.get("slot_number")
    if not all([date, shift_type, slot_level, slot_number]):
        return jsonify({"status": "error", "message": "Missing data"}), 400
    ensure_applications_file()
    wb = openpyxl.load_workbook(APPLICATIONS_FILE)
    ws = wb.active
    current_pref = 1
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[1] == "Student Coach" and row[2] == session.get("student_id") and row[4][:7] == date[:7] and row[11] in ["Pending", "Approved"]:
            current_pref = max(current_pref, int(row[8])+1)
    if current_pref > 3:
        return jsonify({"status": "error", "message": "You can only submit up to 3 shifts per month."}), 400
    ts = datetime.now(timezone("Asia/Singapore")).strftime("%Y-%m-%d %H:%M:%S")
    record = [
        ts, "Student Coach", session.get("student_id"), session.get("student_name"),
        date, shift_type, slot_level, slot_number, current_pref, "Shift", "", "Pending"
    ]
    ws.append(record)
    wb.save(APPLICATIONS_FILE)
    return jsonify({"status": "success", "message": f"Shift booked (Pending) — Preference {current_pref}", "preference": current_pref})

@app.route("/projecthub/my_bookings")
def my_bookings():
    return render_template("my_bookings.html")

# ==========================
# ADMIN ROUTES
# ==========================
@app.route("/admin_home")
def admin_home():
    if session.get("role") != "POD Staff and Administration":
        return redirect(url_for("select_division"))
    return render_template("admin_home.html")

@app.route("/admin_approvals")
def admin_approvals():
    if session.get("role") != "POD Staff and Administration":
        return redirect(url_for("select_division"))
    return render_template("admin_approvals.html")

@app.route("/api/admin/pending_applications")
def admin_pending_applications():
    if session.get("role") != "POD Staff and Administration":
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    ensure_applications_file()
    wb = openpyxl.load_workbook(APPLICATIONS_FILE)
    ws = wb.active
    applications = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[1] != "Student Coach":
            continue
        applications.append({
            "timestamp": row[0],
            "division": row[1],
            "student_id": row[2],
            "student_name": row[3],
            "date": row[4],
            "shift_type": row[5],
            "slot_level": row[6],
            "slot_number": row[7],
            "preference": row[8],
            "type": row[9],
            "details": row[10],
            "status": row[11],
            "waiting_count": row[12],
            "admin_decision": row[13] if len(row) > 13 else "",
            "admin_remark": row[14] if len(row) > 14 else ""
        })
    return jsonify(applications)

@app.route("/api/admin/approve", methods=["POST"])
def admin_approve():
    if session.get("role") != "POD Staff and Administration":
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    data = request.get_json()
    success = update_application_status(
        date=data["date"],
        shift=data["shift"],
        level=data["level"],
        slot=data["slot"],
        student_id=data["student_id"],
        status="Approved"
    )
    return jsonify({"status": "ok" if success else "not_found"})

@app.route("/api/admin/reject", methods=["POST"])
def admin_reject():
    if session.get("role") != "POD Staff and Administration":
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    data = request.get_json()
    success = update_application_status(
        date=data["date"],
        shift=data["shift"],
        level=data["level"],
        slot=data["slot"],
        student_id=data["student_id"],
        status="Rejected"
    )
    return jsonify({"status": "ok" if success else "not_found"})

@app.route("/api/admin/decide", methods=["POST"])
def admin_decide():
    if session.get("role") != "POD Staff and Administration":
        return jsonify({"status":"error", "message":"Unauthorized"}), 403

    data = request.get_json()
    date = data.get("date")
    shift = data.get("shift")
    level = data.get("level")
    slot = data.get("slot")
    student_id = data.get("student_id")
    # Use 'status' if sent by JS, fallback to 'decision'
    decision = data.get("status") or data.get("decision")
    remark = data.get("remark", "")

    ensure_applications_file()
    wb = openpyxl.load_workbook(APPLICATIONS_FILE)
    ws = wb.active

    found = False
    for row in ws.iter_rows(min_row=2):
        if (
            row[1].value == "Student Coach" and
            str(row[2].value) == str(student_id) and
            str(row[4].value) == str(date) and
            row[5].value == shift and
            row[6].value == level and
            str(row[7].value) == str(slot)
        ):
            # Update AdminDecision & Remark
            row[13].value = decision  # AdminDecision column
            row[14].value = remark    # AdminRemark column

            # Update Status only if Approved / Rejected (quick action effect)
            if decision in ["Approved", "Rejected"]:
                row[11].value = decision # Status column
            found = True
            break

    if found:
        wb.save(APPLICATIONS_FILE)
        return jsonify({"status":"ok"})
    else:
        return jsonify({"status":"not_found", "message":"Row not found"})

def admin_reallocate():
    if session.get("role") != "POD Staff and Administration":
        return jsonify({"status":"error","message":"Unauthorized"}),403

    data = request.get_json()
    date = data.get("date")
    shift = data.get("shift")
    level = data.get("level")
    slot = data.get("slot")
    student_id = data.get("student_id")

    # Update the booking to Approved even if there is already an approved booking for the same slot
    ensure_applications_file()
    wb = openpyxl.load_workbook(APPLICATIONS_FILE)
    ws = wb.active

    found = False
    for row in ws.iter_rows(min_row=2):
        if (
            row[1].value == "Student Coach" and
            row[2].value == student_id and
            row[4].value == date and
            row[5].value == shift and
            row[6].value == level and
            row[7].value == slot
        ):
            row[11].value = "Approved"  # Status
            row[13].value = "Approved via Reallocate"  # Admin Decision or Remark column
            found = True
            break
    if found:
        wb.save(APPLICATIONS_FILE)
        return jsonify({"status":"ok"})
    return jsonify({"status":"not_found"})

# ==========================
# RUN
# ==========================
if __name__ == "__main__":
    ensure_applications_file()
    ensure_committee_file()
    app.run(host="127.0.0.1", port=5000, debug=True)
