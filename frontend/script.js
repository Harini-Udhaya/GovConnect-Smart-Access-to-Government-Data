// ── Config ──────────────────────────────────────────────────────────────────

const API_BASE = "http://localhost:8000";

// ── State ────────────────────────────────────────────────────────────────────

let pendingFiles = [];        // FileList awaiting upload
let queryCount   = 0;
let sidebarOpen  = true;
let isProcessing = false;

// ── DOM refs ─────────────────────────────────────────────────────────────────

const $  = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

const apiKeyInput   = $("apiKeyInput");
const keyToggle     = $("keyToggle");
const keyStatus     = $("keyStatus");
const uploadZone    = $("uploadZone");
const fileInput     = $("fileInput");
const uploadBtn     = $("uploadBtn");
const uploadProgress = $("uploadProgress");
const progressFill  = $("progressFill");
const progressLabel = $("progressLabel");
const docList       = $("docList");
const statDocs      = $("statDocs");
const statChunks    = $("statChunks");
const statQueries   = $("statQueries");
const resetBtn      = $("resetBtn");
const sidebarToggle = $("sidebarToggle");
const sidebar       = $("sidebar");
const chatWindow    = $("chatWindow");
const welcomeState  = $("welcomeState");
const messages      = $("messages");
const queryInput    = $("queryInput");
const sendBtn       = $("sendBtn");
const topbarStatus  = $("topbarStatus");
const statusDot     = $("statusDot");
const statusText    = $("statusText");
const sampleQueries = $("sampleQueries");

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  refreshStats();
  bindEvents();
});

// ── Bind Events ──────────────────────────────────────────────────────────────

function bindEvents() {
  // API key input
  apiKeyInput.addEventListener("input", onApiKeyChange);
  keyToggle.addEventListener("click", toggleKeyVisibility);

  // Upload zone
  uploadZone.addEventListener("click", () => fileInput.click());
  uploadZone.addEventListener("dragover", e => { e.preventDefault(); uploadZone.classList.add("drag-over"); });
  uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("drag-over"));
  uploadZone.addEventListener("drop", e => {
    e.preventDefault();
    uploadZone.classList.remove("drag-over");
    handleFilePick(e.dataTransfer.files);
  });
  fileInput.addEventListener("change", () => handleFilePick(fileInput.files));
  uploadBtn.addEventListener("click", uploadFiles);

  // Sidebar toggle
  sidebarToggle.addEventListener("click", () => {
    sidebarOpen = !sidebarOpen;
    sidebar.classList.toggle("collapsed", !sidebarOpen);
  });

  // Reset
  resetBtn.addEventListener("click", resetIndex);

  // Send query
  sendBtn.addEventListener("click", sendQuery);
  queryInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuery();
    }
  });
  queryInput.addEventListener("input", autoResize);
  queryInput.addEventListener("input", updateSendBtn);

  // Sample queries
  sampleQueries?.addEventListener("click", e => {
    const chip = e.target.closest(".sample-chip");
    if (!chip) return;
    queryInput.value = chip.dataset.q;
    autoResize();
    updateSendBtn();
    queryInput.focus();
  });
}

// ── API Key ──────────────────────────────────────────────────────────────────

function onApiKeyChange() {
  const key = apiKeyInput.value.trim();
  if (key.startsWith("gsk_") && key.length > 10) {
    keyStatus.className = "key-status active";
    keyStatus.innerHTML = `<span class="dot"></span> Key provided`;
    setStatus("online", "Ready");
  } else {
    keyStatus.className = "key-status";
    keyStatus.innerHTML = `<span class="dot"></span> No key provided`;
    setStatus("offline", "No API key");
  }
  updateSendBtn();
}

function toggleKeyVisibility() {
  const isHidden = apiKeyInput.type === "password";
  apiKeyInput.type = isHidden ? "text" : "password";
  keyToggle.title = isHidden ? "Hide key" : "Show key";
}

// ── File Handling ─────────────────────────────────────────────────────────────

function handleFilePick(files) {
  if (!files || !files.length) return;
  pendingFiles = Array.from(files).filter(f => f.name.toLowerCase().endsWith(".pdf"));
  if (pendingFiles.length === 0) {
    showToast("Only PDF files are accepted.", "warn");
    return;
  }
  uploadBtn.disabled = false;
  uploadBtn.textContent = `Index ${pendingFiles.length} PDF${pendingFiles.length > 1 ? "s" : ""}`;
  uploadBtn.prepend(makeIcon());
}

