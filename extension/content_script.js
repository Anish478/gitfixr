function extractIssueData() {
  const title = document.querySelector('[data-testid="issue-title"]')?.innerText
    || document.querySelector('.js-issue-title')?.innerText
    || document.title;

  const body = document.querySelector('[data-testid="issue-body"]')?.innerText
    || document.querySelector('.markdown-body')?.innerText
    || document.querySelector('.comment-body')?.innerText
    || "";

  const url = window.location.href;
  const commentEls = document.querySelectorAll('.js-comment-body, [data-testid="comment-body"]');
  const comments = Array.from(commentEls)
    .slice(1)
    .map(el => el.innerText.trim())
    .filter(c => c.length > 0);

  const images = Array.from(
    document.querySelectorAll('.markdown-body img')
  ).map(img => img.src);

  return { issue_url: url, issue_title: title.trim(), issue_body: body.trim(), issue_comments: comments, issue_images: images };

}

console.log("[gitFixr] content script loaded on:", window.location.href);

// Wait for GitHub to finish rendering the issue body dynamically
setTimeout(() => {
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
}, 2000);