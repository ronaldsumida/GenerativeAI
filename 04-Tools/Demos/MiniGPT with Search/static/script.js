const chatInput = document.querySelector("#chat-input");
const sendButton = document.querySelector("#send-btn");
const chatContainer = document.querySelector(".chat-container");
const chatScroll = document.querySelector(".chat-scroll");
const deleteButton = document.querySelector("#delete-btn");
const micButton = document.querySelector("#mic-btn");
const attachButton = document.querySelector("#attach-btn");
const fileInput = document.querySelector("#file-input");
const fileChipList = document.querySelector("#file-chip-list");
const viewConversationButton = document.querySelector("#view-conversation-btn");
const conversationModal = document.querySelector("#conversation-modal");
const conversationJson = document.querySelector("#conversation-json");
const modalSubtitle = document.querySelector("#modal-subtitle");
const closeModalButton = document.querySelector("#close-modal-btn");

let sessionID = "";
let userText = null;
let isRequestInFlight = false;

// Tracks the files uploaded to OpenAI's Files API (or extracted to text) and
// waiting to be sent with the next message. Cleared automatically once the
// message is sent.
let attachedFiles = [];

const initialInputHeight = chatInput.scrollHeight;

const defaultText = `<div class="default-text">
                        <h1>Ready for launch</h1>
                    </div>`;

const init = () => {
    sessionID = "";
    clearAttachment();
    viewConversationButton.disabled = true;
    chatContainer.innerHTML = defaultText;
    chatScroll.scrollTo(0, chatScroll.scrollHeight);
};

const createChatElement = (content, className) => {
    const chatDiv = document.createElement("div");
    chatDiv.classList.add("chat", className);
    chatDiv.innerHTML = content;
    return chatDiv;
};

// ── File attachment handling ────────────────────────────────────────────────

const clearAttachment = () => {
    attachedFiles = [];
    renderChips();
};

const renderChips = () => {
    fileChipList.innerHTML = "";

    attachedFiles.forEach((attachment) => {
        const chip = document.createElement("div");
        chip.classList.add("file-chip");
        chip.classList.toggle("uploading", attachment.uploading);
        const icon = attachment.uploading ? "progress_activity" : (attachment.imageUrl ? "image" : "description");
        chip.innerHTML = `
            <span class="material-symbols-rounded chip-icon">${icon}</span>
            <span class="chip-filename">${attachment.filename}</span>
            <button class="icon-btn material-symbols-rounded chip-remove" type="button" title="Remove file">close</button>
        `;
        chip.querySelector(".chip-remove").addEventListener("click", () => {
            attachedFiles = attachedFiles.filter(a => a !== attachment);
            renderChips();
        });
        fileChipList.appendChild(chip);
    });

    // Disable sending while any file is still uploading
    sendButton.disabled = attachedFiles.some(a => a.uploading);
};

const uploadFile = async (file) => {
    const attachment = { fileId: null, fileText: null, imageUrl: null, filename: file.name, uploading: true };
    attachedFiles.push(attachment);
    renderChips();

    try {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch("/upload_file", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!response.ok || result.error) {
            throw new Error(result.error || "Upload failed");
        }

        attachment.fileId = result.kind === "file_id" ? result.file_id : null;
        attachment.fileText = result.kind === "text" ? result.text : null;
        attachment.imageUrl = result.kind === "image_url" ? result.image_url : null;
        attachment.filename = result.filename;
    }
    catch (error) {
        console.error(error);
        alert(`Sorry, "${file.name}" couldn't be uploaded (${error.message}).`);
        attachedFiles = attachedFiles.filter(a => a !== attachment);
    }
    finally {
        attachment.uploading = false;
        renderChips();
    }
};

attachButton.addEventListener("click", () => {
    fileInput.click();
});

fileInput.addEventListener("change", () => {
    Array.from(fileInput.files).forEach(file => uploadFile(file));
    fileInput.value = "";
});

// ── Chat handling ────────────────────────────────────────────────────────────

