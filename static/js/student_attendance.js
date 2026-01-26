// ------------------ Clock In / Clock Out ------------------
function clockAction(action, key) {
    const formData = new FormData();
    formData.append("action", action);
    formData.append("key", key);

    fetch("/student/attendance/clock", {
        method: "POST",
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            // Find the <td> with matching data-key for this action
            const tdEl = document.querySelector(`td[data-key='${key}']`);
            if (tdEl) {
                tdEl.textContent = data.time; // Replace button with timestamp
            }
        } else {
            alert(data.error || "Failed to " + action);
        }
    })
    .catch(err => {
        console.error(err);
        alert("Server error");
    });
}

// ------------------ Save Shift Start / End / Remarks ------------------
function saveAttendance(key, idx) {
    const formData = new FormData();
    formData.append("key", key);
    formData.append("shiftstart", document.getElementById("start_" + idx).value);
    formData.append("shiftend", document.getElementById("end_" + idx).value);
    formData.append("remarks", document.getElementById("remarks_" + idx).value);

    fetch("/student/attendance/save", {
        method: "POST",
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            // Show a temporary "✓ Saved" indicator next to Save button
            const btn = document.querySelectorAll(".btn-save")[idx - 1];
            let savedSpan = btn.nextElementSibling;
            if (!savedSpan || !savedSpan.classList.contains("saved-indicator")) {
                savedSpan = document.createElement("span");
                savedSpan.className = "saved-indicator";
                btn.after(savedSpan);
            }
            savedSpan.textContent = "✓ Saved";
            savedSpan.style.opacity = 1;
            setTimeout(() => {
                savedSpan.style.opacity = 0;
            }, 1200);
        } else {
            alert(data.error || "Failed to save");
        }
    })
    .catch(err => {
        console.error(err);
        alert("Server error");
    });
}
