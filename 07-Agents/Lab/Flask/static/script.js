// ---------- Log viewer ----------

const LEVEL_RE = /\b(ERROR|WARN|INFO|DEBUG)\b/;

function escapeHtml(s) {
    return s
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function renderLog(text) {
    const lines = text.split("\n");
    const html = lines
        .map((line) => {
            const escaped = escapeHtml(line);
            const m = escaped.match(LEVEL_RE);
            if (!m) return escaped;
            const level = m[1];
            return escaped.replace(
                LEVEL_RE,
                `<span class="lvl-${level}">${level}</span>`
            );
        })
        .join("\n");

    const logEl = document.getElementById("log-content");
    logEl.innerHTML = html;

    const nonEmpty = lines.filter((l) => l.trim().length > 0).length;
    document.getElementById("log-meta").textContent = `${nonEmpty.toLocaleString()} lines`;
}

async function loadLog() {
    try {
        const res = await fetch("/api/log");
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const text = await res.text();
        renderLog(text);
    }
    catch (err) {
        document.getElementById("log-content").textContent =
            `Failed to load app.log: ${err.message}`;
        document.getElementById("log-meta").textContent = "error";
    }
}

// ---------- Chat panel ----------

let sessionId = "";

function appendMessage(role, initialText) {
    const container = document.getElementById("chat-messages");
    const wrapper = document.createElement("div");
    wrapper.className = `message ${role}`;

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    if (role === "assistant") {
        // Assistant text is markdown from the agent; render it as HTML.
        // Trust note: this content comes from our own backend/LLM, not
        // directly from user input, so we skip a sanitizer for simplicity.
        // If you route untrusted content through here, add DOMPurify.
        bubble.dataset.raw = initialText || "";
        bubble.innerHTML = renderMarkdown(bubble.dataset.raw);
    }
    else {
        bubble.textContent = initialText || "";
    }

    wrapper.appendChild(bubble);
    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
    return bubble;
}

function renderMarkdown(raw) {
    if (!raw) return "";
    if (typeof marked === "undefined") return escapeHtml(raw); // CDN failed to load
    return marked.parse(raw, { breaks: true });
}

function appendToAssistantBubble(bubble, textChunk) {
    bubble.dataset.raw = (bubble.dataset.raw || "") + textChunk;
    bubble.innerHTML = renderMarkdown(bubble.dataset.raw);
}

async function sendMessage(input) {
    const sendBtn = document.getElementById("chat-send");
    const chatInput = document.getElementById("chat-input");
    const messages = document.getElementById("chat-messages");

    appendMessage("user", input);

    const assistantBubble = appendMessage("assistant", "");
    assistantBubble.classList.add("pending");

    sendBtn.disabled = true;
    chatInput.disabled = true;

    try {
        const body = new URLSearchParams();
        body.set("input", input);

        const headers = {};
        headers["X-Session-ID"] = sessionId;

        const res = await fetch("/streaming_chat", {
            method: "POST",
            headers,
            body
        });

        sessionId = res.headers.get("X-Session-ID");

        if (!res.ok || !res.body) {
            const errText = await res.text();
            assistantBubble.classList.remove("pending");
            assistantBubble.textContent = errText || "Something went wrong.";
            return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let firstChunk = true;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            if (firstChunk) {
                assistantBubble.classList.remove("pending");
                firstChunk = false;
            }
            appendToAssistantBubble(assistantBubble, decoder.decode(value, { stream: true }));
            messages.scrollTop = messages.scrollHeight;
        }

        assistantBubble.classList.remove("pending");
        if (!(assistantBubble.dataset.raw || "").trim()) {
            assistantBubble.textContent = "(no response)";
        }
    }
    catch (err) {
        assistantBubble.classList.remove("pending");
        assistantBubble.textContent = `Request failed: ${err.message}`;
    }
    finally {
        sendBtn.disabled = false;
        chatInput.disabled = false;
        chatInput.focus();
    }
}

function initChatForm() {
    const form = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const value = chatInput.value.trim();
        if (!value) return;
        chatInput.value = "";
        sendMessage(value);
    });

    // Enter sends, Shift+Enter inserts a newline
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            form.requestSubmit();
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    loadLog();
    initChatForm();
});
