// CANVAS DRAW
document.querySelectorAll(".sign-canvas").forEach(canvas => {
    const ctx = canvas.getContext("2d");
    let drawing = false;

    canvas.addEventListener("mousedown", () => {
        drawing = true;
        ctx.beginPath();
    });

    canvas.addEventListener("mouseup", () => drawing = false);
    canvas.addEventListener("mouseleave", () => drawing = false);

    canvas.addEventListener("mousemove", e => {
        if (!drawing) return;
        ctx.lineWidth = 2;
        ctx.lineCap = "round";
        ctx.strokeStyle = "#000";
        ctx.lineTo(e.offsetX, e.offsetY);
        ctx.stroke();
    });
});

function clearCanvas(i) {
    const c = document.getElementById("canvas_" + i);
    c.getContext("2d").clearRect(0, 0, c.width, c.height);
}

// VERIFY AJAX
function verifyShift(key, i) {
    const remarks = document.getElementById("remarks_" + i).value;
    const canvas = document.getElementById("canvas_" + i);
    const file = document.getElementById("file_" + i).files[0];

    const canvasData = canvas.toDataURL();
    const hasCanvas = canvasData.length > 1000;

    const form = new FormData();
    form.append("key", key);
    form.append("remarks", remarks);

    if (hasCanvas) {
        form.append("canvasData", canvasData);
    } else if (file) {
        form.append("staffsign", file);
    } else {
        alert("Signature required");
        return;
    }

    fetch("/admin/verify_shifts/save", {
        method: "POST",
        body: form
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("Shift verified successfully ✔");
        } else {
            alert(data.error);
        }
    })
    .catch(() => alert("Server error"));
}
