// Default主题特有的函数和变量
// 使用统一的主题加载器，避免代码重复

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', async function() {
    // 使用主题加载器初始化主页面
    await initThemeLoader('main');
});

// Default主题特定的初始化和自定义函数可以在这里添加
