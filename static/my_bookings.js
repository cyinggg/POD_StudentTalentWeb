$(document).ready(function () {
    $.get("/api/applications", function (data) {
        const tbody = $("#myBookingsTable tbody");
        tbody.empty();

        if (!data || data.length === 0) {
            tbody.append(`<tr><td colspan="5" class="text-center p-4">No bookings found</td></tr>`);
            return;
        }

        data.forEach(app => {
            tbody.append(`
                <tr>
                    <td class="border px-2 py-1">${app.date}</td>
                    <td class="border px-2 py-1">${app.shift}</td>
                    <td class="border px-2 py-1">${app.level}</td>
                    <td class="border px-2 py-1">${app.slot}</td>
                    <td class="border px-2 py-1">${app.status}</td>
                </tr>
            `);
        });
    });
});
