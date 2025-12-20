// ---------- Load pending Student Coach booking requests ----------
function loadPending() {
    $.get("/api/admin/pending_applications", function(data) {
        const tbody = $("#approvalTable").empty(); // Clear table

        if (data.length === 0) {
            tbody.append(`<tr><td colspan="6" class="text-center p-4">No pending requests</td></tr>`);
            return;
        }

        data.forEach(app => {
            tbody.append(`
                <tr>
                    <td class="border px-4 py-2">${app.date}</td>
                    <td class="border px-4 py-2">${app.shift_type}</td>
                    <td class="border px-4 py-2">${app.slot_level}</td>
                    <td class="border px-4 py-2">${app.slot_number}</td>
                    <td class="border px-4 py-2">${app.student_name}</td>
                    <td class="border px-4 py-2">
                        <button class="btn btn-small" onclick="approveShift('${app.date}', '${app.shift_type}', '${app.slot_level}', ${app.slot_number}, '${app.student_id}')">Approve</button>
                        <button class="btn btn-small btn-danger" onclick="rejectShift('${app.date}', '${app.shift_type}', '${app.slot_level}', ${app.slot_number}, '${app.student_id}')">Reject</button>
                    </td>
                </tr>
            `);
        });
    });
}

// ---------- Approve a booking ----------
function approveShift(date, shift_type, slot_level, slot_number, student_id) {
    $.ajax({
        url: "/api/admin/approve",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({
            date: date,
            shift: shift_type,
            level: slot_level,
            slot: slot_number,
            student_id: student_id
        }),
        success: function(res) {
            if (res.status === "ok") {
                alert("Booking approved!");
                loadPending(); // refresh table
            } else {
                alert("Error: booking not found");
            }
        }
    });
}

// ---------- Reject a booking ----------
function rejectShift(date, shift_type, slot_level, slot_number, student_id) {
    $.ajax({
        url: "/api/admin/reject",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({
            date: date,
            shift: shift_type,
            level: slot_level,
            slot: slot_number,
            student_id: student_id
        }),
        success: function(res) {
            if (res.status === "ok") {
                alert("Booking rejected!");
                loadPending(); // refresh table
            } else {
                alert("Error: booking not found");
            }
        }
    });
}

// ---------- Initialize ----------
$(document).ready(function() {
    loadPending(); // load table on page load
});
