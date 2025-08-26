// 管理员页面 - Wooden 主题
// 使用统一的主题加载器，避免代码重复

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', async function() {
    // 使用主题加载器初始化管理员页面
    await initThemeLoader('admin');
});

// Wooden主题特定的函数可以在此添加