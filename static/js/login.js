document.addEventListener("DOMContentLoaded", function() {
    const form = document.getElementById("loginForm");
    const errorDiv = document.getElementById("errorMsg");

    form.addEventListener("submit", function(e) {
        e.preventDefault(); // prevent default form submit

        const id = document.getElementById("id").value.trim();
        const contact = document.getElementById("contact").value.trim();
        errorDiv.innerText = "";

        if(!id || !contact){
            errorDiv.innerText = "Please enter both ID and contact.";
            return;
        }

        fetch("/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ id, contact })
        })
        .then(res => res.json())
        .then(data => {
            if(data.success && data.redirect){
                window.location.href = data.redirect; // redirect to student or admin home
            } else {
                errorDiv.innerText = data.error || "Login failed";
            }
        })
        .catch(err => {
            console.error(err);
            errorDiv.innerText = "Server error, try again later.";
        });
    });
});
