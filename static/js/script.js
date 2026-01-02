async function fetchAttendance() {
    try {
        const response = await fetch("/live-attendance");
        const data = await response.json();
        let html = "";
        for (const date in data) {
            html += `<h3>Date: ${date}</h3>`;

            for (const slot in data[date]) {
                html += `
                    <h4>${slot}</h4>
                    <table>
                        <tr>
                            <th>Name</th>
                            <th>Status</th>
                            <th>Minutes</th>
                        </tr>
                `;
                for (const name in data[date][slot]) {
                    const person = data[date][slot][name];
                    html += `
                        <tr>
                            <td>${person.name}</td>
                            <td>${person.status}</td>
                            <td>${person.minutes}</td>
                        </tr> `;
                }
                html += "</table>";
            }}
        document.getElementById("attendance-data").innerHTML = html;

    } catch (error) {
        console.error("Failed to fetch attendance:", error);
        document.getElementById("attendance-data").innerText =
            "Error loading attendance data";
    }
}

setInterval(fetchAttendance, 1000);
window.onload = fetchAttendance;

document.getElementById("upload-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const status = document.getElementById("upload-status");
    const formData = new FormData(e.target);
    try {
        const response = await fetch("/upload-image", {
            method: "POST",
            body: formData
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Upload failed");
        }
        status.style.color = "green";
        status.innerText = data.message;
    } catch (err) {
        console.error(err);
        status.style.color = "red";
        status.innerText = "Server error";
    }
});
