const chatInput = document.querySelector("#chat-input");
const sendButton = document.querySelector("#send-btn");
const chatContainer = document.querySelector(".chat-container");
const themeButton = document.querySelector("#theme-btn");
const deleteButton = document.querySelector("#delete-btn");
const micButton = document.querySelector("#mic-btn");

let sessionID = "";
let userText = null;
let isRequestInFlight = false;

const initialInputHeight = chatInput.scrollHeight;

const defaultText = `<div class="default-text">
                        <h1>Ask LINA</h1>
                        <p>I'm LINA, your Language-Integrated Northwind Assistant.<br />How can I help you today?</p>
                    </div>`;

const init = () => {
    sessionID = "";
    const themeColor = localStorage.getItem("themeColor");
    document.body.classList.toggle("light-mode", themeColor === "light_mode");
    themeButton.innerText = document.body.classList.contains("light-mode") ? "dark_mode" : "light_mode";
    chatContainer.innerHTML = defaultText;
    chatContainer.scrollTo(0, chatContainer.scrollHeight);
};

const createChatElement = (content, className) => {
    const chatDiv = document.createElement("div");
    chatDiv.classList.add("chat", className);
    chatDiv.innerHTML = content;
    return chatDiv;
};

// Parses a single raw SSE event block (an "event: X\ndata: Y" pair,
// as produced by app.py's sse() helper) into { event, data }. The
// server escapes literal newlines within a data payload as "\n" so
// the payload stays on one SSE line; undo that here.
const parseSSEEvent = (rawEvent) => {
    let event = "message";
    let data = "";

    for (const line of rawEvent.split("\n")) {
        if (line.startsWith("event:")) {
            event = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
            // Only strip the single leading space the SSE spec puts after
            // the colon (per spec, at most one). A full .trim() here would
            // also eat meaningful leading/trailing spaces inside the actual
            // payload, which matters when content streams in small pieces
            // (e.g. word-by-word) — each chunk's boundary space would be
            // lost and words would run together.
            data = line.slice(5).replace(/^ /, "").replace(/\\n/g, "\n");
        }
    }

    return { event, data };
};

const streamChatResponse = async (incomingChatDiv) => {
    const divElement = document.createElement("div");
    divElement.classList.add("markdown-output");
    const chatDetails = incomingChatDiv.querySelector(".chat-details");
    chatDetails.appendChild(divElement);

    let accumulatedText = "";
    let sseBuffer = "";

    try {
        const response = await fetch("/streaming_chat", {
            method: "POST",
            body: new URLSearchParams({ input: userText }),
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Session-ID": sessionID
            }
        });

        sessionID = response.headers.get("X-Session-ID");
        incomingChatDiv.querySelector(".typing-animation")?.remove();

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            sseBuffer += decoder.decode(value, { stream: true });

            // SSE events are separated by a blank line. The last entry after
            // splitting may be an incomplete event still arriving, so hold it
            // back in the buffer until the next chunk completes it.
            const rawEvents = sseBuffer.split("\n\n");
            sseBuffer = rawEvents.pop();

            for (const rawEvent of rawEvents) {
                if (!rawEvent.trim())
                    continue;

                const { event, data } = parseSSEEvent(rawEvent);

                if (event === "text") {
                    accumulatedText += data;
                    divElement.innerHTML = marked.parse(accumulatedText);
                } else if (event === "confirm") {
                    // The agent paused for human approval. accumulatedText
                    // already holds everything streamed before the pause, so
                    // just append the prompt and swap in Yes/No buttons.
                    accumulatedText += data;
                    divElement.innerHTML = marked.parse(accumulatedText);
                    appendConfirmButtons(divElement);
                }

                chatContainer.scrollIntoView({ behavior: "smooth", block: "end" });
            }
        }
    }
    catch (error) {
        console.error(error);
        incomingChatDiv.querySelector(".typing-animation")?.remove();
        const errorMessage = accumulatedText.length === 0
            ? `I'm sorry, but something went wrong (${error.message}).`
            : `...I'm sorry, but something went wrong (${error.message}).`;
        accumulatedText += errorMessage;
        divElement.innerHTML = marked.parse(accumulatedText);
    }
    finally {
        isRequestInFlight = false;
        sendButton.disabled = false;
    }
};

