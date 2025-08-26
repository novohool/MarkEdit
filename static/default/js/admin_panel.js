// 管理员面板页面 - Default 主题
// 使用统一的主题加载器，避免代码重复

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', async function() {
    // 使用主题加载器初始化管理员面板页面
    await initThemeLoader('admin_panel');
});

// Default主题特定的其他函数可以在这里添加