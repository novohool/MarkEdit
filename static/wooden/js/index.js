// 木质主题版本的index.js文件
// 用户面板相关函数已移至公共库 /static/common/js/common.js

// 页面加载时获取用户主题设置并应用
document.addEventListener('DOMContentLoaded', function() {
    // 获取用户主题设置
    fetch('/api/user/theme')
        .then(response => response.json())
        .then(data => {
            const theme = data.theme || 'default';
            const themeSelector = document.getElementById('theme-selector');
            if (themeSelector) {
                themeSelector.value = theme;
            }
            
            // 应用主题CSS
            const linkElement = document.getElementById('theme-link');
            if (linkElement) {
                linkElement.href = `/static/${theme}/css/style.css`;
            }
        })
        .catch(error => {
            console.error('获取用户信息失败:', error);
        });
    
    // 添加用户面板按钮事件监听器
    const myAccountBtn = document.getElementById('myaccount-btn');
    if (myAccountBtn) {
        myAccountBtn.addEventListener('click', function() {
            // 改为显示用户面板下拉菜单
            loadUserInfo(); // 加载用户信息（使用公共库函数）
            const userPanelDrawer = document.getElementById('user-panel-drawer');
            const drawerOverlay = document.getElementById('drawer-overlay');
            if (userPanelDrawer && drawerOverlay) {
                userPanelDrawer.classList.add('open');
                drawerOverlay.classList.add('open');
            }
        });
    }
    
    // 添加dashboard按钮事件监听器
    const dashboardBtn = document.getElementById('dashboard-btn');
    if (dashboardBtn) {
        dashboardBtn.addEventListener('click', function() {
            // 跳转到dashboard页面
            window.location.href = '/dashboard';
        });
    }
    
    // 绑定抽屉菜单事件 - 已在main.js中通过bindEventListeners调用，避免重复绑定
    // bindDrawerEvents();
    
    // 绑定用户面板事件监听器（使用公共库函数）
    const userPanelSaveThemeBtn = document.getElementById('user-panel-save-theme-btn');
    if (userPanelSaveThemeBtn) {
        userPanelSaveThemeBtn.addEventListener('click', saveUserTheme);
    }
    
    const userPanelSaveLlmConfigBtn = document.getElementById('user-panel-save-llm-config-btn');
    if (userPanelSaveLlmConfigBtn) {
        userPanelSaveLlmConfigBtn.addEventListener('click', saveUserLlmConfig);
    }
    
    const userPanelResetLlmConfigBtn = document.getElementById('user-panel-reset-llm-config-btn');
    if (userPanelResetLlmConfigBtn) {
        userPanelResetLlmConfigBtn.addEventListener('click', resetUserLlmConfig);
    }
});

// showMessage 函数已移至公共库