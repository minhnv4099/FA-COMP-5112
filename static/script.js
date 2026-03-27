const messagesDiv = document.getElementById("messages");
const userInput = document.getElementById("userInput");
let showReasoning = true;

// FEATURE: Enter to send
userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

function toggleReasoning() {
    showReasoning = !showReasoning;
    document.querySelectorAll(".block-reasoning").forEach(el => {
        el.classList.toggle("hidden", !showReasoning);
    });
}

/**
 * LOGIC MỚI: Quản lý block động trong bubble của bot
 */
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
        div.innerHTML = `<div style="font-size:10px; color:#818cf8; margin-bottom:4px">THOUGHT</div><div class="content"></div>`;
        if (!showReasoning) div.classList.add('hidden');
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

async function sendMessage() {
    const threadId = getThreadId();
    const text = userInput.value.trim();
    if (!text) return;

    // 1. Render User Message
    const userRow = document.createElement("div");
    userRow.className = "message-row right";
    userRow.innerHTML = `<div class="bubble user">${text}</div>`;
    messagesDiv.appendChild(userRow);
    userInput.value = "";

    // 2. Render Bot Message Bubble (Container rỗng)
    const botRow = document.createElement("div");
    botRow.className = "message-row left";
    const botBubble = document.createElement("div");
    botBubble.className = "bubble bot";
    botRow.appendChild(botBubble);
    messagesDiv.appendChild(botRow);

    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    let buffer = "";
    let lastTextContent = ""; // Dùng để render markdown cho block text hiện tại

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              message: text,
              thread_id: threadId
            })
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        let isAtBottom = true;

        // Lắng nghe sự kiện cuộn của người dùng để cập nhật trạng thái
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
                        const toolInfo = data.content || {};
                        const block = getBlock(botBubble, "tool");

                        block.innerHTML = `
                            <div class="tool-call-info">🛠️ Call: ${toolInfo.name || 'Unknown'}</div>
                            <div class="tool-args" style="font-size: 11px; opacity: 1;">
                                Args: ${JSON.stringify(toolInfo.args || {})}
                            </div>
                        `;
                    }
                    else if (data.type === "tool_result") {
                        const tools = botBubble.querySelectorAll(".block-tool");
                        const lastTool = tools[tools.length - 1];

                        if (lastTool) {
                            let content = data.content || "";

                            // 1. Xử lý xóa bỏ các dòng Copyright và các dòng chỉ có dấu #
                            // Regex này xóa dòng chứa Copyright và email của bạn
                            // const copyrightPattern = /#.*Copyright.*vnguyen9@lakeheadu\.ca.*/gi;
                            // content = content.replace(copyrightPattern, "");

                            // Xóa các dòng chỉ chứa dấu # và khoảng trắng (thường thấy ở header file)
                            // content = content.replace(/^\s*#\s*$/gm, "");

                            // 2. Cắt ngắn nội dung 500 ký tự
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

                            lastTool.appendChild(resDiv);
                        }
                    }
                     if (isAtBottom) {
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                     }
                } catch (e) { console.log("Skip partial JSON"); }
            }
        }
    } catch (err) {
        botBubble.innerHTML += `<div style="color:red">Error: ${err.message}</div>`;
    }
}