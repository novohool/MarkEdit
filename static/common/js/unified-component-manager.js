/**
 * 统一前端组件管理器
 * 合并重复的UI管理逻辑，提供标准化的组件操作接口
 */

class UnifiedComponentManager {
    constructor() {
        this.components = new Map();
        this.eventListeners = new Map();
        this.initialized = false;
    }

    /**
     * 初始化组件管理器
     */
    init() {
        if (this.initialized) {
            console.warn('UnifiedComponentManager 已经初始化');
            return;
        }

        this.initializeDrawerSystem();
        this.initializeModalSystem();
        this.initializeThemeSystem();
        this.initializeFormSystem();
        this.initializeMessageSystem();

        this.initialized = true;
        console.log('UnifiedComponentManager 初始化完成');
        
        // 触发初始化完成事件
        document.dispatchEvent(new CustomEvent('component-manager:ready', {
            detail: { manager: this }
        }));
    }

    /**
     * 初始化抽屉菜单系统
     */
    initializeDrawerSystem() {
        this.components.set('drawer', new DrawerManager());
    }

    /**
     * 初始化模态框系统
     */
    initializeModalSystem() {
        this.components.set('modal', new ModalManager());
    }

    /**
     * 初始化主题系统
     */
    initializeThemeSystem() {
        this.components.set('theme', new ThemeManager());
    }

    /**
     * 初始化表单系统
     */
    initializeFormSystem() {
        this.components.set('form', new FormManager());
    }

    /**
     * 初始化消息系统
     */
    initializeMessageSystem() {
        this.components.set('message', new MessageManager());
    }

    /**
     * 获取组件管理器
     */
    getComponent(name) {
        return this.components.get(name);
    }

    /**
     * 销毁组件管理器
     */
    destroy() {
        this.components.forEach(component => {
            if (component.destroy) {
                component.destroy();
            }
        });
        this.components.clear();
        this.eventListeners.clear();
        this.initialized = false;
    }
}

/**
 * 抽屉菜单管理器
 */
class DrawerManager {
    constructor() {
        this.activeDrawer = null;
        this.overlay = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.ensureDrawersClosed(); // 确保所有抽屉默认关闭
    }


    bindEvents() {
        // 绑定所有抽屉菜单按钮
        document.addEventListener('click', (e) => {
            // 打开抽屉按钮
            if (e.target.matches('[data-drawer-open]')) {
                const drawerId = e.target.getAttribute('data-drawer-open');
                this.openDrawer(drawerId);
            }
            // 关闭抽屉按钮
            else if (e.target.matches('[data-drawer-close]') || e.target.closest('[data-drawer-close]')) {
                this.closeActiveDrawer();
            }
        });

        // ESC键关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.activeDrawer) {
                this.closeActiveDrawer();
            }
        });
    }

    openDrawer(drawerId) {
        const drawer = document.getElementById(drawerId);
        if (!drawer) return;

        // 关闭当前打开的抽屉
        this.closeActiveDrawer();

        // 打开新抽屉
        drawer.classList.add('open');
        this.activeDrawer = drawer;
        document.body.classList.add('drawer-open');

        // 触发打开事件
        drawer.dispatchEvent(new CustomEvent('drawer:opened', { detail: { drawerId } }));
    }

    /**
     * 确保所有抽屉默认关闭
     */
    ensureDrawersClosed() {
        // 关闭所有可能打开的抽屉
        const drawers = document.querySelectorAll('.drawer');
        drawers.forEach(drawer => {
            drawer.classList.remove('open');
        });
        
        // 关闭所有覆盖层
        const overlays = document.querySelectorAll('.drawer-overlay');
        overlays.forEach(overlay => {
            overlay.classList.remove('open');
        });
        
        // 移除body上的抽屉相关类
        document.body.classList.remove('drawer-open', 'admin-drawer-open', 'drawer-left-open', 'chapter-drawer-open');
        
        this.activeDrawer = null;
    }

    closeActiveDrawer() {
        if (!this.activeDrawer) return;

        const drawerId = this.activeDrawer.id;
        this.activeDrawer.classList.remove('open');
        document.body.classList.remove('drawer-open');

        // 触发关闭事件
        this.activeDrawer.dispatchEvent(new CustomEvent('drawer:closed', { detail: { drawerId } }));
        
        this.activeDrawer = null;
    }

    isDrawerOpen(drawerId) {
        const drawer = document.getElementById(drawerId);
        return drawer && drawer.classList.contains('open');
    }
}

/**
 * 模态框管理器
 */
class ModalManager {
    constructor() {
        this.activeModal = null;
        this.modalStack = [];
        this.init();
    }

    init() {
        this.bindEvents();
        this.ensureModalsClosed(); // 确保所有模态框默认关闭
    }

