document.addEventListener("DOMContentLoaded", function() {
    // --------------------- Elements ---------------------
    const tableContainer = document.getElementById("tableContainer");
    const calendarContainer = document.getElementById("calendarContainer");
    const btnTableView = document.getElementById("btnTableView");
    const btnCalendarView = document.getElementById("btnCalendarView");

    const modal = new bootstrap.Modal(document.getElementById("remarksModal"));
    const modalInput = document.getElementById("modalRemarksInput");
    let currentRow = null;

    // Table Filters
    const filterText = document.getElementById("filterText");
    const filterDate = document.getElementById("filterDate");
    const filterShift = document.getElementById("filterShift");
    const filterLevel = document.getElementById("filterLevel");
    const filterStatus = document.getElementById("filterStatus");
    const filterDecision = document.getElementById("filterDecision");
    const filterOJT = document.getElementById("filterOJT");
    const filterNight = document.getElementById("filterNight");

    // ------------------ Restore saved filters ------------------
    const savedFilters = localStorage.getItem("adminShiftFilters");

    if (savedFilters) {
        const f = JSON.parse(savedFilters);

        filterText.value = f.text || "";
        filterDate.value = f.date || "";
        filterShift.value = f.shift || "";
        filterLevel.value = f.level || "";
        filterStatus.value = f.status || "";
        filterDecision.value = f.decision || "";
        filterOJT.value = f.ojt || "";
        filterNight.value = f.night || "";
    }

    // ------------------ Notification ------------------
    function showNotification(message, isSuccess = true) {
        const box = document.getElementById("notification");
        const text = document.getElementById("notification-text");
        if (!box || !text) { alert(message); return; }

        text.textContent = message;
        box.classList.remove("hidden");
        box.classList.toggle("success", isSuccess);
        box.classList.toggle("error", !isSuccess);

        setTimeout(() => box.classList.add("hidden"), 3000);
    }

    // ------------------ Toggle Views ------------------
    btnTableView.addEventListener("click", () => {
        tableContainer.style.display = "block";
        calendarContainer.style.display = "none";
        btnTableView.classList.replace("btn-secondary", "btn-primary");
        btnCalendarView.classList.replace("btn-primary", "btn-secondary");
    });

    btnCalendarView.addEventListener("click", () => {
        tableContainer.style.display = "none";
        calendarContainer.style.display = "block";
        btnCalendarView.classList.replace("btn-secondary", "btn-primary");
        btnTableView.classList.replace("btn-primary", "btn-secondary");
    });

    // ------------------ Table Inline Editing ------------------
    document.querySelectorAll(".edit-remarks-btn").forEach(btn => {
        btn.addEventListener("click", function() {
            currentRow = this.closest("tr");
            modalInput.value = currentRow.querySelector(".admin-remarks-text").textContent;
        });
    });

    document.getElementById("saveRemarksModal").addEventListener("click", function() {
        if (currentRow) {
            currentRow.querySelector(".admin-remarks-text").textContent = modalInput.value;
            modal.hide();
        }
    });

    // Update status badge on table select change
    document.querySelectorAll(".decision-select").forEach(select => {
        select.addEventListener("change", function() {
            const row = this.closest("tr");
            const badge = row.querySelector(".status-badge");
            badge.textContent = this.value;
            badge.className = `badge status-badge ${this.value.toLowerCase()}`;
        });
    });

    // Table save buttons
    document.querySelectorAll(".save-btn").forEach(btn => {
        btn.addEventListener("click", function() {
            const row = this.closest("tr");
            const key = row.dataset.key;
            const status = row.querySelector(".status-badge").textContent;
            const admindecision = row.querySelector(".decision-select").value;
            const adminremarks = row.querySelector(".admin-remarks-text").textContent;

            const formData = new URLSearchParams();
            formData.append("key", key);
            formData.append("status", status);
            formData.append("admindecision", admindecision);
            formData.append("adminremarks", adminremarks);

            fetch("/admin/shift_application/update", {
                method: "POST",
                body: formData
            })
            .then(async res => {
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || "Server error");
                showNotification(`Table: ${data.message}`, true);

                // ---------- UPDATE ROW STATE ----------
                row.dataset.status = status.toLowerCase();
                row.dataset.decision = admindecision.toLowerCase();

                // update badge text
                const badge = row.querySelector(".status-badge");
                badge.textContent = status;
                badge.className = `badge status-badge ${status.toLowerCase()}`;

                // re-apply filters immediately
                applyFilters();
                
            })
            .catch(e => showNotification(e.message || "Update failed", false));
        });
    });

    // ------------------ Calendar Inline Editing ------------------
    document.querySelectorAll(".save-btn-inline").forEach(btn => {
        btn.addEventListener("click", async function() {
            const shiftBadge = this.closest(".shift-badge");
            const key = shiftBadge.dataset.key;
            const select = shiftBadge.querySelector(".decision-select-inline");
            const textarea = shiftBadge.querySelector(".remarks-input-inline");

            const admindecision = select.value;
            const adminremarks = textarea.value;
            const status = admindecision || "pending";

            const formData = new URLSearchParams();
            formData.append("key", key);
            formData.append("status", status);
            formData.append("admindecision", admindecision);
            formData.append("adminremarks", adminremarks);

            try {
                const res = await fetch("/admin/shift_application/update", {
                    method: "POST",
                    body: formData
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || "Server error");

                showNotification(`Calendar: ${data.message}`, true);

                // ----------- UPDATE UI IN PLACE -----------
                // visual update
                shiftBadge.classList.remove("pending", "approved", "rejected", "cancel");

                if (admindecision)
                    shiftBadge.classList.add(admindecision.toLowerCase());
                else
                    shiftBadge.classList.add("pending");

                // Update actual state
                const finalStatus = admindecision ? admindecision : "pending";

                shiftBadge.dataset.decision = finalStatus;
                shiftBadge.dataset.status = finalStatus;

                // Update the badge text color for visibility (optional)
                const decisionValue = (admindecision || "pending").toLowerCase();

                if (decisionValue === "pending") {
                    shiftBadge.style.color = "#000";
                } else {
                    shiftBadge.style.color = "#fff";
                }

            } catch (e) {
                showNotification(e.message || "Update failed", false);
            }
        });
    });

    // ------------------ Table Filters ------------------
    function applyFilters() {
        const text = filterText.value.toLowerCase();
        const status = filterStatus.value;
        const decision = filterDecision.value;
        const ojt = filterOJT.value;
        const night = filterNight.value;

        document.querySelectorAll("#applicationTable tbody tr").forEach(row => {
            let visible = true;

            if (text) {
                const id = row.dataset.id || "";
                const name = row.dataset.name || "";
                visible &= id.includes(text) || name.includes(text);
            }

            if (filterDate.value && row.dataset.date !== filterDate.value) visible = false;
            if (filterShift.value && row.dataset.shift !== filterShift.value) visible = false;
            if (filterLevel.value && row.dataset.level !== filterLevel.value) visible = false;
            if (status && row.dataset.status !== status) visible = false;
            if (decision && row.dataset.decision !== decision) visible = false;
            if (ojt && row.dataset.ojt !== ojt) visible = false;
            if (night && row.dataset.night !== night) visible = false;

            row.style.display = visible ? "" : "none";
        });
    }

    [
    filterText, filterStatus, filterDecision,
    filterOJT, filterNight, filterDate,
    filterShift, filterLevel
    ].forEach(el => {
        el.addEventListener("input", () => {
            applyFilters();

            // save filters
            localStorage.setItem("adminShiftFilters", JSON.stringify({
                text: filterText.value,
                date: filterDate.value,
                shift: filterShift.value,
                level: filterLevel.value,
                status: filterStatus.value,
                decision: filterDecision.value,
                ojt: filterOJT.value,
                night: filterNight.value
            }));
        });
    });

    applyFilters();
});

