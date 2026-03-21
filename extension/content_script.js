function extractIssueData() {
  const title = document.querySelector('[data-testid="issue-title"]')?.innerText
             || document.querySelector('.js-issue-title')?.innerText
             || document.title;

  const body  = document.querySelector('.markdown-body')?.innerText
             || "";

  const url   = window.location.href;

  return { issue_url: url, issue_title: title.trim(), issue_body: body.trim() };
}

console.log("[gitFixr] content script loaded on:", window.location.href);

const data = extractIssueData();
console.log("[gitFixr] extracted issue data:", data);

chrome.runtime.sendMessage(
  { type: "ISSUE_DETECTED", payload: data },
  (response) => {
    if (chrome.runtime.lastError) {
      console.warn("[gitFixr] sendMessage error:", chrome.runtime.lastError);
    } else {
      console.log("[gitFixr] run_id received:", response?.run_id);
    }
  }
);