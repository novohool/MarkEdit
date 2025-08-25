// Wooden 主题版本的 admin_panel.js 文件
// 所有公共函数已移至 /static/common/js/common.js
// 此文件仅包含 Wooden 主题特有的逻辑（如有）

// 如果需要 Wooden 主题特有的功能，请在此处添加
// 管理员面板页面 - Wooden 主题
// 使用公共函数库，避免代码重复

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    // 首先绑定事件，确保交互功能可用
    bindDrawerEvents();
    
    // 绑定标签页切换事件
    bindTabEvents();
    
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

// Wooden主题特定的其他函数可以在这里添加
// 目前大部分功能都使用公共库实现

// 标签页切换功能
function bindTabEvents() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // 移除所有按钮的活跃状态
            tabButtons.forEach(btn => btn.classList.remove('active'));
            // 添加当前按钮的活跃状态
            this.classList.add('active');
            
            // 隐藏所有标签页内容
            tabContents.forEach(content => content.classList.remove('active'));
            // 显示目标标签页内容
            const targetContent = document.getElementById(targetTab + '-tab');
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
}

