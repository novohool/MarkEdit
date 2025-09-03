/**
 * 我的账户页面 - 数据绑定和交互管理
 * 优化版本，提供更好的用户体验和数据绑定
 */

class MyAccountManager {
    constructor() {
        this.userData = null;
        this.settings = {
            theme: 'default',
            llmConfig: {},
            preferences: {}
        };
        this.isLoading = false;
        this.init();
    }

    /**
     * 初始化管理器
     */
    async init() {
        console.log('初始化我的账户管理器...');

        // 等待组件管理器初始化完成
        await this.waitForComponentManager();

        // 初始化数据绑定
        this.initializeDataBinding();

        // 绑定事件监听器
        this.bindEventListeners();

        // 加载用户数据
        await this.loadUserData();

        // 加载用户设置
        await this.loadUserSettings();

        // 加载活动记录
        await this.loadRecentActivities();

        // 初始化主题选择器
        this.initializeThemeSelector();

        console.log('我的账户管理器初始化完成');
    }

    /**
     * 等待组件管理器初始化
     */
    async waitForComponentManager() {
        let attempts = 0;
        const maxAttempts = 50;

        while (!window.ComponentManager?.isInitialized && attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }

        if (!window.ComponentManager?.isInitialized) {
            console.warn('组件管理器初始化超时，使用降级模式');
        }
    }

    /**
     * 初始化数据绑定
     */
    initializeDataBinding() {
        if (window.ComponentManager?.isInitialized) {
            // 设置初始数据结构
            window.ComponentManager.setDataBatch({
                'user.username': '加载中...',
                'user.primaryRole': '用户',
                'user.createdAt': '-',
                'user.lastLogin': '-',
                'user.currentTheme': '-',
                'settings.theme': 'default',
                'settings.llmConfig': {},
                'activities.list': []
            });

            // 监听数据变化
            window.ComponentManager.on('dataChange', (event) => {
                console.log('数据变化:', event.detail);
            });

            console.log('数据绑定初始化完成');
        }
    }

