// ======= MAIN.JS =======

// Get the video grid container
const videoGrid = document.getElementById("videos");

// Function to render videos on the page
function renderVideos(videos) {
    videoGrid.innerHTML = "";
    

    videos.forEach(video => {
        const card = document.createElement("div");
        card.className = "video-card";
        card.innerHTML = `
            <img src="${video.thumbnail_url}" alt="${video.title}">
            <h3>${video.title}</h3>
            <a href="${video.youtube_link}" target="_blank">Watch Video</a>
        `;
        videoGrid.appendChild(card);
    });
}

// ======= FETCH PUBLISHED VIDEOS FROM BACKEND =======
async function fetchVideos() {
    try {
        const response = await fetch("/videos");
        if (!response.ok) throw new Error("Network response was not ok");
        const videos = await response.json();
        renderVideos(videos);  // No need to filter here
    } catch (error) {
        console.error("Error loading videos:", error);
        videoGrid.innerHTML = "<p style='text-align:center; color:red;'>Failed to fetch videos</p>";
    }
}


// Initial fetch
fetchVideos();

// ======= SEARCH FUNCTIONALITY =======
const searchBtn = document.getElementById("searchBtn");
const searchInput = document.getElementById("searchInput");

searchBtn.addEventListener("click", () => {
    const query = searchInput.value.trim().toLowerCase();
    const cards = document.querySelectorAll(".video-card");
    cards.forEach(card => {
        const title = card.querySelector("h3").textContent.toLowerCase();
        card.style.display = title.includes(query) ? "block" : "none";
    });
});

// Optional: search on pressing Enter
searchInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") searchBtn.click();
});
