# app.py
# Flask web app for POD_StudentTalent (updated/fixed version)
# - division selection
# - login using StudentTalent.xlsx (Student ID + Contact)
# - calendar per-division (current month)
# - clickable dates: submit event application or availability
# - admin page for POD Staff and Administration to view pending applications

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import openpyxl
from datetime import datetime
from pytz import timezone
import calendar
import os

app = Flask(__name__)
app.secret_key = "change_this_to_a_random_secret_in_production"

# Add global context processor
@app.context_processor
def inject_current_time():
    return {'current_time': datetime.now()}

# ---------- File paths ----------
DATA_DIR = "data"
STUDENTCOACH_FILE = os.path.join(DATA_DIR, "StudentCoach.xlsx")
APPLICATIONS_FILE = os.path.join(DATA_DIR, "applications.xlsx")
NOTIFICATIONS_FILE = os.path.join(DATA_DIR, "notifications.xlsx")
COMMITTEE_FILE = os.path.join(DATA_DIR, "committee_calendar.xlsx")

# ========================
# HELP FUNCTIONS
# ========================
def load_students_dict():
    """
    Load students from StudentTalent.xlsx into a dict keyed by Student ID.
    Returns: { "2400788": {"full_name": "...", "student_id":"...", "contact":"...", "division":"..."} ...}
    This function now reads the Division column (assumed to be the 10th column, index 9).
    """
    students = {}
    if not os.path.exists(STUDENTCOACH_FILE):
        return students

    wb = openpyxl.load_workbook(STUDENTCOACH_FILE)
    ws = wb.active
    # Expect headers in row 1 as specified previously. Adjust indices if your sheet layout differs.
    for row in ws.iter_rows(min_row=2, values_only=True):
        # Columns expected:
        # 0: Full Name
        # 1: Student ID
        # 2: Cluster
        # 3: Degree
        # 4: Current Year
        # 5: Contact
        # 6: Telegram Handle
        # 7: SIT CAN ID
        # 8: Birthday
        # 9: Division  <-- NEW
        if not row or not row[1]:
            continue
        sid = str(row[1]).strip()
        # read division (if present)
        div = ""
        try:
            div = str(row[9]).strip() if row[9] is not None else ""
        except Exception:
            div = ""
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

def ensure_committee_file():
    if os.path.exists(COMMITTEE_FILE):
        return
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "Timestamp",
        "Division",
        "StudentID",
        "StudentName",
        "Date",
        "Type",
        "Details",
        "Status"
    ])
    wb.save(COMMITTEE_FILE)

# For Admin Page — POD Staff and Administration
ALLOWED_STATUSES = {"Pending", "Approved", "Rejected"}
def update_application_status(date, shift, level, slot, student_id, status):

    if status not in {"Approved", "Rejected"}:
        raise ValueError(f"Invalid admin status update: {status}")

    ensure_applications_file()
    wb = openpyxl.load_workbook(APPLICATIONS_FILE)
    ws = wb.active

    found = False
    approved_exists = False

    # ---------- First pass: detect existing Approved ----------
    for row in ws.iter_rows(min_row=2):
        if (
            row[1].value == "Student Coach" and
            row[4].value == date and
            row[5].value == shift and
            row[6].value == level and
            row[7].value == slot
        ):
            current_status = str(row[11].value).strip()

            if current_status not in ALLOWED_STATUSES:
                raise ValueError(f"Invalid status in Excel: {current_status}")

            if current_status == "Approved":
                approved_exists = True

    # ---------- Block second approval ----------
    if status == "Approved" and approved_exists:
        return False

    # ---------- Second pass: update target row ----------
    for row in ws.iter_rows(min_row=2):
        if (
            row[1].value == "Student Coach" and
            row[2].value == student_id and
            row[4].value == date and
            row[5].value == shift and
            row[6].value == level and
            row[7].value == slot
        ):
            current_status = str(row[11].value).strip()

            if current_status not in ALLOWED_STATUSES:
                raise ValueError(f"Invalid status in Excel: {current_status}")

            row[11].value = status
            found = True
            break

    if found:
        wb.save(APPLICATIONS_FILE)

    return found

def load_pending_applications():
    """Return a list of pending Student Coach applications"""
    wb = openpyxl.load_workbook(APPLICATIONS_FILE)
    ws = wb.active
    pending = []
    for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        division = row[1]
        status = row[10]  # Assuming 'Status' is column K / index 10
        if division == "Student Coach" and status == "Pending":
            pending.append({
                "row_index": idx,  # needed to update Excel
                "date": row[4],
                "shift_type": row[5],
                "slot_level": row[6],
                "slot_number": row[7],
                "student_id": row[2],
                "student_name": row[3],
            })
    return pending

# Read Committee entries for calendar display
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