    /**
     * 绑定所有事件监听器
     */
    bindEventListeners() {
        // 主题保存按钮
        const saveThemeBtn = document.getElementById('save-theme-btn');
        if (saveThemeBtn) {
            saveThemeBtn.addEventListener('click', () => this.saveThemeSettings());
        }

        // LLM配置保存按钮
        const saveLLMBtn = document.getElementById('save-llm-config-btn');
        if (saveLLMBtn) {
            saveLLMBtn.addEventListener('click', () => this.saveLLMConfig());
        }

        // LLM配置重置按钮
        const resetLLMBtn = document.getElementById('reset-llm-config-btn');
        if (resetLLMBtn) {
            resetLLMBtn.addEventListener('click', () => this.resetLLMConfig());
        }

        // 主题选项点击事件
        document.querySelectorAll('.theme-option').forEach(option => {
            option.addEventListener('click', (e) => {
                this.selectTheme(e.currentTarget);
            });
        });

        // 登出按钮
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.handleLogout());
        }

        // 主题选择器变化事件
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            themeSelector.addEventListener('change', (e) => {
                this.changeTheme(e.target.value);
            });
        }

        console.log('事件监听器绑定完成');
    }

    /**
     * 加载用户数据
     */
    async loadUserData() {
        try {
            this.setLoadingState(true);

            const response = await fetch('/api/user/profile');
            if (!response.ok) {
                if (response.status === 401) {
                    window.location.href = '/login';
                    return;
                }
                const errorText = await response.text();
                throw new Error(`获取用户信息失败: ${errorText}`);
            }

            this.userData = await response.json();
            
            // 确保数据格式正确
            if (!this.userData.username) {
                // 尝试从用户信息API获取
                const infoResponse = await fetch('/api/user/info');
                if (infoResponse.ok) {
                    const infoData = await infoResponse.json();
                    this.userData = { ...this.userData, ...infoData };
                }
            }
            
            this.renderUserInfo();

        } catch (error) {
            console.error('加载用户数据失败:', error);
            this.showMessage('加载用户信息失败', 'error');
            
            // 显示错误状态
            const usernameEl = document.getElementById('username');
            if (usernameEl) {
                usernameEl.textContent = '加载失败';
            }
        } finally {
            this.setLoadingState(false);
        }
    }

    /**
     * 加载用户设置
     */
    async loadUserSettings() {
        try {
            const response = await fetch('/api/user/settings');
            if (response.ok) {
                this.settings = await response.json();
                this.renderSettings();
            }
        } catch (error) {
            console.error('加载用户设置失败:', error);
            // 使用默认设置
            this.renderSettings();
        }
    }

    /**
     * 加载最近活动记录
     */
    async loadRecentActivities() {
        try {
            const response = await fetch('/api/user/activities');
            if (response.ok) {
                const activities = await response.json();
                this.renderActivities(activities);
            } else {
                this.renderActivities([]);
            }
        } catch (error) {
            console.error('加载活动记录失败:', error);
            this.renderActivities([]);
        }
    }

    /**
     * 渲染用户信息
     */
    renderUserInfo() {
        if (!this.userData) return;

        const roles = this.userData.roles || ['用户'];
        const primaryRole = this.getPrimaryRole(roles);

        // 使用数据绑定更新用户信息
        if (window.ComponentManager?.isInitialized) {
            window.ComponentManager.setDataBatch({
                'user.username': this.userData.username || '未知用户',
                'user.primaryRole': primaryRole,
                'user.createdAt': this.userData.created_at ? this.formatDateTime(this.userData.created_at) : '-',
                'user.lastLogin': this.userData.last_login ? this.formatDateTime(this.userData.last_login) : '首次登录',
                'user.currentTheme': this.getThemeDisplayName(this.userData.theme || 'default')
            });
        } else {
            // 降级到直接DOM操作
            this.renderUserInfoFallback();
        }

        // 更新用户角色样式
        const userRoleEl = document.getElementById('user-role');
        if (userRoleEl) {
            userRoleEl.className = `user-role-badge role-${primaryRole.toLowerCase().replace(/\s+/g, '-')}`;
        }

        console.log('用户信息渲染完成');
    }

    /**
     * 降级用户信息渲染
     */
    renderUserInfoFallback() {
        // 更新用户名
        const usernameEl = document.getElementById('username');
        if (usernameEl) {
            usernameEl.textContent = this.userData.username || '未知用户';
        }

        // 更新用户角色
        const userRoleEl = document.getElementById('user-role');
        if (userRoleEl) {
            const roles = this.userData.roles || ['用户'];
            const primaryRole = this.getPrimaryRole(roles);
            userRoleEl.textContent = primaryRole;
        }

        // 更新注册时间
        const createdAtEl = document.getElementById('created-at');
        if (createdAtEl && this.userData.created_at) {
            createdAtEl.textContent = this.formatDateTime(this.userData.created_at);
        }

        // 更新最后登录时间
        const loginTimeEl = document.getElementById('login-time');
        if (loginTimeEl) {
            if (this.userData.last_login) {
                loginTimeEl.textContent = this.formatDateTime(this.userData.last_login);
            } else {
                loginTimeEl.textContent = '首次登录';
            }
        }

        // 更新当前主题
        const currentThemeEl = document.getElementById('current-theme');
        if (currentThemeEl) {
            currentThemeEl.textContent = this.getThemeDisplayName(this.userData.theme || 'default');
        }
    }

    /**
     * 渲染设置
     */
    renderSettings() {
        // 渲染主题设置
        this.renderThemeSettings();

        // 渲染LLM配置
        this.renderLLMConfig();
    }

    /**
     * 渲染主题设置
     */
    renderThemeSettings() {
        const currentTheme = this.settings.theme || 'default';

        // 更新主题选项选中状态
        document.querySelectorAll('.theme-option').forEach(option => {
            const theme = option.getAttribute('data-theme');
            const radio = option.querySelector('input[type="radio"]');

            if (theme === currentTheme) {
                option.classList.add('selected');
                if (radio) radio.checked = true;
            } else {
                option.classList.remove('selected');
                if (radio) radio.checked = false;
            }
        });

        // 更新主题选择器
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            themeSelector.value = currentTheme;
        }
    }

    /**
     * 渲染LLM配置
     */
    renderLLMConfig() {
        const llmConfigTextarea = document.getElementById('llm-config');
        if (llmConfigTextarea) {
            const config = this.settings.llmConfig || {};
            llmConfigTextarea.value = JSON.stringify(config, null, 2);
        }
    }

    /**
     * 渲染活动记录
     */
    renderActivities(activities) {
        const activitiesContainer = document.getElementById('recent-activities');
        if (!activitiesContainer) return;

        if (!activities || activities.length === 0) {
            activitiesContainer.innerHTML = `
                <div class="activity-item empty">
                    <div class="activity-icon">📝</div>
                    <div class="activity-content">
                        <div class="activity-title">暂无活动记录</div>
                        <div class="activity-desc">开始使用系统后，您的操作记录将显示在这里</div>
                    </div>
                </div>
            `;
            return;
        }

        const activitiesHTML = activities.slice(0, 5).map(activity => `
            <div class="activity-item">
                <div class="activity-icon">${this.getActivityIcon(activity.type)}</div>
                <div class="activity-content">
                    <div class="activity-title">${this.escapeHtml(activity.title)}</div>
                    <div class="activity-desc">${this.escapeHtml(activity.description)}</div>
                    <div class="activity-time">${this.formatRelativeTime(activity.timestamp)}</div>
                </div>
            </div>
        `).join('');

        activitiesContainer.innerHTML = activitiesHTML;
    }

    /**
     * 初始化主题选择器
     */
    initializeThemeSelector() {
        // 从localStorage或用户数据中获取当前主题
        const currentTheme = localStorage.getItem('selectedTheme') ||
            this.userData?.theme ||
            'default';

        this.settings.theme = currentTheme;
        this.renderThemeSettings();
    }

    /**
     * 选择主题
     */
    selectTheme(themeOption) {
        // 移除所有选中状态
        document.querySelectorAll('.theme-option').forEach(option => {
            option.classList.remove('selected');
            const radio = option.querySelector('input[type="radio"]');
            if (radio) radio.checked = false;
        });

        // 设置当前选中状态
        themeOption.classList.add('selected');
        const radio = themeOption.querySelector('input[type="radio"]');
        if (radio) radio.checked = true;

        // 更新设置
        const theme = themeOption.getAttribute('data-theme');
        this.settings.theme = theme;

        // 添加视觉反馈
        this.addSelectionFeedback(themeOption);
    }

    /**
     * 添加选择反馈动画
     */
    addSelectionFeedback(element) {
        element.style.transform = 'scale(0.95)';
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 150);
    }

    /**
     * 保存主题设置
     */
    async saveThemeSettings() {
        try {
            this.setButtonLoading('save-theme-btn', true);

            const response = await fetch('/api/user/theme', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    theme: this.settings.theme
                })
            });

            if (!response.ok) {
                throw new Error('保存主题设置失败');
            }

            // 更新localStorage
            localStorage.setItem('selectedTheme', this.settings.theme);

            // 应用主题
            this.applyTheme(this.settings.theme);

            this.showMessage('主题设置保存成功', 'success');

        } catch (error) {
            console.error('保存主题设置失败:', error);
            this.showMessage('保存主题设置失败', 'error');
        } finally {
            this.setButtonLoading('save-theme-btn', false);
        }
    }

    /**
     * 应用主题
     */
    applyTheme(theme) {
        // 更新主题链接
        const themeLink = document.getElementById('theme-link');
        if (themeLink) {
            themeLink.href = `/static/${theme}/css/style.css`;
        }

        // 更新主题选择器
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            themeSelector.value = theme;
        }

        // 更新当前主题显示
        const currentThemeEl = document.getElementById('current-theme');
        if (currentThemeEl) {
            currentThemeEl.textContent = this.getThemeDisplayName(theme);
        }

        // 触发主题变更事件
        document.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme }
        }));
    }

    /**
     * 保存LLM配置
     */
    async saveLLMConfig() {
        try {
            this.setButtonLoading('save-llm-config-btn', true);

            const llmConfigTextarea = document.getElementById('llm-config');
            const configText = llmConfigTextarea.value.trim();

            let config = {};
            if (configText) {
                try {
                    config = JSON.parse(configText);
                } catch (parseError) {
                    throw new Error('LLM配置格式不正确，请检查JSON格式');
                }
            }

            const response = await fetch('/api/user/llm-config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });

            if (!response.ok) {
                throw new Error('保存LLM配置失败');
            }

            this.settings.llmConfig = config;
            this.showMessage('LLM配置保存成功', 'success');

        } catch (error) {
            console.error('保存LLM配置失败:', error);
            this.showMessage(error.message, 'error');
        } finally {
            this.setButtonLoading('save-llm-config-btn', false);
        }
    }

    /**
     * 重置LLM配置
     */
    resetLLMConfig() {
        if (confirm('确定要重置LLM配置吗？这将清空所有配置内容。')) {
            const llmConfigTextarea = document.getElementById('llm-config');
            if (llmConfigTextarea) {
                llmConfigTextarea.value = JSON.stringify({
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7,
                    "max_tokens": 2000
                }, null, 2);
            }
            this.showMessage('LLM配置已重置为默认值', 'info');
        }
    }

    /**
     * 处理登出
     */
    async handleLogout() {
        if (confirm('确定要登出吗？')) {
            try {
                const response = await fetch('/logout', {
                    method: 'POST'
                });

                if (response.ok) {
                    window.location.href = '/login';
                } else {
                    throw new Error('登出失败');
                }
            } catch (error) {
                console.error('登出失败:', error);
                this.showMessage('登出失败，请重试', 'error');
            }
        }
    }

    /**
     * 改变主题（实时预览）
     */
    changeTheme(theme) {
        this.settings.theme = theme;
        this.applyTheme(theme);
    }

    /**
     * 设置加载状态
     */
    setLoadingState(loading) {
        this.isLoading = loading;
        const loadingElements = document.querySelectorAll('.loading');

        loadingElements.forEach(el => {
            if (loading) {
                el.style.opacity = '0.6';
                el.style.pointerEvents = 'none';
            } else {
                el.style.opacity = '1';
                el.style.pointerEvents = 'auto';
            }
        });
    }

    /**
     * 设置按钮加载状态
     */
    setButtonLoading(buttonId, loading) {
        const button = document.getElementById(buttonId);
        if (!button) return;

        if (loading) {
            button.disabled = true;
            button.dataset.originalText = button.textContent;
            button.innerHTML = '<span class="loading-spinner"></span> 保存中...';
        } else {
            button.disabled = false;
            button.textContent = button.dataset.originalText || '保存';
        }
    }

    /**
     * 显示消息
     */
    showMessage(message, type = 'info') {
        // 使用统一组件管理器显示消息
        if (window.ComponentManager && typeof window.ComponentManager.getComponent === 'function') {
            const messageManager = window.ComponentManager.getComponent('message');
            if (messageManager) {
                switch (type) {
                    case 'success':
                        messageManager.success(message);
                        break;
                    case 'error':
                        messageManager.error(message);
                        break;
                    case 'warning':
                        messageManager.warning(message);
                        break;
                    default:
                        messageManager.info(message);
                }
                return;
            }
        }

        // 降级到简单的alert
        alert(message);
    }

    // === 工具方法 ===

    /**
     * 获取主要角色
     */
    getPrimaryRole(roles) {
        const roleHierarchy = ['super_admin', 'admin', 'editor', 'user'];

        for (const role of roleHierarchy) {
            if (roles.includes(role)) {
                return this.getRoleDisplayName(role);
            }
        }

        return roles[0] || '用户';
    }

    /**
     * 获取角色显示名称
     */
    getRoleDisplayName(role) {
        const roleNames = {
            'super_admin': '超级管理员',
            'admin': '管理员',
            'editor': '编辑者',
            'user': '用户'
        };
        return roleNames[role] || role;
    }

    /**
     * 获取主题显示名称
     */
    getThemeDisplayName(theme) {
        const themeNames = {
            'default': '默认主题',
            'wooden': '木质主题'
        };
        return themeNames[theme] || theme;
    }

    /**
     * 获取活动图标
     */
    getActivityIcon(type) {
        const icons = {
            'login': '🔐',
            'file_edit': '📝',
            'file_create': '📄',
            'file_delete': '🗑️',
            'theme_change': '🎨',
            'config_update': '⚙️',
            'build': '🔨'
        };
        return icons[type] || '📋';
    }

    /**
     * 格式化日期时间
     */
    formatDateTime(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return '无效日期';
        }
    }

    /**
     * 格式化相对时间
     */
    formatRelativeTime(dateString) {
        try {
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMins / 60);
            const diffDays = Math.floor(diffHours / 24);

            if (diffMins < 1) return '刚刚';
            if (diffMins < 60) return `${diffMins}分钟前`;
            if (diffHours < 24) return `${diffHours}小时前`;
            if (diffDays < 7) return `${diffDays}天前`;

            return this.formatDateTime(dateString);
        } catch (error) {
            return '未知时间';
        }
    }

    /**
     * HTML转义
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 全局实例
window.myAccountManager = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.myAccountManager = new MyAccountManager();
});

// 兼容性函数
function handleLogout() {
    if (window.myAccountManager) {
        window.myAccountManager.handleLogout();
    }
}