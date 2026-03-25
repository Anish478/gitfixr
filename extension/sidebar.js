const box     = document.getElementById("box");
const prLink  = document.getElementById("pr-link");
const prAnchor = document.getElementById("pr-anchor");

// On popup open: read current status from storage (handles case where
// pipeline already finished before the user opened the popup)
chrome.storage.local.get(["status", "pr_url", "error"], (stored) => {
  if (stored.status) render(stored);
});

// Also listen for live updates pushed from background.js while popup is open
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "PIPELINE_UPDATE") render(msg.payload);
});

function render({ status, pr_url, error }) {
  box.className = "";   // reset class list

  if (status === "running") {
    box.classList.add("running");
    box.textContent = "⏳ Pipeline running…";
    prLink.style.display = "none";

  } else if (status === "success") {
    box.classList.add("success");
    box.textContent = "✅ Fix complete!";
    prLink.style.display = "block";
    prAnchor.href = pr_url;

  } else if (status === "failed") {
    box.classList.add("failed");
    box.textContent = `❌ Pipeline failed: ${error ?? "check backend logs"}`;

  } else if (status === "error") {
    box.classList.add("failed");
    box.textContent = `⚠️ Could not reach backend`;
  }
}