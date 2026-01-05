// ================= File Validation & Toast System =================

document.addEventListener("DOMContentLoaded", () => {
    const uploadForm = document.querySelector("form");
    const fileInput = document.querySelector("input[type='file']");
    const toast = document.getElementById("toast");

    // Allowed system Excel files
    const allowedFiles = [
        "account.xlsx",
        "slot_control.xlsx",
        "shift_application.xlsx",
        "shift_record.xlsx",
        "shift_verify.xlsx"
    ];

    // ====== Show Toast ======
    window.showToast = function(message, success = true) {
        toast.textContent = message;
        toast.className = "toast " + (success ? "success" : "error");
        toast.style.display = "block";
        setTimeout(() => { toast.style.display = "none"; }, 3000);
    };

    // ====== Upload Validation ======
    if (uploadForm) {
        uploadForm.addEventListener("submit", function(e) {
            if (!fileInput.files.length) {
                showToast("Please select a file to upload.", false);
                e.preventDefault();
                return;
            }

            const filename = fileInput.files[0].name.toLowerCase();

            // Check extension
            if (!filename.endsWith(".xlsx") && !filename.endsWith(".xls")) {
                showToast("Only Excel files (.xlsx, .xls) are allowed.", false);
                e.preventDefault();
                return;
            }

            // Check whitelist
            if (!allowedFiles.includes(filename)) {
                showToast("This file is not allowed. Upload system Excel files only.", false);
                e.preventDefault();
                return;
            }
        });
    }

    // ====== Show Flask flash messages (if any) ======
    if (window.FLASH_MESSAGES && Array.isArray(window.FLASH_MESSAGES)) {
        window.FLASH_MESSAGES.forEach(msg => {
            showToast(msg.message, msg.category === "success");
        });
    }
});
