const BACKEND_URL = "http://localhost:8000";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "ISSUE_DETECTED") {
    handleIssueDetected(message.payload, sendResponse);
    return true;  // keep channel open for async sendResponse
  }
});

async function handleIssueDetected(payload, sendResponse) {
  try {
    const res = await fetch(`${BACKEND_URL}/fix-issue`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    const { run_id } = data;

    // Persist so sidebar can read it later
    await chrome.storage.local.set({ run_id, status: "running" });

    console.log("[gitFixr] pipeline started, run_id:", run_id);
    sendResponse({ run_id });

  } catch (err) {
    console.error("[gitFixr] backend error:", err);
    sendResponse({ error: err.message });
  }
}