    /**
     * 确保所有模态框默认关闭
     */
    ensureModalsClosed() {
        // 关闭所有可能打开的模态框
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.classList.remove('show');
        });
        
        // 关闭所有下拉菜单
        const dropdowns = document.querySelectorAll('.dropdown');
        dropdowns.forEach(dropdown => {
            dropdown.classList.remove('open');
        });
        
        // 移除body上的模态框相关类
        document.body.classList.remove('modal-open');
        
        this.activeModal = null;
        this.modalStack = [];
    }

    bindEvents() {
        document.addEventListener('click', (e) => {
            // 打开模态框按钮
            if (e.target.matches('[data-modal-open]')) {
                const modalId = e.target.getAttribute('data-modal-open');
                this.openModal(modalId);
            }
            // 关闭模态框按钮
            else if (e.target.matches('[data-modal-close]') || e.target.closest('[data-modal-close]')) {
                this.closeActiveModal();
            }
            // 点击背景关闭
            else if (e.target.classList.contains('modal')) {
                this.closeActiveModal();
            }
        });

        // ESC键关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.activeModal) {
                this.closeActiveModal();
            }
        });
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;

        // 如果有活动模态框，推入堆栈
        if (this.activeModal) {
            this.modalStack.push(this.activeModal);
        }

        modal.classList.add('show');
        this.activeModal = modal;
        document.body.classList.add('modal-open');

        // 聚焦到模态框
        modal.focus();

        // 触发打开事件
        modal.dispatchEvent(new CustomEvent('modal:opened', { detail: { modalId } }));
    }

    closeActiveModal() {
        if (!this.activeModal) return;

        const modalId = this.activeModal.id;
        this.activeModal.classList.remove('show');
        
        // 触发关闭事件
        this.activeModal.dispatchEvent(new CustomEvent('modal:closed', { detail: { modalId } }));

        // 恢复上一个模态框
        if (this.modalStack.length > 0) {
            this.activeModal = this.modalStack.pop();
        } else {
            this.activeModal = null;
            document.body.classList.remove('modal-open');
        }
    }

    createModal(config) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.id = config.id || 'modal-' + Date.now();
        
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${config.title || ''}</h3>
                    <button class="modal-close" data-modal-close aria-label="关闭">×</button>
                </div>
                <div class="modal-body">
                    ${config.content || ''}
                </div>
                ${config.footer ? `<div class="modal-footer">${config.footer}</div>` : ''}
            </div>
        `;

        document.body.appendChild(modal);
        return modal;
    }
}

/**
 * 主题管理器
 */
class ThemeManager {
    constructor() {
        this.currentTheme = 'default';
        this.themeSelectors = [];
        this.init();
    }

    init() {
        this.detectCurrentTheme();
        this.bindThemeSelectors();
    }

    detectCurrentTheme() {
        // 从CSS链接中检测当前主题
        const themeLink = document.getElementById('theme-link');
        if (themeLink) {
            const href = themeLink.href;
            const match = href.match(/\/static\/([^\/]+)\/css\//);
            if (match) {
                this.currentTheme = match[1];
            }
        }
    }

    bindThemeSelectors() {
        // 绑定所有主题选择器
        document.addEventListener('change', (e) => {
            if (e.target.matches('[data-theme-selector]')) {
                this.switchTheme(e.target.value);
            }
        });

        // 初始化现有的主题选择器
        this.updateThemeSelectors();
    }

    async switchTheme(theme) {
        try {
            // 发送主题更新请求
            const response = await fetch('/api/user/theme', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ theme })
            });

            if (!response.ok) {
                throw new Error('主题切换失败');
            }

            // 更新CSS链接
            this.applyTheme(theme);
            this.currentTheme = theme;

            // 更新所有主题选择器
            this.updateThemeSelectors();

            // 触发主题切换事件
            document.dispatchEvent(new CustomEvent('theme:changed', { 
                detail: { theme, previousTheme: this.currentTheme } 
            }));

        } catch (error) {
            console.error('主题切换失败:', error);
            throw error;
        }
    }

    applyTheme(theme) {
        const themeLink = document.getElementById('theme-link');
        if (themeLink) {
            themeLink.href = `/static/${theme}/css/style.css`;
        }

        // 更新其他主题相关的资源
        const themeScript = document.getElementById('theme-script');
        if (themeScript) {
            themeScript.src = `/static/${theme}/js/main.js`;
        }
    }

    updateThemeSelectors() {
        const selectors = document.querySelectorAll('[data-theme-selector]');
        selectors.forEach(selector => {
            selector.value = this.currentTheme;
        });
    }

    getCurrentTheme() {
        return this.currentTheme;
    }
}

/**
 * 表单管理器
 */
class FormManager {
    constructor() {
        this.validators = new Map();
        this.forms = new Map();
        this.init();
    }

    init() {
        this.bindFormEvents();
    }

    bindFormEvents() {
        document.addEventListener('submit', (e) => {
            if (e.target.matches('form[data-form-managed]')) {
                e.preventDefault();
                this.handleFormSubmit(e.target);
            }
        });

        document.addEventListener('input', (e) => {
            if (e.target.matches('[data-validate]')) {
                this.validateField(e.target);
            }
        });
    }

    async handleFormSubmit(form) {
        const formId = form.id;
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // 表单验证
        if (!this.validateForm(form)) {
            return;
        }

        try {
            // 显示加载状态
            this.setFormLoading(form, true);

            // 获取提交配置
            const url = form.getAttribute('data-submit-url') || form.action;
            const method = form.getAttribute('data-submit-method') || form.method || 'POST';

            const response = await fetch(url, {
                method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error('提交失败');
            }

            const result = await response.json();

            // 触发成功事件
            form.dispatchEvent(new CustomEvent('form:success', { 
                detail: { data, result } 
            }));

        } catch (error) {
            // 触发失败事件
            form.dispatchEvent(new CustomEvent('form:error', { 
                detail: { error, data } 
            }));
        } finally {
            this.setFormLoading(form, false);
        }
    }

    validateForm(form) {
        const fields = form.querySelectorAll('[data-validate]');
        let isValid = true;

        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        return isValid;
    }

    validateField(field) {
        const rules = field.getAttribute('data-validate').split(',');
        const value = field.value.trim();
        let isValid = true;

        // 清除之前的错误
        this.clearFieldError(field);

        for (const rule of rules) {
            const [ruleName, ruleParam] = rule.split(':');
            
            switch (ruleName) {
                case 'required':
                    if (!value) {
                        this.showFieldError(field, '此字段为必填项');
                        isValid = false;
                    }
                    break;
                case 'minLength':
                    if (value.length < parseInt(ruleParam)) {
                        this.showFieldError(field, `最少需要${ruleParam}个字符`);
                        isValid = false;
                    }
                    break;
                case 'email':
                    if (value && !this.isValidEmail(value)) {
                        this.showFieldError(field, '请输入有效的邮箱地址');
                        isValid = false;
                    }
                    break;
                case 'json':
                    if (value) {
                        try {
                            JSON.parse(value);
                        } catch (e) {
                            this.showFieldError(field, '请输入有效的JSON格式');
                            isValid = false;
                        }
                    }
                    break;
            }

            if (!isValid) break;
        }

        return isValid;
    }

    showFieldError(field, message) {
        field.classList.add('error');
        
        let errorElement = field.parentNode.querySelector('.field-error');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'field-error';
            field.parentNode.appendChild(errorElement);
        }
        errorElement.textContent = message;
    }

    clearFieldError(field) {
        field.classList.remove('error');
        const errorElement = field.parentNode.querySelector('.field-error');
        if (errorElement) {
            errorElement.remove();
        }
    }

    setFormLoading(form, loading) {
        const submitBtn = form.querySelector('[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = loading;
            submitBtn.textContent = loading ? '提交中...' : '提交';
        }
    }

    isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }
    
    /**
     * 显示表单并填充数据
     */
    show(id, data = {}) {
        const form = document.getElementById(id);
        if (form) {
            // 填充表单数据
            Object.entries(data).forEach(([key, value]) => {
                const field = form.querySelector(`[name="${key}"]`);
                if (field) {
                    if (field.type === 'checkbox' || field.type === 'radio') {
                        field.checked = value;
                    } else {
                        field.value = value;
                    }
                }
            });
            
            // 显示表单
            form.style.display = 'block';
        }
    }
    
    /**
     * 隐藏表单并重置
     */
    hide(id) {
        const form = document.getElementById(id);
        if (form) {
            // 重置表单
            form.reset();
            
            // 清除验证错误
            const errorElements = form.querySelectorAll('.field-error');
            errorElements.forEach(el => el.remove());
            
            const errorFields = form.querySelectorAll('.error');
            errorFields.forEach(field => field.classList.remove('error'));
            
            // 隐藏表单
            form.style.display = 'none';
        }
    }
}

/**
 * 消息管理器
 */
class MessageManager {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        this.createContainer();
    }

    createContainer() {
        if (document.getElementById('message-container')) {
            this.container = document.getElementById('message-container');
            return;
        }

        this.container = document.createElement('div');
        this.container.id = 'message-container';
        this.container.className = 'message-container';
        this.container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
        `;
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 5000) {
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;
        messageEl.innerHTML = `
            <div class="message-content">
                <span class="message-text">${message}</span>
                <button class="message-close" onclick="this.parentNode.parentNode.remove()">×</button>
            </div>
        `;

        messageEl.style.cssText = `
            margin-bottom: 10px;
            padding: 12px 16px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            background: ${this.getTypeColor(type)};
            color: white;
            animation: slideInRight 0.3s ease;
        `;

        this.container.appendChild(messageEl);

        // 自动移除
        if (duration > 0) {
            setTimeout(() => {
                if (messageEl.parentNode) {
                    messageEl.remove();
                }
            }, duration);
        }

        return messageEl;
    }

    success(message, duration) {
        return this.show(message, 'success', duration);
    }

    error(message, duration) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration) {
        return this.show(message, 'info', duration);
    }

    getTypeColor(type) {
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };
        return colors[type] || colors.info;
    }
}

// 创建全局实例
window.ComponentManager = new UnifiedComponentManager();

// 自动初始化
document.addEventListener('DOMContentLoaded', () => {
    window.ComponentManager.init();
});

// 导出给其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        UnifiedComponentManager,
        DrawerManager,
        ModalManager,
        ThemeManager,
        FormManager,
        MessageManager
    };
}