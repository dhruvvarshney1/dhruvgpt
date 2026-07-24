/**
 * DhruvGPT — Frontend application logic.
 *
 * Vanilla JS, no build step. Connects to the FastAPI backend for chat
 * streaming and conversation management.
 */

// ── Configuration ──────────────────────────────────────────────────────────
// For local development, use http://localhost:8000.
// For production, replace with your Render service URL, e.g.:
//   const API_BASE_URL = "https://your-service-name.onrender.com";
const API_BASE_URL = "https://dhruvgpt.onrender.com";

// ── Configure marked with highlight.js via the extension API ───────────────
marked.use({
    breaks: true, // Convert single \n to <br> for paragraph spacing
    gfm: true,    // GitHub Flavored Markdown
    extensions: [],
    renderer: {
        code(token) {
            const lang = (token.lang || '').trim();
            const text = token.text || '';
            let highlighted;
            if (lang && hljs.getLanguage(lang)) {
                highlighted = hljs.highlight(text, { language: lang }).value;
            } else {
                highlighted = hljs.highlightAuto(text).value;
            }
            const langLabel = lang || 'code';
            return `<pre><div class="code-lang-label">${langLabel}</div><code class="hljs language-${langLabel}">${highlighted}</code></pre>`;
        }
    }
});

// ── State ──────────────────────────────────────────────────────────────────
let currentConversationId = null;
let isStreaming = false;
let userHasScrolledUp = false;
let activeRequest = null;
let renderFrame = 0;

// ── DOM references ─────────────────────────────────────────────────────────
const sidebar          = document.getElementById("sidebar");
const sidebarToggle    = document.getElementById("sidebar-toggle");
const newChatBtn       = document.getElementById("new-chat-btn");
const conversationList = document.getElementById("conversation-list");
const messagesContainer= document.getElementById("messages");
const emptyState       = document.getElementById("empty-state");
const chatForm         = document.getElementById("chat-form");
const messageInput     = document.getElementById("message-input");
const sendBtn          = document.getElementById("send-btn");
const modelSelect      = document.getElementById("model-select");

// ── Initialise ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    loadConversations();
    loadModels();

    modelSelect.addEventListener("change", () => {
        localStorage.setItem("selected_model", modelSelect.value);
    });

    chatForm.addEventListener("submit", handleSubmit);
    newChatBtn.addEventListener("click", newChat);
    sidebarToggle.addEventListener("click", () => sidebar.classList.toggle("open"));

    messagesContainer.addEventListener("scroll", () => {
        // If we are more than ~10px from the bottom, user has scrolled up
        const distToBottom = messagesContainer.scrollHeight - messagesContainer.scrollTop - messagesContainer.clientHeight;
        userHasScrolledUp = distToBottom > 10;
    });

    // Auto-resize textarea
    messageInput.addEventListener("input", () => {
        messageInput.style.height = "auto";
        messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + "px";
    });

    // Ctrl+Enter / Cmd+Enter to send
    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            chatForm.requestSubmit();
        }
    });
});

// ── Load available models ──────────────────────────────────────────────────
async function loadModels() {
    const defaultModels = [
        "meta/llama-3.1-8b-instruct",
        "meta/llama-3.1-70b-instruct",
        "meta/llama-3.3-70b-instruct",
        "deepseek-ai/deepseek-r1-distill-llama-70b",
    ];

    let models = defaultModels;
    try {
        const res = await fetch(`${API_BASE_URL}/models`);
        if (res.ok) {
            const fetched = await res.json();
            if (Array.isArray(fetched) && fetched.length > 0) {
                models = fetched;
            }
        }
    } catch (err) {
        console.error("Failed to load models:", err);
    }

    modelSelect.innerHTML = models
        .map((m) => `<option value="${m}">${m}</option>`)
        .join("");

    const saved = localStorage.getItem("selected_model");
    if (saved && modelSelect.querySelector(`option[value="${saved}"]`)) {
        modelSelect.value = saved;
    }
}

