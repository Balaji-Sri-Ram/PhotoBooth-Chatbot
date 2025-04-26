// ======= Global Variables =======
let uploadedFile = null;
let cameraStream = null;
let capturedImageData = null; // For camera photo
let analyzingMsgEl = null;

// ======= Handle File Selection from Upload Button =======
document.getElementById("imageInput").addEventListener("change", function (e) {
    uploadedFile = e.target.files[0];
    capturedImageData = null; // Clear any old camera image
    if (uploadedFile) {
        appendMessage("user", `📷 Selected: ${uploadedFile.name}`);
    }
});

// ======= Analyze Image When Button Is Clicked =======
function analyzeImage() {
    if (uploadedFile) {
        // ✅ Analyze uploaded image
        analyzeUploadedFile(uploadedFile);
    } else if (capturedImageData) {
        // ✅ Analyze captured image
        analyzeCapturedImage(capturedImageData);
    } else {
        appendMessage("bot", "❗ Please upload or capture an image first.");
    }
}

// ======= Analyze Uploaded File =======
function analyzeUploadedFile(file) {
    analyzingMsgEl = appendMessage("bot", `<span class="spinner"></span> Analyzing your photo, hang tight...`, true);

    const formData = new FormData();
    formData.append("image", file);

    fetch("/image", {
        method: "POST",
        body: formData,
    })
        .then((res) => res.json())
        .then((data) => {
            removeAnalyzingMsg();
            appendMessage("bot", data.response);
        })
        .catch((err) => {
            removeAnalyzingMsg();
            appendMessage("bot", "🚫 Error analyzing image.");
            console.error(err);
        });
}

// ======= Analyze Captured Base64 Image =======
function analyzeCapturedImage(imageData) {
    analyzingMsgEl = appendMessage("bot", `<span class="spinner"></span> Analyzing your captured photo...`, true);

    fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageData })
    })
        .then(response => response.json())
        .then(data => {
            removeAnalyzingMsg();
            appendMessage("bot", data.response || "No response from AI.");
        })
        .catch(error => {
            removeAnalyzingMsg();
            appendMessage("bot", "🚫 Error analyzing image.");
            console.error("Camera analyze error:", error);
        });
}

// ======= Message Display Logic =======
function appendMessage(sender, message, isHTML = false) {
    const chatBox = document.getElementById("chat-messages");
    const bubble = document.createElement("div");
    bubble.className = sender === "user" ? "msg user" : "msg bot";

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const timestamp = `<div class="timestamp">${time}</div>`;

    if (isHTML) {
        bubble.innerHTML = message + timestamp;
    } else {
        bubble.innerText = message;
        bubble.innerHTML += timestamp;
    }

    chatBox.appendChild(bubble);
    chatBox.scrollTop = chatBox.scrollHeight;
    return bubble;
}

function removeAnalyzingMsg() {
    if (analyzingMsgEl) {
        analyzingMsgEl.remove();
        analyzingMsgEl = null;
    }
}

// ======= Camera Controls =======
function startCamera() {
    const cameraSection = document.getElementById("cameraSection");
    const video = document.getElementById("video");

    cameraSection.style.display = "block";

    navigator.mediaDevices.getUserMedia({ video: true })
        .then((stream) => {
            cameraStream = stream;
            video.srcObject = stream;
        })
        .catch((err) => {
            alert("Error accessing camera: " + err);
        });
}

function stopCamera() {
    const cameraSection = document.getElementById("cameraSection");
    const video = document.getElementById("video");

    if (cameraStream) {
        let tracks = cameraStream.getTracks();
        tracks.forEach(track => track.stop());
        cameraStream = null;
    }

    video.srcObject = null;
    cameraSection.style.display = "none";
}

// ======= Capture Photo and Store for Manual Analyze =======
function capturePhoto() {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const context = canvas.getContext('2d');
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    capturedImageData = canvas.toDataURL('image/png'); // 🔁 Store it for later

    // Show in chat
    appendMessage("user", `<img src="${capturedImageData}" alt="Captured Photo" width="150" />`, true);

    uploadedFile = null; // Clear uploaded file if switching to camera
    stopCamera();
}