function makeIcon() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", "14"); svg.setAttribute("height", "14");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2.5");
  svg.innerHTML = `<polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/><path d="M20 21H4"/>`;
  return svg;
}

async function uploadFiles() {
  if (!pendingFiles.length) return;

  uploadBtn.disabled = true;
  uploadProgress.style.display = "block";
  progressFill.style.width = "20%";
  progressLabel.textContent = "Uploading…";
  setStatus("busy", "Indexing…");

  const formData = new FormData();
  pendingFiles.forEach(f => formData.append("files", f));

  try {
    progressFill.style.width = "55%";
    progressLabel.textContent = "Processing PDFs…";

    const resp = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });

    progressFill.style.width = "85%";
    progressLabel.textContent = "Indexing embeddings…";

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || "Upload failed");
    }

    const data = await resp.json();
    progressFill.style.width = "100%";
    progressLabel.textContent = "Done!";

    // Render doc pills
    data.results.forEach(r => {
      if (r.status === "success") addDocPill(r.file, r.chunks_indexed);
    });

    await refreshStats();
    const ok = data.results.filter(r => r.status === "success").length;
    showToast(`✅ ${ok} document${ok > 1 ? "s" : ""} indexed successfully`, "success");
    setStatus("online", "Ready");

    setTimeout(() => {
      uploadProgress.style.display = "none";
      progressFill.style.width = "0%";
    }, 1200);

  } catch (e) {
    progressLabel.textContent = `Error: ${e.message}`;
    showToast(`❌ ${e.message}`, "error");
    setStatus("offline", "Error");
    uploadBtn.disabled = false;
  }

  pendingFiles = [];
  fileInput.value = "";
}

function addDocPill(name, chunks) {
  const div = document.createElement("div");
  div.className = "doc-item";
  div.innerHTML = `
    <span class="doc-item-icon">📄</span>
    <span class="doc-item-name" title="${name}">${name}</span>
    <span class="doc-item-badge">${chunks} chunks</span>
  `;
  docList.appendChild(div);
}

// ── Stats ─────────────────────────────────────────────────────────────────────

async function refreshStats() {
  try {
    const resp = await fetch(`${API_BASE}/stats`);
    if (!resp.ok) return;
    const data = await resp.json();
    statDocs.textContent   = data.total_documents ?? 0;
    statChunks.textContent = data.total_chunks    ?? 0;
    statQueries.textContent = queryCount;
  } catch { /* API not running yet */ }
}

// ── Reset ─────────────────────────────────────────────────────────────────────

async function resetIndex() {
  if (!confirm("This will clear all indexed documents. Continue?")) return;
  try {
    await fetch(`${API_BASE}/reset`, { method: "POST" });
    docList.innerHTML = "";
    queryCount = 0;
    await refreshStats();
    showToast("Index reset.", "info");
  } catch (e) {
    showToast("Reset failed: " + e.message, "error");
  }
}

// ── Chat ──────────────────────────────────────────────────────────────────────

async function sendQuery() {
  const question = queryInput.value.trim();
  if (!question || isProcessing) return;

  const apiKey = apiKeyInput.value.trim();
  if (!apiKey) {
    showToast("Please enter your Groq API key.", "warn");
    return;
  }

  // Hide welcome
  welcomeState?.remove();

  isProcessing = true;
  updateSendBtn();
  setStatus("busy", "Thinking…");

  // Append user message
  appendMessage("user", question);
  queryInput.value = "";
  autoResize();

  // Show thinking indicator
  const thinkId = showThinking();

  try {
    const resp = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, groq_api_key: apiKey }),
    });

    removeThinking(thinkId);

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || "Query failed");
    }

    const data = await resp.json();
    const isFallback = data.answer.includes("not available in the provided documents");
    appendMessage("ai", data.answer, data.sources, isFallback);

    queryCount++;
    statQueries.textContent = queryCount;
    setStatus("online", "Ready");

  } catch (e) {
    removeThinking(thinkId);
    appendMessage("ai", `⚠️ Error: ${e.message}`, [], true);
    setStatus("offline", "Error");
  }

  isProcessing = false;
  updateSendBtn();
}

