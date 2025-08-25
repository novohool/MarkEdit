// 管理员页面 - Default 主题
// 使用公共管理员函数库，避免代码重复

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 首先绑定抽屉事件，确保交互功能可用
    if (typeof bindDrawerEvents === 'function') {
        bindDrawerEvents();
        console.log('在admin.js中绑定了抽屉事件');
    }
    
    // 初始化管理员页面（公共函数）
    if (typeof initializeAdminPage === 'function') {
        initializeAdminPage();
    }
    
    // 初始化公共设置
    if (typeof initializeCommonSettings === 'function') {
        initializeCommonSettings();
    }
});

// Default主题特定的函数（如果有的话）
// 目前所有功能都使用公共库，保持文件简洁