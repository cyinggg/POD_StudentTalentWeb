// ----------------------------
// Canvas setup per row
// ----------------------------
const canvases = {};
const ctxs = {};
const drawing = {};
const hasDrawn = {};

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".sign-canvas").forEach(canvas => {
        const idx = canvas.id.split("_")[1];
        canvases[idx] = canvas;
        ctxs[idx] = canvas.getContext("2d");
        drawing[idx] = false;
        hasDrawn[idx] = false;

        ctxs[idx].lineWidth = 2;
        ctxs[idx].lineCap = "round";
        ctxs[idx].strokeStyle = "#000";

        canvas.addEventListener("mousedown", e => startDraw(e, idx));
        canvas.addEventListener("mousemove", e => draw(e, idx));
        canvas.addEventListener("mouseup", () => stopDraw(idx));
        canvas.addEventListener("mouseleave", () => stopDraw(idx));
    });
});

function getPos(e, canvas) {
    const r = canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
}

function startDraw(e, idx) {
    drawing[idx] = true;
    hasDrawn[idx] = true;
    const pos = getPos(e, canvases[idx]);
    ctxs[idx].beginPath();
    ctxs[idx].moveTo(pos.x, pos.y);
}

function draw(e, idx) {
    if (!drawing[idx]) return;
    const pos = getPos(e, canvases[idx]);
    ctxs[idx].lineTo(pos.x, pos.y);
    ctxs[idx].stroke();
}

function stopDraw(idx) { drawing[idx] = false; }

function clearCanvas(idx) {
    ctxs[idx].clearRect(0, 0, canvases[idx].width, canvases[idx].height);
    hasDrawn[idx] = false;
    const fileInput = document.getElementById(`file_${idx}`);
    if (fileInput) fileInput.value = "";
    const preview = document.getElementById(`preview_${idx}`);
    if (preview) { preview.src = ""; preview.style.display = "none"; }
}

// ----------------------------
// Upload preview
// ----------------------------
function previewFile(idx) {
    const fileInput = document.getElementById(`file_${idx}`);
    const preview = document.getElementById(`preview_${idx}`);
    if (fileInput.files && fileInput.files[0]) {
        const reader = new FileReader();
        reader.onload = e => {
            preview.src = e.target.result;
            preview.style.display = "block";
        };
        reader.readAsDataURL(fileInput.files[0]);
    } else {
        preview.src = "";
        preview.style.display = "none";
    }
}

// ----------------------------
// Canvas blank detection
// ----------------------------
function isCanvasBlank(canvas) {
    const blank = document.createElement("canvas");
    blank.width = canvas.width;
    blank.height = canvas.height;
    return canvas.toDataURL() === blank.toDataURL();
}

// ----------------------------
// Verify shift submission
// ----------------------------
function verifyShift(key, idx) {
    const staffnameInput = document.getElementById(`staffname_${idx}`);
    const remarksInput = document.getElementById(`remarks_${idx}`);
    const fileInput = document.getElementById(`file_${idx}`);
    const canvas = canvases[idx];

    const staffname = staffnameInput.value.trim();
    const remarks = remarksInput.value.trim();

    if (!staffname) { alert("Staff name is required"); return; }

    const formData = new FormData();
    formData.append("key", key);
    formData.append("staffname", staffname);
    formData.append("remarks", remarks);

    // Use canvas if drawn and not blank
    if (hasDrawn[idx] && !isCanvasBlank(canvas)) {
        formData.append("canvasData", canvas.toDataURL("image/png"));
    } else if (fileInput.files.length > 0) {
        formData.append("staffsign", fileInput.files[0]);
    } else {
        alert("Signature required (draw or upload)"); return;
    }

    fetch("/admin/verify_shifts/save", { method: "POST", body: formData })
    .then(r => r.json())
    .then(data => {
        if (!data.success) { alert(data.error || "Save failed"); return; }
        const btn = document.getElementById(`verifyBtn_${idx}`);
        btn.textContent = "Verified ✓";
        btn.disabled = true;
        btn.classList.add("verified");
    })
    .catch(err => { console.error(err); alert("Server error"); });
}
