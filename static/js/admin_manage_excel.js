document.addEventListener("DOMContentLoaded", function() {
    const toast = document.getElementById("toast");

    function showToast(message, success = true) {
        if (!toast) return;
        toast.textContent = message;
        toast.className = `toast ${success ? "success" : "error"}`;
        toast.style.display = "block";
        setTimeout(() => {
            toast.style.display = "none";
        }, 3000);
    }

    // Automatically show flash messages from Flask
    if (window.FLASH_MESSAGES && Array.isArray(window.FLASH_MESSAGES)) {
        window.FLASH_MESSAGES.forEach(flash => {
            showToast(flash.message, flash.category === "success");
        });
    }
});
