/**
 * 统一主题切换组件
 * 用于替换各页面重复的主题切换逻辑
 */

class UnifiedThemeSwitch {
    constructor() {
        this.selectors = [];
        this.currentTheme = 'default';
        this.initialized = false;
    }
    
    init() {
        if (this.initialized) return;
        
        this.detectCurrentTheme();
        this.scanThemeSelectors();
        this.bindGlobalEvents();
        this.initialized = true;
    }

    /**
     * 检测当前主题
     */
    detectCurrentTheme() {
        const themeLink = document.getElementById('theme-link');
        if (themeLink) {
            const href = themeLink.href;
            const match = href.match(/\/static\/([^\/]+)\/css\//);
            if (match) {
                this.currentTheme = match[1];
            }
        }
    }

    /**
     * 扫描并注册所有主题选择器
     */
    scanThemeSelectors() {
        const selectors = document.querySelectorAll('select[id*="theme"], [data-theme-selector]');
        selectors.forEach(selector => {
            this.registerThemeSelector(selector);
        });
    }

    /**
     * 注册主题选择器
     */
    registerThemeSelector(selector) {
        if (this.selectors.includes(selector)) return;

        this.selectors.push(selector);
        
        // 设置当前值
        selector.value = this.currentTheme;
        
        // 绑定变化事件
        selector.addEventListener('change', (e) => {
            this.handleThemeChange(e.target.value, e.target);
        });
    }

    /**
     * 处理主题变化
     */
    async handleThemeChange(newTheme, sourceSelector) {
        if (newTheme === this.currentTheme) return;

        try {
            // 立即应用视觉变化
            this.applyThemeVisually(newTheme);
            
            // 如果是保存按钮触发的，不发送API请求
            const isSaveAction = sourceSelector && sourceSelector.hasAttribute('data-no-auto-save');
            
            if (!isSaveAction) {
                // 发送API请求保存主题
                await this.saveTheme(newTheme);
            }
            
            // 更新状态
            this.currentTheme = newTheme;
            this.syncAllSelectors();
            
            // 触发主题变化事件
            document.dispatchEvent(new CustomEvent('theme:switched', {
                detail: { 
                    theme: newTheme, 
                    sourceSelector: sourceSelector,
                    saved: !isSaveAction
                }
            }));
            
        } catch (error) {
            console.error('主题切换失败:', error);
            
            // 恢复选择器状态
            if (sourceSelector) {
                sourceSelector.value = this.currentTheme;
            }
            
            throw error;
        }
    }

    /**
     * 立即应用主题的视觉变化
     */
    applyThemeVisually(theme) {
        const themeLink = document.getElementById('theme-link');
        if (themeLink) {
            themeLink.href = `/static/${theme}/css/style.css`;
        }

        // 更新其他主题相关的资源
        const themeScript = document.getElementById('theme-script');
        if (themeScript) {
            themeScript.src = `/static/${theme}/js/main.js`;
        }

        // 更新其他可能的主题相关元素
        const themeElements = document.querySelectorAll('[data-theme-resource]');
        themeElements.forEach(el => {
            const resourceType = el.getAttribute('data-theme-resource');
            const basePath = el.getAttribute('data-base-path');
            if (basePath) {
                el.href = basePath.replace('{{theme}}', theme);
            }
        });
    }

    /**
     * 保存主题到服务器
     */
    async saveTheme(theme) {
        const response = await fetch('/api/user/theme', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ theme: theme })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '主题保存失败');
        }

        return await response.json();
    }

    /**
     * 同步所有主题选择器的值
     */
    syncAllSelectors() {
        this.selectors.forEach(selector => {
            if (selector.value !== this.currentTheme) {
                selector.value = this.currentTheme;
            }
        });
    }

    /**
     * 绑定全局事件
     */
    bindGlobalEvents() {
        // 监听DOM变化，自动注册新的主题选择器
        const initObserver = () => {
            // 确保document.body存在
            if (!document.body) {
                // 如果document.body不存在，等待DOMContentLoaded事件
                document.addEventListener('DOMContentLoaded', initObserver);
                return;
            }
            
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            const newSelectors = node.querySelectorAll('select[id*="theme"], [data-theme-selector]');
                            newSelectors.forEach(selector => {
                                this.registerThemeSelector(selector);
                            });
                        }
                    });
                });
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
            
            // 将observer保存到实例上，以便后续可能需要断开连接
            this.observer = observer;
        };
        
        // 初始化observer
        initObserver();
    }

    /**
     * 手动保存当前主题（用于保存按钮）
     */
    async saveCurrentTheme() {
        try {
            await this.saveTheme(this.currentTheme);
            
            // 触发保存成功事件
            document.dispatchEvent(new CustomEvent('theme:saved', {
                detail: { theme: this.currentTheme }
            }));
            
            return true;
        } catch (error) {
            // 触发保存失败事件
            document.dispatchEvent(new CustomEvent('theme:save-error', {
                detail: { theme: this.currentTheme, error: error }
            }));
            
            throw error;
        }
    }

    /**
     * 获取当前主题
     */
    getCurrentTheme() {
        return this.currentTheme;
    }

    /**
     * 获取可用的主题列表
     */
    getAvailableThemes() {
        // 从页面中的选择器获取可用主题
        const firstSelector = this.selectors[0];
        if (firstSelector) {
            return Array.from(firstSelector.options).map(option => ({
                value: option.value,
                text: option.textContent
            }));
        }
        
        // 默认主题列表
        return [
            { value: 'default', text: '默认主题' },
            { value: 'wooden', text: '木质主题' }
        ];
    }

    /**
     * 销毁主题切换器
     */
    destroy() {
        // 断开MutationObserver的连接
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
        }
        
        this.selectors.forEach(selector => {
            selector.removeEventListener('change', this.handleThemeChange);
        });
        this.selectors = [];
    }
}

// 自动初始化
document.addEventListener('DOMContentLoaded', () => {
    window.UnifiedThemeSwitch = new UnifiedThemeSwitch();
    window.UnifiedThemeSwitch.init();
});

// 为了向后兼容，提供全局函数
window.switchTheme = function(theme) {
    return window.UnifiedThemeSwitch.handleThemeChange(theme);
};

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UnifiedThemeSwitch;
}