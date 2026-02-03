// ------------------ Clock In / Clock Out ------------------
function clockAction(action, key) {
    fetch("/student/attendance/clock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, key })
    })
    .then(r => r.json())
    .then(data => {
        if (!data.success) {
            alert(data.error);
            return;
        }

        const spanId = (action === "clockin" ? "clockin_" : "clockout_") + key;
        const span = document.getElementById(spanId);
        if (span) span.textContent = data.time;

        const btn = document.querySelector(`button[data-key="${key}"][data-action="${action}"]`);
        if (btn) btn.remove();

        if (action === "clockin") {
            const outBtn = document.querySelector(`button[data-key="${key}"][data-action="clockout"]`);
            if (outBtn) outBtn.disabled = false;
        }
    });
}

// ------------------ Save Shift Start / End / Remarks ------------------
function saveAttendance(key, idx) {
    const formData = new FormData();
    formData.append("key", key);
    formData.append("shiftstart", document.getElementById("start_" + idx).value);
    formData.append("shiftend", document.getElementById("end_" + idx).value);
    formData.append("remarks", document.getElementById("remarks_" + idx).value);

    fetch("/student/attendance/save", { method: "POST", body: formData })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            const btn = document.querySelectorAll(".btn-save")[idx-1];
            let savedSpan = btn.nextElementSibling;
            if (!savedSpan || !savedSpan.classList.contains("saved-indicator")) {
                savedSpan = document.createElement("span");
                savedSpan.className = "saved-indicator";
                btn.after(savedSpan);
            }
            savedSpan.textContent = "✓ Saved";
            savedSpan.style.opacity = 1;
            setTimeout(()=>{savedSpan.style.opacity=0},1200);
        } else {
            alert(data.error || "Failed to save");
        }
    })
    .catch(err => { console.error(err); alert("Server error"); });
}

// ------------------ Live SG Time ------------------
function updateCurrentSGTime() {
    const nowEl = document.getElementById("now");
    if (!nowEl) return;

    setInterval(() => {
        const now = new Date();
        // Convert to Singapore Time offset +08:00
        const sgTime = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Singapore" }));
        // Format as YYYY-MM-DD HH:MM:SS
        const formatted = sgTime.getFullYear() + "-" +
                          String(sgTime.getMonth() + 1).padStart(2, "0") + "-" +
                          String(sgTime.getDate()).padStart(2, "0") + " " +
                          String(sgTime.getHours()).padStart(2, "0") + ":" +
                          String(sgTime.getMinutes()).padStart(2, "0") + ":" +
                          String(sgTime.getSeconds()).padStart(2, "0");
        nowEl.textContent = formatted;
    }, 1000);
}

// Initialize live SG time on page load
document.addEventListener("DOMContentLoaded", () => {
    updateCurrentSGTime();
});