function appendMessage(role, text, sources = [], isFallback = false) {
  const row = document.createElement("div");
  row.className = `msg-row ${role}`;

  const avatarEmoji = role === "ai" ? "🤖" : "👤";
  const bubbleClass = role === "ai"
    ? (isFallback ? "bubble ai fallback" : "bubble ai")
    : "bubble user";

  const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  let sourcesHTML = "";
  if (role === "ai" && sources && sources.length > 0) {
    const srcId = `src-${Date.now()}`;
    const itemsHTML = sources.map((s, i) => {
      const pct = Math.round(s.score * 100);
      const snippet = s.text.slice(0, 340) + (s.text.length > 340 ? "…" : "");
      return `
        <div class="source-item">
          <div class="source-item-header">
            <div class="source-doc-name">📑 ${escapeHtml(s.document)}</div>
            <div class="source-score">
              <div class="score-bar"><div class="score-fill" style="width:${pct}%"></div></div>
              <span class="score-label">${pct}%</span>
            </div>
          </div>
          <div class="source-snippet">${escapeHtml(snippet)}</div>
        </div>`;
    }).join("");

    sourcesHTML = `
      <div class="source-section" id="${srcId}-wrap">
        <button class="source-toggle" id="${srcId}-btn" onclick="toggleSource('${srcId}')">
          <span>📄 View Sources (${sources.length})</span>
          <svg class="source-toggle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
        </button>
        <div class="source-body" id="${srcId}-body">${itemsHTML}</div>
      </div>`;
  }

  row.innerHTML = `
    <div class="msg-avatar ${role}">${avatarEmoji}</div>
    <div class="msg-bubble-wrap">
      <div class="${bubbleClass}">${formatText(text)}${sourcesHTML}</div>
      <div class="bubble-time">${timeStr}</div>
    </div>`;

  messages.appendChild(row);
  scrollToBottom();
}

function showThinking() {
  const id = `think-${Date.now()}`;
  const row = document.createElement("div");
  row.className = "thinking-row";
  row.id = id;
  row.innerHTML = `
    <div class="msg-avatar ai">🤖</div>
    <div class="thinking-bubble">
      <div class="dots"><span></span><span></span><span></span></div>
      <span class="thinking-text">Thinking…</span>
    </div>`;
  messages.appendChild(row);
  scrollToBottom();
  return id;
}

function removeThinking(id) {
  document.getElementById(id)?.remove();
}

function toggleSource(id) {
  const btn  = document.getElementById(`${id}-btn`);
  const body = document.getElementById(`${id}-body`);
  const isOpen = body.classList.toggle("open");
  btn.classList.toggle("open", isOpen);
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatText(text) {
  return text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>");
}

function escapeHtml(str) {
  return str?.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;") ?? "";
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    chatWindow.scrollTop = chatWindow.scrollHeight;
  });
}

function autoResize() {
  queryInput.style.height = "auto";
  queryInput.style.height = Math.min(queryInput.scrollHeight, 160) + "px";
}

function updateSendBtn() {
  const hasKey   = apiKeyInput.value.trim().length > 0;
  const hasQuery = queryInput.value.trim().length > 0;
  sendBtn.disabled = !(hasKey && hasQuery) || isProcessing;
}

function setStatus(state, text) {
  statusDot.className = `status-dot ${state}`;
  statusText.textContent = text;
}

function showToast(msg, type = "info") {
  const existing = document.querySelector(".toast");
  existing?.remove();

  const colors = { success: "#4ade80", error: "#f87171", warn: "#fbbf24", info: "#38bdf8" };
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.style.cssText = `
    position:fixed; bottom:80px; left:50%; transform:translateX(-50%);
    background:#1e242d; border:1px solid ${colors[type] || "#38bdf8"};
    color:${colors[type] || "#38bdf8"};
    padding:10px 20px; border-radius:8px;
    font-size:0.8rem; font-family:'DM Mono',monospace;
    box-shadow:0 4px 20px rgba(0,0,0,0.5);
    z-index:1000; white-space:nowrap;
    animation:fadeUp .2s ease;
  `;
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}
