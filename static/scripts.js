// ========================
// GLOBAL VARIABLES
// ========================
let committeeSelectedDate = null;
let coachSelectedDate = null;
let coachShiftData = [];
let committeeEntries = [];

const isCommittee = window.isCommittee || false;
const isCoach = window.isCoach || false; // set in template for Student Coach

// ========================
// GENERAL FUNCTIONS
// ========================
function initLogoutButton() {
    const btn = document.getElementById("logoutBtn");
    if (!btn) return;

    btn.addEventListener("click", () => {
        const choice = confirm(
            "Back to Division Selection?"
        );

        if (choice) {
            // Optional: call /logout to clear session
            window.location.href = "/logout"; 
        } 
        // Else: do nothing, user can close browser manually
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
        loadCoachShifts();
        enableCoachDayClicks();
    }
});

// ========================
// COMMITTEE FUNCTIONS
// ========================
function loadCommitteeEntries() {
    $.get("/api/committee/entries", function (data) {
        committeeEntries = data;
        $(".day-marker").text(""); // clear previous

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

        coachSelectedDate = $(this).data("date");
        $("#coachSelectedDate").text(coachSelectedDate);

        // LOAD DATA FIRST
        loadCoachShifts(() => {
            buildShiftSlots();
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

        console.log("Raw applications from backend:", data);

        coachShiftData = data.filter(a =>
            a.division === "Student Coach" &&
            a.shift_type &&
            a.date
        ).map(a => {
            assertValidStatus(a.status);
            return a;
        });

        console.log("Loaded coachShiftData:", coachShiftData);

        // Ensure calendar DOM exists
        setTimeout(() => {
            renderCoachCalendarMarkers();
        }, 0);

        if (callback) callback();
    });
}

function renderCoachCalendarMarkers() {

    // Clear existing markers
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
    if (!coachSelectedDate || !coachShiftData) {
        console.warn("buildShiftSlots skipped: data not ready");
        return;
    }

    const shifts = ["Morning", "Afternoon", "Night"];
    const levels = ["L3", "L4", "L6"];
    const slots = [1, 2];

    let html = "";

    shifts.forEach(shift => {
        html += `<div class="mb-3"><h3 class="font-semibold">${shift}</h3>`;

        levels.forEach(level => {
            html += `<div class="flex gap-2 mb-1">`;

            slots.forEach(slot => {
                // All bookings for this slot
                const slotApps = coachShiftData.filter(s =>
                    s.date === coachSelectedDate &&
                    s.shift_type === shift &&
                    s.slot_level === level &&
                    s.slot_number === slot
                );

                // My booking
                const myApp = slotApps.find(
                    s => String(s.student_id) === String(window.studentId)
                );

                // Someone else approved
                const approvedApp = slotApps.find(
                    s => s.status === "Approved" &&
                        String(s.student_id) !== String(window.studentId)
                );

                // Pending by others
                const pendingCount = slotApps.filter(
                    s => s.status === "Pending" &&
                        String(s.student_id) !== String(window.studentId)
                ).length;

                let label = "Book";
                let disabled = false;
                let action = "book";

                // ---------- FINAL BEHAVIOUR ----------
                if (myApp) {
                    if (myApp.status === "Pending") {
                        label = "🟡 Applied pending approval — Cancel";
                        action = "cancel";
                    }
                    else if (myApp.status === "Approved") {
                        label = `🟢 ${myApp.student_name} — Cancel`;
                        action = "cancel";
                    }
                    else if (myApp.status === "Rejected") {
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

                // Escape quotes in variables to prevent JS syntax errors
                const safeShift = shift.replace(/'/g, "\\'");
                const safeLevel = level.replace(/'/g, "\\'");
                const safeAction = action.replace(/'/g, "\\'");

                html += `<button class="slot-btn border px-2 py-1 rounded ${disabled ? 'opacity-50' : ''}"
                                 data-shift="${safeShift}"
                                 data-level="${safeLevel}"
                                 data-slot="${slot}"
                                 data-action="${safeAction}"
                                 onclick="handleCoachSlotClick('${safeShift}','${safeLevel}',${slot},'${safeAction}')"
                                 ${disabled ? 'disabled' : ''}>
                            ${label}
                        </button>`;
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

    const myApp = slotApps.find(
        s => String(s.student_id) === String(window.studentId)
    );

    const approvedByOthers = slotApps.find(
        s =>
            s.status === "Approved" &&
            String(s.student_id) !== String(window.studentId)
    );

    // ==========================
    // STATUS INVARIANT (FAIL FAST)
    // ==========================
    if (myApp && !["Pending", "Approved", "Rejected"].includes(myApp.status)) {
        throw new Error("Invalid myApp.status detected: " + myApp.status);
    }

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
                loadCoachShifts(() => buildShiftSlots());
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
    // BOOK (preference guard)
    // ==========================
    const myBookingsMonth = coachShiftData.filter(s =>
        String(s.student_id) === String(window.studentId) &&
        s.status !== "Rejected" &&
        s.date.slice(0, 7) === coachSelectedDate.slice(0, 7)
    );

    const preference = myBookingsMonth.length + 1;

    if (preference > 3) {
        alert("You can only select up to 3 shifts per month.");
        return;
    }

    const payload = {
        date: coachSelectedDate,
        shift_type: shift,
        slot_level: level,
        slot_number: slot
    };

    console.log("Submitting coach slot:", payload);

    $.ajax({
        url: "/api/submit",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify(payload),
        success: function (res) {
            console.log("Submit success:", res);
            loadCoachShifts(() => buildShiftSlots());
        },
        error: function (xhr) {
            console.error("Submit failed:", xhr.responseText);
            alert("Submit failed.");
        }
    });
}

document.addEventListener("DOMContentLoaded", function () {
    const dropdown = document.getElementById("directoryDropdown");
    if (!dropdown) return;

    dropdown.addEventListener("change", function () {
        if (this.value) {
            window.location.href = this.value;
        }
    });
});
