/* MarkEdit 增强主题切换管理器
 * 支持TailwindCSS风格组件样式的主题切换
 */

class EnhancedThemeManager {
    constructor() {
        this.currentTheme = 'default';
        this.themeLinks = {
            main: null,
            components: null
        };
        this.selectors = [];
        
        this.init();
    }
    
    init() {
        // 获取主题样式链接元素
        this.themeLinks.main = document.getElementById('theme-link');
        this.themeLinks.components = document.getElementById('components-style');
        
        // 获取所有主题选择器
        this.selectors = document.querySelectorAll('.theme-selector, #theme-selector, #user-theme-selector, #user-panel-theme-selector');
        
        // 绑定选择器事件
        this.bindSelectors();
        
        // 获取当前主题
        this.detectCurrentTheme();
        
        // 同步所有选择器
        this.syncSelectors();
        
        console.log('EnhancedThemeManager initialized with theme:', this.currentTheme);
    }
    
    detectCurrentTheme() {
        if (this.themeLinks.main) {
            const href = this.themeLinks.main.href;
            if (href.includes('/wooden/')) {
                this.currentTheme = 'wooden';
            } else {
                this.currentTheme = 'default';
            }
        }
    }
    
    bindSelectors() {
        this.selectors.forEach(selector => {
            if (selector) {
                selector.addEventListener('change', (event) => {
                    this.switchTheme(event.target.value);
                });
            }
        });
    }
    
    switchTheme(themeName) {
        if (!themeName || themeName === this.currentTheme) {
            return;
        }
        
        // 更新主题样式链接
        this.updateThemeLinks(themeName);
        
        // 更新当前主题
        this.currentTheme = themeName;
        
        // 同步所有选择器
        this.syncSelectors();
        
        // 保存主题设置到localStorage
        this.saveThemePreference(themeName);
        
        // 触发主题切换事件
        this.dispatchThemeChangeEvent(themeName);
        
        // 添加切换动画效果
        this.addSwitchAnimation();
        
        console.log('Theme switched to:', themeName);
    }
    
    updateThemeLinks(themeName) {
        // 更新主样式表
        if (this.themeLinks.main) {
            this.themeLinks.main.href = `/static/${themeName}/css/style.css`;
        }
        
        // 更新组件样式表
        if (this.themeLinks.components) {
            this.themeLinks.components.href = `/static/${themeName}/css/integrated-components.css`;
        }
    }
    
    syncSelectors() {
        this.selectors.forEach(selector => {
            if (selector && selector.value !== this.currentTheme) {
                selector.value = this.currentTheme;
            }
        });
    }
    
    saveThemePreference(themeName) {
        try {
            localStorage.setItem('markEditTheme', themeName);
        } catch (error) {
            console.warn('无法保存主题设置到localStorage:', error);
        }
    }
    
    loadThemePreference() {
        try {
            const savedTheme = localStorage.getItem('markEditTheme');
            if (savedTheme && (savedTheme === 'default' || savedTheme === 'wooden')) {
                return savedTheme;
            }
        } catch (error) {
            console.warn('无法从localStorage加载主题设置:', error);
        }
        return 'default';
    }
    
    dispatchThemeChangeEvent(themeName) {
        const event = new CustomEvent('themeChanged', {
            detail: {
                theme: themeName,
                previousTheme: this.currentTheme
            }
        });
        document.dispatchEvent(event);
    }
    
    addSwitchAnimation() {
        // 为body添加主题切换动画
        document.body.classList.add('theme-switching');
        
        setTimeout(() => {
            document.body.classList.remove('theme-switching');
        }, 300);
    }
    
    // 公共方法：获取当前主题
    getCurrentTheme() {
        return this.currentTheme;
    }
    
    // 公共方法：程序化切换主题
    setTheme(themeName) {
        this.switchTheme(themeName);
    }
    
    // 公共方法：添加主题选择器
    addSelector(selector) {
        if (selector && !this.selectors.includes(selector)) {
            this.selectors.push(selector);
            selector.addEventListener('change', (event) => {
                this.switchTheme(event.target.value);
            });
            selector.value = this.currentTheme;
        }
    }
    
    // 公共方法：移除主题选择器
    removeSelector(selector) {
        const index = this.selectors.indexOf(selector);
        if (index > -1) {
            this.selectors.splice(index, 1);
        }
    }
    
    // 初始化页面加载时的主题
    initializePageTheme() {
        const preferredTheme = this.loadThemePreference();
        if (preferredTheme !== this.currentTheme) {
            this.switchTheme(preferredTheme);
        }
    }
}

// 主题切换动画CSS（通过JavaScript注入）
const themeAnimationCSS = `
<style id="theme-animation-css">
.theme-switching {
    transition: all 0.3s ease-in-out;
}

.theme-switching * {
    transition: background-color 0.3s ease-in-out, 
                color 0.3s ease-in-out, 
                border-color 0.3s ease-in-out,
                box-shadow 0.3s ease-in-out !important;
}
</style>
`;

// 注入主题动画样式
if (!document.getElementById('theme-animation-css')) {
    document.head.insertAdjacentHTML('beforeend', themeAnimationCSS);
}

// 创建全局主题管理器实例
let enhancedThemeManager;

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    enhancedThemeManager = new EnhancedThemeManager();
    
    // 初始化页面主题
    enhancedThemeManager.initializePageTheme();
});

// 向后兼容的全局函数
function setupThemeSelector() {
    console.log('Using enhanced theme manager - setupThemeSelector is handled automatically');
    
    // 重新检测和绑定选择器（兼容动态添加的选择器）
    if (enhancedThemeManager) {
        enhancedThemeManager.init();
    }
}

// 兼容原有的API
function switchTheme(themeName) {
    if (enhancedThemeManager) {
        enhancedThemeManager.setTheme(themeName);
    }
}

function getCurrentTheme() {
    return enhancedThemeManager ? enhancedThemeManager.getCurrentTheme() : 'default';
}

// 导出主题管理器（如果支持模块化）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EnhancedThemeManager, enhancedThemeManager };
} else if (typeof window !== 'undefined') {
    window.EnhancedThemeManager = EnhancedThemeManager;
    window.enhancedThemeManager = enhancedThemeManager;
}