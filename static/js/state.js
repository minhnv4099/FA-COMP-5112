const AppState = {
    saveCurrentPage(pageId) {
        sessionStorage.setItem('active_page', pageId);
    },

    getLastPage() {
        return sessionStorage.getItem('active_page') || 'home';
    },

    async reload() {
        const lastPage = this.getLastPage();
        await showPage(lastPage);
    }
};

// Lắng nghe sự kiện load trang
window.addEventListener('load', () => {
    // Để một khoảng nghỉ rất ngắn để DOM ổn định
    setTimeout(() => AppState.reload(), 50);
});
