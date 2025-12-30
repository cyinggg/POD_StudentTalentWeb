document.addEventListener("DOMContentLoaded", () => {

    document.querySelectorAll(".shift-block").forEach(block => {

        block.addEventListener("click", async () => {

            // Ineligible guard
            if (block.classList.contains("ineligible")) {
                alert("You are not eligible to book this shift.");
                return;
            }

            // Determine status safely
            let status = "";
            if (block.classList.contains("open")) status = "open";
            else if (block.classList.contains("pending")) status = "pending";
            else if (block.classList.contains("approved")) status = "approved";

            if (!status) {
                alert("Invalid shift status.");
                return;
            }

            // Determine action
            let action = "book";
            if (status === "pending") {
                if (!confirm("Cancel this pending shift?")) return;
                action = "cancel";
            }
            if (status === "approved") {
                if (!confirm("This shift is approved. Cancellation requires admin approval. Proceed?")) return;
                action = "cancel";
            }

            // Prepare payload
            const formData = new FormData();
            formData.append("date", block.dataset.date);
            formData.append("shiftperiod", block.dataset.shift);
            formData.append("shiftlevel", block.dataset.level);
            formData.append("action", action);

            try {
                const resp = await fetch("/student_coach/shift_action", {
                    method: "POST",
                    body: formData
                });

                const data = await resp.json();

                if (data.success) {
                    location.reload();
                } else {
                    alert(data.error || data.message || "Action failed");
                }
            } catch (err) {
                console.error(err);
                alert("Server error. Please try again.");
            }
        });

    });

});
