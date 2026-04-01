function updateSidebarHistory() {
    const conversations = JSON.parse(sessionStorage.getItem('conversations')) || [];
    const historyContainer = document.getElementById("chatHistoryList");
    conversations.sort((a, b) => b.last_updated - a.last_updated);

    autoFocus();

    if (!historyContainer || !conversations) return;

    // Xóa danh sách cũ trước khi nạp mới
    historyContainer.innerHTML = "";
    let has_active = false

    conversations.forEach(chat => {
        const chatItem = document.createElement("a");
        chatItem.href = "#";
        chatItem.className = "nav-item";
        chatItem.id = chat.chat_thread_id;
        // Nếu đang ở thread này thì thêm class active
        chatItem.innerHTML = `💬 ${chat.title}...`;
        if (chat.chat_thread_id === sessionStorage.getItem('chat_thread_id')) {
            sessionStorage.setItem('chat_thread_id', chat.chat_thread_id);
            sessionStorage.setItem('chat_html_backup', chat.chat_html_backup);
            chatItem.classList.add("active");
            has_active = true;
        }

        // Khi click vào thì load chat đó lên
        chatItem.onclick = (e) => {
            e.preventDefault();
            loadSavedChat(chat.chat_thread_id);
        };

        historyContainer.appendChild(chatItem);
    });

    const chatItems = historyContainer.querySelectorAll('.nav-item');

    // When delete the current active conversation,
    // activate the most recent chat.
    if (!has_active && chatItems.length > 0) {
        const firstChat = conversations[0];
        chatItems[0].classList.add("active");
        sessionStorage.setItem('chat_thread_id', chatItems[0].id);
        sessionStorage.setItem('chat_html_backup', firstChat.chat_html_backup);
    }
    fillMessages();
}

async function loadSavedChat(threadId) {
    console.log(`Loading conversation: ${threadId}`);
    const clickedChat = document.getElementById(threadId);
    document.querySelectorAll('.nav-item').forEach(p => p.classList.remove('active'));
    clickedChat.classList.add("active");

    // 1. Lấy danh sách từ Storage
    const conversations = JSON.parse(sessionStorage.getItem('conversations')) || [];

    // 2. Tìm cuộc hội thoại có ID tương ứng trong mảng
    const selectedChat = conversations.find(c => c.chat_thread_id === threadId);

    if (selectedChat) {
        // 3. Cập nhật "Phiên làm việc hiện tại" vào Storage
        sessionStorage.setItem('chat_thread_id', selectedChat.chat_thread_id);
        sessionStorage.setItem('chat_html_backup', selectedChat.chat_html_backup || "");

        // 4. Chuyển sang trang Chat
        // Dùng isNewChat = false để showPage không tạo Thread mới đè lên cái cũ
        await showPage('chat');
    }
    const userInput = document.getElementById("userInput");
    if (userInput) userInput.focus();
}

async function showPage(pageId, needUpdateHis = true) {
    // 1. Nạp layout trước khi làm bất cứ việc gì khác nếu cần
    if (pageId === 'chat' || pageId === 'settings') {
        const container = document.getElementById('page-' + pageId);
        // Chỉ fetch nếu bên trong container chưa có nội dung (tránh nạp đè)
        if (container && container.innerHTML.trim() === "") {
            await loadLayout(pageId);
        }
    }

    // 2. Ẩn/Hiện các trang
    document.querySelectorAll('.page-container').forEach(p => p.classList.add('hidden'));
    const target = document.getElementById('page-' + pageId);
    if (target) {
        target.classList.remove('hidden');
    }

    // 3. Save current page
    AppState.saveCurrentPage(pageId);

    // 4. Logic khởi tạo cho Chat
    if (pageId === 'chat') {
        initChatEvents();
        await loadAvailableModels();
        if (needUpdateHis) updateSidebarHistory();
    }
}

async function loadAvailableModels() {
    try {
        const response = await fetch('/chat/model/available');
        const models = await response.json();
        const selectEl = document.getElementById("modelSelect");

        if (selectEl) {
            selectEl.innerHTML = models.map(m =>
                `<option value="${m}">${m}</option>`
            ).join('');
        }
    } catch (err) {
        console.error("Failed to load models:", err);
    }
}


// update messages into session
function updateMessages() {
    const messagesDiv = document.getElementById("messages");
    if (messagesDiv) sessionStorage.setItem('chat_html_backup', messagesDiv.innerHTML || "");
}

// fill messages between user and bot
function fillMessages() {
    const messagesDiv = document.getElementById("messages");
    const backup = sessionStorage.getItem('chat_html_backup');
    if (backup !== null && backup !== undefined && messagesDiv) {
        messagesDiv.innerHTML = backup;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        activeBotBubble = null;
        if (typeof isSending !== 'undefined') isSending = false; // Mở khóa gửi tin nhắn
    }
}

// clear shown messages
function clearMessages() {
    sessionStorage.removeItem('chat_thread_id'); // optional
    sessionStorage.removeItem('chat_html_backup');
    if (typeof isSending !== 'undefined') isSending = false; // Mở khóa gửi tin nhắn
    activeBotBubble = null;
    const messagesDiv = document.getElementById("messages");
    // emptify messages
    if (messagesDiv) {
        messagesDiv.innerHTML = "";
    }
}


async function loadLayout(layoutType) {
    try {
        const response = await fetch(`/static/templates/${layoutType}_layout.html`);
        if (!response.ok) throw new Error("Template not found");
        const html = await response.text();
        document.getElementById('page-' + layoutType).innerHTML = html;
    } catch (err) {
        console.error("Error loading layout:", err);
    }
}

function autoFocus() {
    const userInput = document.getElementById("userInput");
    if (userInput) userInput.focus();
}

function previewImage(input) {
    const preview = document.getElementById('imagePreview');
    if (input.files && input.files[0]) {
      const reader = new FileReader();
      reader.onload = function(e) {
        preview.src = e.target.result;
        preview.style.display = 'block';
      }
      reader.readAsDataURL(input.files[0]);
    }
}

async function saveSettings() {
    // Logic lưu vào localStorage
    const config = {
        api: document.getElementById('apiEndpoint').value,
        theme: document.getElementById('themeSelect').value,
        mcp_url: document.getElementById('mcpInterval').value,
    };
    localStorage.removeItem('chatbot_config');
    sessionStorage.setItem('chatbot_config', JSON.stringify(config));
    alert("Settings saved!");
    await showPage('home');
}

