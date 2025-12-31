document.addEventListener("DOMContentLoaded", function() {
    let currentRow = null;
    const modal = new bootstrap.Modal(document.getElementById("remarksModal"));
    const modalInput = document.getElementById("modalRemarksInput");

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

            fetch(updateUrl, {
                method: "POST",
                headers: {"Content-Type": "application/x-www-form-urlencoded"},
                body: new URLSearchParams({
                    timestamp: timestamp,
                    status: status,
                    admindecision: admindecision,
                    adminremarks: adminremarks
                })
            })
            .then(res => res.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message || "Updated successfully!");
            } else {
                showNotification("Error: " + data.error);
            }
        })
        .catch(err => showNotification("Request failed: " + err));

        function showNotification(msg) {
            const toast = document.getElementById("toast");
            toast.textContent = msg;
            toast.classList.remove("hidden");
            setTimeout(() => toast.classList.add("hidden"), 3000);
        }
        });
    });
});