// ── Sidebar: load conversations ────────────────────────────────────────────
async function loadConversations() {
    try {
        const res = await fetch(`${API_BASE_URL}/conversations`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const conversations = await res.json();
        renderConversationList(conversations);
    } catch (err) {
        console.error("Failed to load conversations:", err);
    }
}

function renderConversationList(conversations) {
    conversationList.innerHTML = "";
    if (conversations.length === 0) {
        conversationList.innerHTML = `<div class="empty-sidebar">No conversations yet</div>`;
        return;
    }
    for (const conv of conversations) {
        const item = document.createElement("div");
        item.className = "conv-item" + (conv.id === currentConversationId ? " active" : "");
        item.dataset.id = conv.id;

        const title = document.createElement("span");
        title.className = "conv-item-title";
        title.textContent = conv.title || "Untitled chat";
        title.addEventListener("click", () => openConversation(conv.id));

        const deleteBtn = document.createElement("button");
        deleteBtn.className = "conv-item-delete";
        deleteBtn.title = "Delete conversation";
        deleteBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';
        deleteBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            deleteConversation(conv.id);
        });

        item.appendChild(title);
        item.appendChild(deleteBtn);
        conversationList.appendChild(item);
    }
}

// ── Sidebar: open a conversation ───────────────────────────────────────────
async function openConversation(id) {
    try {
        const res = await fetch(`${API_BASE_URL}/conversations/${id}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const conversation = await res.json();

        currentConversationId = id;
        renderMessages(conversation.messages);
        highlightActiveConversation();
        sidebar.classList.remove("open");
    } catch (err) {
        console.error("Failed to open conversation:", err);
    }
}

function renderMessages(messages) {
    messagesContainer.innerHTML = "";
    for (const msg of messages) {
        appendMessageBubble(msg.role, msg.content, msg.role === "assistant");
    }
    scrollToBottom();
}

// ── Sidebar: new chat ──────────────────────────────────────────────────────
function newChat() {
    currentConversationId = null;
    messagesContainer.innerHTML = "";
    messagesContainer.appendChild(createEmptyState());
    highlightActiveConversation();
    messageInput.focus();
    sidebar.classList.remove("open");
}

function createEmptyState() {
    const el = document.createElement("div");
    el.id = "empty-state";
    el.className = "empty-state";
    el.innerHTML = `
        <div class="empty-state-icon">💬</div>
        <h2>Ask me anything</h2>
        <p>Send a message to begin chatting with the AI assistant.</p>
    `;
    return el;
}

// ── Sidebar: delete conversation ───────────────────────────────────────────
async function deleteConversation(id) {
    if (!confirm("Delete this conversation? This cannot be undone.")) return;

    try {
        const res = await fetch(`${API_BASE_URL}/conversations/${id}`, { method: "DELETE" });
        if (!res.ok && res.status !== 204) throw new Error(`HTTP ${res.status}`);

        if (id === currentConversationId) {
            newChat();
        }
        await loadConversations();
    } catch (err) {
        console.error("Failed to delete conversation:", err);
    }
}

// ── Highlight active conversation in sidebar ───────────────────────────────
function highlightActiveConversation() {
    document.querySelectorAll(".conv-item").forEach((el) => {
        el.classList.toggle("active", el.dataset.id === currentConversationId);
    });
}

// ── Chat form submit ───────────────────────────────────────────────────────
function handleSubmit(e) {
    e.preventDefault();
    if (isStreaming) {
        activeRequest?.abort();
        return;
    }
    const text = messageInput.value.trim();
    if (!text || isStreaming) return;
    sendMessage(text);
}

// ── Send message & stream response ─────────────────────────────────────────
async function sendMessage(text) {
    // Clear empty state
    const empty = document.getElementById("empty-state");
    if (empty) empty.remove();

    const isNewConversation = currentConversationId === null;

    // Optimistically render the user message
    appendMessageBubble("user", text, false);
    messageInput.value = "";
    messageInput.style.height = "auto";
    forceScrollToBottom();

    // Disable input while streaming
    setStreaming(true);

    // Keep reasoning and answer separate; neither is inferred by the client.
    const assistant = appendAssistantStream();
    let fullText = "";
    let reasoningText = "";
    let streamEnded = false;
    activeRequest = new AbortController();

    try {
        const res = await fetch(`${API_BASE_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                conversation_id: currentConversationId,
                message: text,
                model: modelSelect.value,
            }),
            signal: activeRequest.signal,
        });

        if (!res.ok) {
            const errBody = await res.text();
            throw new Error(`HTTP ${res.status}: ${errBody}`);
        }

        // Read the SSE stream via ReadableStream
        if (!res.body) throw new Error("Streaming is not supported by this browser.");
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Split on double newlines (SSE frame boundary)
            const frames = buffer.split("\n\n");
            // Keep the last incomplete frame in the buffer
            buffer = frames.pop();

            for (const frame of frames) {
                if (!frame.trim()) continue;
                const { event, data } = parseSSEFrame(frame);
                if (!event) continue;

                switch (event) {
                    case "conversation_id":
                        currentConversationId = data;
                        loadConversations();
                        break;

                    case "token":
                        fullText += data || "";
                        scheduleStreamRender(assistant, fullText, reasoningText);
                        break;
                    case "reasoning":
                        reasoningText += data || "";
                        scheduleStreamRender(assistant, fullText, reasoningText);
                        break;

                    case "done":
                        streamEnded = true;
                        renderStream(assistant, fullText, reasoningText, false);
                        scrollToBottom();
                        if (isNewConversation) {
                            // Poll for the generated title
                            setTimeout(loadConversations, 1500);
                            setTimeout(loadConversations, 3000);
                        }
                        break;

                    case "error":
                        let errorMsg;
                        try {
                            const errData = JSON.parse(data);
                            errorMsg = errData.message || data;
                        } catch {
                            errorMsg = data;
                        }
                        if (fullText) {
                            renderStream(assistant, fullText, reasoningText, false);
                            appendErrorMessage(errorMsg, text);
                        } else {
                            showStreamError(assistant, errorMsg, text);
                        }
                        scrollToBottom();
                        break;
                }
            }
        }

        // Handle any remaining buffer
        if (buffer.trim()) {
            const { event, data } = parseSSEFrame(buffer);
            if (event === "token") fullText += data || "";
            if (event === "reasoning") reasoningText += data || "";
            if (event === "done" || !event) {
                streamEnded = event === "done";
                renderStream(assistant, fullText, reasoningText, false);
            }
        }

        renderStream(assistant, fullText, reasoningText, !streamEnded && !activeRequest.signal.aborted);

    } catch (err) {
        if (err.name === "AbortError") {
            renderStream(assistant, fullText, reasoningText, false);
            if (fullText) appendErrorMessage("Stopped — partial output preserved.", text);
        } else {
            console.error("Chat error:", err);
            renderStream(assistant, fullText, reasoningText, false);
            if (fullText) appendErrorMessage("Connection error: " + err.message, text);
            else showStreamError(assistant, err.message || "Something went wrong.", text);
        }
    } finally {
        activeRequest = null;
        setStreaming(false);
        if (!userHasScrolledUp) forceScrollToBottom();
    }
}

