async function showPage(pageId, isNewChat = true) {
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
        const messagesDiv = document.getElementById("messages");

        if (isNewChat) {
            console.log("Starting a fresh chat...");
            // 1. Clear old thread ID
            sessionStorage.removeItem('chat_thread_id');
            // 2. Clear conversation history
            sessionStorage.removeItem('chat_html_backup');
            if (messagesDiv) {
                messagesDiv.innerHTML = "";
            }

            // Reset biến global quản lý bubble (nếu có)
            activeBotBubble = null;

        } else {
            console.log("Restoring chat from backup...");
            const backup = sessionStorage.getItem('chat_html_backup');
            if (backup && messagesDiv) {
                messagesDiv.innerHTML = backup;
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
        }
        initChatEvents();
    }
}


async function loadLayout(layoutType) {
    try {
        const response = await fetch(`/static/templates/${layoutType}_layout.html`);
        if (!response.ok) throw new Error("Template not found");
        const html = await response.text();
        document.getElementById('page-' + layoutType).innerHTML = html;
        console.log(`${layoutType} layout loaded successfully!`);
    } catch (err) {
        console.error("Error loading layout:", err);
    }
}

function initChatEvents() {
    const userInput = document.getElementById("userInput");
    if (userInput) {
        userInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
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


function saveChatConversation() {
    const html = document.getElementById("messages").innerHTML;
    sessionStorage.setItem('chat_html_backup', html);
}

async function saveSettings() {
    // Logic lưu vào localStorage
    const config = {
        api: document.getElementById('apiEndpoint').value,
        theme: document.getElementById('themeSelect').value
    };
    localStorage.removeItem('chatbot_config');
    sessionStorage.setItem('chatbot_config', JSON.stringify(config));
    alert("Settings saved!");
    await showPage('home');
}

