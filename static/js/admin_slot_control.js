/* =========================================================
   ADMIN SLOT CONTROL JS
   - Single source of truth
   - Works for BOTH table + calendar view
   - Persists isOpen / onjobtrain / nightShift / remarks
========================================================= */

/* ---------- TOAST NOTIFICATION ---------- */
function showToast(message, isError = false) {
    const toast = document.getElementById("toast");
    if (!toast) return;

    toast.textContent = message;
    toast.className = "toast show" + (isError ? " error" : "");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 2000);
}

/* ---------- CORE UPDATE FUNCTION ---------- */
function updateSlot(el) {
    const row = el.closest("tr, .slot-admin"); // table row or calendar slot
    const payload = new FormData();

    payload.append("date", el.dataset.date);
    payload.append("shiftPeriod", el.dataset.shift);
    payload.append("shiftLevel", el.dataset.level);

    // Get the current value of all checkboxes and remarks in the same row
    payload.append("isOpen", row.querySelector('input[data-field="isOpen"]').checked ? 1 : 0);
    payload.append("onjobtrain", row.querySelector('input[data-field="onjobtrain"]').checked ? 1 : 0);
    payload.append("nightShift", row.querySelector('input[data-field="nightShift"]').checked ? 1 : 0);
    payload.append("remarks", row.querySelector('input[data-field="remarks"], textarea[data-field="remarks"]')?.value || "");

    fetch("/admin/slot_control/update", {
        method: "POST",
        body: payload
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast("Slot updated successfully");
        } else {
            showToast(data.error || "Failed to update slot", true);
        }
    })
    .catch(err => {
        console.error(err);
        showToast("Server error", true);
    });
}

/* ---------- PAGE LOAD SAFETY ---------- */
document.addEventListener("DOMContentLoaded", () => {
    console.log("Admin Slot Control JS loaded");
});
