let showReasoning = true;
let activeBotBubble = null;
let isSending = false;

function initChatEvents() {
    const userInput = document.getElementById("userInput");
    if (userInput) {
        userInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (!isSending) {
                    sendMessage();
                }
            }
        });
    }
}

function toggleReasoning() {
    showReasoning = !showReasoning;
    document.querySelectorAll(".block-reasoning").forEach(el => {
        el.classList.toggle("hidden", !showReasoning);
    });
//    document.querySelectorAll(".block-tool").forEach(el => {
//        el.classList.toggle("hidden", !showReasoning);
//    });
}


//Quản lý block động trong bubble của bot
function getBlock(container, type) {
    const last = container.lastElementChild;
    // Nếu block cuối cùng cùng loại với type đang tới (chỉ áp dụng cho text/reasoning)
    // thì dùng lại block đó để nối tiếp text.
    if (last && last.dataset.type === type && (type === 'text' || type === 'reasoning')) {
        return last;
    }

    // Nếu khác loại hoặc là tool_call, tạo block mới
    const div = document.createElement("div");
    div.dataset.type = type;
    div.className = `block-${type}`;

    if (type === 'reasoning') {
        div.innerHTML = `
        <div style="font-size:10px; color:#818cf8; margin-top:0; margin-bottom:2px; line-height:1;">THOUGHT</div>
        <div class="content" style="margin-top:0;"></div>`;
    if (!showReasoning) div.classList.add('hidden');
    }
    else if (type === 'interrupt') {
        div.innerHTML = `
            <div class="interrupt-card">
                <div class="interrupt-header">⚠️ Tool Call Preview</div>
                <div class="interrupt-desc" style="font-weight:bold; margin-bottom:8px"></div>
                <div class="interrupt-tool-info" style="font-size:11px; color:#94a3b8"></div>
                <div class="interrupt-interactive-area hidden" style="margin-top:10px">
                    <textarea class="interrupt-input" style="width:100%; background:#0f172a; color:white; border:1px solid #4338ca; border-radius:4px; padding:5px; font-family:monospace"></textarea>
                    <button class="confirm-action-btn" style="margin-top:5px; background:#4338ca; color:white; border:none; padding:4px 10px; border-radius:4px; cursor:pointer">Confirm</button>
                </div>
                <div class="interrupt-actions" style="margin-top:12px; display:flex; gap:8px"></div>
            </div>
        `;
    }

    container.appendChild(div);
    return div;
}

// Hàm lấy hoặc tạo thread_id
function getThreadId() {
    let threadId = sessionStorage.getItem('chat_thread_id');
    if (!threadId) {
        // Tạo UUID v4 chuẩn
        threadId = crypto.randomUUID();
        sessionStorage.setItem('chat_thread_id', threadId);
    }
    return threadId;
}

function renderUserMessage(text) {
    const messagesDiv = document.getElementById("messages");
    const userRow = document.createElement("div");
    userRow.className = "message-row right";
    userRow.innerHTML = `
        <div>
            <span class="bubble user" style="">${text}</span>
            <span class="user-icon">
                <img src="/static/assets/human_icon.jpg"
                     width="30" height="30">
            </span>
        </div>
`;
    messagesDiv.appendChild(userRow);
    userInput.value = "";
}

function createBotBubble() {
    const messagesDiv = document.getElementById("messages");
    const botRow = document.createElement("div");
    botRow.className = "message-row left";
    const botBubble = document.createElement("div");
    botBubble.className = "bubble bot";
    botRow.appendChild(botBubble);
    messagesDiv.appendChild(botRow);

    return botBubble
}

function disableInterruptBlock(container) {
    // Tìm block interrupt cuối cùng trong bubble
    const interrupts = container.querySelectorAll(".block-interrupt");
    const lastInterrupt = interrupts[interrupts.length - 1];

    if (lastInterrupt) {
        // Thêm class actioned để CSS xử lý làm mờ và khóa click
        lastInterrupt.classList.add("actioned");

        // Ẩn vùng interactive (textarea/confirm button) nếu đang mở
        const interactiveArea = lastInterrupt.querySelector(".interrupt-interactive-area");
        if (interactiveArea) {
            interactiveArea.classList.add("hidden");
        }

        // Vô hiệu hóa tất cả button bên trong
        lastInterrupt.querySelectorAll("button").forEach(btn => {
            btn.disabled = true;
            btn.classList.add('actioned');
        });
    }
}

