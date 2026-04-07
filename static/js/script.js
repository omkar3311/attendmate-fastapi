async function fetchAttendance() {
    try {
        const response = await fetch("/live-attendance");
        const data = await response.json();
        
        if (data.no_slots == true) {
            document.getElementById("attendance-data").innerHTML =
                `<p class="no-slots">No slots available</p>`;
            document.getElementById("live-camera").classList.remove("active");
            return;
        }

        let html = "";
        let attendanceLive = false;
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
                    attendanceLive = true;
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
        const camera = document.getElementById("live-camera");
        if (attendanceLive) {
            camera.classList.add("active");
        } else {
            camera.classList.remove("active");
        }

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
const toggle = document.getElementById("chatbot-toggle");
const container = document.getElementById("chatbot-container");
const closeBtn = document.getElementById("chatbot-close");

const input = document.getElementById("chatbot-input");
const sendBtn = document.getElementById("chatbot-send");
const messages = document.getElementById("chatbot-messages");

let chatHistory = [];

toggle.onclick = () => {
    container.style.display = "flex";
};

closeBtn.onclick = () => {
    container.style.display = "none";
};

sendBtn.onclick = sendMessage;
input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
});

async function sendMessage(){

let text = input.value.trim();
if(!text) return;

addMessage(text,"user");
input.value = "";

const botDiv = document.createElement("div");
botDiv.className = "chat-bot";

botDiv.innerHTML = `<div class="stream-text"></div>`;

messages.appendChild(botDiv);

const streamText = botDiv.querySelector(".stream-text");

messages.scrollTop = messages.scrollHeight;

const response = await fetch("/chat/groq",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({
query:text,
file_name:"data/attendmate.txt",
session_id:"student"
})
});

const data = await response.json();

let fullText = data.answer;

let i = 0;

function stream(){

if(i < fullText.length){

let current = fullText.substring(0,i);

streamText.innerHTML = current + `<span class="typing">...</span>`;

i++;

messages.scrollTop = messages.scrollHeight;

setTimeout(stream,8);

}else{

streamText.innerHTML = fullText;

}

}

stream();

}

function addMessage(text, sender) {
    const div = document.createElement("div");
    div.className = sender === "user" ? "chat-user" : "chat-bot";
    div.innerText = text;

    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;

    chatHistory.push({ sender, text });
}


// Draggable

dragElement(toggle);

function dragElement(el) {
    let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;

    el.onmousedown = dragMouseDown;

    function dragMouseDown(e) {
        e.preventDefault();

        pos3 = e.clientX;
        pos4 = e.clientY;

        document.onmouseup = closeDrag;
        document.onmousemove = elementDrag;
    }

    function elementDrag(e) {
        e.preventDefault();

        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;

        pos3 = e.clientX;
        pos4 = e.clientY;

        el.style.top = (el.offsetTop - pos2) + "px";
        el.style.left = (el.offsetLeft - pos1) + "px";
    }

    function closeDrag() {
        document.onmouseup = null;
        document.onmousemove = null;
    }
}   