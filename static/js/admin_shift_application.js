document.addEventListener("DOMContentLoaded", function() {
    let currentRow = null;
    const modal = new bootstrap.Modal(document.getElementById("remarksModal"));
    const modalInput = document.getElementById("modalRemarksInput");

    // ------------------ NOTIFICATION FUNCTION ------------------
    function showNotification(message, isSuccess = true) {
        const box = document.getElementById("notification");
        const text = document.getElementById("notification-text");

        if (!box || !text) {
            console.error("Notification elements not found in DOM");
            alert(message); // fallback
            return;
        }

        text.textContent = message;
        box.classList.remove("hidden");
        box.classList.toggle("success", isSuccess);
        box.classList.toggle("error", !isSuccess);

        setTimeout(() => {
            box.classList.add("hidden");
        }, 3000);
    }
    // ------------------------------------------------------------

    // Edit remarks
    document.querySelectorAll(".edit-remarks-btn").forEach(btn => {
        btn.addEventListener("click", function() {
            currentRow = this.closest("tr");
            modalInput.value = currentRow.querySelector(".admin-remarks-text").textContent;
        });
    });

    // Save modal
    document.getElementById("saveRemarksModal").addEventListener("click", function() {
        if (currentRow) {
            currentRow.querySelector(".admin-remarks-text").textContent = modalInput.value;
            modal.hide();
        }
    });

    // Update status badge on dropdown change
    document.querySelectorAll(".decision-select").forEach(select => {
        select.addEventListener("change", function() {
            const row = this.closest("tr");
            const badge = row.querySelector(".status-badge");
            badge.textContent = this.value;
            badge.className = `badge status-badge ${this.value.toLowerCase()}`;
        });
    });

    // Save button
    document.querySelectorAll(".save-btn").forEach(btn => {
        btn.addEventListener("click", function() {
            const row = this.closest("tr");
            const timestamp = row.dataset.timestamp;
            const key = row.dataset.key;  // composite key: id_date_shift_level
            const status = row.querySelector(".status-badge").textContent;
            const admindecision = row.querySelector(".decision-select").value;
            const adminremarks = row.querySelector(".admin-remarks-text").textContent;

            // ------------------ FORM DATA ------------------
            const formData = new URLSearchParams();
            formData.append("timestamp", timestamp);
            formData.append("key", key);
            formData.append("status", status);
            formData.append("admindecision", admindecision);
            formData.append("adminremarks", adminremarks);
            // -----------------------------------------------

            fetch("/admin/shift_application/update", {
                method: "POST",
                body: formData
            })
            .then(async response => {
                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || "Server error");
                }

                showNotification(data.message, true);
            })
            .catch(error => {
                console.error(error);
                showNotification(error.message || "Update failed", false);
            });
        });
    });
});

// Filter
const filterText = document.getElementById("filterText");
const filterDate = document.getElementById("filterDate");
const filterShift = document.getElementById("filterShift");
const filterLevel = document.getElementById("filterLevel");
const filterStatus = document.getElementById("filterStatus");
const filterDecision = document.getElementById("filterDecision");
const filterOJT = document.getElementById("filterOJT");
const filterNight = document.getElementById("filterNight");

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

        if (filterDate.value && row.dataset.date !== filterDate.value) {
            visible = false;
        }

        if (filterShift.value && row.dataset.shift !== filterShift.value) {
            visible = false;
        }

        if (filterLevel.value && row.dataset.level !== filterLevel.value) {
            visible = false;
        }

        if (status && row.dataset.status !== status) visible = false;
        if (decision && row.dataset.decision !== decision) visible = false;
        if (ojt && row.dataset.ojt !== ojt) visible = false;
        if (night && row.dataset.night !== night) visible = false;

        row.style.display = visible ? "" : "none";
    });
}

[
  filterText,
  filterStatus,
  filterDecision,
  filterOJT,
  filterNight,
  filterDate,
  filterShift,
  filterLevel
].forEach(el => el.addEventListener("input", applyFilters));