const streamChatResponse = async (incomingChatDiv, attachments) => {
    const divElement = document.createElement("div");
    divElement.classList.add("markdown-output");
    const assistantMessage = incomingChatDiv.querySelector(".assistant-message");
    assistantMessage.appendChild(divElement);

    let accumulatedText = "";

    try {
        const formData = new URLSearchParams({ input: userText });
        if (attachments.length > 0) {
            const payload = attachments.map(a => {
                if (a.fileId) return { kind: "file_id", file_id: a.fileId, filename: a.filename };
                if (a.imageUrl) return { kind: "image_url", image_url: a.imageUrl, filename: a.filename };
                return { kind: "text", text: a.fileText, filename: a.filename };
            });
            formData.append("attachments", JSON.stringify(payload));
        }

        const response = await fetch("/streaming_chat", {
            method: "POST",
            body: formData,
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Session-ID": sessionID
            }
        });

        sessionID = response.headers.get("X-Session-ID");
        viewConversationButton.disabled = false;
        incomingChatDiv.querySelector(".typing-animation")?.remove();

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            accumulatedText += decoder.decode(value, { stream: true });
            // Parse and render markdown incrementally
            divElement.innerHTML = marked.parse(accumulatedText);
            chatScroll.scrollTo({ top: chatScroll.scrollHeight, behavior: "smooth" });
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

const showTypingAnimation = (attachments) => {
    const html = `<div class="assistant-message">
                    <div class="typing-animation">
                        <div class="typing-dot" style="--delay: 0.2s"></div>
                        <div class="typing-dot" style="--delay: 0.3s"></div>
                        <div class="typing-dot" style="--delay: 0.4s"></div>
                    </div>
                </div>`;
    const incomingChatDiv = createChatElement(html, "incoming");
    chatContainer.append(incomingChatDiv);
    chatScroll.scrollTo(0, chatScroll.scrollHeight);
    streamChatResponse(incomingChatDiv, attachments);
};

const handleOutgoingChat = () => {
    if (isRequestInFlight || attachedFiles.some(a => a.uploading))
        return;

    userText = chatInput.value.trim();
    if (!userText)
        return;

    // Capture the attached files (if any) for this message, then clear the
    // attachment list so it isn't accidentally included with the next message.
    const attachments = attachedFiles.map(({ fileId, fileText, imageUrl, filename }) => ({ fileId, fileText, imageUrl, filename }));
    clearAttachment();

    isRequestInFlight = true;
    sendButton.disabled = true;
    chatInput.value = "";
    chatInput.style.height = `${initialInputHeight}px`;

    const attachmentHtml = attachments
        .map(a => `<div class="chat-file-attachment">
               <span class="material-symbols-rounded">${a.imageUrl ? "image" : "description"}</span>
               <span>${a.filename}</span>
           </div>`)
        .join("");

    const html = `<div class="user-bubble">
                    ${attachmentHtml}
                    <p>${userText}</p>
                </div>`;

    const outgoingChatDiv = createChatElement(html, "outgoing");
    chatContainer.querySelector(".default-text")?.remove();
    chatContainer.append(outgoingChatDiv);
    chatScroll.scrollTo(0, chatScroll.scrollHeight);
    setTimeout(() => showTypingAnimation(attachments), 500);
};

deleteButton.addEventListener("click", () => {
    if (confirm("Are you sure you want to delete the conversation?")) {
        init();
    }
});

// ── Cached conversation modal ───────────────────────────────────────────────

viewConversationButton.addEventListener("click", async () => {
    try {
        const response = await fetch(`/conversation/${sessionID}`);
        const messages = await response.json();

        if (!response.ok) {
            throw new Error(messages.error || "Request failed");
        }

        // textContent (not innerHTML) - message/attachment content is
        // user-controlled and could contain characters that would otherwise
        // be interpreted as HTML.
        conversationJson.textContent = JSON.stringify(messages, null, 2);
        modalSubtitle.textContent = `session ${sessionID}`;
        conversationModal.showModal();
    }
    catch (error) {
        console.error(error);
        alert(`Sorry, couldn't load the conversation (${error.message}).`);
    }
});

closeModalButton.addEventListener("click", () => {
    conversationModal.close();
});

// Close when clicking the backdrop (Escape already closes <dialog> natively)
conversationModal.addEventListener("click", (e) => {
    if (e.target === conversationModal) {
        conversationModal.close();
    }
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
