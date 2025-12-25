// ========================
// GLOBAL VARIABLES
// ========================
let committeeSelectedDate = null;
let coachSelectedDate = null;
let coachShiftData = [];
let committeeEntries = [];
let MAX_SHIFTS = 100;
let slotControlData = [];

const isCommittee = window.isCommittee || false;
const isCoach = window.isCoach || false; // set in template for Student Coach
const shifts = ["Morning", "Afternoon", "Night"];
const levels = ["L3", "L4", "L6"];
const slots = [1, 2];

// ========================
// GENERAL FUNCTIONS
// ========================
function initLogoutButton() {
    const btn = document.getElementById("logoutBtn");
    if (!btn) return;

    btn.addEventListener("click", () => {
        const choice = confirm("Back to Division Selection?");
        if (choice) {
            window.location.href = "/logout"; 
        }
    });
}

function loadSlotControl(callback) {
    $.get("/api/slot_control", function(data) {
        slotControlData = data; // array of {date, shift_type, slot_level, slot_number, is_open, remark}
        if (callback) callback();
    });
}

// ========================
// ON DOCUMENT READY
// ========================
$(document).ready(function () {
    initLogoutButton();

    if (window.isCommittee) {
        loadCommitteeEntries();
        enableCommitteeDayClicks();
    }

    if (window.isCoach) {
        enableCoachDayClicks();
    }
});

// ========================
// COMMITTEE FUNCTIONS
// ========================
function loadCommitteeEntries() {
    $.get("/api/committee/entries", function (data) {
        committeeEntries = data;
        $(".day-marker").text("");

        data.forEach(entry => {
            const cell = $(`td[data-date='${entry.date}']`);
            if (!cell.length) return;

            const marker = cell.find(".day-marker");
            if (entry.type === "Availability") {
                marker.text("🟢 Available");
            } else if (entry.type === "Event") {
                if (entry.status === "Approved") marker.text("🟢 Event Approved");
                else if (entry.status === "Pending") marker.text("🟡 Event Pending");
                else if (entry.status === "Rejected") marker.text("🔴 Event Rejected");
            }
        });
    });
}

function enableCommitteeDayClicks() {
    $(".calendar-day").click(function () {
        committeeSelectedDate = $(this).data("date");
        $("#committeeSelectedDate").text("Selected Date: " + committeeSelectedDate);
        openCommitteeModal();
    });
}

function openCommitteeModal() {
    $("#committeeModal").removeClass("hidden");
}

function closeCommitteeModal() {
    $("#committeeModal").addClass("hidden");
    $("#committeeType").val("Availability");
    $("#committeeDetails").val("");
}

function submitCommitteeEntry() {
    if (!committeeSelectedDate) { alert("No date selected"); return; }

    const payload = {
        date: committeeSelectedDate,
        type: $("#committeeType").val(),
        details: $("#committeeDetails").val()
    };

    $.ajax({
        url: "/api/committee/submit",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify(payload),
        success: function () {
            closeCommitteeModal();
            loadCommitteeEntries();
        },
        error: function () { alert("Submission failed"); }
    });
}

// ========================
// HELP FUNCTION FOR STUDENT COACH
// ========================
function normalizeStatus(status) {
    if (status === null || status === undefined || status === "") {
        return "Pending";
    }
    return String(status).trim();
}
function assertValidStatus(status) {
    if (!["Pending", "Approved", "Rejected"].includes(status)) {
        throw new Error("Invalid status from backend: " + status);
    }
    return status;
}

// ========================
// STUDENT COACH FUNCTIONS
// ========================
function enableCoachDayClicks() {
    $(".calendar-day").click(function () {
        if (!isCoach) return;

        // -----------------------------
        // Set selected date
        // -----------------------------
        coachSelectedDate = $(this).data("date");
        $("#coachSelectedDate").text(coachSelectedDate);

        // -----------------------------
        // Load slot control & coach data
        // -----------------------------
        loadCoachShifts(() => {
            loadSlotControl(buildShiftSlots);
            $("#coachModal").removeClass("hidden");
        });
    });
}

function closeCoachModal() {
    $("#coachModal").addClass("hidden");
    $("#shiftContainer").empty();
}

function loadCoachShifts(callback) {
    $.get("/api/applications", function (data) {

        coachShiftData = data.filter(a =>
            a.division === "Student Coach" &&
            a.shift_type &&
            a.date
        ).map(a => {
            assertValidStatus(a.status);
            return a;
        });

        // Update calendar markers
        setTimeout(() => { renderCoachCalendarMarkers(); }, 0);

        if (callback) callback();
    });
}

function renderCoachCalendarMarkers() {
    $(".day-marker").empty();
    if (!coachShiftData || coachShiftData.length === 0) return;

    coachShiftData.forEach(app => {
        const cell = $(`td[data-date='${app.date}']`);
        if (!cell.length) return;
        const marker = cell.find(".day-marker");

        let icon = "⚪";
        if (app.status === "Pending") icon = "🟡";
        else if (app.status === "Approved") icon = "🟢";
        else if (app.status === "Rejected") icon = "🔴";

        marker.append(`
            <div class="text-[10px] leading-tight">
                ${icon} ${app.shift_type}
            </div>
        `);
    });
}

