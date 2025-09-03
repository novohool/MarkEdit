// 主题JavaScript加载器
// 统一处理不同主题的JavaScript逻辑，避免代码重复

/**
 * 主题加载器类
 * 负责根据主题加载相应的CSS和JavaScript逻辑
 */
class ThemeLoader {
    constructor() {
        this.currentTheme = 'default';
        this.pageType = null; // 'main', 'admin', 'admin_panel' 等
        this.initialized = false;
    }

    /**
     * 初始化主题加载器
     * @param {string} pageType - 页面类型
     */
    async init(pageType) {
        this.pageType = pageType;
        
        try {
            // 获取当前用户主题设置
            await this.loadCurrentTheme();
            
            // 根据页面类型执行相应的初始化
            switch(pageType) {
                case 'main':
                    await this.initMainPage();
                    break;
                case 'admin':
                    await this.initAdminPage();
                    break;
                case 'admin_panel':
                    await this.initAdminPanelPage();
                    break;
                default:
                    console.warn('未知的页面类型:', pageType);
            }
            
            this.initialized = true;
            console.log(`主题加载器初始化完成，当前主题: ${this.currentTheme}, 页面类型: ${pageType}`);
            
        } catch (error) {
            console.error('主题加载器初始化失败:', error);
            // 使用默认设置继续
            this.currentTheme = 'default';
            this.initialized = true;
        }
    }

    /**
     * 加载当前用户的主题设置
     */
    async loadCurrentTheme() {
        try {
            const response = await fetch('/api/user/theme');
            if (response.ok) {
                const data = await response.json();
                this.currentTheme = data.theme || 'default';
            }
        } catch (error) {
            console.warn('获取主题设置失败，使用默认主题:', error);
            this.currentTheme = 'default';
        }
    }

    /**
     * 初始化主页面
     */
    async initMainPage() {
        // 初始化编辑器状态
        if (typeof initializeEditor === 'function') {
            initializeEditor();
        }
        
        // 初始化CodeMirror编辑器
        if (typeof initializeCodeMirror === 'function') {
            initializeCodeMirror();
        }
        
        // 加载文件树
        if (typeof loadFileTree === 'function') {
            loadFileTree();
        }
        
        // 绑定事件监听器（包含文件浏览器初始化）
        if (typeof bindEventListeners === 'function') {
            bindEventListeners();
        }
        
        // 注意：不再调用 initializeResizer 和 initializeSidebarState
        // 因为 bindEventListeners 中的 initializeFileBrowser 已经包含了这些初始化
    }

    /**
     * 初始化管理员页面
     */
    async initAdminPage() {
        // 绑定抽屉事件
        if (typeof bindDrawerEvents === 'function') {
            bindDrawerEvents();
            console.log(`在${this.currentTheme}主题admin页面中绑定了抽屉事件`);
        }
        
        // 初始化管理员页面
        if (typeof initializeAdminPage === 'function') {
            initializeAdminPage();
        }
        
        // 初始化公共设置
        if (typeof initializeCommonSettings === 'function') {
            initializeCommonSettings();
        }
    }

    /**
     * 初始化管理员面板页面
     */
    async initAdminPanelPage() {
        try {
            // 绑定基础事件
            if (typeof bindDrawerEvents === 'function') {
                bindDrawerEvents();
            }
            
            // 绑定标签页切换事件
            this.bindTabEvents();
            
            // 初始化面板
            await this.initializeAdminPanel();
            
            // 初始化公共设置
            if (typeof initializeCommonSettings === 'function') {
                initializeCommonSettings();
            }
            
        } catch (error) {
            console.error('管理员面板页面初始化失败:', error);
            // 确保基本事件绑定可用
            if (typeof bindDrawerEvents === 'function') {
                bindDrawerEvents();
            }
        }
    }

    /**
     * 初始化管理员面板的具体逻辑
     */
    async initializeAdminPanel() {
        // 设置主题选择器
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            themeSelector.value = this.currentTheme;
            themeSelector.addEventListener('change', (e) => {
                this.switchTheme(e.target.value);
            });
        }
        
        // 应用主题CSS
        this.applyThemeCSS();
        
        // 检查用户权限
        if (typeof checkUserInfo === 'function') {
            await checkUserInfo();
        }
        
        // 加载配置数据
        if (typeof loadConfigData === 'function') {
            await loadConfigData();
        }
        
        // 绑定管理员面板事件
        if (typeof bindAdminPanelEvents === 'function') {
            bindAdminPanelEvents();
        }
    }

    /**
     * 绑定标签页切换事件
     */
    bindTabEvents() {
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

    /**
     * 切换主题
     * @param {string} themeName - 主题名称
     */
    async switchTheme(themeName) {
        try {
            // 发送请求更新主题设置
            const response = await fetch('/api/user/theme', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ theme: themeName })
            });
            
            if (response.ok) {
                this.currentTheme = themeName;
                this.applyThemeCSS();
                
                if (typeof showMessage === 'function') {
                    window.ComponentManager.getComponent('message').success(`主题已切换为: ${themeName}`);
                }
                
                // 刷新页面以应用新主题
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                throw new Error('主题切换失败');
            }
        } catch (error) {
            console.error('主题切换失败:', error);
            if (typeof showMessage === 'function') {
                window.ComponentManager.getComponent('message').error('主题切换失败: ' + error.message);
            }
        }
    }

    /**
     * 应用主题CSS
     */
    applyThemeCSS() {
        const linkElement = document.getElementById('theme-link');
        if (linkElement) {
            linkElement.href = `/static/${this.currentTheme}/css/style.css`;
        }
        
        // 更新页面特定的CSS文件
        const adminPanelLink = document.querySelector('link[href*="admin_panel.css"]');
        if (adminPanelLink) {
            adminPanelLink.href = `/static/${this.currentTheme}/css/admin_panel.css`;
        }
        
        const integratedComponentsLink = document.querySelector('link[href*="integrated-components.css"]');
        if (integratedComponentsLink) {
            integratedComponentsLink.href = `/static/${this.currentTheme}/css/integrated-components.css`;
        }
        
        // 确保主题相关的CSS变量生效
        document.documentElement.setAttribute('data-theme', this.currentTheme);
    }

    /**
     * 获取当前主题
     * @returns {string} 当前主题名称
     */
    getCurrentTheme() {
        return this.currentTheme;
    }

    /**
     * 获取页面类型
     * @returns {string} 页面类型
     */
    getPageType() {
        return this.pageType;
    }
}

// 创建全局主题加载器实例
window.themeLoader = new ThemeLoader();

// 提供快捷初始化函数
window.initThemeLoader = async function(pageType) {
    await window.themeLoader.init(pageType);
};

// 向后兼容：提供原有的函数名
window.bindTabEvents = function() {
    if (window.themeLoader.initialized) {
        window.themeLoader.bindTabEvents();
    }
};

window.initializeAdminPanel = async function() {
    if (window.themeLoader.initialized) {
        await window.themeLoader.initializeAdminPanel();
    }
};