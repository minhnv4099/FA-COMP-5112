// Hàm cuộn lên đầu
function scrollToTop() {
   const box = document.getElementById("chat-wrapper");
    if (box) {
        box.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }
}

function scrollToBottom() {
    const box = document.getElementById("chat-wrapper");
    if (box) {
        box.scrollTo({
            top: box.scrollHeight,
            behavior: 'smooth'
        });
    }
}

async function sendQuickPrompt(element) {
    const descElement = element.querySelector('.sugg-desc');
    if (!descElement) return;

    const textToSend = descElement.innerText; // Lấy nội dung chữ
    const userInput = document.getElementById("userInput");

    // 2. Kiểm tra trạng thái gửi (tránh gửi chồng chéo)
    if (typeof isSending !== 'undefined' && isSending) return;

    // 3. Điền vào input và kích hoạt sự kiện input (để auto-resize nếu có)
    if (userInput) {
        userInput.value = textToSend;
        userInput.dispatchEvent(new Event('input'));
    }

    const container = element.closest('.suggestions-column');
    if (container) {
        container.style.opacity = '1';
    }

    if (typeof sendMessage === 'function') {
        setTimeout(scrollToBottom(), 100);
        await sendMessage();
    }
}