function buildShiftSlots() {
    if (!coachSelectedDate || !coachShiftData) return;

    let html = "";

    shifts.forEach(shift => {
        html += `<div class="mb-3"><h3 class="font-semibold">${shift}</h3>`;
        levels.forEach(level => {
            html += `<div class="flex gap-2 mb-1">`;

            slots.forEach(slot => {

                // -----------------------------
                // Check slot control for open/close
                // -----------------------------
                const slotControl = slotControlData.find(sc =>
                    sc.date === coachSelectedDate &&
                    sc.shift_type === shift &&
                    sc.slot_level === level &&
                    sc.slot_number === slot
                );

                let slotStatus = "Closed";
                let slotRemark = "";
                if (slotControl && slotControl.is_open === "Open") {
                    slotStatus = "Open";
                    slotRemark = slotControl.remark || "";
                }

                // -----------------------------
                // Existing bookings
                // -----------------------------
                const slotApps = coachShiftData.filter(s =>
                    s.date === coachSelectedDate &&
                    s.shift_type === shift &&
                    s.slot_level === level &&
                    s.slot_number === slot
                );

                const myApp = slotApps.find(s => String(s.student_id) === String(window.studentId));
                const approvedApp = slotApps.find(s => s.status === "Approved" && String(s.student_id) !== String(window.studentId));
                const pendingCount = slotApps.filter(s => s.status === "Pending" && String(s.student_id) !== String(window.studentId)).length;

                // -----------------------------
                // Button label and status
                // -----------------------------
                let label = "Book";
                let disabled = false;
                let action = "book";

                if (slotStatus === "Closed") {
                    label = `CLOSED${slotRemark ? " — " + slotRemark : ""}`;
                    disabled = true;
                    action = "disabled";
                }

                if (slotStatus === "Open") {
                    if (myApp) {
                        if (myApp.status === "Pending") {
                            label = "🟡 Applied pending approval — Cancel";
                            action = "cancel";
                        } else if (myApp.status === "Approved") {
                            label = `🟢 ${myApp.student_name} — Cancel`;
                            action = "cancel";
                        } else if (myApp.status === "Rejected") {
                            label = "🔴 Rejected";
                            disabled = true;
                            action = "disabled";
                        }
                    } else if (approvedApp) {
                        label = `🟢 ${approvedApp.student_name}`;
                        disabled = true;
                        action = "disabled";
                    } else if (pendingCount > 0) {
                        label = `🟡 Join waiting list (${pendingCount})`;
                        action = "book";
                    }
                }

                const safeShift = shift.replace(/'/g, "\\'");
                const safeLevel = level.replace(/'/g, "\\'");
                const safeAction = action.replace(/'/g, "\\'");

                html += `
                    <button class="slot-btn border px-2 py-1 rounded ${disabled ? 'opacity-50' : ''}"
                        data-shift="${safeShift}"
                        data-level="${safeLevel}"
                        data-slot="${slot}"
                        data-action="${safeAction}"
                        onclick="handleCoachSlotClick('${safeShift}','${safeLevel}',${slot},'${safeAction}')"
                        ${disabled ? 'disabled' : ''}>
                        ${label}
                    </button>
                `;
            });

            html += `</div>`;
        });

        html += `</div>`;
    });

    $("#shiftContainer").html(html);
}

function handleCoachSlotClick(shift, level, slot) {

    const slotApps = coachShiftData.filter(s =>
        s.date === coachSelectedDate &&
        s.shift_type === shift &&
        s.slot_level === level &&
        s.slot_number === slot
    );

    const myApp = slotApps.find(s => String(s.student_id) === String(window.studentId));
    const approvedByOthers = slotApps.find(s =>
        s.status === "Approved" &&
        String(s.student_id) !== String(window.studentId)
    );

    // ==========================
    // CANCEL (own pending / approved)
    // ==========================
    if (myApp && (myApp.status === "Pending" || myApp.status === "Approved")) {
        if (!confirm("Cancel this shift?")) return;

        $.ajax({
            url: "/api/coach/cancel",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                date: coachSelectedDate,
                shift,
                level,
                slot
            }),
            success: function () {
                loadCoachShifts(buildShiftSlots);
            }
        });

        return;
    }

    // ==========================
    // BLOCKED (approved by others)
    // ==========================
    if (approvedByOthers) {
        alert("This slot is already filled.");
        return;
    }

    // ==========================
    // BOOK (check max shifts)
    // ==========================
    const myBookingsMonth = coachShiftData.filter(s =>
        String(s.student_id) === String(window.studentId) &&
        s.status !== "Rejected" &&
        s.date.slice(0, 7) === coachSelectedDate.slice(0, 7)
    );

    if (myBookingsMonth.length + 1 > MAX_SHIFTS) {
        alert("You can only select up to TBC shifts per month.");
        return;
    }

    const payload = {
        date: coachSelectedDate,
        shift_type: shift,
        slot_level: level,
        slot_number: slot
    };

    $.ajax({
        url: "/api/submit",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify(payload),
        success: function () {
            loadCoachShifts(buildShiftSlots);
        },
        error: function (xhr) {
            alert("Submit failed.");
        }
    });
}

// ========================
// DIRECTORY DROPDOWN NAV
// ========================
document.addEventListener("DOMContentLoaded", function () {
    const dropdown = document.getElementById("directoryDropdown");
    if (!dropdown) return;

    dropdown.addEventListener("change", function () {
        if (this.value) {
            window.location.href = this.value;
        }
    });
});
