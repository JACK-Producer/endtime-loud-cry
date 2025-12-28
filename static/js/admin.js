const API_URL = "/admin/video";
const GET_URL = "/admin/videos/all"; // new route to get all videos


const videoForm = document.getElementById("videoForm");
const formMessage = document.getElementById("formMessage");
const videoList = document.getElementById("videoList");

/* =========================
   LOAD VIDEOS
========================= */
/* =========================
   LOAD VIDEOS
========================= */
function loadVideos() {
    fetch(GET_URL)
        .then(res => res.json())
        .then(videos => {
            videoList.innerHTML = "";

            videos.forEach(video => {
                const card = document.createElement("div");
                card.className = "video-card";

                // Format publish date
                let publishedDateText = "Not published yet";
                if (video.published_at) {
                    const date = new Date(video.published_at);
                    publishedDateText = `Published on ${date.toLocaleDateString(
                        "en-GB",
                        { year: "numeric", month: "long", day: "numeric" }
                    )}`;
                }

                card.innerHTML = `
                    <img src="${video.thumbnail_url}" alt="${video.title}">

                    <p class="publish-date">${publishedDateText}</p>

                    <input 
                        type="text"
                        value="${video.title}"
                        id="title-${video.id}"
                        class="locked"
                        readonly
                    >

                    <input 
                        type="url"
                        value="${video.youtube_link}"
                        id="link-${video.id}"
                        class="locked"
                        readonly
                    >

                    <div class="card-actions">
                        <button class="edit-btn" onclick="enableEdit(${video.id})">
                            Edit
                        </button>
                        <button class="danger-btn" onclick="deleteVideo(${video.id})">
                            Delete
                        </button>
                    </div>
                `;

                videoList.appendChild(card);
            });
        })
        .catch(err => {
            console.error("Error loading videos:", err);
        });
}




/* =========================
   ADD VIDEO
========================= */
videoForm.addEventListener("submit", function (e) {
    e.preventDefault();

    const title = document.getElementById("title").value;
    const youtube_link = document.getElementById("youtube_link").value;

    fetch(API_URL, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, youtube_link })
    })
    .then(async res => {
        const text = await res.text();
        if (!res.ok) throw new Error(text || "Failed to add video");
    })
    .then(() => {
        formMessage.innerText = "Video added successfully";
        videoForm.reset();
        loadVideos();
    })
    .catch(err => {
        formMessage.innerText = err.message;
        console.error(err);
    });
});

/* =========================
   ENABLE EDIT MODE
========================= */
function enableEdit(id) {
    const title = document.getElementById(`title-${id}`);
    const link = document.getElementById(`link-${id}`);

    title.removeAttribute("readonly");
    link.removeAttribute("readonly");

    title.classList.remove("locked");
    link.classList.remove("locked");

    title.focus();

    const actions = title.closest(".video-card")
        .querySelector(".card-actions");

    actions.innerHTML = `
        <button class="save-btn" onclick="saveEdit(${id})">
            Save
        </button>
        <button class="cancel-btn" onclick="cancelEdit(${id})">
            Cancel
        </button>
    `;
}


/* =========================
   SAVE EDIT
========================= */
function saveEdit(id) {
    const title = document.getElementById(`title-${id}`).value;
    const youtube_link = document.getElementById(`link-${id}`).value;

    fetch(`${API_URL}/${id}`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, youtube_link })
    })
    .then(res => {
        if (!res.ok) throw new Error("Failed to update");
        loadVideos();   // 🔒 reloads LOCKED state
    })
    .catch(err => alert(err.message));
}


/* =========================
   CANCEL EDIT
========================= */
function cancelEdit(id) {
    loadVideos(); // reload original data
}

/* =========================
   DELETE VIDEO
========================= */
function deleteVideo(id) {
    if (!confirm("Are you sure you want to delete this video?")) return;

    fetch(`${API_URL}/${id}`, {
        method: "DELETE",
        credentials: "include"
    })
    .then(() => loadVideos())
    .catch(err => console.error(err));
}

/* =========================
   INIT
========================= */
loadVideos();