function appendAssistantStream() {
    const row = document.createElement("div");
    row.className = "message-row assistant";
    const panel = document.createElement("details");
    panel.className = "reasoning-panel";
    panel.hidden = true;
    panel.innerHTML = '<summary>Reasoning</summary><div class="reasoning-content"></div>';
    const bubble = document.createElement("div");
    bubble.className = "message-bubble streaming-cursor thinking";
    bubble.textContent = "Thinking";
    row.append(panel, bubble);
    messagesContainer.appendChild(row);
    return { row, panel, reasoning: panel.querySelector(".reasoning-content"), bubble };
}

function scheduleStreamRender(view, answer, reasoning) {
    if (renderFrame) return;
    renderFrame = requestAnimationFrame(() => {
        renderFrame = 0;
        renderStream(view, answer, reasoning, true);
    });
}

function renderStream(view, answer, reasoning, streaming) {
    if (!streaming && renderFrame) {
        cancelAnimationFrame(renderFrame);
        renderFrame = 0;
    }
    if (reasoning) {
        view.panel.hidden = false;
        view.reasoning.innerHTML = safeMarkdown(reasoning);
    }
    view.bubble.classList.toggle("streaming-cursor", streaming);
    view.bubble.classList.toggle("thinking", !answer && streaming);
    if (answer) {
        view.bubble.innerHTML = safeMarkdown(answer);
        if (!streaming) addCopyButtons(view.bubble);
    } else if (!streaming) view.bubble.textContent = reasoning ? "" : "No response received.";
    if (streaming) scrollToBottom();
}

