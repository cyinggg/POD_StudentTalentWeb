// ========================
// GLOBAL VARIABLES
// ========================
let committeeSelectedDate = null;
let coachSelectedDate = null;
let coachShiftData = [];
let committeeEntries = [];
let MAX_SHIFTS = 100;
let slotControlData = [];

const shifts = ["Morning", "Afternoon", "Night"];
const levels = ["L3", "L4", "L6"];
const slots = [1, 2];

// ========================
// GENERAL FUNCTIONS
// ========================
function initLogoutButton() {
    const btn = $("#logoutBtn");
    if (!btn.length) return;

    btn.click(() => {
        if (confirm("Back to Division Selection?")) {
            window.location.href = "/logout";
        }
    });
}

function loadSlotControl(callback) {
    $.get("/api/slot_control", function(data) {
        slotControlData = data || [];
        if (callback) callback();
    });
}

// ========================
// COMMITTEE FUNCTIONS
// ========================
function loadCommitteeEntries() {
    $.get("/api/committee/entries", function (data) {
        committeeEntries = data || [];
        $(".day-marker").text("");

        data.forEach(entry => {
            const cell = $(`td[data-date='${entry.date}']`);
            if (!cell.length) return;

            const marker = cell.find(".day-marker");
            if (entry.type === "Availability") marker.text("🟢 Available");
            else if (entry.type === "Event") {
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
        $("#committeeModal").removeClass("hidden");
    });
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
// STUDENT COACH FUNCTIONS
// ========================
function normalizeStatus(status) {
    if (!status) return "Pending";
    return String(status).trim();
}
function assertValidStatus(status) {
    if (!["Pending", "Approved", "Rejected"].includes(status)) {
        throw new Error("Invalid status from backend: " + status);
    }
    return status;
}

function enableCoachDayClicks() {
    $(".calendar-day").click(function () {
        if (!window.isCoach) return;

        coachSelectedDate = $(this).data("date");
        $("#coachSelectedDate").text(coachSelectedDate);

        // Load slot control first, then coach shifts
        loadSlotControl(() => {
            loadCoachShifts(buildShiftSlots);
        });

        $("#coachModal").removeClass("hidden");
    });
}

function closeCoachModal() {
    $("#coachModal").addClass("hidden");
    $("#shiftContainer").empty();
}

function loadCoachShifts(callback) {
    $.get("/api/applications", function (data) {
        coachShiftData = (data || []).filter(a =>
            a.division === "Student Coach" &&
            a.shift_type &&
            a.date
        ).map(a => {
            assertValidStatus(a.status);
            return a;
        });

        setTimeout(() => { renderCoachCalendarMarkers(); }, 0);
        if (callback) callback();
    });
}

function renderCoachCalendarMarkers() {
    $(".day-marker").empty();
    if (!coachShiftData.length) return;

    coachShiftData.forEach(app => {
        const cell = $(`td[data-date='${app.date}']`);
        if (!cell.length) return;
        const marker = cell.find(".day-marker");

        let icon = "⚪";
        if (app.status === "Pending") icon = "🟡";
        else if (app.status === "Approved") icon = "🟢";
        else if (app.status === "Rejected") icon = "🔴";

        marker.append(`<div class="text-[10px] leading-tight">${icon} ${app.shift_type}</div>`);
    });
}

// ========================
// BUILD SHIFT SLOTS WITH SLOT CONTROL
// ========================
function buildShiftSlots() {
    if (!coachSelectedDate) return;

    let html = "";
    shifts.forEach(shift => {
        html += `
        <details open class="border rounded p-2 bg-gray-50">
            <summary class="font-semibold cursor-pointer">${shift}</summary>
            <div class="flex flex-wrap gap-2 mt-2">
        `;

        levels.forEach(level => {
            slots.forEach(slot => {
                const slotControl = slotControlData.find(sc =>
                    sc.date === coachSelectedDate &&
                    sc.shift_type === shift &&
                    sc.slot_level === level &&
                    sc.slot_number === slot
                );

                let slotStatus = "Closed";
                let remark = "";
                if (slotControl) {
                    slotStatus = (slotControl.is_open === true || String(slotControl.is_open).toLowerCase() === "true") ? "Open" : "Closed";
                    remark = slotControl.remarks || "";
                }

                const slotApps = coachShiftData.filter(s =>
                    s.date === coachSelectedDate &&
                    s.shift_type === shift &&
                    s.slot_level === level &&
                    s.slot_number === slot
                );

                const myApp = slotApps.find(s => String(s.student_id) === String(window.studentId));
                const approvedApp = slotApps.find(s => s.status === "Approved" && String(s.student_id) !== String(window.studentId));
                const pendingCount = slotApps.filter(s => s.status === "Pending" && String(s.student_id) !== String(window.studentId)).length;

                let label = slotStatus === "Closed" ? "CLOSED" : "Book";
                let disabled = slotStatus === "Closed";
                let action = slotStatus === "Closed" ? "disabled" : "book";
                let btnColor = slotStatus === "Closed" ? "bg-gray-300 text-gray-600" : "bg-green-500 text-white";

                if (slotStatus === "Open") {
                    if (myApp) {
                        if (myApp.status === "Pending") { label = "🟡 Pending — Cancel"; action = "cancel"; btnColor="bg-yellow-400 text-black"; }
                        else if (myApp.status === "Approved") { label = `🟢 ${myApp.student_name} — Cancel`; action = "cancel"; btnColor="bg-blue-500 text-white"; }
                        else if (myApp.status === "Rejected") { label = "🔴 Rejected"; disabled = true; action = "disabled"; btnColor="bg-red-500 text-white"; }
                    } else if (approvedApp) {
                        label = `🟢 ${approvedApp.student_name}`;
                        disabled = true;
                        action = "disabled";
                        btnColor="bg-blue-500 text-white";
                    } else if (pendingCount > 0) {
                        label = `🟡 Join waiting list (${pendingCount})`;
                        action = "book";
                        btnColor="bg-yellow-400 text-black";
                    }
                }

                html += `
                    <button class="slot-btn ${btnColor} px-3 py-1 rounded font-semibold ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105 transition'}"
                        data-shift="${shift}"
                        data-level="${level}"
                        data-slot="${slot}"
                        data-action="${action}"
                        title="${remark}"
                        onclick="handleCoachSlotClick('${shift}','${level}',${slot},'${action}')"
                        ${disabled ? 'disabled' : ''}>
                        ${label}${remark ? ' – ' + remark : ''}
                    </button>
                `;
            });
        });

        html += `</div></details>`;
    });

    $("#shiftContainer").html(html);
}

// ========================
// HANDLE COACH SLOT CLICK
// ========================
function handleCoachSlotClick(shift, level, slot, action) {
    const slotApps = coachShiftData.filter(s =>
        s.date === coachSelectedDate &&
        s.shift_type === shift &&
        s.slot_level === level &&
        s.slot_number === slot
    );

    const myApp = slotApps.find(s => String(s.student_id) === String(window.studentId));
    const approvedByOthers = slotApps.find(s =>
        s.status === "Approved" && String(s.student_id) !== String(window.studentId)
    );

    if (myApp && (myApp.status === "Pending" || myApp.status === "Approved")) {
        if (!confirm("Cancel this shift?")) return;

        $.ajax({
            url: "/api/coach/cancel",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({ date: coachSelectedDate, shift, level, slot }),
            success: function () { loadCoachShifts(buildShiftSlots); }
        });
        return;
    }

    if (approvedByOthers) { alert("This slot is already filled."); return; }

    const myBookingsMonth = coachShiftData.filter(s =>
        String(s.student_id) === String(window.studentId) &&
        s.status !== "Rejected" &&
        s.date.slice(0, 7) === coachSelectedDate.slice(0, 7)
    );

    if (myBookingsMonth.length + 1 > MAX_SHIFTS) {
        alert("You can only select up to TBC shifts per month.");
        return;
    }

    $.ajax({
        url: "/api/submit",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({ date: coachSelectedDate, shift_type: shift, slot_level: level, slot_number: slot }),
        success: function () { loadCoachShifts(buildShiftSlots); },
        error: function () { alert("Submit failed."); }
    });
}

// ========================
// DOCUMENT READY
// ========================
$(document).ready(function () {
    // Logout
    initLogoutButton();

    // Directory navigation
    const dropdown = $("#directoryDropdown");
    if (dropdown.length) {
        dropdown.change(function () { if (this.value) window.location.href = this.value; });
    }

    // Committee
    if (window.isCommittee) { loadCommitteeEntries(); enableCommitteeDayClicks(); }

    // Student Coach
    if (window.isCoach) { enableCoachDayClicks(); }
});
