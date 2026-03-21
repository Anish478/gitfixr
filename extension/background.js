// TODO: Service worker — bridges extension UI and backend
// Responsibilities:
//   1. Receive issue data from content_script.js
//   2. POST to backend /fix-issue, get back run_id
//   3. Open WebSocket to /stream/{run_id}
//   4. Forward events to sidebar.js via chrome.runtime.sendMessage