def ensure_applications_file():
    """
    Create the applications file if it does not exist, with header row.
    Columns: Timestamp,Division,StudentID,StudentName,Date,ShiftType,SlotLevel,SlotNumber,Type,Details,Status
    Type is "Event" or "Availability". Status starts as "Pending".
    """
    if os.path.exists(APPLICATIONS_FILE):
        return
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "Timestamp","Division","StudentID","StudentName","Date",
        "ShiftType","SlotLevel","SlotNumber",
        "Preference","Type","Details","Status"
        ])
    wb.save(APPLICATIONS_FILE)

def append_application(record):
    """
    Append a record (list) to applications.xlsx
    """
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

# ========================
# ROUTES
# ========================
@app.route("/")
def select_division():
    divisions = [
        "POD Staff and Administration",
        "Student Talent Committee and Ambassador",
        "Student Coach",
        "Student Technologist",
        "Student Project Engineer",
        "Student Project Executive"
    ]
    # Clear any previous session
    session.pop("division", None)
    session.pop("student_id", None)
    session.pop("student_name", None)
    session.pop("role", None)
    return render_template("select_division.html", divisions=divisions)

@app.route("/start_login/<path:division>", methods=["GET"])
def start_login(division):
    session["division"] = division
    return render_template("login.html", division=division, student_name=None, error=None)

@app.route("/verify_id", methods=["POST"])
def verify_id():
    student_id = request.form.get("student_id", "").strip()
    division = session.get("division", None)
    students = load_students_dict()
    student = students.get(student_id)
    if not student:
        # Not found — show login again with error
        return render_template("login.html", division=division, student_name=None, error="Student ID not found in StudentTalent.xlsx")
    # Found: render login page again but with name filled and ask for contact
    session["temp_student_id"] = student_id
    session["temp_student_name"] = student["full_name"]
    return render_template("login.html", division=division, student_name=student["full_name"], error=None)

@app.route("/login", methods=["POST"])
def login():
    division = session.get("division", None)
    # Get stored temp_student_id
    temp_id = session.get("temp_student_id", None)
    if not temp_id:
        return redirect(url_for("select_division"))

    contact_input = request.form.get("contact", "").strip()
    students = load_students_dict()
    student = students.get(temp_id)
    if not student:
        return render_template("login.html", division=division, student_name=None, error="Student not found (unexpected).")

    # Compare contact (exact match)
    if contact_input == student["contact"]:
        # Successful login
        session["student_id"] = student["student_id"]
        session["student_name"] = student["full_name"]
        session["role"] = division  # role stored as division

        # remove temp
        session.pop("temp_student_id", None)
        session.pop("temp_student_name", None)

        # Redirect based on role
        if division == "POD Staff and Administration":
            return redirect(url_for("admin_home"))
        else:
            return redirect(url_for("calendar_view"))
    else:
        # contact mismatch
        return render_template("login.html", division=division, student_name=student["full_name"], error="Contact does not match record.")

@app.route("/calendar")
def calendar_view():
    # Ensure user is logged in
    if "student_id" not in session:
        return redirect(url_for("select_division"))

    # Determine year & month (Singapore timezone)
    sg = datetime.now(timezone("Asia/Singapore"))
    year = sg.year
    month = sg.month
    month_name = calendar.month_name[month]

    # Build month calendar as matrix of weeks (Monday-first)
    cal = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)

    role = session.get("role")
    # NOTE: these comparisons must match the strings in select_division()
    is_pod = (role == "POD Staff and Administration")
    is_committee = (role == "Student Talent Committee and Ambassador")
    is_coach = (role == "Student Coach")

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

# ========================
# Committee
# ========================
# ---------- API — fetch calendar data ----------
@app.route("/api/committee/calendar")
def api_committee_calendar():
    if session.get("role") not in [
        "Student Talent Committee and Ambassador",
        "POD Staff and Administration"
    ]:
        return jsonify([])

    return jsonify(load_committee_entries(session.get("role")))

# ---------- API — submit Event or Availability ----------
@app.route("/api/committee/submit", methods=["POST"])
def api_committee_submit():
    # Lock comittee submissioin rotes by division
    if session.get("role") not in [
        "Student Talent Committee and Ambassador",
    ]:
        return jsonify({"message": "Unauthorized"}), 403

    data = request.get_json()
    entry_type = data.get("type")  # Availability or Event

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

# ========================
# STUDENT COACH
# ========================
# ---------- API — fetch applications ----------
@app.route("/api/applications")
def api_applications():
    ensure_applications_file()
    wb = openpyxl.load_workbook(APPLICATIONS_FILE)
    ws = wb.active

    rows = []

    # ---------- Waiting list (exclude approved, count pending only) ----------
    waiting_map = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[1] != "Student Coach":
            continue
        if r[11] != "Pending":
            continue

        key = (r[4], r[5], r[6], r[7])
        waiting_map[key] = waiting_map.get(key, 0) + 1

    # ---------- Build response ----------
    for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):

        if row[1] != "Student Coach":
            continue

        status = row[11]
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"Invalid status in Excel at row {idx}: {status}")

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

