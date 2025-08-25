// 管理员面板页面 - Default 主题
// 使用公共函数库，避免代码重复

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    // 首先绑定事件，确保交互功能可用
    bindDrawerEvents();
    
    // 然后进行其他初始化
    initializeAdminPanel();
    
    // 初始化公共设置
    initializeCommonSettings();
});

// 初始化管理员面板页面
async function initializeAdminPanel() {
    try {
        // 获取用户主题设置
        const themeResponse = await fetch('/api/user/theme');
        const themeData = await themeResponse.json();
        const theme = themeData.theme || 'default';
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            themeSelector.value = theme;
            themeSelector.addEventListener('change', function() {
                const selectedTheme = this.value;
                switchTheme(selectedTheme);
            });
        }
        
        // 应用主题CSS
        const linkElement = document.getElementById('theme-link');
        if (linkElement) {
            linkElement.href = `/static/${theme}/css/style.css`;
        }
        
        // 检查用户权限
        await checkUserInfo();
        
        // 加载配置数据和备份文件列表
        await loadConfigData();
        
        // 绑定管理员面板特有的事件
        bindAdminPanelEvents();
        
    } catch (error) {
        console.error('页面初始化失败:', error);
        showMessage('页面初始化失败: ' + error.message, 'error');
        
        // 即使初始化失败，也要确保基本的事件绑定可用
        try {
            bindDrawerEvents();
            console.log('在异常处理中重新绑定了抽屉事件');
        } catch (bindError) {
            console.error('事件绑定也失败了:', bindError);
        }
    }
}

// 绑定管理员面板特有的事件（已移至 admin-common.js）
// function bindAdminPanelEvents() { ... }

// 保存章节顺序已移至公共库

// 重置章节顺序已移至公共库

// Default主题特定的其他函数可以在这里添加
// 目前大部分功能都使用公共库实现