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
                        <h1>Ask AGNES</h1>
                        <p>I'm AGNES, your AI-powered Agno expert.<br />How can I help you today?</p>
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

const streamChatResponse = async (incomingChatDiv) => {
    const divElement = document.createElement("div");
    divElement.classList.add("markdown-output");
    const chatDetails = incomingChatDiv.querySelector(".chat-details");
    chatDetails.appendChild(divElement);

    let accumulatedText = "";

    try {
        const response = await fetch("/streaming_chat", {
            method: "POST"    ,
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
            accumulatedText += decoder.decode(value, { stream: true });
            // Parse and render markdown incrementally
            divElement.innerHTML = marked.parse(accumulatedText);
            chatContainer.scrollIntoView({ behavior: "smooth", block: "end" });
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