# ---------- API — submit shift booking ----------
@app.route("/api/submit", methods=["POST"])
def api_submit():

    # Lock coach submission routes by division
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

    # ---------- Determine preference (per student, per month) ----------
    current_pref = 1
    for row in ws.iter_rows(min_row=2, values_only=True):
        if (
            row[1] == "Student Coach" and
            row[2] == session.get("student_id") and
            row[4][:7] == date[:7] and
            row[11] in ["Pending", "Approved"]
        ):
            current_pref = max(current_pref, int(row[8]) + 1)

    # ===============================
    # Defensive preference limit
    # ===============================
    if current_pref > 3:
        return jsonify({
            "status": "error",
            "message": "You can only submit up to 3 preferences per month."
        }), 400

    # ---------- Append booking ----------
    ts = datetime.now(timezone("Asia/Singapore")).strftime("%Y-%m-%d %H:%M:%S")

    record = [
        ts,
        "Student Coach",
        session.get("student_id"),
        session.get("student_name"),
        date,
        shift_type,
        slot_level,
        slot_number,
        current_pref,
        "Shift",
        "",
        "Pending"
    ]

    ws.append(record)
    wb.save(APPLICATIONS_FILE)

    return jsonify({
        "status": "success",
        "message": f"Shift booked (Pending) — Preference {current_pref}",
        "preference": current_pref
    })

# ---------- API — coach cancel (Shift) ----------
@app.route("/api/coach/cancel", methods=["POST"])
def api_coach_cancel():
    if session.get("role") != "Student Coach":
        return jsonify({"message": "Unauthorized"}), 403

    data = request.get_json()
    date = data.get("date")
    shift = data.get("shift")
    level = data.get("level")
    slot = data.get("slot")

    ensure_applications_file()
    wb = openpyxl.load_workbook(APPLICATIONS_FILE)
    ws = wb.active

    for row in ws.iter_rows(min_row=2):

        # ---------- Match the exact slot ----------
        if (
            row[1].value != "Student Coach" or
            row[2].value != session.get("student_id") or
            row[4].value != date or
            row[5].value != shift or
            row[6].value != level or
            row[7].value != slot
        ):
            continue

        status = row[11].value

        # ---------- Defensive status validation ----------
        if status not in ["Pending", "Approved", "Rejected"]:
            raise ValueError(f"Invalid status in Excel: {status}")

        # ---------- Only allow cancel for Pending / Approved ----------
        if status in ["Pending", "Approved"]:
            ws.delete_rows(row[0].row)
            wb.save(APPLICATIONS_FILE)
            return jsonify({"message": "Shift cancelled"})

        # ---------- Rejected cannot be cancelled ----------
        return jsonify({"message": "Rejected shifts cannot be cancelled"}), 400

    return jsonify({"message": "Shift not found"}), 404

# ========================
# Admin Page - Shift Approval and
# ========================
# ---------- Admin page route with login restriction ----------
@app.route("/admin_home")
def admin_home():
    if session.get("role") != "POD Staff and Administration":
        return redirect(url_for("index"))
    
    # Pass current datetime object to template
    return render_template("admin_home.html")

@app.route("/admin_approvals")
def admin_approvals():
    if session.get("role") not in ["POD Staff and Administration"]:
        return redirect(url_for("index"))  # redirect non-admins
    return render_template("admin_approvals.html")

# ---------- API endpoint for pending applications ----------
@app.route("/api/admin/pending_applications")
def admin_pending_applications():
    if session.get("role") != "POD Staff and Administration":
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    ensure_applications_file()
    wb = openpyxl.load_workbook(APPLICATIONS_FILE)
    ws = wb.active

    applications = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        division = row[1]
        status = row[11]

        # if division == "Student Coach" and status == "Pending":
        # Pending with space will fail equality check
        if division == "Student Coach" and str(status).strip() == "Pending":
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
                "status": row[11]
            })

    return jsonify(applications)

# ---------- Approve a booking ----------
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

# ---------- Reject a booking ----------
@app.route("/api/admin/reject", methods=["POST"])
def admin_reject():
    if session.get("role") != "POD Staff and Administration":
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    data = request.get_json()
    success = update_application_status(
        data["date"],
        data["shift"],
        data["level"],
        data["slot"],
        data["student_id"],
        "Rejected"
    )

    return jsonify({"status": "ok" if success else "not_found"})

# ---------- Run ----------
if __name__ == "__main__":
    # Ensure applications file exists on startup
    ensure_applications_file()
    app.run(host="127.0.0.1", port=5000, debug=True)
