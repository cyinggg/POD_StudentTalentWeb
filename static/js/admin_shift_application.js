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
            const status = row.querySelector(".status-badge").textContent;
            const admindecision = row.querySelector(".decision-select").value;
            const adminremarks = row.querySelector(".admin-remarks-text").textContent;

            // ------------------ FORM DATA ------------------
            const formData = new URLSearchParams();
            formData.append("timestamp", timestamp);
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