function disableInput() {
    if (isSending) return;

    const userInput = document.getElementById("userInput");
    const sendBtn = document.getElementById("sendBtn");

    const text = userInput.value.trim();
    if (!text && !customPayload) return;

    try {
        isSending = true;
        userInput.disabled = true;
        if (sendBtn) sendBtn.disabled = true;
        userInput.placeholder = "AI is thinking...";

        // --- Logic gửi tin nhắn của bạn (Fetch/Stream) ---
        const threadId = getThreadId();
        // ... (phần code fetch API của Minh ở đây) ...

        // Ví dụ: Sau khi render xong nội dung hoặc kết thúc stream
        // saveCurrentChat(threadId);

    } catch (error) {
        console.error("Send message error:", error);
    } finally {
        // 3. Mở khóa UI (Dù thành công hay lỗi cũng phải mở lại)
        isSending = false;
        userInput.disabled = false;
        if (sendBtn) sendBtn.disabled = false;
        userInput.placeholder = "Type a message...";

        // Focus lại vào ô nhập để gõ tiếp
        userInput.focus();
    }
}


async function sendMessage(customPayload = null) {
    if (isSending) return;

    const modelSelect = document.getElementById("modelSelect");
    const selectedModel = modelSelect ? modelSelect.value : "default-model";

    const displaySessionId = document.getElementById("displaySessionId");
    const displayThreadId = document.getElementById("displayThreadId");

    const messagesDiv = document.getElementById("chat-wrapper");
    const sendBtn = document.getElementById("sendBtn");
    const userInput = document.getElementById("userInput");
    const text = userInput.value.trim();
    if (!text && !customPayload) return;

    isSending = true;
    userInput.disabled = true;
    if (sendBtn) sendBtn.disabled = true;
    userInput.placeholder = "AI is thinking...";

    threadId = getThreadId()
    let bodyData;
    let botBubble;
    let updateHis = true;

    // interrupt decision
    if (customPayload) {
        bodyData = {
            thread_id: threadId,
            decision: customPayload.decision,
            additional_info: customPayload.additional_info,
            model_name: selectedModel,
            system_prompt: '',
        };
        if (activeBotBubble) {
            botBubble = activeBotBubble;
        } else {
            botBubble = createBotBubble()
        }
        const statusDiv = document.createElement("div");
        statusDiv.className = "status-info";
        statusDiv.textContent = "⏳ Processing decision...";
        botBubble.appendChild(statusDiv);
    } else {
        renderUserMessage(text);
        userInput.value = "";
        bodyData = {
            thread_id: threadId,
            message: text,
            model_name: selectedModel,
            system_prompt: '',
        };

        botBubble = createBotBubble();
        activeBotBubble = botBubble;
    }

    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    let buffer = "";
    let lastTextContent = ""; // Dùng để render markdown cho block text hiện tại

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(bodyData)
        });
        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        let isAtBottom = true;
        messagesDiv.onscroll = () => {
            // Nếu khoảng cách từ đáy đến vị trí hiện tại < 50px thì coi như đang ở đáy
            const offset = 10;
            isAtBottom = messagesDiv.scrollHeight - messagesDiv.scrollTop <= messagesDiv.clientHeight + offset;
        };

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            let lines = buffer.split("\n\n");
            buffer = lines.pop();

            for (let line of lines) {
                const cleanLine = line.replace(/^data: /, "").trim();
                if (!cleanLine) continue;

                try {
                    const data = JSON.parse(cleanLine);

                    if (data.type === "reasoning") {
                        const block = getBlock(botBubble, "reasoning");
                        const contentTarget = block.querySelector(".content");
                        contentTarget.textContent += data.content;
                    }
                    else if (data.type === "text") {
                        const block = getBlock(botBubble, "text");
                        // Lưu ý: mỗi khi đổi từ loại khác sang text, reset lastTextContent
                        // Ở đây getBlock đã xử lý việc trả về block cũ nếu liên tục là text
                        if (block.dataset.raw === undefined) block.dataset.raw = "";
                        block.dataset.raw += data.content;
                        block.innerHTML = marked.parse(block.dataset.raw);
                    }
                    else if (data.type === "tool_call") {
                        // Lấy thông tin từ data.content thay vì data trực tiếp
                        const block = getBlock(botBubble, "tool");
                        const toolInfo = data.content || {};

                        const argsHtml = Object.entries(toolInfo.args || {}).map(([key, value]) => {
                            // Nếu value là object/array phức tạp thì stringify nó, nếu là text/số thì để nguyên
                            const displayValue = (typeof value === 'object') ? JSON.stringify(value) : value;

                            return `
                                <div class="arg-item" style="margin-bottom: 5px;">
                                    <div style="font-weight: bold; color: #94a3b8;">${key}:</div>
                                    <div style="padding-left: 10px; color: #e2e8f0;">${displayValue}</div>
                                </div>
                            `;
                        }).join('');

                        block.innerHTML = `
                            <div class="tool-call-info">🛠️ Call: ${toolInfo.name || 'Unknown'}</div>
                            <div class="tool-args" style="font-size: 11px; opacity: 1;">
                                Args: ${JSON.stringify(toolInfo.args || {}, null, 2)}
                            </div>
                        `;
                    }
                    else if (data.type === "interrupt") {
                        updateHis = false;
                        const block = getBlock(botBubble, "interrupt");
                        const info = data.content || {};

                        // Đổ dữ liệu cơ bản
                        block.querySelector(".interrupt-desc").textContent = info.description;
                        block.querySelector(".interrupt-tool-info").textContent = `Tool: ${info.name}`;

                        const actionsDiv = block.querySelector(".interrupt-actions");
                        const interactiveArea = block.querySelector(".interrupt-interactive-area");
                        const textArea = block.querySelector(".interrupt-input");
                        const confirmBtn = block.querySelector(".confirm-action-btn");

                        // Xóa các button cũ nếu có (đề phòng stream gửi lại)
                        actionsDiv.innerHTML = "";

                        info.allowed_decisions.forEach(decision => {
                            const btn = document.createElement("button");
                            btn.textContent = decision.toUpperCase();
                            btn.className = `btn-${decision}`; // Bạn có thể style riêng cho từng màu

                            btn.onclick = () => {
                                if (decision === 'approve') {
                                    disableInterruptBlock(botBubble);
                                    sendMessage({
                                        decision: decision,
                                    });
                                }
                                else if (decision === 'edit') {
                                    interactiveArea.classList.remove("hidden");
                                    edit_content = {
                                        name: info.name,
                                        args: info.args
                                    }
                                    textArea.value = JSON.stringify(edit_content, null, 2);
                                    confirmBtn.onclick = () => {
                                        disableInterruptBlock(botBubble);
                                        sendMessage({
                                            decision: decision,
                                            additional_info: JSON.parse(textArea.value),
                                        })
                                        interactiveArea.classList.add("hidden");
                                    };
                                }
                                else if (decision === 'reject') {
                                    interactiveArea.classList.remove("hidden");
                                    textArea.placeholder = "Enter rejection reason...";
                                    textArea.value = "";
                                    confirmBtn.onclick = () => {
                                        disableInterruptBlock(botBubble);
                                        sendMessage({
                                            decision: decision,
                                            additional_info: textArea.value,
                                        })
                                        interactiveArea.classList.add("hidden");
                                    };
                                }
                            };
                            actionsDiv.appendChild(btn);
                        });
                    }
                    else if (data.type === "tool_result") {
                        const tools = botBubble.querySelectorAll(".block-tool");
                        const lastTool = tools[tools.length - 1];

                        if (lastTool) {
                            let content = data.content || "";
                            if (content.length > 500) {
                                content = content.substring(0, 500) + "\n...";
                            }

                            // 3. Tạo Element hiển thị
                            const resDiv = document.createElement("div");
                            resDiv.className = "tool-message tool-result";

                            // QUAN TRỌNG: CSS white-space để hiện \n thành xuống dòng
                            resDiv.style.whiteSpace = "pre-wrap";
                            resDiv.style.wordBreak = "break-all";
                            resDiv.style.fontFamily = "monospace";
                            resDiv.style.marginTop = "10px";
                            resDiv.style.paddingTop = "10px";
                            resDiv.style.borderTop = "1px solid #334155";
                            resDiv.style.color = "#34d399";

                            // Gán nội dung (trim để mất các khoảng trống thừa đầu cuối)
                            resDiv.textContent = `📥 Result:\n${content.trim()}`;

                            botBubble.appendChild(resDiv);
                        }
                    }
                    if (isAtBottom) {
                        scrollToBottom();
                    }
                } catch (err) {
                    botBubble.innerHTML += `<div style="color:red">Error: ${err.message}</div>`;
                }
            }
        }
    } catch (err) {
        console.error(err);
    } finally {
        saveCurrentChat();
        if (updateHis) updateSidebarHistory();

        isSending = false;
        userInput.disabled = false;
        if (sendBtn) sendBtn.disabled = false;
        userInput.placeholder = "Type a message...";
        userInput.focus();
    }
}
