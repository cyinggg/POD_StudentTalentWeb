function clockAction(action, key) {
    const formData = new FormData();
    formData.append("action", action);
    formData.append("key", key);

    fetch("/student/attendance/clock", {
        method: "POST",
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert(action.toUpperCase() + " successful");
            location.reload();
        } else {
            alert(data.error);
        }
    });
}

function saveAttendance(key, idx) {
    const formData = new FormData();
    formData.append("key", key);
    formData.append("shiftstart", document.getElementById("start_" + idx).value);
    formData.append("shiftend", document.getElementById("end_" + idx).value);
    formData.append("remarks", document.getElementById("remarks_" + idx).value);

    fetch("/student/attendance/save", {
        method: "POST",
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert("Saved successfully");
            location.reload();
        } else {
            alert(data.error);
        }
    });
}
