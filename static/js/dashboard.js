function createNewChat() {
    // save only when the current chat has message
    if (document.getElementById("messages")?.innerText) {
        saveCurrentChat();
    }

    // clear session messages
    clearMessages();
    const newThreadId = crypto.randomUUID();
    sessionStorage.setItem('chat_thread_id', newThreadId);

    showPage('chat', false);
    document.querySelectorAll('.nav-item').forEach(p => p.classList.remove('active'));
    autoFocus();
}

function saveCurrentChat() {
    threadId = sessionStorage.getItem('chat_thread_id');
    if (!threadId) return;

    // 1. Lấy danh sách conversations hiện có (Parse từ String sang Object)
    let conversations = JSON.parse(sessionStorage.getItem('conversations')) || [];
    updateMessages();

    // 2. Chuẩn bị dữ liệu chat hiện tại
    const currentChatData = {
        chat_thread_id: threadId,
        chat_html_backup: sessionStorage.getItem('chat_html_backup'),
        last_updated: new Date().getTime(), // Dùng timestamp để dễ sắp xếp
        title: document.getElementById("messages")?.innerText?.substring(0, 25) || "New Conversation"
    };

    // 3. Kiểm tra xem threadId này đã có trong mảng chưa
    const existingIndex = conversations.findIndex(c => c.chat_thread_id === threadId);

    if (existingIndex !== -1) {
        // NẾU ĐÃ CÓ: Ghi đè (Update) phần tử đó
        conversations[existingIndex] = currentChatData;
    } else {
        // NẾU CHƯA CÓ: Thêm mới vào đầu mảng (Unshift)
        conversations.unshift(currentChatData);
    }

    // 4. Lưu ngược lại vào Storage
    sessionStorage.setItem('conversations', JSON.stringify(conversations));

    // Auto delete oldest chat
    if (conversations.length > 10) {
        clearOldestUpdatedChat();
    }
}

function deleteCurrentChat() {
    autoFocus();

    const threadId = sessionStorage.getItem('chat_thread_id');
    if (!threadId) {
        console.log("No chats to delete.");
        return;
    }

        // 1. Lấy danh sách từ storage
    let conversations = JSON.parse(sessionStorage.getItem('conversations')) || [];

        // 2. Lọc bỏ cuộc hội thoại có ID hiện tại
    conversations = conversations.filter(c => c.chat_thread_id !== threadId);

        // 3. Cập nhật lại danh sách tổng
    sessionStorage.setItem('conversations', JSON.stringify(conversations));
    clearMessages();
    // auto activate a chat
    updateSidebarHistory();

    if (conversations.length === 0) {
        clearMessages();
        return;
    }
}


function clearOldestUpdatedChat() {
    // 1. Lấy mảng từ storage
    let conversations = JSON.parse(sessionStorage.getItem('conversations')) || [];
    autoFocus();

    if (conversations.length === 0) {
        console.log("No chats to delete.");
        return;
    }

    // 2. Sắp xếp mảng theo thời gian tăng dần (cũ nhất đứng đầu)
    // Nếu bạn đã dùng .unshift() khi save, thì phần tử cuối mảng thường là cũ nhất
    // Nhưng để chắc chắn, ta dùng sort theo last_updated
    conversations.sort((a, b) => a.last_updated - b.last_updated);

    // 3. Lấy ra ID của thằng cũ nhất để thông báo (tùy chọn)
    const oldest = conversations[0];

    // 4. Xóa phần tử đầu tiên trong mảng đã sort
    conversations.shift();

    // 5. Lưu lại và cập nhật giao diện
    sessionStorage.setItem('conversations', JSON.stringify(conversations));

    // auto activate a chat
    updateSidebarHistory();

    if (conversations.length === 0) {
        clearMessages();
        return;
    }
}


function clearAllChats() {
    if (confirm("Bạn có chắc chắn muốn xóa TẤT CẢ lịch sử trò chuyện không? Hành động này không thể hoàn tác.")) {
        // 1. Xóa mảng tổng
        sessionStorage.removeItem('conversations');

        // 2. Xóa dữ liệu của phiên hiện tại
        clearMessages();
        // 4. Cập nhật Sidebar (để hiện danh sách trống)
        updateSidebarHistory();

        // 5. Đưa người dùng về trang chủ hoặc tạo chat mới
        console.log("All chats cleared.");
    }
}

function leaveChatLayout() {
    saveCurrentChat();
    clearMessages();
    showPage('home');
}