// Renders Yes/No buttons under a paused agent message and wires them to
// send the user's decision exactly as if they'd typed it. Appended inside
// the markdown-output block (not chat-details) so it stacks below the
// prompt text instead of competing for space in the row-flex avatar layout.
const appendConfirmButtons = (markdownOutputDiv) => {
    const wrap = document.createElement("div");
    wrap.classList.add("confirm-buttons");
    wrap.innerHTML = `<button type="button" class="confirm-btn confirm-yes">Yes</button>
                       <button type="button" class="confirm-btn confirm-no">No</button>`;
    markdownOutputDiv.appendChild(wrap);

    wrap.querySelector(".confirm-yes").addEventListener("click", () => {
        wrap.remove();
        sendDecision("Yes");
    });
    wrap.querySelector(".confirm-no").addEventListener("click", () => {
        wrap.remove();
        sendDecision("No");
    });

    chatContainer.scrollIntoView({ behavior: "smooth", block: "end" });
};

// Sends a HITL decision made by clicking a button, reusing the same
// request flow as a normal typed chat message.
const sendDecision = (answer) => {
    if (isRequestInFlight)
        return;

    isRequestInFlight = true;
    sendButton.disabled = true;
    userText = answer;

    const html = `<div class="chat-content">
                    <div class="chat-details">
                        <img src="/static/user.jpg" class="avatar" alt="user-img">
                        <div class="markdown-output">
                            <p>${answer}</p>
                        </div>
                    </div>
                </div>`;

    const outgoingChatDiv = createChatElement(html, "outgoing");
    chatContainer.append(outgoingChatDiv);
    chatContainer.scrollTo(0, chatContainer.scrollHeight);
    showTypingAnimation();
};

const showTypingAnimation = () => {
    const html = `<div class="chat-content">
                    <div class="chat-details">
                        <img src="/static/chatbot.jpg" class="avatar" alt="chatbot-img">
                        <div class="typing-animation">
                            <div class="typing-dot" style="--delay: 0.2s"></div>
                            <div class="typing-dot" style="--delay: 0.3s"></div>
                            <div class="typing-dot" style="--delay: 0.4s"></div>
                        </div>
                    </div>
                </div>`;
    const incomingChatDiv = createChatElement(html, "incoming");
    chatContainer.append(incomingChatDiv);
    chatContainer.scrollTo(0, chatContainer.scrollHeight);
    streamChatResponse(incomingChatDiv);
};

const handleOutgoingChat = () => {
    if (isRequestInFlight)
        return;

    userText = chatInput.value.trim();
    if (!userText)
        return;

    isRequestInFlight = true;
    sendButton.disabled = true;
    chatInput.value = "";
    chatInput.style.height = `${initialInputHeight}px`;

    const html = `<div class="chat-content">
                    <div class="chat-details">
                        <img src="/static/user.jpg" class="avatar" alt="user-img">
                        <div class="markdown-output">
                            <p>${userText}</p>
                        </div>
                    </div>
                </div>`;

    const outgoingChatDiv = createChatElement(html, "outgoing");
    chatContainer.querySelector(".default-text")?.remove();
    chatContainer.append(outgoingChatDiv);
    chatContainer.scrollTo(0, chatContainer.scrollHeight);
    setTimeout(showTypingAnimation, 500);
};

deleteButton.addEventListener("click", () => {
    if (confirm("Are you sure you want to delete the conversation?")) {
        init();
    }
});

themeButton.addEventListener("click", () => {
    const isLight = document.body.classList.toggle("light-mode");
    localStorage.setItem("themeColor", isLight ? "light_mode" : "dark_mode");
    themeButton.innerText = isLight ? "dark_mode" : "light_mode";
});

chatInput.addEventListener("input", () => {
    chatInput.style.height = `${initialInputHeight}px`;
    chatInput.style.height = `${chatInput.scrollHeight}px`;
});

chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && window.innerWidth > 800) {
        e.preventDefault();
        handleOutgoingChat();
    }
});

async function typewriter(text, el, delay = 5) {
    for (let i = 0; i < text.length; i++) {
        await new Promise(resolve => setTimeout(resolve, delay));
        el.value += text[i];
        el.style.height = `${initialInputHeight}px`;
        el.style.height = `${el.scrollHeight}px`;
    }
}

micButton.addEventListener("click", () => {
    chatInput.value = "";
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        console.log("Speech recognition is not supported in this browser.");
        micButton.disabled= true; // Disable the mic button
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.interimResults = false;

    recognition.addEventListener("result", async (e) => {
        const query = Array.from(e.results)
            .map(result => result[0].transcript)
            .join('');
        await typewriter(query, chatInput);
        handleOutgoingChat();
    });

    recognition.start();
});

init();
sendButton.addEventListener("click", handleOutgoingChat);