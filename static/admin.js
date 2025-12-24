// ---------- Load pending Student Coach booking requests ----------
function loadPending() {
    $.get("/api/admin/pending_applications", function(data) {
        const tbody = $("#approvalTable").empty(); // Clear table

        if (data.length === 0) {
            tbody.append(`<tr><td colspan="9" class="text-center p-4">No requests found</td></tr>`);
            return;
        }

        data.forEach(app => {
            tbody.append(`
                <tr data-student="${app.student_id}" data-date="${app.date}" data-shift="${app.shift_type}" data-level="${app.slot_level}" data-slot="${app.slot_number}">
                    <td class="border px-4 py-2">${app.date}</td>
                    <td class="border px-4 py-2">${app.shift_type}</td>
                    <td class="border px-4 py-2">${app.slot_level}</td>
                    <td class="border px-4 py-2">${app.slot_number}</td>
                    <td class="border px-4 py-2">${app.student_name}</td>
                    <td class="border px-4 py-2 status-col">${app.status}</td>
                    <td class="border px-4 py-2">
                        <select class="admin-decision">
                            <option value="">Select</option>
                            <option value="Approved" ${app.admin_decision === 'Approved' ? 'selected' : ''}>Approved</option>
                            <option value="Rejected" ${app.admin_decision === 'Rejected' ? 'selected' : ''}>Rejected</option>
                            <option value="Advance Excuse" ${app.admin_decision === 'Advance Excuse' ? 'selected' : ''}>Advance Excuse</option>
                            <option value="Last Minute Unavailable" ${app.admin_decision === 'Last Minute Unavailable' ? 'selected' : ''}>Last Minute Unavailable</option>
                            <option value="Last Minute Valid Excuse" ${app.admin_decision === 'Last Minute Valid Excuse' ? 'selected' : ''}>Last Minute Valid Excuse</option>
                            <option value="No Show" ${app.admin_decision === 'No Show' ? 'selected' : ''}>No Show</option>
                        </select>
                        <button class="save-decision px-2 py-1 bg-gray-200 rounded">Save</button>
                    </td>
                    <td class="border px-4 py-2"><input type="text" class="admin-remark w-full border rounded px-2 py-1" value="${app.remark || ''}"></td>
                    <td class="border px-4 py-2">
                        ${app.status === 'Pending' ? `
                        <button class="approve-btn px-2 py-1 bg-green-500 text-white rounded">Approve</button>
                        <button class="reject-btn px-2 py-1 bg-red-500 text-white rounded">Reject</button>` : ''}
                        <button class="reallocate-btn px-2 py-1 bg-yellow-500 text-black rounded">Reallocate</button>
                    </td>
                </tr>
            `);
        });
    });
}

// ---------- Approve / Reject quick buttons ----------
$(document).on("click", ".approve-btn", function() {
    const tr = $(this).closest("tr");
    updateStatus(tr, "Approved");
});

$(document).on("click", ".reject-btn", function() {
    const tr = $(this).closest("tr");
    updateStatus(tr, "Rejected");
});

// ---------- Save admin decision + remark ----------
$(document).on("click", ".save-decision", function() {
    const tr = $(this).closest("tr");
    const decision = tr.find(".admin-decision").val();
    const remark = tr.find(".admin-remark").val();
    if (!decision) { alert("Select a decision first."); return; }
    updateStatus(tr, decision, remark);
});

// ---------- Reallocate button ----------
$(document).on("click", ".reallocate-btn", function() {
    const tr = $(this).closest("tr");
    alert("Reallocate button clicked for this slot."); // notification
    const student_id = tr.data("student");
    const date = tr.data("date");
    const shift = tr.data("shift");
    const level = tr.data("level");
    const slot = tr.data("slot");

    // Make POST request to backend to allow reallocate
    $.ajax({
        url: "/api/admin/reallocate",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({ student_id, date, shift, level, slot }),
        success: function(res) {
            alert(res.message || "Reallocation processed.");
            loadPending();
        }
    });
});

// ---------- Update status helper ----------
function updateStatus(tr, decision, remark="") {
    const student_id = tr.data("student");
    const date = tr.data("date");
    const shift = tr.data("shift");
    const level = tr.data("level");
    const slot = tr.data("slot");

    $.ajax({
        url: "/api/admin/decide",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({ student_id, date, shift, level, slot, decision, remark }),
        success: function(res) {
            if (res.status === "ok") {
                tr.find(".status-col").text(decision);
                alert(`Status updated to ${decision}`);
            } else {
                alert("Error updating status.");
            }
        }
    });
}

// ---------- Filter Table ----------
function filterTable() {
    const studentFilter = $("#filterStudent").val().toLowerCase();
    const dateFilter = $("#filterDate").val().toLowerCase();
    const statusFilter = $("#filterStatus").val().toLowerCase();

    $("#approvalTable tr").each(function() {
        const studentName = $(this).find("td:eq(4)").text().toLowerCase();
        const date = $(this).find("td:eq(0)").text().toLowerCase();
        const status = $(this).find("td:eq(5)").text().toLowerCase();

        const matchStudent = studentName.includes(studentFilter);
        const matchDate = date.includes(dateFilter);
        const matchStatus = statusFilter === "" || status === statusFilter;

        $(this).toggle(matchStudent && matchDate && matchStatus);
    });
}

$("#filterStudent, #filterDate, #filterStatus").on("input change", filterTable);

// ---------- Initialize ----------
$(document).ready(function() {
    loadPending();
});