function safeMarkdown(text) {
    const html = marked.parse(text || "", { async: false });
    return window.DOMPurify ? DOMPurify.sanitize(html) : html.replace(/<script[\s\S]*?<\/script>/gi, "");
}

function showStreamError(view, message, retryText) {
    view.bubble.classList.remove("streaming-cursor", "thinking");
    view.bubble.classList.add("message-error");
    view.bubble.textContent = "⚠ " + message;
    view.bubble.appendChild(createRetryButton(retryText, view.row));
}

// ── SSE frame parser ───────────────────────────────────────────────────────
function parseSSEFrame(frame) {
    let event = null;
    const dataParts = [];

    for (const line of frame.split("\n")) {
        if (line.startsWith("event: ")) {
            event = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
            dataParts.push(line.slice(6));
        } else if (line === "data:") {
            // Bare "data:" line represents an empty line in multi-line data
            dataParts.push("");
        }
    }

    // Rejoin multi-line data fields with newlines per the SSE spec
    const data = dataParts.length > 0 ? dataParts.join("\n") : null;
    return { event, data };
}

// ── DOM helpers ────────────────────────────────────────────────────────────

/**
 * Append a message bubble to the chat area.
 * @param {"user"|"assistant"} role
 * @param {string} content
 * @param {boolean} renderMarkdown - if true, parse content with marked
 * @returns {HTMLElement} The bubble element (for live updates during streaming)
 */
function appendMessageBubble(role, content, renderMarkdown) {
    const row = document.createElement("div");
    row.className = `message-row ${role}`;

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    if (role === "user") {
        // User messages: always textContent (XSS safe)
        bubble.textContent = content;
    } else if (renderMarkdown && content) {
        // Completed assistant messages: render markdown
        bubble.innerHTML = safeMarkdown(content);
        addCopyButtons(bubble);
    } else {
        bubble.textContent = content;
    }

    row.appendChild(bubble);
    messagesContainer.appendChild(row);
    return bubble;
}

function appendErrorMessage(message, retryText = null) {
    const row = document.createElement("div");
    row.className = "message-row assistant";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble message-error";
    bubble.textContent = "⚠ " + message;

    if (retryText) {
        bubble.appendChild(createRetryButton(retryText, row));
    }

    row.appendChild(bubble);
    messagesContainer.appendChild(row);
    forceScrollToBottom();
}

function createRetryButton(textToRetry, rowToRemove) {
    const btn = document.createElement("button");
    btn.className = "btn-retry";
    btn.textContent = "Retry";
    btn.addEventListener("click", () => {
        rowToRemove.remove();
        sendMessage(textToRetry);
    });
    return btn;
}

function scrollToBottom() {
    if (!userHasScrolledUp) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

function forceScrollToBottom() {
    userHasScrolledUp = false;
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function setStreaming(streaming) {
    isStreaming = streaming;
    messageInput.disabled = streaming;
    sendBtn.disabled = false;
    sendBtn.title = streaming ? "Stop response" : "Send message";
    sendBtn.setAttribute("aria-label", streaming ? "Stop response" : "Send");
    sendBtn.innerHTML = streaming
        ? '<span class="stop-icon" aria-hidden="true"></span>'
        : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';
    if (!streaming) {
        messageInput.focus();
    }
}

function addCopyButtons(container) {
    const preBlocks = container.querySelectorAll('pre');
    preBlocks.forEach((pre) => {
        if (pre.parentNode.classList.contains('code-block-wrapper')) return;

        const wrapper = document.createElement('div');
        wrapper.className = 'code-block-wrapper';

        const btn = document.createElement('button');
        btn.className = 'btn-copy';
        btn.textContent = 'Copy';
        btn.onclick = () => {
            const code = pre.querySelector('code')?.innerText || pre.innerText;
            navigator.clipboard.writeText(code).then(() => {
                btn.textContent = 'Copied!';
                btn.classList.add('copied');
                setTimeout(() => {
                    btn.textContent = 'Copy';
                    btn.classList.remove('copied');
                }, 2000);
            });
        };

        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(btn);
        wrapper.appendChild(pre);
    });
}
