/* ================= TOAST NOTIFICATION ================= */
function showToast(message, isError = false) {
    const toast = document.getElementById("toast");
    if (!toast) return;

    toast.textContent = message;
    toast.className = "toast show" + (isError ? " error" : "");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 2000);
}

/* ================= SAVE ANIMATION ================= */
function showSaved(el) {
    const parent = el.parentElement;
    const old = parent.querySelector(".saved-indicator");
    if (old) old.remove();

    const span = document.createElement("span");
    span.className = "saved-indicator";
    span.textContent = "✓ Saved";
    parent.appendChild(span);

    // Fade out animation
    setTimeout(() => span.classList.add("fade-out"), 700);
    setTimeout(() => span.remove(), 1400);
}

/* ================= SYNC ACROSS TABLE & CALENDAR ================= */
function syncViews(key, field, value) {
    document.querySelectorAll(`[data-key="${key}"]`).forEach(el => {
        // checkbox fields
        if (field === "isopen" || field === "onjobtrain" || field === "nightshift") {
            const cb = el.querySelector(`input[data-field="${field}"]`);
            if (cb) cb.checked = value == 1;
        }
        // remarks field
        if (field === "remarks") {
            const ta = el.querySelector('input[data-field="remarks"], textarea[data-field="remarks"]');
            if (ta) ta.value = value;
        }
    });
}

/* ================= CORE UPDATE FUNCTION ================= */
function updateSlot(el) {
    const row = el.closest("tr") || el.closest(".slot-admin");
    if (!row) return;

    const field = el.dataset.field;
    const date = el.dataset.date;
    const shift = el.dataset.shift;
    const level = el.dataset.level;

    if (!field || !date || !shift || !level) {
        console.warn("Missing dataset attributes:", el);
        return;
    }

    // Determine all field values in the row
    const isOpen = row.querySelector('input[data-field="isopen"]')?.checked ? 1 : 0;
    const onjobtrain = row.querySelector('input[data-field="onjobtrain"]')?.checked ? 1 : 0;
    const nightShift = row.querySelector('input[data-field="nightshift"]')?.checked ? 1 : 0;
    const remarks = row.querySelector('input[data-field="remarks"], textarea[data-field="remarks"]')?.value || "";

    // Prepare FormData for Flask route
    const payload = new FormData();
    payload.append("date", date);
    payload.append("shiftPeriod", shift);
    payload.append("shiftLevel", level);
    payload.append("isOpen", isOpen);
    payload.append("onjobtrain", onjobtrain);
    payload.append("nightShift", nightShift);
    payload.append("remarks", remarks);

    fetch(updateUrl, {
        method: "POST",
        body: payload
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            // Sync across views
            syncViews(`${date}_${shift}_${level}`, "isopen", isOpen);
            syncViews(`${date}_${shift}_${level}`, "onjobtrain", onjobtrain);
            syncViews(`${date}_${shift}_${level}`, "nightshift", nightShift);
            syncViews(`${date}_${shift}_${level}`, "remarks", remarks);

            showSaved(el);
        } else {
            showToast(data.error || "Save failed", true);
        }
    })
    .catch(err => {
        console.error(err);
        showToast("Server error", true);
    });
}

/* ================= INITIALIZE ================= */
document.addEventListener("DOMContentLoaded", () => {
    console.log("Admin Slot Control JS loaded");

    // Assign data-key attributes to sync across table & calendar
    document.querySelectorAll('input[data-date]').forEach(el => {
        const key = `${el.dataset.date}_${el.dataset.shift}_${el.dataset.level}`;
        const parent = el.closest("tr") || el.closest(".slot-admin");
        if (parent) parent.dataset.key = key;
    });
});
