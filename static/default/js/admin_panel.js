// 管理员面板页面 - Default 主题
// 使用统一的主题加载器，避免代码重复

// 全局变量用于存储权限信息
window.userPermissions = null;
window.permissionFlags = null;
window.currentUser = null;

// 管理数据加载器类 - 增强版本
class AdminDataLoader {
    constructor() {
        this.retryCount = new Map(); // 为每个方法单独计数
        this.maxRetries = 3;
        this.retryDelay = 2000; // 2秒
        this.loadingStates = new Map(); // 跟踪加载状态
        this.cache = new Map(); // 数据缓存
        this.cacheTimeout = 5 * 60 * 1000; // 5分钟缓存
        this.abortControllers = new Map(); // 请求控制器
    }
    
    // 通用数据加载方法
    async loadData(endpoint, methodName, renderMethod, containerId = null) {
        // 取消之前的请求
        if (this.abortControllers.has(methodName)) {
            this.abortControllers.get(methodName).abort();
        }
        
        const controller = new AbortController();
        this.abortControllers.set(methodName, controller);
        
        // 检查缓存
        const cacheKey = `${endpoint}_${methodName}`;
        const cached = this.cache.get(cacheKey);
        if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
            console.log(`使用缓存数据: ${methodName}`);
            this[renderMethod](cached.data);
            return cached.data;
        }
        
        // 设置加载状态
        this.setLoadingState(methodName, true);
        if (containerId) {
            this.showLoadingIndicator(containerId, `正在加载${this.getDataTypeName(methodName)}...`);
        }
        
        try {
            const response = await fetch(endpoint, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                signal: controller.signal
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            const items = data[this.getDataKey(methodName)] || [];
            
            // 缓存数据
            this.cache.set(cacheKey, {
                data: items,
                timestamp: Date.now()
            });
            
            // 渲染数据
            this[renderMethod](items);
            
            // 重置重试计数
            this.retryCount.set(methodName, 0);
            
            // 清除加载状态
            this.setLoadingState(methodName, false);
            
            console.log(`${methodName} 加载成功:`, items.length, '项');
            return items;
            
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log(`${methodName} 请求被取消`);
                return;
            }
            
            console.error(`${methodName} 加载失败:`, error);
            this.handleLoadError(error, methodName, () => this.loadData(endpoint, methodName, renderMethod, containerId));
            throw error;
        } finally {
            this.setLoadingState(methodName, false);
            this.abortControllers.delete(methodName);
        }
    }
    
    async loadUserData() {
        return this.loadData('/api/admin/users', 'loadUserData', 'renderUserTable', 'admin-user-list');
    }
    
    async loadRoleData() {
        return this.loadData('/api/admin/roles', 'loadRoleData', 'renderRoleTable', 'admin-role-list');
    }
    
    async loadPermissionData() {
        return this.loadData('/api/admin/permissions', 'loadPermissionData', 'renderPermissionTable', 'admin-permission-list');
    }
    
    // 批量加载所有数据
    async loadAllData() {
        const loadPromises = [
            this.loadUserData().catch(e => ({ error: e, type: 'users' })),
            this.loadRoleData().catch(e => ({ error: e, type: 'roles' })),
            this.loadPermissionData().catch(e => ({ error: e, type: 'permissions' }))
        ];
        
        const results = await Promise.allSettled(loadPromises);
        
        // 统计加载结果
        const successful = results.filter(r => r.status === 'fulfilled' && !r.value.error).length;
        const failed = results.length - successful;
        
        if (failed > 0) {
            this.showErrorMessage(`部分数据加载失败 (${failed}/${results.length})，请检查网络连接或刷新页面重试`);
        }
        
        return results;
    }
    
    handleLoadError(error, methodName, retryCallback) {
        const currentRetries = this.retryCount.get(methodName) || 0;
        
        if (currentRetries < this.maxRetries) {
            this.retryCount.set(methodName, currentRetries + 1);
            const delay = this.retryDelay * Math.pow(2, currentRetries); // 指数退避
            
            console.log(`${methodName} 重试第 ${currentRetries + 1} 次，${delay}ms 后重试...`);
            
            // 显示重试提示
            this.showRetryMessage(methodName, currentRetries + 1, delay);
            
            setTimeout(() => {
                retryCallback();
            }, delay);
        } else {
            this.retryCount.set(methodName, 0); // 重置计数
            const errorMsg = this.getDetailedErrorMessage(error, methodName);
            this.showErrorMessage(errorMsg);
        }
    }
    
    getDetailedErrorMessage(error, methodName) {
        const dataType = this.getDataTypeName(methodName);
        
        if (error.message.includes('401')) {
            return `${dataType}加载失败：请重新登录`;
        } else if (error.message.includes('403')) {
            return `${dataType}加载失败：权限不足`;
        } else if (error.message.includes('404')) {
            return `${dataType}加载失败：接口不存在`;
        } else if (error.message.includes('500')) {
            return `${dataType}加载失败：服务器内部错误`;
        } else if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
            return `${dataType}加载失败：网络连接错误，请检查网络连接`;
        } else {
            return `${dataType}加载失败：${error.message}`;
        }
    }
    
    showRetryMessage(methodName, retryCount, delay) {
        const dataType = this.getDataTypeName(methodName);
        const message = `${dataType}加载失败，正在重试 (${retryCount}/${this.maxRetries})...`;
        
        // 创建或更新重试提示
        let retryDiv = document.getElementById(`retry-message-${methodName}`);
        if (!retryDiv) {
            retryDiv = document.createElement('div');
            retryDiv.id = `retry-message-${methodName}`;
            retryDiv.className = 'retry-message alert alert-warning';
            retryDiv.style.cssText = `
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                color: #856404;
                padding: 8px 12px;
                border-radius: 4px;
                margin: 5px 0;
                font-size: 14px;
            `;
            
            const container = this.findContainer();
            if (container) {
                container.insertBefore(retryDiv, container.firstChild);
            }
        }
        
        retryDiv.innerHTML = `
            <span>${message}</span>
            <div class="retry-progress" style="width: 100%; height: 2px; background: #ddd; margin-top: 5px; border-radius: 1px;">
                <div class="retry-progress-bar" style="height: 100%; background: #ffc107; width: 0%; transition: width ${delay}ms linear; border-radius: 1px;"></div>
            </div>
        `;
        
        // 启动进度条动画
        setTimeout(() => {
            const progressBar = retryDiv.querySelector('.retry-progress-bar');
            if (progressBar) {
                progressBar.style.width = '100%';
            }
        }, 100);
        
        // 延迟后移除提示
        setTimeout(() => {
            if (retryDiv && retryDiv.parentNode) {
                retryDiv.remove();
            }
        }, delay + 500);
    }
    
    showErrorMessage(message) {
        // 移除所有重试消息
        document.querySelectorAll('[id^="retry-message-"]').forEach(el => el.remove());
        
        const container = this.findContainer();
        if (!container) {
            alert(message); // 备用方案
            return;
        }
        
        // 移除之前的错误消息
        const existingError = container.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message alert alert-danger';
        errorDiv.style.cssText = `
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 12px;
            border-radius: 4px;
            margin: 10px 0;
            position: relative;
            animation: slideIn 0.3s ease-out;
        `;
        
        errorDiv.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <strong>⚠️ 错误:</strong> ${message}
                </div>
                <div>
                    <button onclick="window.adminDataLoader.loadAllData()" 
                            style="background: #dc3545; color: white; border: none; padding: 4px 8px; border-radius: 3px; margin-right: 8px; cursor: pointer;">
                        重新加载
                    </button>
                    <button onclick="this.closest('.error-message').remove()" 
                            style="background: none; border: none; font-size: 18px; cursor: pointer; color: #721c24;">
                        ×
                    </button>
                </div>
            </div>
        `;
        
        container.insertBefore(errorDiv, container.firstChild);
        
        // 5秒后自动隐藏
        setTimeout(() => {
            if (errorDiv && errorDiv.parentNode) {
                errorDiv.style.opacity = '0';
                errorDiv.style.transition = 'opacity 0.3s ease-out';
                setTimeout(() => errorDiv.remove(), 300);
            }
        }, 5000);
    }
    
    showLoadingIndicator(containerId, message) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading-indicator';
        loadingDiv.style.cssText = `
            text-align: center;
            padding: 20px;
            color: #666;
            font-style: italic;
        `;
        loadingDiv.innerHTML = `
            <div class="loading-spinner" style="display: inline-block; margin-right: 8px;">⏳</div>
            ${message}
        `;
        
        container.innerHTML = '';
        container.appendChild(loadingDiv);
    }
    
    findContainer() {
        const containers = [
            '.admin-content',
            '.admin-container',
            'main',
            'body'
        ];
        
        for (const selector of containers) {
            const container = document.querySelector(selector);
            if (container) return container;
        }
        return null;
    }
    
    setLoadingState(methodName, isLoading) {
        this.loadingStates.set(methodName, isLoading);
    }
    
    isLoading(methodName) {
        return this.loadingStates.get(methodName) || false;
    }
    
    getDataTypeName(methodName) {
        const typeMap = {
            'loadUserData': '用户数据',
            'loadRoleData': '角色数据',
            'loadPermissionData': '权限数据'
        };
        return typeMap[methodName] || '数据';
    }
    
    getDataKey(methodName) {
        const keyMap = {
            'loadUserData': 'users',
            'loadRoleData': 'roles',
            'loadPermissionData': 'permissions'
        };
        return keyMap[methodName] || 'data';
    }
    
    renderUserTable(users) {
        const tbody = document.getElementById('admin-user-list');
        if (!tbody) return;
        
        if (users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">暂无用户数据</td></tr>';
            return;
        }
        
        tbody.innerHTML = users.map(user => `
            <tr class="${user.is_default ? 'data-row-default' : ''}">
                <td>${this.escapeHtml(user.username || '')}</td>
                <td>${this.escapeHtml(user.user_type || 'user')}</td>
                <td>${Array.isArray(user.roles) ? user.roles.join(', ') : ''}</td>
                <td><span class="status-badge ${user.is_active ? 'active' : 'inactive'}">${user.is_active ? '活跃' : '非活跃'}</span></td>
                <td>${user.last_login || '从未登录'}</td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="editUser('${user.id}')">编辑</button>
                    ${!user.is_default ? `<button class="btn btn-sm btn-danger" onclick="deleteUser('${user.id}')">删除</button>` : ''}
                </td>
            </tr>
        `).join('');
        
        // 存储数据供其他功能使用
        window.adminUsers = users;
    }
    
    renderRoleTable(roles) {
        const tbody = document.getElementById('admin-role-list');
        if (!tbody) {
            console.warn('角色表格容器未找到');
            return;
        }
        
        if (roles.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">暂无角色数据</td></tr>';
            return;
        }
        
        tbody.innerHTML = roles.map(role => `
            <tr class="${role.is_default ? 'data-row-default' : ''}">
                <td>
                    ${this.escapeHtml(role.name || '')}
                    ${role.is_default ? '<span class="default-tag">默认</span>' : ''}
                </td>
                <td>${this.escapeHtml(role.description || '')}</td>
                <td>${role.permissions ? role.permissions.length : 0}</td>
                <td>${role.user_count || 0}</td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="editRole('${role.id}')">编辑</button>
                    ${!role.is_default ? `<button class="btn btn-sm btn-danger" onclick="deleteRole('${role.id}')">删除</button>` : ''}
                </td>
            </tr>
        `).join('');
        
        // 存储数据供其他功能使用
        window.adminRoles = roles;
        console.log('角色表格渲染完成:', roles.length, '个角色');
    }
    
    renderPermissionTable(permissions) {
        const tbody = document.getElementById('admin-permission-list');
        if (!tbody) {
            console.warn('权限表格容器未找到');
            return;
        }
        
        if (permissions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无权限数据</td></tr>';
            return;
        }
        
        tbody.innerHTML = permissions.map(permission => `
            <tr class="${permission.is_default ? 'data-row-default' : ''}">
                <td>
                    ${this.escapeHtml(permission.name || '')}
                    ${permission.is_default ? '<span class="default-tag">默认</span>' : ''}
                </td>
                <td>${this.escapeHtml(permission.description || '')}</td>
                <td>${this.getPermissionGroup(permission.name)}</td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="editPermission('${permission.id}')">编辑</button>
                    ${!permission.is_default ? `<button class="btn btn-sm btn-danger" onclick="deletePermission('${permission.id}')">删除</button>` : ''}
                </td>
            </tr>
        `).join('');
        
        // 存储数据供其他功能使用
        window.adminPermissions = permissions;
        console.log('权限表格渲染完成:', permissions.length, '个权限');
    }
    
    getPermissionGroup(permissionName) {
        const groups = {
            'user.': '用户管理',
            'role.': '角色管理',
            'permission.': '权限管理',
            'system.': '系统管理',
            'file.': '文件管理',
            'build.': '构建权限'
        };

        for (const [prefix, group] of Object.entries(groups)) {
            if (permissionName.startsWith(prefix)) {
                return group;
            }
        }
        return '其他权限';
    }
    
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // 清除缓存
    clearCache() {
        this.cache.clear();
        console.log('数据缓存已清除');
    }
    
    // 取消所有请求
    cancelAllRequests() {
        this.abortControllers.forEach(controller => controller.abort());
        this.abortControllers.clear();
        console.log('所有请求已取消');
    }
}

// 创建全局数据加载器实例
window.adminDataLoader = new AdminDataLoader();

// 辅助函数：安全更新元素内容
function updateElement(id, content) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = content;
    }
}

// 辅助函数：显示加载状态
function showLoadingState(containerId, message = '正在加载...') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `<div class="loading-state">${message}</div>`;
    }
}

// 页面加载时初始化 - 增强版本
document.addEventListener('DOMContentLoaded', async function() {
    try {
        console.log('开始初始化管理面板...');
        
        // 使用主题加载器初始化管理员面板页面
        await initThemeLoader('admin_panel');
        
        // 初始化权限信息
        initPermissions();
        
        // 初始化数据观察器
        if (typeof initializeDataBinding === 'function') {
            initializeDataBinding();
        }
        
        // 初始化用户权限管理功能
        await initUserManagement();
        
        // 初始化统计信息（使用增强的数据加载器）
        await initStats();
        
        // 初始化角色权限分配器
        await initRoleAssignment();
        
        // 初始化权限分组预览
        await initPermissionGroups();
        
        // 调用admin-common.js中的统一事件绑定函数
        if (typeof bindAdminPanelEvents === 'function') {
            bindAdminPanelEvents();
        } else {
            console.warn('bindAdminPanelEvents function not found in admin-common.js');
            // 如果没有admin-common.js，使用本地的事件绑定
            bindLocalAdminPanelEvents();
        }
        
        // 设置错误处理
        window.addEventListener('unhandledrejection', function(event) {
            console.error('未处理的Promise拒绝:', event.reason);
            window.adminDataLoader.showErrorMessage('发生未知错误，请刷新页面重试');
        });
        
        // 设置网络状态监听
        window.addEventListener('online', function() {
            showMessage('网络连接已恢复', 'success');
            // 重新加载数据
            setTimeout(() => {
                window.adminDataLoader.loadAllData();
            }, 1000);
        });
        
        window.addEventListener('offline', function() {
            showMessage('网络连接已断开', 'warning');
        });
        
        console.log('管理面板初始化完成');
        
    } catch (error) {
        console.error('管理面板初始化失败:', error);
        
        // 显示详细的错误信息
        const errorMessage = error.message || '未知错误';
        window.adminDataLoader.showErrorMessage(`页面初始化失败：${errorMessage}。请刷新页面重试。`);
        
        // 尝试基本功能初始化
        try {
            console.log('尝试基本功能初始化...');
            initPermissions();
            bindLocalAdminPanelEvents();
        } catch (fallbackError) {
            console.error('基本功能初始化也失败:', fallbackError);
        }
    }
});

// 本地事件绑定函数
function bindLocalAdminPanelEvents() {
    console.log('绑定本地管理面板事件...');
    
    // 绑定基本的按钮事件
    bindUserManagementButtons();
    bindChapterManagementButtons();
    bindBuildButtons();
    bindSystemManagementButtons();
    bindEpubConversionButtons();
    bindBackupManagementButtons();
    
    console.log('本地管理面板事件绑定完成');
}

// 初始化权限信息函数
function initPermissions() {
    // 从JSON脚本标签中读取权限数据
    const userPermissionsElement = document.getElementById('user-permissions-data');
    const permissionFlagsElement = document.getElementById('permission-flags-data');
    const usernameElement = document.getElementById('username-data');
    
    if (userPermissionsElement && permissionFlagsElement) {
        try {
            window.userPermissions = JSON.parse(userPermissionsElement.textContent);
            window.permissionFlags = JSON.parse(permissionFlagsElement.textContent);
            window.currentUser = usernameElement ? JSON.parse(usernameElement.textContent) : null;
        } catch (error) {
            console.error('Error parsing permission data:', error);
        }
    }
    
    // 尝试从页面元素中获取用户信息
    const usernameDisplay = document.getElementById('user-panel-username');
    const createdTimeDisplay = document.getElementById('user-panel-created-at');
    const loginTimeDisplay = document.getElementById('user-panel-login-time');
    const themeDisplay = document.getElementById('user-panel-current-theme');
    const roleDisplay = document.getElementById('user-panel-user-role');
    
    // 如果页面中有这些元素但没有内容，显示提示信息
    if (usernameDisplay && !usernameDisplay.textContent.trim()) {
        usernameDisplay.textContent = '未登录';
    }
    
    if (createdTimeDisplay && !createdTimeDisplay.textContent.trim()) {
        createdTimeDisplay.textContent = '-';
    }
    
    if (loginTimeDisplay && !loginTimeDisplay.textContent.trim()) {
        loginTimeDisplay.textContent = '从未登录';
    }
    
    if (themeDisplay && !themeDisplay.textContent.trim()) {
        themeDisplay.textContent = '-';
    }
    
    if (roleDisplay && !roleDisplay.textContent.trim()) {
        roleDisplay.textContent = '普通用户';
    }
}

// 初始化统计信息 - 增强版本
async function initStats() {
    try {
        // 使用增强的数据加载器
        const results = await window.adminDataLoader.loadAllData();
        
        let users = [], roles = [], permissions = [];
        let successCount = 0;
        
        // 处理加载结果
        results.forEach((result, index) => {
            if (result.status === 'fulfilled' && !result.value.error) {
                successCount++;
                switch (index) {
                    case 0: // users
                        users = result.value || [];
                        break;
                    case 1: // roles
                        roles = result.value || [];
                        break;
                    case 2: // permissions
                        permissions = result.value || [];
                        break;
                }
            } else {
                const errorType = ['用户', '角色', '权限'][index];
                console.warn(`${errorType}数据加载失败:`, result.reason || result.value?.error);
            }
        });
        
        // 计算统计信息
        const stats = {
            totalUsers: users.length,
            totalRoles: roles.length,
            totalPermissions: permissions.length,
            activeUsers: users.filter(u => u.is_active).length,
            defaultUsers: users.filter(u => u.is_default).length,
            defaultRoles: roles.filter(r => r.is_default).length,
            defaultPermissions: permissions.filter(p => p.is_default).length
        };
        
        stats.defaultItems = stats.defaultUsers + stats.defaultRoles + stats.defaultPermissions;
        
        // 更新统计显示
        updateElement('stats-total-users', stats.totalUsers);
        updateElement('stats-total-roles', stats.totalRoles);
        updateElement('stats-total-permissions', stats.totalPermissions);
        updateElement('stats-default-items', stats.defaultItems);
        updateElement('stats-active-users', stats.activeUsers);
        
        // 更新数据观察器
        if (window.adminDataObserver) {
            window.adminDataObserver.updateData('users', users);
            window.adminDataObserver.updateData('roles', roles);
            window.adminDataObserver.updateData('permissions', permissions);
            window.adminDataObserver.updateData('stats', stats);
        }
        
        // 显示加载状态
        if (successCount === results.length) {
            console.log('所有统计数据加载成功');
        } else {
            console.warn(`部分数据加载失败 (${successCount}/${results.length})`);
        }
        
        return stats;
        
    } catch (error) {
        console.error('统计信息初始化失败:', error);
        
        // 设置默认值
        const defaultStats = {
            totalUsers: 0,
            totalRoles: 0,
            totalPermissions: 0,
            defaultItems: 0,
            activeUsers: 0
        };
        
        Object.entries(defaultStats).forEach(([key, value]) => {
            updateElement(`stats-${key.replace(/([A-Z])/g, '-$1').toLowerCase()}`, value);
        });
        
        // 显示错误信息
        window.adminDataLoader.showErrorMessage('统计数据初始化失败，请刷新页面重试');
        
        return defaultStats;
    }
}

// 初始化管理面板所有按钮事件绑定
function bindAdminPanelEvents() {
    console.log('Binding admin panel events...');
    
    // 绑定章节管理按钮
    bindChapterManagementButtons();
    
    // 绑定图书生成按钮
    bindBuildButtons();
    
    // 绑定系统管理按钮
    bindSystemManagementButtons();
    
    // 绑定EPUB转换按钮
    bindEpubConversionButtons();
    
    // 绑定备份管理按钮
    bindBackupManagementButtons();
    
    // 绑定用户管理按钮
    bindUserManagementButtons();
    
    console.log('Admin panel events bound successfully');
}

// 绑定章节管理按钮
function bindChapterManagementButtons() {
    const saveChaptersBtn = document.getElementById('save-chapters-btn');
    const resetChaptersBtn = document.getElementById('reset-chapters-btn');
    
    if (saveChaptersBtn) {
        saveChaptersBtn.addEventListener('click', function() {
            if (typeof saveChapterOrder === 'function') {
                saveChapterOrder();
            } else {
                console.warn('saveChapterOrder function not found');
            }
        });
    }
    
    if (resetChaptersBtn) {
        resetChaptersBtn.addEventListener('click', function() {
            if (typeof resetChapterOrder === 'function') {
                resetChapterOrder();
            } else {
                console.warn('resetChapterOrder function not found');
            }
        });
    }
}

// 绑定图书生成按钮
function bindBuildButtons() {
    const buildAllBtn = document.getElementById('build-all-btn');
    const buildEpubBtn = document.getElementById('build-epub-btn');
    const buildPdfBtn = document.getElementById('build-pdf-btn');
    const buildPdfWkhtmltopdfBtn = document.getElementById('build-pdf-wkhtmltopdf-btn');
    
    if (buildAllBtn) {
        buildAllBtn.addEventListener('click', function() {
            if (typeof buildBook === 'function') {
                buildBook('build');
            } else {
                console.warn('buildBook function not found');
            }
        });
    }
    
    if (buildEpubBtn) {
        buildEpubBtn.addEventListener('click', function() {
            if (typeof buildBook === 'function') {
                buildBook('epub');
            } else {
                console.warn('buildBook function not found');
            }
        });
    }
    
    if (buildPdfBtn) {
        buildPdfBtn.addEventListener('click', function() {
            if (typeof buildBook === 'function') {
                buildBook('pdf');
            } else {
                console.warn('buildBook function not found');
            }
        });
    }
    
    if (buildPdfWkhtmltopdfBtn) {
        buildPdfWkhtmltopdfBtn.addEventListener('click', function() {
            if (typeof buildBook === 'function') {
                buildBook('pdf-wkhtmltopdf');
            } else {
                console.warn('buildBook function not found');
            }
        });
    }
}

// 绑定系统管理按钮
function bindSystemManagementButtons() {
    const uploadSrcBtn = document.getElementById('upload-src-btn');
    const downloadSrcBtn = document.getElementById('download-src-btn');
    const resetSrcBtn = document.getElementById('reset-src-btn');
    
    if (uploadSrcBtn) {
        uploadSrcBtn.addEventListener('click', function() {
            const fileInput = document.getElementById('src-upload');
            if (fileInput && fileInput.files.length > 0) {
                if (typeof uploadSrcDirectory === 'function') {
                    uploadSrcDirectory(fileInput.files[0]);
                } else {
                    console.warn('uploadSrcDirectory function not found');
                }
            } else {
                window.ComponentManager.getComponent('message').warning('请选择要上传的zip文件');
            }
        });
    }
    
    if (downloadSrcBtn) {
        downloadSrcBtn.addEventListener('click', function() {
            if (typeof downloadSrc === 'function') {
                downloadSrc();
            } else {
                console.warn('downloadSrc function not found');
            }
        });
    }
    
    if (resetSrcBtn) {
        resetSrcBtn.addEventListener('click', function() {
            if (confirm('确定要重置Src目录吗？这将删除所有现有内容。')) {
                if (typeof resetSrcDirectory === 'function') {
                    resetSrcDirectory();
                } else {
                    console.warn('resetSrcDirectory function not found');
                }
            }
        });
    }
}

// 绑定EPUB转换按钮
function bindEpubConversionButtons() {
    const convertEpubBtn = document.getElementById('convert-epub-btn');
    const downloadConvertedBtn = document.getElementById('download-converted-btn');
    
    if (convertEpubBtn) {
        convertEpubBtn.addEventListener('click', function() {
            const fileInput = document.getElementById('epub-upload');
            if (fileInput && fileInput.files.length > 0) {
                if (typeof convertEpubToMarkdown === 'function') {
                    convertEpubToMarkdown(fileInput.files[0]);
                } else {
                    console.warn('convertEpubToMarkdown function not found');
                }
            } else {
                window.ComponentManager.getComponent('message').warning('请选择要转换的EPUB文件');
            }
        });
    }
    
    if (downloadConvertedBtn) {
        downloadConvertedBtn.addEventListener('click', function() {
            if (typeof downloadConvertedFiles === 'function') {
                downloadConvertedFiles();
            } else {
                console.warn('downloadConvertedFiles function not found');
            }
        });
    }
}

// 绑定备份管理按钮
function bindBackupManagementButtons() {
    const manualBackupBtn = document.getElementById('manual-backup-btn');
    
    if (manualBackupBtn) {
        manualBackupBtn.addEventListener('click', function() {
            if (typeof createManualBackup === 'function') {
                createManualBackup();
            } else {
                console.warn('createManualBackup function not found');
            }
        });
    }
}

// 绑定用户管理按钮
function bindUserManagementButtons() {
    // 显示权限管理区域按钮
    const showRolePermissionBtn = document.getElementById('show-role-permission-btn');
    if (showRolePermissionBtn) {
        showRolePermissionBtn.addEventListener('click', function() {
            toggleSection('role-permission');
        });
    }
    
    // 快速创建用户按钮
    const quickCreateUserBtn = document.getElementById('quick-create-user-btn');
    if (quickCreateUserBtn) {
        quickCreateUserBtn.addEventListener('click', function() {
            showQuickCreateUserModal();
        });
    }
    
    // 快速分配角色按钮
    const quickAssignRoleBtn = document.getElementById('quick-assign-role-btn');
    if (quickAssignRoleBtn) {
        quickAssignRoleBtn.addEventListener('click', function() {
            showQuickAssignRoleModal();
        });
    }
    
    // 系统初始化按钮
    const systemInitBtn = document.getElementById('system-init-btn');
    if (systemInitBtn) {
        systemInitBtn.addEventListener('click', function() {
            initializeSystemDefaults();
        });
    }
    
    // 刷新用户列表按钮
    const refreshUsersBtn = document.getElementById('refresh-admin-users-btn');
    if (refreshUsersBtn) {
        refreshUsersBtn.addEventListener('click', function() {
            loadAdminUserList();
        });
    }
    
    // 切换用户列表显示按钮
    const toggleUserListBtn = document.getElementById('toggle-user-list-btn');
    if (toggleUserListBtn) {
        toggleUserListBtn.addEventListener('click', function() {
            toggleAdminUserList();
        });
    }
    
    // 用户搜索
    const userSearchInput = document.getElementById('admin-user-search');
    if (userSearchInput) {
        userSearchInput.addEventListener('input', debounce(function() {
            filterAdminUserList(this.value);
        }, 300));
    }
}

// 初始化用户权限管理功能
async function initUserManagement() {
    try {
        // 用户管理相关的初始化逻辑
        bindUserManagementButtons();
        
        // 初始化数据绑定
        await initializeDataBinding();
        
        // 设置自动刷新
        setupAutoRefresh();
        
        console.log('用户管理功能初始化完成');
        
    } catch (error) {
        console.error('用户管理初始化失败:', error);
        window.adminDataLoader.showErrorMessage('用户管理功能初始化失败');
    }
}

// 初始化数据绑定
async function initializeDataBinding() {
    // 绑定用户列表切换按钮
    const toggleBtn = document.getElementById('toggle-user-list-btn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', async function() {
            const container = document.getElementById('admin-user-list-container');
            if (container) {
                if (container.style.display === 'none') {
                    container.style.display = 'block';
                    showLoadingState('admin-user-list', '正在加载用户列表...');
                    await window.adminDataLoader.loadUserData();
                } else {
                    container.style.display = 'none';
                }
            }
        });
    }
    
    // 绑定刷新按钮
    const refreshBtn = document.getElementById('refresh-admin-users-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async function() {
            showLoadingState('admin-user-list', '正在刷新用户列表...');
            await window.adminDataLoader.loadUserData();
        });
    }
}

// 设置自动刷新
function setupAutoRefresh() {
    // 每5分钟自动刷新统计数据
    setInterval(async () => {
        try {
            await initStats();
        } catch (error) {
            console.warn('自动刷新统计数据失败:', error);
        }
    }, 5 * 60 * 1000); // 5分钟
}

// 初始化角色权限分配器 - 增强版本
async function initRoleAssignment() {
    try {
        // 使用增强的数据加载器
        const [users, roles] = await Promise.all([
            window.adminDataLoader.loadUserData().catch(e => {
                console.warn('用户数据加载失败:', e);
                return [];
            }),
            window.adminDataLoader.loadRoleData().catch(e => {
                console.warn('角色数据加载失败:', e);
                return [];
            })
        ]);
        
        // 填充用户选择器
        const userSelect = document.getElementById('admin-user-select');
        if (userSelect) {
            updateUserSelector(userSelect, users);
            
            // 绑定用户选择事件
            userSelect.addEventListener('change', function() {
                loadUserRoles(this.value, roles);
            });
        }
        
        // 填充角色选择器（如果存在）
        const roleSelectors = document.querySelectorAll('.role-selector, #admin-role-select');
        roleSelectors.forEach(selector => {
            updateRoleSelector(selector, roles);
        });
        
        // 绑定保存用户角色按钮
        const saveRolesBtn = document.getElementById('admin-save-user-roles-btn');
        if (saveRolesBtn) {
            saveRolesBtn.addEventListener('click', function() {
                saveUserRoles();
            });
        }
        
        // 绑定批量操作按钮
        bindBatchOperationButtons();
        
        console.log('角色权限分配器初始化完成');
        
    } catch (error) {
        console.error('角色权限分配器初始化失败:', error);
        window.adminDataLoader.showErrorMessage('角色权限分配功能初始化失败');
    }
}

// 更新用户选择器
function updateUserSelector(selector, users) {
    if (!selector) return;
    
    const currentValue = selector.value;
    selector.innerHTML = '<option value="">请选择用户</option>';
    
    users.forEach(user => {
        const option = document.createElement('option');
        option.value = user.id;
        option.textContent = `${user.username || '未知用户'}${user.is_default ? ' (默认)' : ''}`;
        
        if (user.is_default) {
            option.style.color = '#f59e0b';
            option.style.fontWeight = 'bold';
        }
        
        selector.appendChild(option);
    });
    
    // 恢复之前的选择
    if (currentValue) {
        selector.value = currentValue;
    }
}

// 更新角色选择器
function updateRoleSelector(selector, roles) {
    if (!selector) return;
    
    const currentValue = selector.value;
    selector.innerHTML = '<option value="">请选择角色</option>';
    
    roles.forEach(role => {
        const option = document.createElement('option');
        option.value = role.id;
        option.textContent = `${role.name}${role.is_default ? ' (默认)' : ''}`;
        
        if (role.is_default) {
            option.style.color = '#f59e0b';
            option.style.fontWeight = 'bold';
        }
        
        selector.appendChild(option);
    });
    
    // 恢复之前的选择
    if (currentValue) {
        selector.value = currentValue;
    }
}

// 绑定批量操作按钮
function bindBatchOperationButtons() {
    // 批量分配角色按钮
    const batchAssignBtn = document.getElementById('batch-assign-roles-btn');
    if (batchAssignBtn) {
        batchAssignBtn.addEventListener('click', function() {
            showBatchAssignModal();
        });
    }
    
    // 批量移除角色按钮
    const batchRemoveBtn = document.getElementById('batch-remove-roles-btn');
    if (batchRemoveBtn) {
        batchRemoveBtn.addEventListener('click', function() {
            showBatchRemoveModal();
        });
    }
}

// 初始化权限分组预览
async function initPermissionGroups() {
    try {
        const response = await fetch('/api/admin/assignable-permissions');
        const data = await response.json();
        const groups = data.groups || {};
        
        const container = document.getElementById('admin-permission-groups');
        if (container) {
            let html = '';
            
            Object.entries(groups).forEach(([groupName, permissions]) => {
                if (permissions.length > 0) {
                    html += `<div class="permission-group">`;
                    html += `<div class="permission-group-header">`;
                    html += `<span class="permission-group-title">${groupName}</span>`;
                    html += `<span class="permission-group-count">${permissions.length} 项权限</span>`;
                    html += `</div>`;
                    
                    html += `<div class="permission-items">`;
                    permissions.forEach(permission => {
                        html += `<div class="permission-item ${permission.is_default ? 'default' : ''}">`;
                        html += `<div class="permission-item-info">`;
                        html += `<div class="permission-item-name">`;
                        html += permission.name;
                        if (permission.is_default) {
                            html += ` <span class="default-tag">默认</span>`;
                        }
                        html += `</div>`;
                        html += `<div class="permission-item-desc">${permission.description}</div>`;
                        html += `</div>`;
                        html += `</div>`;
                    });
                    html += `</div>`;
                    html += `</div>`;
                }
            });
            
            container.innerHTML = html || '<p>暂无权限数据</p>';
        }
        
    } catch (error) {
        console.error('Error loading permission groups:', error);
        const container = document.getElementById('admin-permission-groups');
        if (container) {
            container.innerHTML = '<p style="color: red;">加载权限分组失败</p>';
        }
    }
}

// 切换快速用户列表显示/隐藏
function toggleQuickUserList() {
    const quickUserSection = document.getElementById('quick-user-section');
    if (quickUserSection) {
        if (quickUserSection.style.display === 'none') {
            quickUserSection.style.display = 'block';
            loadQuickUserList();
        } else {
            quickUserSection.style.display = 'none';
        }
    }
}

// 隐藏快速用户列表
function hideQuickUserList() {
    const quickUserSection = document.getElementById('quick-user-section');
    if (quickUserSection) {
        quickUserSection.style.display = 'none';
    }
}

// 加载快速用户列表
async function loadQuickUserList() {
    const quickUserList = document.getElementById('quick-user-list');
    if (!quickUserList) return;
    
    try {
        quickUserList.innerHTML = '<p>正在加载用户列表...</p>';
        
        const response = await fetch('/api/admin/users');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        const users = data.users || [];
        
        if (users.length === 0) {
            quickUserList.innerHTML = '<p>暂无用户数据</p>';
            return;
        }
        
        // 生成用户列表 HTML
        let html = '<table class="data-table"><thead><tr>';
        html += '<th>用户ID</th><th>用户名</th><th>用户类型</th><th>创建时间</th>';
        html += '</tr></thead><tbody>';
        
        users.forEach(user => {
            html += '<tr>';
            html += `<td>${user.id}</td>`;
            html += `<td>${user.username}</td>`;
            html += `<td>${user.user_type || '普通用户'}</td>`;
            html += `<td>${user.created_at || '-'}</td>`;
            html += '</tr>';
        });
        
        html += '</tbody></table>';
        quickUserList.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading user list:', error);
        quickUserList.innerHTML = `<p style="color: red;">加载失败：${error.message}</p>`;
    }
}

// Default主题特定的其他函数可以在这里添加

// 切换管理用户列表显示
function toggleAdminUserList() {
    const container = document.getElementById('admin-user-list-container');
    if (container) {
        if (container.style.display === 'none') {
            container.style.display = 'block';
            loadAdminUserList();
        } else {
            container.style.display = 'none';
        }
    }
}

// 加载管理用户列表
async function loadAdminUserList() {
    const tbody = document.getElementById('admin-user-list');
    if (!tbody) return;
    
    try {
        tbody.innerHTML = '<tr><td colspan="6" class="loading">正在加载用户列表...</td></tr>';
        
        const response = await fetch('/api/admin/users');
        
        if (!response.ok) {
            if (response.status === 401) {
                tbody.innerHTML = '<tr><td colspan="6" style="color: red;">请先登录</td></tr>';
                return;
            } else if (response.status === 403) {
                tbody.innerHTML = '<tr><td colspan="6" style="color: red;">权限不足，无法访问用户列表</td></tr>';
                return;
            } else {
                throw new Error(`HTTP ${response.status}: 获取用户列表失败`);
            }
        }
        
        const data = await response.json();
        const users = data.users || [];
        
        if (users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">暂无用户数据</td></tr>';
            return;
        }
        
        // 生成用户列表
        let html = '';
        users.forEach(user => {
            const isDefault = user.is_default;
            const rowClass = isDefault ? 'data-row-default' : '';
            
            html += `<tr class="${rowClass}">`;
            
            // 用户名
            html += '<td>';
            if (isDefault) {
                html += `<div class="default-indicator">`;
                html += `<span>${user.username}</span>`;
                html += `<span class="default-tag">默认</span>`;
                html += `</div>`;
            } else {
                html += user.username;
            }
            html += '</td>';
            
            // 类型
            html += `<td>${user.user_type || '普通用户'}</td>`;
            
            // 角色
            html += '<td>';
            if (user.roles && user.roles.length > 0) {
                // 为每个角色添加样式标签
                const roleTags = user.roles.map(role => {
                    const isDefault = ['super_admin', 'admin', 'user'].includes(role);
                    const tagClass = isDefault ? 'role-tag default' : 'role-tag';
                    return `<span class="${tagClass}">${role}</span>`;
                });
                html += roleTags.join(' ');
            } else {
                html += '<span class="text-muted">无角色</span>';
            }
            html += '</td>';
            
            // 状态
            html += `<td><span class="status-active">正常</span></td>`;
            
            // 最后登录
            html += `<td>${user.login_time ? new Date(user.login_time).toLocaleString() : '从未登录'}</td>`;
            
            // 操作
            html += '<td>';
            if (isDefault) {
                html += '<span class="action-disabled">保护中</span>';
            } else {
                html += `<button class="btn btn-sm btn-secondary" onclick="editUser(${user.id})">编辑</button> `;
                html += `<button class="btn btn-sm btn-danger" onclick="deleteUser(${user.id})">删除</button>`;
            }
            html += '</td>';
            
            html += '</tr>';
        });
        
        tbody.innerHTML = html;
        
        // 存储用户数据供搜索使用
        window.adminUsers = users;
        
    } catch (error) {
        console.error('Error loading admin user list:', error);
        tbody.innerHTML = `<tr><td colspan="6" style="color: red;">加载失败：${error.message}</td></tr>`;
    }
}

// 筛选管理用户列表
function filterAdminUserList(searchTerm) {
    if (!window.adminUsers) return;
    
    const tbody = document.getElementById('admin-user-list');
    if (!tbody) return;
    
    const filteredUsers = window.adminUsers.filter(user => 
        user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (user.user_type || '').toLowerCase().includes(searchTerm.toLowerCase())
    );
    
    // 重新渲染过滤后的用户列表
    renderFilteredUsers(filteredUsers);
}

// 渲染过滤后的用户列表
function renderFilteredUsers(users) {
    const tbody = document.getElementById('admin-user-list');
    if (!tbody) return;
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">未找到匹配的用户</td></tr>';
        return;
    }
    
    let html = '';
    users.forEach(user => {
        const isDefault = user.is_default;
        const rowClass = isDefault ? 'data-row-default' : '';
        
        html += `<tr class="${rowClass}">`;
        
        // 用户名
        html += '<td>';
        if (isDefault) {
            html += `<div class="default-indicator">`;
            html += `<span>${user.username}</span>`;
            html += `<span class="default-tag">默认</span>`;
            html += `</div>`;
        } else {
            html += user.username;
        }
        html += '</td>';
        
        // 类型
        html += `<td>${user.user_type || '普通用户'}</td>`;
        
        // 角色
        html += '<td>';
        if (user.roles && user.roles.length > 0) {
            html += user.roles.join(', ');
        } else {
            html += '无';
        }
        html += '</td>';
        
        // 状态
        html += `<td><span class="status-active">正常</span></td>`;
        
        // 最后登录
        html += `<td>${user.login_time ? new Date(user.login_time).toLocaleString() : '从未登录'}</td>`;
        
        // 操作
        html += '<td>';
        if (isDefault) {
            html += '<span class="action-disabled">保护中</span>';
        } else {
            html += `<button class="btn btn-sm btn-secondary" onclick="editUser(${user.id})">编辑</button> `;
            html += `<button class="btn btn-sm btn-danger" onclick="deleteUser(${user.id})">删除</button>`;
        }
        html += '</td>';
        
        html += '</tr>';
    });
    
    tbody.innerHTML = html;
}

// 加载用户角色 - 增强版本
async function loadUserRoles(userId, allRoles) {
    const currentRolesDiv = document.getElementById('admin-user-current-roles');
    const availableRolesDiv = document.getElementById('admin-available-roles');
    
    if (!currentRolesDiv || !availableRolesDiv) {
        console.warn('用户角色容器未找到');
        return;
    }
    
    if (!userId) {
        currentRolesDiv.innerHTML = '<p class="text-muted">请先选择用户</p>';
        availableRolesDiv.innerHTML = '<p class="text-muted">请先选择用户</p>';
        return;
    }
    
    // 显示加载状态
    currentRolesDiv.innerHTML = '<div class="loading-indicator">⏳ 正在加载用户角色...</div>';
    availableRolesDiv.innerHTML = '<div class="loading-indicator">⏳ 正在加载可用角色...</div>';
    
    try {
        // 获取用户当前角色
        const response = await fetch(`/api/admin/users/${userId}/roles`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}`;
            if (response.status === 401) {
                errorMessage = '请重新登录';
            } else if (response.status === 403) {
                errorMessage = '权限不足';
            } else if (response.status === 404) {
                errorMessage = '用户不存在';
            } else {
                errorMessage = `服务器错误 (${response.status})`;
            }
            throw new Error(errorMessage);
        }
        
        const data = await response.json();
        const userRoles = data.roles || [];
        
        // 渲染当前角色
        renderCurrentRoles(currentRolesDiv, userRoles);
        
        // 渲染可用角色
        renderAvailableRoles(availableRolesDiv, allRoles, userRoles);
        
        console.log(`用户 ${userId} 的角色加载完成:`, userRoles.length, '个角色');
        
    } catch (error) {
        console.error('加载用户角色失败:', error);
        
        const errorHtml = `
            <div class="error-state">
                <p style="color: #dc3545; margin: 0;">
                    <strong>⚠️ 加载失败:</strong> ${error.message}
                </p>
                <button onclick="loadUserRoles('${userId}', window.adminRoles || [])" 
                        class="btn btn-sm btn-secondary" style="margin-top: 8px;">
                    重新加载
                </button>
            </div>
        `;
        
        currentRolesDiv.innerHTML = errorHtml;
        availableRolesDiv.innerHTML = '<p class="text-muted">请先加载用户角色</p>';
    }
}

// 渲染当前角色
function renderCurrentRoles(container, userRoles) {
    if (userRoles.length === 0) {
        container.innerHTML = '<p class="text-muted">该用户暂无角色</p>';
        return;
    }
    
    let html = '<div class="current-roles">';
    html += '<h5 style="margin-bottom: 10px;">当前角色:</h5>';
    
    userRoles.forEach(role => {
        const isDefault = role.is_default || ['super_admin', 'admin', 'user'].includes(role.name);
        html += `<span class="role-tag ${isDefault ? 'default' : 'custom'}">`;
        html += role.name;
        if (isDefault) {
            html += ' <small>(默认)</small>';
        }
        html += '</span>';
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// 渲染可用角色
function renderAvailableRoles(container, allRoles, userRoles) {
    if (!allRoles || allRoles.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无可用角色</p>';
        return;
    }
    
    const userRoleIds = userRoles.map(r => r.id);
    
    let html = '<div class="available-roles">';
    html += '<h5 style="margin-bottom: 10px;">分配角色:</h5>';
    
    // 按默认/自定义分组
    const defaultRoles = allRoles.filter(r => r.is_default);
    const customRoles = allRoles.filter(r => !r.is_default);
    
    if (defaultRoles.length > 0) {
        html += '<div class="role-group">';
        html += '<h6 class="role-group-title">默认角色</h6>';
        defaultRoles.forEach(role => {
            html += renderRoleCheckbox(role, userRoleIds.includes(role.id));
        });
        html += '</div>';
    }
    
    if (customRoles.length > 0) {
        html += '<div class="role-group">';
        html += '<h6 class="role-group-title">自定义角色</h6>';
        customRoles.forEach(role => {
            html += renderRoleCheckbox(role, userRoleIds.includes(role.id));
        });
        html += '</div>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}

// 渲染角色复选框
function renderRoleCheckbox(role, isChecked) {
    const isDefault = role.is_default;
    
    return `
        <label class="role-checkbox ${isDefault ? 'default' : 'custom'}">
            <input type="checkbox" value="${role.id}" ${isChecked ? 'checked' : ''}>
            <span class="role-name">${role.name}</span>
            ${isDefault ? '<span class="default-tag">默认</span>' : ''}
            ${role.description ? `<small class="role-desc">${role.description}</small>` : ''}
        </label>
    `;
}

// 保存用户角色 - 增强版本
async function saveUserRoles() {
    const userSelect = document.getElementById('admin-user-select');
    const userId = userSelect ? userSelect.value : null;
    
    if (!userId) {
        showMessage('请先选择用户', 'warning');
        return;
    }
    
    // 获取选中的角色
    const checkboxes = document.querySelectorAll('#admin-available-roles input[type="checkbox"]:checked');
    const roleIds = Array.from(checkboxes).map(cb => parseInt(cb.value));
    
    // 获取用户名用于显示
    const userName = userSelect.options[userSelect.selectedIndex]?.text || `用户 ${userId}`;
    
    // 显示保存状态
    const saveBtn = document.getElementById('admin-save-user-roles-btn');
    const originalText = saveBtn ? saveBtn.textContent : '';
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = '保存中...';
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}/roles`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ role_ids: roleIds })
        });
        
        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}`;
            if (response.status === 401) {
                errorMessage = '请重新登录';
            } else if (response.status === 403) {
                errorMessage = '权限不足，无法修改用户角色';
            } else if (response.status === 404) {
                errorMessage = '用户不存在';
            } else if (response.status === 400) {
                const errorData = await response.json().catch(() => ({}));
                errorMessage = errorData.detail || '请求参数错误';
            } else {
                errorMessage = `服务器错误 (${response.status})`;
            }
            throw new Error(errorMessage);
        }
        
        const data = await response.json();
        
        // 显示成功消息
        showMessage(`${userName} 的角色分配成功`, 'success');
        
        // 刷新用户角色显示
        try {
            const allRoles = window.adminRoles || await window.adminDataLoader.loadRoleData();
            await loadUserRoles(userId, allRoles);
        } catch (refreshError) {
            console.warn('刷新用户角色显示失败:', refreshError);
        }
        
        // 刷新用户列表
        try {
            await loadAdminUserList();
        } catch (refreshError) {
            console.warn('刷新用户列表失败:', refreshError);
        }
        
        // 更新统计信息
        try {
            await initStats();
        } catch (statsError) {
            console.warn('更新统计信息失败:', statsError);
        }
        
        console.log(`用户 ${userId} 角色保存成功:`, roleIds);
        
    } catch (error) {
        console.error('保存用户角色失败:', error);
        showMessage(`保存失败：${error.message}`, 'error');
    } finally {
        // 恢复按钮状态
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = originalText;
        }
    }
}

// 初始化系统默认数据
async function initializeSystemDefaults() {
    if (!confirm('确定要初始化系统默认数据吗？这将创建默认的角色和权限。')) {
        return;
    }
    
    try {
        const response = await fetch('/api/admin/initialize-default-roles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        window.ComponentManager.getComponent('message').success('系统默认数据初始化成功');
        
        // 刷新页面数据
        await initStats();
        await initRoleAssignment();
        await initPermissionGroups();
        
    } catch (error) {
        console.error('Error initializing system defaults:', error);
        window.ComponentManager.getComponent('message').error(`初始化失败：${error.message}`);
    }
}

// 显示消息 - 增强版本
function showMessage(message, type = 'info') {
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
    
    // 降级到自定义消息显示
    showCustomMessage(message, type);
}

// 自定义消息显示
function showCustomMessage(message, type = 'info') {
    const container = document.querySelector('.admin-panel-container') || document.body;
    
    // 移除之前的消息
    const existingMessage = container.querySelector('.custom-message');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `custom-message alert alert-${type}`;
    
    const colors = {
        success: { bg: '#d4edda', border: '#c3e6cb', color: '#155724' },
        error: { bg: '#f8d7da', border: '#f5c6cb', color: '#721c24' },
        warning: { bg: '#fff3cd', border: '#ffeaa7', color: '#856404' },
        info: { bg: '#d1ecf1', border: '#bee5eb', color: '#0c5460' }
    };
    
    const style = colors[type] || colors.info;
    
    messageDiv.style.cssText = `
        background: ${style.bg};
        border: 1px solid ${style.border};
        color: ${style.color};
        padding: 12px 16px;
        border-radius: 4px;
        margin: 10px 0;
        position: relative;
        animation: slideIn 0.3s ease-out;
        z-index: 1000;
    `;
    
    messageDiv.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <span>${message}</span>
            <button onclick="this.closest('.custom-message').remove()" 
                    style="background: none; border: none; font-size: 18px; cursor: pointer; color: ${style.color};">
                ×
            </button>
        </div>
    `;
    
    container.insertBefore(messageDiv, container.firstChild);
    
    // 自动隐藏
    setTimeout(() => {
        if (messageDiv && messageDiv.parentNode) {
            messageDiv.style.opacity = '0';
            messageDiv.style.transition = 'opacity 0.3s ease-out';
            setTimeout(() => messageDiv.remove(), 300);
        }
    }, 5000);
}

// 显示确认对话框
function showConfirmDialog(message, onConfirm, onCancel = null) {
    if (window.ComponentManager && typeof window.ComponentManager.getComponent === 'function') {
        const dialogManager = window.ComponentManager.getComponent('dialog');
        if (dialogManager) {
            return dialogManager.confirm(message, onConfirm, onCancel);
        }
    }
    
    // 降级到原生确认框
    if (confirm(message)) {
        if (typeof onConfirm === 'function') {
            onConfirm();
        }
    } else {
        if (typeof onCancel === 'function') {
            onCancel();
        }
    }
}

// 显示加载状态
function showLoadingState(containerId, message = '正在加载...') {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-state';
    loadingDiv.style.cssText = `
        text-align: center;
        padding: 20px;
        color: #666;
        font-style: italic;
    `;
    loadingDiv.innerHTML = `
        <div class="loading-spinner" style="display: inline-block; margin-right: 8px; animation: spin 1s linear infinite;">⏳</div>
        ${message}
    `;
    
    container.innerHTML = '';
    container.appendChild(loadingDiv);
}

// 添加CSS动画
if (!document.getElementById('admin-panel-animations')) {
    const style = document.createElement('style');
    style.id = 'admin-panel-animations';
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateY(-10px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        .loading-indicator {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            color: #666;
            font-style: italic;
        }
        
        .error-state {
            padding: 15px;
            text-align: center;
        }
        
        .role-tag {
            display: inline-block;
            padding: 4px 8px;
            margin: 2px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .role-tag.default {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }
        
        .role-tag.custom {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        
        .role-checkbox {
            display: block;
            padding: 8px;
            margin: 4px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .role-checkbox:hover {
            background-color: #f8f9fa;
        }
        
        .role-checkbox.default {
            border-color: #ffeaa7;
            background-color: #fffbf0;
        }
        
        .role-name {
            font-weight: 500;
            margin-left: 8px;
        }
        
        .role-desc {
            display: block;
            color: #666;
            margin-left: 24px;
            font-size: 11px;
        }
        
        .default-tag {
            background: #ffc107;
            color: #212529;
            padding: 2px 6px;
            border-radius: 8px;
            font-size: 10px;
            font-weight: bold;
            margin-left: 4px;
        }
        
        .role-group {
            margin-bottom: 15px;
        }
        
        .role-group-title {
            font-size: 14px;
            font-weight: 600;
            color: #495057;
            margin-bottom: 8px;
            padding-bottom: 4px;
            border-bottom: 1px solid #dee2e6;
        }
        
        .status-badge {
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
        }
        
        .status-badge.active {
            background: #d4edda;
            color: #155724;
        }
        
        .status-badge.inactive {
            background: #f8d7da;
            color: #721c24;
        }
    `;
    document.head.appendChild(style);
}

// 工具函数
function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 初始化数据绑定系统
function initializeDataBinding() {
    console.log('初始化数据绑定系统...');
    
    // 创建数据观察器
    window.adminDataObserver = new AdminDataObserver();
    
    // 绑定数据更新事件
    bindDataUpdateEvents();
    
    console.log('数据绑定系统初始化完成');
}

// 管理面板数据观察器
class AdminDataObserver {
    constructor() {
        this.data = {
            users: [],
            roles: [],
            permissions: [],
            stats: {}
        };
        this.listeners = new Map();
        this.updateQueue = new Set();
        this.isUpdating = false;
    }

    // 订阅数据变化
    subscribe(key, callback) {
        if (!this.listeners.has(key)) {
            this.listeners.set(key, new Set());
        }
        this.listeners.get(key).add(callback);
    }

    // 取消订阅
    unsubscribe(key, callback) {
        if (this.listeners.has(key)) {
            this.listeners.get(key).delete(callback);
        }
    }

    // 更新数据
    updateData(key, newData) {
        const oldData = this.data[key];
        this.data[key] = newData;
        
        // 通知监听器
        this.notifyListeners(key, newData, oldData);
        
        // 添加到更新队列
        this.updateQueue.add(key);
        this.processUpdateQueue();
    }

    // 获取数据
    getData(key) {
        return this.data[key];
    }

    // 通知监听器
    notifyListeners(key, newData, oldData) {
        if (this.listeners.has(key)) {
            this.listeners.get(key).forEach(callback => {
                try {
                    callback(newData, oldData);
                } catch (error) {
                    console.error(`数据监听器执行失败 (${key}):`, error);
                }
            });
        }
    }

    // 处理更新队列
    async processUpdateQueue() {
        if (this.isUpdating || this.updateQueue.size === 0) {
            return;
        }

        this.isUpdating = true;
        
        try {
            // 批量处理更新
            const updates = Array.from(this.updateQueue);
            this.updateQueue.clear();
            
            // 更新UI组件
            await this.updateUIComponents(updates);
            
        } catch (error) {
            console.error('处理数据更新队列失败:', error);
        } finally {
            this.isUpdating = false;
        }
    }

    // 更新UI组件
    async updateUIComponents(updates) {
        const updatePromises = updates.map(key => {
            switch (key) {
                case 'users':
                    return this.updateUserComponents();
                case 'roles':
                    return this.updateRoleComponents();
                case 'permissions':
                    return this.updatePermissionComponents();
                case 'stats':
                    return this.updateStatsComponents();
                default:
                    return Promise.resolve();
            }
        });

        await Promise.all(updatePromises);
    }

    // 更新用户相关组件
    async updateUserComponents() {
        const users = this.data.users;
        
        // 更新用户列表 - 使用本地的 renderUserTable 函数
        if (typeof this.renderUserTable === 'function') {
            this.renderUserTable(users);
        }
        
        // 更新用户选择器
        updateUserSelectors(users);
        
        // 更新统计信息
        this.updateStatsComponents();
    }

    // 更新角色相关组件
    async updateRoleComponents() {
        const roles = this.data.roles;
        
        // 更新角色列表
        if (typeof renderRoleList === 'function') {
            renderRoleList(roles);
        }
        
        // 更新角色选择器
        updateRoleSelectors(roles);
        
        // 更新统计信息
        this.updateStatsComponents();
    }

    // 更新权限相关组件
    async updatePermissionComponents() {
        const permissions = this.data.permissions;
        
        // 更新权限列表
        if (typeof renderPermissionList === 'function') {
            renderPermissionList(permissions);
        }
        
        // 更新权限分组
        updatePermissionGroups(permissions);
        
        // 更新统计信息
        this.updateStatsComponents();
    }

    // 更新统计组件
    async updateStatsComponents() {
        const stats = this.calculateStats();
        
        // 更新统计显示
        Object.entries(stats).forEach(([key, value]) => {
            updateElement(`stats-${key}`, value);
        });
    }

    // 计算统计信息
    calculateStats() {
        return {
            'total-users': this.data.users.length,
            'total-roles': this.data.roles.length,
            'total-permissions': this.data.permissions.length,
            'default-items': this.calculateDefaultItems()
        };
    }

    // 计算默认数据项数量
    calculateDefaultItems() {
        const defaultUsers = this.data.users.filter(u => u.is_default).length;
        const defaultRoles = this.data.roles.filter(r => r.is_default).length;
        const defaultPermissions = this.data.permissions.filter(p => p.is_default).length;
        return defaultUsers + defaultRoles + defaultPermissions;
    }
}

// 绑定数据更新事件
function bindDataUpdateEvents() {
    // 监听用户数据变化
    window.adminDataObserver.subscribe('users', (users) => {
        console.log('用户数据已更新:', users.length, '个用户');
    });

    // 监听角色数据变化
    window.adminDataObserver.subscribe('roles', (roles) => {
        console.log('角色数据已更新:', roles.length, '个角色');
    });

    // 监听权限数据变化
    window.adminDataObserver.subscribe('permissions', (permissions) => {
        console.log('权限数据已更新:', permissions.length, '个权限');
    });
}

// 更新用户选择器
function updateUserSelectors(users) {
    const selectors = document.querySelectorAll('.user-selector, #admin-user-select, #assignment-user-select');
    
    selectors.forEach(selector => {
        if (!selector) return;
        
        const currentValue = selector.value;
        selector.innerHTML = '<option value="">请选择用户</option>';
        
        users.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = user.username;
            
            if (user.is_default) {
                option.style.color = '#f59e0b';
                option.style.fontWeight = 'bold';
                option.textContent += ' (默认)';
            }
            
            selector.appendChild(option);
        });
        
        // 恢复之前的选择
        if (currentValue) {
            selector.value = currentValue;
        }
    });
}

// 更新角色选择器
function updateRoleSelectors(roles) {
    const selectors = document.querySelectorAll('.role-selector, #admin-role-select, #assignment-role-select');
    
    selectors.forEach(selector => {
        if (!selector) return;
        
        const currentValue = selector.value;
        selector.innerHTML = '<option value="">请选择角色</option>';
        
        roles.forEach(role => {
            const option = document.createElement('option');
            option.value = role.id;
            option.textContent = role.name;
            
            if (role.is_default) {
                option.style.color = '#f59e0b';
                option.style.fontWeight = 'bold';
                option.textContent += ' (默认)';
            }
            
            selector.appendChild(option);
        });
        
        // 恢复之前的选择
        if (currentValue) {
            selector.value = currentValue;
        }
    });
}

// 更新权限分组显示
function updatePermissionGroups(permissions) {
    const container = document.getElementById('admin-permission-groups');
    if (!container) return;
    
    // 按分组整理权限
    const groups = {};
    permissions.forEach(permission => {
        const group = getPermissionGroup(permission.name);
        if (!groups[group]) {
            groups[group] = [];
        }
        groups[group].push(permission);
    });
    
    // 生成HTML
    let html = '';
    Object.entries(groups).forEach(([groupName, groupPermissions]) => {
        if (groupPermissions.length > 0) {
            html += `<div class="permission-group">`;
            html += `<div class="permission-group-header">`;
            html += `<span class="permission-group-title">${groupName}</span>`;
            html += `<span class="permission-group-count">${groupPermissions.length} 项权限</span>`;
            html += `</div>`;
            
            html += `<div class="permission-items">`;
            groupPermissions.forEach(permission => {
                html += `<div class="permission-item ${permission.is_default ? 'default' : ''}">`;
                html += `<div class="permission-item-info">`;
                html += `<div class="permission-item-name">`;
                html += permission.name;
                if (permission.is_default) {
                    html += ` <span class="default-tag">默认</span>`;
                }
                html += `</div>`;
                html += `<div class="permission-item-desc">${permission.description || ''}</div>`;
                html += `</div>`;
                html += `</div>`;
            });
            html += `</div>`;
            html += `</div>`;
        }
    });
    
    container.innerHTML = html || '<p>暂无权限数据</p>';
}

// 获取权限分组
function getPermissionGroup(permissionName) {
    const groups = {
        'user.': '用户管理',
        'role.': '角色管理',
        'permission.': '权限管理',
        'system.': '系统管理',
        'file.': '文件管理',
        'build.': '构建权限'
    };

    for (const [prefix, group] of Object.entries(groups)) {
        if (permissionName.startsWith(prefix)) {
            return group;
        }
    }
    return '其他权限';
}

// 设置自动刷新
function setupAutoRefresh() {
    // 每30秒自动刷新统计信息
    setInterval(async () => {
        try {
            await refreshStats();
        } catch (error) {
            console.error('自动刷新统计信息失败:', error);
        }
    }, 30000);
}

// 刷新统计信息
async function refreshStats() {
    try {
        const [usersResponse, rolesResponse, permissionsResponse] = await Promise.all([
            fetch('/api/admin/users'),
            fetch('/api/admin/roles'),
            fetch('/api/admin/permissions')
        ]);
        
        const [usersData, rolesData, permissionsData] = await Promise.all([
            usersResponse.json(),
            rolesResponse.json(),
            permissionsResponse.json()
        ]);
        
        // 更新数据观察器
        if (window.adminDataObserver) {
            window.adminDataObserver.updateData('users', usersData.users || []);
            window.adminDataObserver.updateData('roles', rolesData.roles || []);
            window.adminDataObserver.updateData('permissions', permissionsData.permissions || []);
        }
        
    } catch (error) {
        console.error('刷新统计信息失败:', error);
    }
}
// 编辑角色
function editRole(roleId) {
    const role = window.adminRoles?.find(r => r.id === roleId);
    if (!role) {
        showMessage('角色不存在', 'error');
        return;
    }
    
    if (role.is_default) {
        showMessage('默认角色不能编辑', 'warning');
        return;
    }
    
    // 创建编辑角色的模态框
    const modalHtml = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>编辑角色</h3>
                <button type="button" class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <form id="edit-role-form">
                    <div class="form-group">
                        <label for="edit-role-name">角色名称</label>
                        <input type="text" id="edit-role-name" name="name" value="${role.name}" required>
                    </div>
                    <div class="form-group">
                        <label for="edit-role-description">角色描述</label>
                        <textarea id="edit-role-description" name="description" rows="3">${role.description || ''}</textarea>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">取消</button>
                <button type="button" class="btn btn-primary" onclick="saveRoleEdit(${roleId})">保存</button>
            </div>
        </div>
    `;
    
    showModal(modalHtml);
}

// 保存角色编辑
async function saveRoleEdit(roleId) {
    const form = document.getElementById('edit-role-form');
    const formData = new FormData(form);
    
    const roleData = {
        name: formData.get('name'),
        description: formData.get('description')
    };
    
    try {
        const response = await fetch(`/api/admin/roles/${roleId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(roleData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('角色更新成功', 'success');
            closeModal();
            await window.adminDataLoader.loadRoleData(); // 刷新角色列表
        } else {
            throw new Error(result.detail || '更新角色失败');
        }
    } catch (error) {
        console.error('Error updating role:', error);
        showMessage(`更新失败：${error.message}`, 'error');
    }
}

// 删除角色
async function deleteRole(roleId) {
    const role = window.adminRoles?.find(r => r.id === roleId);
    if (!role) {
        showMessage('角色不存在', 'error');
        return;
    }
    
    if (role.is_default) {
        showMessage('默认角色不能删除', 'warning');
        return;
    }
    
    showConfirmDialog(
        `确定要删除角色 "${role.name}" 吗？此操作不可撤销。`,
        async () => {
            try {
                const response = await fetch(`/api/admin/roles/${roleId}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showMessage('角色删除成功', 'success');
                    await window.adminDataLoader.loadRoleData(); // 刷新角色列表
                } else {
                    throw new Error(result.detail || '删除角色失败');
                }
            } catch (error) {
                console.error('Error deleting role:', error);
                showMessage(`删除失败：${error.message}`, 'error');
            }
        }
    );
}

// 编辑权限
function editPermission(permissionId) {
    const permission = window.adminPermissions?.find(p => p.id === permissionId);
    if (!permission) {
        showMessage('权限不存在', 'error');
        return;
    }
    
    if (permission.is_default) {
        showMessage('默认权限不能编辑', 'warning');
        return;
    }
    
    // 创建编辑权限的模态框
    const modalHtml = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>编辑权限</h3>
                <button type="button" class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <form id="edit-permission-form">
                    <div class="form-group">
                        <label for="edit-permission-name">权限名称</label>
                        <input type="text" id="edit-permission-name" name="name" value="${permission.name}" required>
                    </div>
                    <div class="form-group">
                        <label for="edit-permission-description">权限描述</label>
                        <textarea id="edit-permission-description" name="description" rows="3">${permission.description || ''}</textarea>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">取消</button>
                <button type="button" class="btn btn-primary" onclick="savePermissionEdit(${permissionId})">保存</button>
            </div>
        </div>
    `;
    
    showModal(modalHtml);
}

// 保存权限编辑
async function savePermissionEdit(permissionId) {
    const form = document.getElementById('edit-permission-form');
    const formData = new FormData(form);
    
    const permissionData = {
        name: formData.get('name'),
        description: formData.get('description')
    };
    
    try {
        const response = await fetch(`/api/admin/permissions/${permissionId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(permissionData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('权限更新成功', 'success');
            closeModal();
            await window.adminDataLoader.loadPermissionData(); // 刷新权限列表
        } else {
            throw new Error(result.detail || '更新权限失败');
        }
    } catch (error) {
        console.error('Error updating permission:', error);
        showMessage(`更新失败：${error.message}`, 'error');
    }
}

// 删除权限
async function deletePermission(permissionId) {
    const permission = window.adminPermissions?.find(p => p.id === permissionId);
    if (!permission) {
        showMessage('权限不存在', 'error');
        return;
    }
    
    if (permission.is_default) {
        showMessage('默认权限不能删除', 'warning');
        return;
    }
    
    showConfirmDialog(
        `确定要删除权限 "${permission.name}" 吗？此操作不可撤销。`,
        async () => {
            try {
                const response = await fetch(`/api/admin/permissions/${permissionId}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showMessage('权限删除成功', 'success');
                    await window.adminDataLoader.loadPermissionData(); // 刷新权限列表
                } else {
                    throw new Error(result.detail || '删除权限失败');
                }
            } catch (error) {
                console.error('Error deleting permission:', error);
                showMessage(`删除失败：${error.message}`, 'error');
            }
        }
    );
}

// 编辑用户
function editUser(userId) {
    const user = window.adminUsers?.find(u => u.id === userId);
    if (!user) {
        window.ComponentManager.getComponent('message').error('用户不存在');
        return;
    }
    
    // 创建编辑用户的模态框
    const modalHtml = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>编辑用户</h3>
                <button type="button" class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <form id="edit-user-form">
                    <div class="form-group">
                        <label for="edit-username">用户名</label>
                        <input type="text" id="edit-username" name="username" value="${user.username}" required>
                    </div>
                    <div class="form-group">
                        <label for="edit-password">新密码（留空则不修改）</label>
                        <input type="password" id="edit-password" name="password" placeholder="留空则不修改密码">
                    </div>
                    <div class="form-group">
                        <label for="edit-theme">主题</label>
                        <select id="edit-theme" name="theme">
                            <option value="default" ${user.theme === 'default' ? 'selected' : ''}>默认</option>
                            <option value="wooden" ${user.theme === 'wooden' ? 'selected' : ''}>木质</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>当前角色</label>
                        <div class="current-roles">
                            ${user.roles && user.roles.length > 0 ? 
                                user.roles.map(role => {
                                    const isDefault = ['super_admin', 'admin', 'user'].includes(role);
                                    const tagClass = isDefault ? 'role-tag default' : 'role-tag';
                                    return `<span class="${tagClass}">${role}</span>`;
                                }).join(' ') : 
                                '<span class="text-muted">无角色</span>'
                            }
                        </div>
                        <small class="form-help">角色管理请使用下方的"角色权限分配"功能</small>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">取消</button>
                <button type="button" class="btn btn-primary" onclick="saveUserEdit(${userId})">保存</button>
            </div>
        </div>
    `;
    
    showModal(modalHtml);
}

// 保存用户编辑
async function saveUserEdit(userId) {
    const form = document.getElementById('edit-user-form');
    const formData = new FormData(form);
    
    const userData = {
        username: formData.get('username'),
        theme: formData.get('theme')
    };
    
    // 只有在输入了新密码时才包含密码字段
    const password = formData.get('password');
    if (password && password.trim()) {
        userData.password = password;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(userData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            window.ComponentManager.getComponent('message').success('用户更新成功');
            closeModal();
            loadAdminUserList(); // 刷新用户列表
        } else {
            throw new Error(result.detail || '更新用户失败');
        }
    } catch (error) {
        console.error('Error updating user:', error);
        window.ComponentManager.getComponent('message').error(`更新失败：${error.message}`);
    }
}

// 删除用户
async function deleteUser(userId) {
    const user = window.adminUsers?.find(u => u.id === userId);
    if (!user) {
        window.ComponentManager.getComponent('message').error('用户不存在');
        return;
    }
    
    if (!confirm(`确定要删除用户 "${user.username}" 吗？此操作不可撤销。`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/user/${userId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            window.ComponentManager.getComponent('message').success('用户删除成功');
            loadAdminUserList(); // 刷新用户列表
        } else {
            throw new Error(result.detail || '删除用户失败');
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        window.ComponentManager.getComponent('message').error(`删除失败：${error.message}`);
    }
}

// 显示模态框
function showModal(html) {
    let modal = document.getElementById('admin-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'admin-modal';
        modal.className = 'modal';
        document.body.appendChild(modal);
    }
    
    modal.innerHTML = html;
    modal.style.display = 'block';
    
    // 点击模态框外部关闭
    modal.onclick = function(event) {
        if (event.target === modal) {
            closeModal();
        }
    };
}

// 关闭模态框
function closeModal() {
    const modal = document.getElementById('admin-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 关闭管理员下拉菜单（兼容性函数）
function closeAdminDrawer() {
    // 兼容性函数，调用新的下拉菜单关闭函数
    if (typeof closeAdminDropdown === 'function') {
        closeAdminDropdown();
    }
    console.log('closeAdminDrawer called, redirecting to closeAdminDropdown');
}

// 重置Src目录为初始状态
async function resetSrcDirectory() {
    // 不再使用confirm对话框，因为在调用此函数之前已经有确认机制
    
    try {
        // 显示加载状态
        const resetBtn = document.getElementById('reset-src-btn');
        const originalText = resetBtn ? resetBtn.textContent : '';
        if (resetBtn) {
            resetBtn.disabled = true;
            resetBtn.textContent = '重置中...';
        }
        
        // 调用API端点
        const response = await fetch('/api/reset-src', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        // 优先使用统一的消息组件，如果不存在则使用showMessage
        if (window.ComponentManager && typeof window.ComponentManager.getComponent === 'function') {
            const messageManager = window.ComponentManager.getComponent('message');
            if (messageManager) {
                messageManager.success('Src目录已重置为初始状态');
            } else {
                showMessage('Src目录已重置为初始状态', 'success');
            }
        } else {
            showMessage('Src目录已重置为初始状态', 'success');
        }
        
        // 刷新页面以显示最新的src目录内容
        // 如果存在文件管理器刷新函数，则调用它
        if (typeof refreshFileManager === 'function') {
            refreshFileManager();
        } else {
            // 否则重新加载页面
            window.location.reload();
        }
        
    } catch (error) {
        console.error('重置Src目录失败:', error);
        
        // 优先使用统一的消息组件，如果不存在则使用showMessage
        if (window.ComponentManager && typeof window.ComponentManager.getComponent === 'function') {
            const messageManager = window.ComponentManager.getComponent('message');
            if (messageManager) {
                messageManager.error(`重置Src目录失败: ${error.message}`);
            } else {
                showMessage(`重置Src目录失败: ${error.message}`, 'error');
            }
        } else {
            showMessage(`重置Src目录失败: ${error.message}`, 'error');
        }
    } finally {
        // 恢复按钮状态
        const resetBtn = document.getElementById('reset-src-btn');
        if (resetBtn) {
            resetBtn.disabled = false;
            resetBtn.textContent = '还原Src目录';
        }
    }
}
// ==================== 新的超级管理员功能 ====================

// 初始化用户管理功能
async function initUserManagement() {
    try {
        console.log('开始初始化用户管理功能...');
        
        // 使用增强的数据加载器
        await window.adminDataLoader.loadAllData();
        
        // 绑定用户管理事件
        bindUserManagementEvents();
        
        console.log('用户管理功能初始化完成');
        
    } catch (error) {
        console.error('用户管理功能初始化失败:', error);
        
        // 显示错误信息
        window.adminDataLoader.showErrorMessage('用户管理功能初始化失败，请刷新页面重试');
    }
}

// 绑定用户管理相关事件
function bindUserManagementEvents() {
    // 创建用户按钮
    const createUserBtn = document.getElementById('create-user-btn');
    if (createUserBtn) {
        createUserBtn.addEventListener('click', showCreateUserModal);
    }
    
    // 批量操作按钮
    const bulkActionsBtn = document.getElementById('bulk-user-actions-btn');
    if (bulkActionsBtn) {
        bulkActionsBtn.addEventListener('click', showBulkActionsModal);
    }
    
    // 导出用户按钮
    const exportUsersBtn = document.getElementById('export-users-btn');
    if (exportUsersBtn) {
        exportUsersBtn.addEventListener('click', exportUsers);
    }
    
    // 用户搜索
    const userSearch = document.getElementById('user-search');
    if (userSearch) {
        userSearch.addEventListener('input', debounce(filterUsers, 300));
    }
    
    // 筛选控件
    const roleFilter = document.getElementById('user-role-filter');
    const statusFilter = document.getElementById('user-status-filter');
    
    if (roleFilter) {
        roleFilter.addEventListener('change', filterUsers);
    }
    
    if (statusFilter) {
        statusFilter.addEventListener('change', filterUsers);
    }
    
    // 清除筛选按钮
    const clearFiltersBtn = document.getElementById('clear-filters-btn');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', clearUserFilters);
    }
    
    // 全选复选框
    const selectAllUsers = document.getElementById('select-all-users');
    if (selectAllUsers) {
        selectAllUsers.addEventListener('change', toggleSelectAllUsers);
    }
}

// 加载用户管理数据
async function loadUserManagementData() {
    try {
        showMessage('正在加载用户数据...', 'info');
        
        const response = await fetch('/api/admin/users', {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        renderUsersTable(data.users || []);
        updateUserStats(data.users || []);
        
        showMessage('用户数据加载成功', 'success');
        
    } catch (error) {
        console.error('加载用户数据失败:', error);
        showMessage('加载用户数据失败: ' + error.message, 'error');
    }
}

// 渲染用户表格
function renderUsersTable(users) {
    const tbody = document.getElementById('users-table-body');
    if (!tbody) return;
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading-cell">暂无用户数据</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(user => `
        <tr>
            <td><input type="checkbox" class="user-checkbox" value="${user.id}"></td>
            <td>${escapeHtml(user.username || '')}</td>
            <td>${escapeHtml(user.email || '')}</td>
            <td>${Array.isArray(user.roles) ? user.roles.join(', ') : ''}</td>
            <td><span class="status-badge ${user.is_active ? 'active' : 'inactive'}">${user.is_active ? '活跃' : '非活跃'}</span></td>
            <td>${user.created_at || '--'}</td>
            <td>${user.last_login || '从未登录'}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="editUser('${user.id}')">编辑</button>
                <button class="btn btn-sm btn-danger" onclick="deleteUser('${user.id}')">删除</button>
                <button class="btn btn-sm btn-warning" onclick="resetUserPassword('${user.id}')">重置密码</button>
            </td>
        </tr>
    `).join('');
}

// 更新用户统计
function updateUserStats(users) {
    const totalUsers = users.length;
    const activeUsers = users.filter(u => u.is_active).length;
    
    updateElement('stats-total-users', totalUsers);
    updateElement('stats-active-users', activeUsers);
}

// 筛选用户
function filterUsers() {
    const searchTerm = document.getElementById('user-search')?.value.toLowerCase() || '';
    const roleFilter = document.getElementById('user-role-filter')?.value || '';
    const statusFilter = document.getElementById('user-status-filter')?.value || '';
    
    const rows = document.querySelectorAll('#users-table-body tr');
    
    rows.forEach(row => {
        const username = row.cells[1]?.textContent.toLowerCase() || '';
        const email = row.cells[2]?.textContent.toLowerCase() || '';
        const roles = row.cells[3]?.textContent.toLowerCase() || '';
        const status = row.cells[4]?.textContent.toLowerCase() || '';
        
        const matchesSearch = !searchTerm || 
            username.includes(searchTerm) || 
            email.includes(searchTerm);
        
        const matchesRole = !roleFilter || roles.includes(roleFilter.toLowerCase());
        
        const matchesStatus = !statusFilter || 
            (statusFilter === 'active' && status.includes('活跃')) ||
            (statusFilter === 'inactive' && status.includes('非活跃'));
        
        row.style.display = matchesSearch && matchesRole && matchesStatus ? '' : 'none';
    });
}

// 清除筛选
function clearUserFilters() {
    document.getElementById('user-search').value = '';
    document.getElementById('user-role-filter').value = '';
    document.getElementById('user-status-filter').value = '';
    filterUsers();
}

// 全选/取消全选用户
function toggleSelectAllUsers() {
    const selectAll = document.getElementById('select-all-users');
    const checkboxes = document.querySelectorAll('.user-checkbox');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll.checked;
    });
}

// 显示创建用户模态框
function showCreateUserModal() {
    // 创建用户模态框HTML
    const modalHtml = `
        <div class="modal-content" style="width: 500px; max-width: 90vw;">
            <div class="modal-header">
                <h3>创建新用户</h3>
                <button type="button" class="modal-close" onclick="closeAdminModal()">&times;</button>
            </div>
            <div class="modal-body" style="padding: 20px;">
                <form id="create-user-form">
                    <div class="form-group">
                        <label for="create-username">用户名</label>
                        <input type="text" id="create-username" name="username" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label for="create-password">密码</label>
                        <input type="password" id="create-password" name="password" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label for="create-email">邮箱</label>
                        <input type="email" id="create-email" name="email" class="form-control">
                    </div>
                    <div class="form-group">
                        <label for="create-theme">主题</label>
                        <select id="create-theme" name="theme" class="form-control">
                            <option value="default">默认</option>
                            <option value="wooden">木质</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="create-user-type">用户类型</label>
                        <select id="create-user-type" name="user_type" class="form-control">
                            <option value="user">普通用户</option>
                            <option value="admin">管理员</option>
                        </select>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeAdminModal()">取消</button>
                <button type="button" class="btn btn-primary" onclick="submitCreateUser()">创建</button>
            </div>
        </div>
    `;
    
    // 显示模态框
    showAdminModal(modalHtml);
}

// 提交创建用户表单
async function submitCreateUser() {
    const form = document.getElementById('create-user-form');
    if (!form) return;
    
    const formData = new FormData(form);
    const userData = {
        username: formData.get('username'),
        password: formData.get('password'),
        email: formData.get('email') || '',
        theme: formData.get('theme') || 'default',
        user_type: formData.get('user_type') || 'user'
    };
    
    // 验证必填字段
    if (!userData.username || !userData.password) {
        showMessage('用户名和密码不能为空', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/admin/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(userData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('用户创建成功', 'success');
            closeAdminModal();
            // 重新加载用户列表
            loadAdminUserList();
        } else {
            throw new Error(result.detail || '创建用户失败');
        }
    } catch (error) {
        console.error('创建用户失败:', error);
        showMessage(`创建用户失败: ${error.message}`, 'error');
    }
}

// 显示管理员模态框
function showAdminModal(html) {
    let modal = document.getElementById('admin-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'admin-modal';
        modal.className = 'modal';
        modal.style.cssText = `
            display: block;
            position: fixed;
            z-index: 10000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        `;
        document.body.appendChild(modal);
    }
    
    // 创建模态框内容容器
    const modalContainer = document.createElement('div');
    modalContainer.className = 'modal-dialog';
    modalContainer.style.cssText = `
        position: relative;
        margin: 5% auto;
        width: fit-content;
        max-width: 90%;
    `;
    modalContainer.innerHTML = html;
    
    modal.innerHTML = '';
    modal.appendChild(modalContainer);
    
    // 点击模态框外部关闭
    modal.onclick = function(event) {
        if (event.target === modal) {
            closeAdminModal();
        }
    };
}

// 关闭管理员模态框
function closeAdminModal() {
    const modal = document.getElementById('admin-modal');
    if (modal) {
        modal.remove();
    }
}

// 显示批量操作模态框
function showBulkActionsModal() {
    const selectedUsers = document.querySelectorAll('.user-checkbox:checked');
    if (selectedUsers.length === 0) {
        showMessage('请先选择要操作的用户', 'warning');
        return;
    }
    
    // 创建批量操作模态框HTML
    const selectedUserCount = selectedUsers.length;
    const modalHtml = `
        <div class="modal-content" style="width: 500px; max-width: 90vw;">
            <div class="modal-header">
                <h3>批量操作</h3>
                <button type="button" class="modal-close" onclick="closeAdminModal()">&times;</button>
            </div>
            <div class="modal-body" style="padding: 20px;">
                <p>已选择 <strong>${selectedUserCount}</strong> 个用户</p>
                
                <div class="form-group">
                    <label>选择操作:</label>
                    <select id="bulk-action-select" class="form-control" onchange="handleBulkActionChange()">
                        <option value="">请选择操作</option>
                        <option value="delete">删除用户</option>
                        <option value="activate">激活用户</option>
                        <option value="deactivate">停用用户</option>
                        <option value="reset-password">重置密码</option>
                    </select>
                </div>
                
                <div id="bulk-action-options" style="display: none; margin-top: 15px;">
                    <!-- 操作选项将在这里动态显示 -->
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeAdminModal()">取消</button>
                <button type="button" class="btn btn-primary" onclick="executeBulkAction()" id="execute-bulk-action-btn" disabled>执行</button>
            </div>
        </div>
    `;
    
    // 显示模态框
    showAdminModal(modalHtml);
}

// 处理批量操作选择变化
function handleBulkActionChange() {
    const actionSelect = document.getElementById('bulk-action-select');
    const optionsContainer = document.getElementById('bulk-action-options');
    const executeBtn = document.getElementById('execute-bulk-action-btn');
    
    if (!actionSelect || !optionsContainer || !executeBtn) return;
    
    const action = actionSelect.value;
    optionsContainer.style.display = action ? 'block' : 'none';
    executeBtn.disabled = !action;
    
    // 根据选择的操作显示不同的选项
    switch (action) {
        case 'delete':
            optionsContainer.innerHTML = `
                <div class="alert alert-warning">
                    <strong>警告:</strong> 此操作将永久删除选中的用户，无法恢复。
                </div>
                <div class="form-check">
                    <input type="checkbox" id="confirm-delete" class="form-check-input">
                    <label for="confirm-delete" class="form-check-label">我确认要删除这些用户</label>
                </div>
            `;
            break;
        case 'activate':
            optionsContainer.innerHTML = `
                <div class="alert alert-info">
                    <strong>信息:</strong> 此操作将激活选中的用户账户。
                </div>
            `;
            break;
        case 'deactivate':
            optionsContainer.innerHTML = `
                <div class="alert alert-info">
                    <strong>信息:</strong> 此操作将停用选中的用户账户。
                </div>
            `;
            break;
        case 'reset-password':
            optionsContainer.innerHTML = `
                <div class="alert alert-warning">
                    <strong>警告:</strong> 此操作将重置选中用户的所有密码。
                </div>
                <div class="form-group">
                    <label for="password-template">密码模板 (可选):</label>
                    <input type="text" id="password-template" class="form-control" placeholder="留空则使用随机密码">
                </div>
            `;
            break;
        default:
            optionsContainer.innerHTML = '';
    }
}

// 执行批量操作
async function executeBulkAction() {
    const actionSelect = document.getElementById('bulk-action-select');
    const selectedUsers = document.querySelectorAll('.user-checkbox:checked');
    
    if (!actionSelect || selectedUsers.length === 0) return;
    
    const action = actionSelect.value;
    if (!action) {
        showMessage('请选择要执行的操作', 'warning');
        return;
    }
    
    // 获取选中的用户ID
    const userIds = Array.from(selectedUsers).map(checkbox => checkbox.value);
    
    // 根据操作类型执行不同的确认检查
    switch (action) {
        case 'delete':
            const confirmDelete = document.getElementById('confirm-delete');
            if (!confirmDelete || !confirmDelete.checked) {
                showMessage('请确认删除操作', 'warning');
                return;
            }
            break;
    }
    
    try {
        // 显示加载状态
        const executeBtn = document.getElementById('execute-bulk-action-btn');
        const originalText = executeBtn.textContent;
        executeBtn.disabled = true;
        executeBtn.textContent = '执行中...';
        
        // 调用相应的API
        let response, result;
        switch (action) {
            case 'delete':
                response = await fetch('/api/admin/users/bulk-delete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({ user_ids: userIds })
                });
                break;
            case 'activate':
                response = await fetch('/api/admin/users/bulk-activate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({ user_ids: userIds })
                });
                break;
            case 'deactivate':
                response = await fetch('/api/admin/users/bulk-deactivate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({ user_ids: userIds })
                });
                break;
            case 'reset-password':
                const passwordTemplate = document.getElementById('password-template')?.value || '';
                response = await fetch('/api/admin/users/bulk-reset-password', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        user_ids: userIds,
                        password_template: passwordTemplate
                    })
                });
                break;
        }
        
        if (!response) {
            throw new Error('未知操作');
        }
        
        result = await response.json();
        
        if (response.ok) {
            showMessage(`批量操作成功完成 (${result.success_count}/${userIds.length})`, 'success');
            closeAdminModal();
            // 重新加载用户列表
            loadAdminUserList();
        } else {
            throw new Error(result.detail || '批量操作失败');
        }
    } catch (error) {
        console.error('批量操作失败:', error);
        showMessage(`批量操作失败: ${error.message}`, 'error');
    } finally {
        // 恢复按钮状态
        const executeBtn = document.getElementById('execute-bulk-action-btn');
        if (executeBtn) {
            executeBtn.disabled = false;
            executeBtn.textContent = '执行';
        }
    }
}

// 导出用户
async function exportUsers() {
    try {
        showMessage('正在导出用户数据...', 'info');
        
        const response = await fetch('/api/admin/users/export', {
            method: 'GET',
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('导出失败');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `users_export_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showMessage('用户数据导出成功', 'success');
        
    } catch (error) {
        console.error('导出用户数据失败:', error);
        showMessage('导出用户数据失败: ' + error.message, 'error');
    }
}

// 编辑用户
function editUser(userId) {
    // 获取用户信息
    const user = window.adminUsers?.find(u => u.id == userId);
    if (!user) {
        showMessage('用户不存在', 'error');
        return;
    }
    
    // 创建编辑用户模态框HTML
    const modalHtml = `
        <div class="modal-content" style="width: 500px; max-width: 90vw;">
            <div class="modal-header">
                <h3>编辑用户</h3>
                <button type="button" class="modal-close" onclick="closeAdminModal()">&times;</button>
            </div>
            <div class="modal-body" style="padding: 20px;">
                <form id="edit-user-form">
                    <input type="hidden" id="edit-user-id" value="${user.id}">
                    <div class="form-group">
                        <label for="edit-username">用户名</label>
                        <input type="text" id="edit-username" name="username" class="form-control" value="${user.username}" required>
                    </div>
                    <div class="form-group">
                        <label for="edit-email">邮箱</label>
                        <input type="email" id="edit-email" name="email" class="form-control" value="${user.email || ''}">
                    </div>
                    <div class="form-group">
                        <label for="edit-theme">主题</label>
                        <select id="edit-theme" name="theme" class="form-control">
                            <option value="default" ${user.theme === 'default' ? 'selected' : ''}>默认</option>
                            <option value="wooden" ${user.theme === 'wooden' ? 'selected' : ''}>木质</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="edit-user-type">用户类型</label>
                        <select id="edit-user-type" name="user_type" class="form-control">
                            <option value="user" ${user.user_type === 'user' ? 'selected' : ''}>普通用户</option>
                            <option value="admin" ${user.user_type === 'admin' ? 'selected' : ''}>管理员</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="edit-password">新密码 (留空则不修改)</label>
                        <input type="password" id="edit-password" name="password" class="form-control" placeholder="留空则不修改密码">
                    </div>
                    <div class="form-group">
                        <label for="edit-confirm-password">确认新密码</label>
                        <input type="password" id="edit-confirm-password" name="confirm_password" class="form-control" placeholder="再次输入新密码">
                    </div>
                    <div class="form-check">
                        <input type="checkbox" id="edit-is-active" name="is_active" class="form-check-input" ${user.is_active ? 'checked' : ''}>
                        <label for="edit-is-active" class="form-check-label">账户活跃</label>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeAdminModal()">取消</button>
                <button type="button" class="btn btn-primary" onclick="submitEditUser()">保存</button>
            </div>
        </div>
    `;
    
    // 显示模态框
    showAdminModal(modalHtml);
}

// 提交编辑用户表单
async function submitEditUser() {
    const form = document.getElementById('edit-user-form');
    if (!form) return;
    
    const formData = new FormData(form);
    const userId = formData.get('user_id');
    const password = formData.get('password');
    const confirmPassword = formData.get('confirm_password');
    
    // 验证密码确认
    if (password && password !== confirmPassword) {
        showMessage('两次输入的密码不一致', 'warning');
        return;
    }
    
    const userData = {
        username: formData.get('username'),
        email: formData.get('email') || '',
        theme: formData.get('theme') || 'default',
        user_type: formData.get('user_type') || 'user',
        is_active: formData.get('is_active') === 'on'
    };
    
    // 只有在输入了新密码时才包含密码字段
    if (password) {
        userData.password = password;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(userData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('用户信息更新成功', 'success');
            closeAdminModal();
            // 重新加载用户列表
            loadAdminUserList();
        } else {
            throw new Error(result.detail || '更新用户信息失败');
        }
    } catch (error) {
        console.error('更新用户信息失败:', error);
        showMessage(`更新用户信息失败: ${error.message}`, 'error');
    }
}

// 删除用户
async function deleteUser(userId) {
    if (!confirm('确定要删除这个用户吗？此操作不可恢复。')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('删除失败');
        }
        
        showMessage('用户删除成功', 'success');
        loadUserManagementData(); // 重新加载数据
        
    } catch (error) {
        console.error('删除用户失败:', error);
        showMessage('删除用户失败: ' + error.message, 'error');
    }
}

// 重置用户密码
async function resetUserPassword(userId) {
    if (!confirm('确定要重置这个用户的密码吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}/reset-password`, {
            method: 'POST',
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('重置密码失败');
        }
        
        const result = await response.json();
        showMessage(`密码重置成功，新密码：${result.new_password}`, 'success');
        
    } catch (error) {
        console.error('重置密码失败:', error);
        showMessage('重置密码失败: ' + error.message, 'error');
    }
}

// 加载角色权限数据
async function loadRolePermissionData() {
    try {
        showMessage('正在加载角色权限数据...', 'info');
        
        const [rolesResponse, permissionsResponse] = await Promise.all([
            fetch('/api/admin/roles', { credentials: 'include' }),
            fetch('/api/admin/permissions', { credentials: 'include' })
        ]);
        
        if (!rolesResponse.ok || !permissionsResponse.ok) {
            throw new Error('加载数据失败');
        }
        
        const rolesData = await rolesResponse.json();
        const permissionsData = await permissionsResponse.json();
        
        renderRolesList(rolesData.roles || []);
        renderPermissionsGroups(permissionsData.permissions || []);
        
        showMessage('角色权限数据加载成功', 'success');
        
    } catch (error) {
        console.error('加载角色权限数据失败:', error);
        showMessage('加载角色权限数据失败: ' + error.message, 'error');
    }
}

// 渲染角色列表
function renderRolesList(roles) {
    const container = document.getElementById('roles-list');
    if (!container) return;
    
    if (roles.length === 0) {
        container.innerHTML = '<div class="loading-placeholder">暂无角色数据</div>';
        return;
    }
    
    container.innerHTML = roles.map(role => `
        <div class="role-item" data-role-id="${role.id}" onclick="selectRole('${role.id}')">
            <div class="role-name">${escapeHtml(role.name)}</div>
            <div class="role-description">${escapeHtml(role.description || '')}</div>
            <div class="role-permissions-count">${role.permissions ? role.permissions.length : 0} 个权限</div>
        </div>
    `).join('');
}

// 渲染权限分组
function renderPermissionsGroups(permissions) {
    const container = document.getElementById('permissions-groups');
    if (!container) return;
    
    if (permissions.length === 0) {
        container.innerHTML = '<div class="loading-placeholder">暂无权限数据</div>';
        return;
    }
    
    // 按分组整理权限
    const groups = {};
    permissions.forEach(permission => {
        const group = getPermissionGroup(permission.name);
        if (!groups[group]) {
            groups[group] = [];
        }
        groups[group].push(permission);
    });
    
    container.innerHTML = Object.entries(groups).map(([groupName, groupPermissions]) => `
        <div class="permission-group">
            <h4>${groupName}</h4>
            <div class="permission-items">
                ${groupPermissions.map(permission => `
                    <div class="permission-item" data-permission-id="${permission.id}">
                        <label>
                            <input type="checkbox" class="permission-checkbox" value="${permission.id}">
                            ${escapeHtml(permission.name)}
                        </label>
                        <div class="permission-description">${escapeHtml(permission.description || '')}</div>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');
}

// 选择角色
function selectRole(roleId) {
    // 移除之前的选中状态
    document.querySelectorAll('.role-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    // 添加选中状态
    const roleItem = document.querySelector(`[data-role-id="${roleId}"]`);
    if (roleItem) {
        roleItem.classList.add('selected');
    }
    
    // 加载角色的权限
    loadRolePermissions(roleId);
    
    // 启用保存按钮
    const saveBtn = document.getElementById('save-role-permissions-btn');
    const resetBtn = document.getElementById('reset-role-permissions-btn');
    
    if (saveBtn) saveBtn.disabled = false;
    if (resetBtn) resetBtn.disabled = false;
}

// 加载角色权限
async function loadRolePermissions(roleId) {
    try {
        const response = await fetch(`/api/admin/roles/${roleId}/permissions`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('加载角色权限失败');
        }
        
        const data = await response.json();
        const rolePermissions = data.permissions || [];
        
        // 更新权限复选框状态
        document.querySelectorAll('.permission-checkbox').forEach(checkbox => {
            checkbox.checked = rolePermissions.some(p => p.id === checkbox.value);
        });
        
        // 更新分配面板
        const assignmentPanel = document.getElementById('role-permission-assignment');
        if (assignmentPanel) {
            assignmentPanel.innerHTML = `
                <div class="assignment-info">
                    <h4>当前角色权限配置</h4>
                    <p>已选择 ${rolePermissions.length} 个权限</p>
                </div>
            `;
        }
        
    } catch (error) {
        console.error('加载角色权限失败:', error);
        showMessage('加载角色权限失败: ' + error.message, 'error');
    }
}

// 获取权限分组
function getPermissionGroup(permissionName) {
    const groups = {
        'user.': '用户管理',
        'role.': '角色管理',
        'permission.': '权限管理',
        'system.': '系统管理',
        'file.': '文件管理',
        'build.': '构建权限',
        'content.': '内容管理',
        'backup.': '备份管理'
    };

    for (const [prefix, group] of Object.entries(groups)) {
        if (permissionName.startsWith(prefix)) {
            return group;
        }
    }
    return '其他权限';
}

// 加载审计日志
async function loadAuditLogs() {
    try {
        showMessage('正在加载审计日志...', 'info');
        
        const response = await fetch('/api/admin/audit-logs', {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('加载审计日志失败');
        }
        
        const data = await response.json();
        renderAuditLogs(data.logs || []);
        
        showMessage('审计日志加载成功', 'success');
        
    } catch (error) {
        console.error('加载审计日志失败:', error);
        showMessage('加载审计日志失败: ' + error.message, 'error');
    }
}

// 渲染审计日志
function renderAuditLogs(logs) {
    const container = document.getElementById('audit-logs-list');
    if (!container) return;
    
    if (logs.length === 0) {
        container.innerHTML = '<div class="loading-placeholder">暂无审计日志</div>';
        return;
    }
    
    container.innerHTML = logs.map(log => `
        <div class="log-item">
            <div class="log-header">
                <span class="log-action">${escapeHtml(log.action)}</span>
                <span class="log-time">${log.created_at}</span>
            </div>
            <div class="log-details">
                <span class="log-user">用户: ${escapeHtml(log.username)}</span>
                <span class="log-ip">IP: ${log.ip_address}</span>
            </div>
            <div class="log-description">${escapeHtml(log.description || '')}</div>
        </div>
    `).join('');
}

// 加载备份数据
async function loadBackupData() {
    try {
        showMessage('正在加载备份数据...', 'info');
        
        const response = await fetch('/api/admin/backups', {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('加载备份数据失败');
        }
        
        const data = await response.json();
        renderBackupList(data.backups || []);
        updateBackupStats(data.backups || []);
        
        showMessage('备份数据加载成功', 'success');
        
    } catch (error) {
        console.error('加载备份数据失败:', error);
        showMessage('加载备份数据失败: ' + error.message, 'error');
    }
}

// 渲染备份列表
function renderBackupList(backups) {
    const container = document.getElementById('backup-files-list');
    if (!container) return;
    
    if (backups.length === 0) {
        container.innerHTML = '<div class="loading-placeholder">暂无备份文件</div>';
        return;
    }
    
    container.innerHTML = backups.map(backup => `
        <div class="backup-item">
            <div class="backup-info">
                <div class="backup-name">${escapeHtml(backup.filename)}</div>
                <div class="backup-meta">
                    <span class="backup-size">${formatFileSize(backup.size)}</span>
                    <span class="backup-date">${backup.created_at}</span>
                    <span class="backup-type">${backup.type || 'manual'}</span>
                </div>
            </div>
            <div class="backup-actions">
                <button class="btn btn-sm btn-secondary" onclick="downloadBackup('${backup.filename}')">下载</button>
                <button class="btn btn-sm btn-warning" onclick="restoreBackup('${backup.filename}')">恢复</button>
                <button class="btn btn-sm btn-danger" onclick="deleteBackup('${backup.filename}')">删除</button>
            </div>
        </div>
    `).join('');
}

// 更新备份统计
function updateBackupStats(backups) {
    const totalBackups = backups.length;
    const totalSize = backups.reduce((sum, backup) => sum + (backup.size || 0), 0);
    const lastBackup = backups.length > 0 ? backups[0].created_at : '--';
    
    updateElement('total-backups', totalBackups);
    updateElement('backup-size', formatFileSize(totalSize));
    updateElement('last-backup', lastBackup);
}

// 加载系统状态
async function loadSystemStatus() {
    try {
        showMessage('正在加载系统状态...', 'info');
        
        const response = await fetch('/api/admin/system-status', {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('加载系统状态失败');
        }
        
        const data = await response.json();
        updateSystemStatus(data);
        
        showMessage('系统状态加载成功', 'success');
        
    } catch (error) {
        console.error('加载系统状态失败:', error);
        showMessage('加载系统状态失败: ' + error.message, 'error');
    }
}

// 更新系统状态
function updateSystemStatus(status) {
    // 更新磁盘使用
    updateElement('disk-usage', `${status.disk_usage || 0}%`);
    updateProgressBar('disk-progress', status.disk_usage || 0);
    
    // 更新内存使用
    updateElement('memory-usage', `${status.memory_usage || 0}%`);
    updateProgressBar('memory-progress', status.memory_usage || 0);
    
    // 更新CPU使用
    updateElement('cpu-usage', `${status.cpu_usage || 0}%`);
    updateProgressBar('cpu-progress', status.cpu_usage || 0);
    
    // 更新系统健康度
    updateElement('system-health', `${status.health || 100}%`);
    updateElement('system-uptime', status.uptime || '--');
}

// 更新进度条
function updateProgressBar(elementId, percentage) {
    const progressBar = document.getElementById(elementId);
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
    }
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// HTML转义函数
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 显示消息
function showMessage(message, type = 'info') {
    // 如果存在统一的消息组件，使用它
    if (window.ComponentManager && window.ComponentManager.getComponent('message')) {
        const messageComponent = window.ComponentManager.getComponent('message');
        messageComponent[type](message);
        return;
    }
    
    // 否则使用简单的alert
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // 创建简单的消息提示
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.textContent = message;
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 6px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
        background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : type === 'warning' ? '#ffc107' : '#17a2b8'};
    `;
    
    document.body.appendChild(messageDiv);
    
    setTimeout(() => {
        messageDiv.style.opacity = '0';
        messageDiv.style.transition = 'opacity 0.3s ease-out';
        setTimeout(() => messageDiv.remove(), 300);
    }, 3000);
}

console.log('超级管理员功能模块加载完成');// 权限管理功能
function initPermissionManagement() {
    // 标签页切换
    const tabBtns = document.querySelectorAll('.permission-tabs .tab-btn');
    const tabPanels = document.querySelectorAll('.permission-tabs .tab-panel');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            
            // 更新按钮状态
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // 更新面板显示
            tabPanels.forEach(panel => {
                panel.classList.remove('active');
                if (panel.id === targetTab + '-tab') {
                    panel.classList.add('active');
                }
            });
            
            // 加载对应数据
            loadPermissionTabData(targetTab);
        });
    });
    
    // 初始化第一个标签页
    loadPermissionTabData('user-roles');
}

function loadPermissionTabData(tabName) {
    switch(tabName) {
        case 'user-roles':
            loadUserRoleData();
            break;
        case 'role-permissions':
            loadRolePermissionData();
            break;
        case 'manage-roles':
            loadManageRolesData();
            break;
        case 'manage-permissions':
            loadManagePermissionsData();
            break;
    }
}

async function loadUserRoleData() {
    try {
        const response = await fetch('/api/admin/users', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            renderUserList(data.users || []);
        }
    } catch (error) {
        console.error('加载用户数据失败:', error);
        showNotification('加载用户数据失败', 'error');
    }
}

function renderUserList(users) {
    const container = document.getElementById('user-role-list');
    if (!container) return;
    
    if (users.length === 0) {
        container.innerHTML = '<div class="no-data">暂无用户数据</div>';
        return;
    }
    
    const html = users.map(user => `
        <div class="user-item" data-user-id="${user.id}" onclick="selectUser(${user.id}, '${user.username}')">
            <div class="user-name">${escapeHtml(user.username)}</div>
            <div class="user-roles">${(user.roles || []).map(r => r.name).join(', ') || '无角色'}</div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

async function selectUser(userId, username) {
    // 更新选中状态
    document.querySelectorAll('.user-item').forEach(item => {
        item.classList.remove('selected');
    });
    document.querySelector(`[data-user-id="${userId}"]`).classList.add('selected');
    
    // 显示用户信息
    const infoContainer = document.getElementById('selected-user-info');
    infoContainer.innerHTML = `
        <div class="selected-info">
            <h5>已选择用户: ${escapeHtml(username)}</h5>
            <p>用户ID: ${userId}</p>
        </div>
    `;
    
    // 加载用户角色
    try {
        const response = await fetch(`/api/admin/users/${userId}/roles`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            renderUserRoles(data.user_roles || [], data.available_roles || []);
            document.getElementById('save-user-roles-btn').disabled = false;
        }
    } catch (error) {
        console.error('加载用户角色失败:', error);
        showNotification('加载用户角色失败', 'error');
    }
}

function renderUserRoles(userRoles, availableRoles) {
    const container = document.getElementById('user-roles-container');
    if (!container) return;
    
    const userRoleIds = userRoles.map(r => r.id);
    
    const html = availableRoles.map(role => `
        <div class="role-checkbox-item">
            <input type="checkbox" 
                   id="user-role-${role.id}" 
                   value="${role.id}" 
                   ${userRoleIds.includes(role.id) ? 'checked' : ''}>
            <label for="user-role-${role.id}">
                <strong>${escapeHtml(role.name)}</strong>
                ${role.description ? `<br><small>${escapeHtml(role.description)}</small>` : ''}
            </label>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

// 保存用户角色
async function saveUserRoles() {
    const selectedUser = document.querySelector('.user-item.selected');
    if (!selectedUser) {
        showNotification('请先选择一个用户', 'warning');
        return;
    }
    
    const userId = selectedUser.getAttribute('data-user-id');
    const selectedRoleIds = Array.from(document.querySelectorAll('#user-roles-container input:checked'))
        .map(cb => parseInt(cb.value));
    
    try {
        const response = await fetch(`/api/admin/users/${userId}/roles`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                role_ids: selectedRoleIds
            })
        });
        
        if (response.ok) {
            showNotification('用户角色保存成功', 'success');
            loadUserRoleData(); // 重新加载数据
        } else {
            const error = await response.json();
            showNotification(error.detail || '保存失败', 'error');
        }
    } catch (error) {
        console.error('保存用户角色失败:', error);
        showNotification('保存用户角色失败', 'error');
    }
}

// 绑定保存按钮事件
document.addEventListener('DOMContentLoaded', function() {
    const saveUserRolesBtn = document.getElementById('save-user-roles-btn');
    if (saveUserRolesBtn) {
        saveUserRolesBtn.addEventListener('click', saveUserRoles);
    }
});// 角色权限管理
async function loadRolePermissionData() {
    try {
        const response = await fetch('/api/admin/roles', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            renderRoleList(data.roles || []);
        }
    } catch (error) {
        console.error('加载角色数据失败:', error);
        showNotification('加载角色数据失败', 'error');
    }
}

function renderRoleList(roles) {
    const container = document.getElementById('role-permission-list');
    if (!container) return;
    
    if (roles.length === 0) {
        container.innerHTML = '<div class="no-data">暂无角色数据</div>';
        return;
    }
    
    const html = roles.map(role => `
        <div class="role-item" data-role-id="${role.id}" onclick="selectRole(${role.id}, '${role.name}')">
            <div class="role-name">${escapeHtml(role.name)}</div>
            <div class="role-description">${escapeHtml(role.description || '')}</div>
            <div class="role-permissions-count">${(role.permissions || []).length} 个权限</div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

async function selectRole(roleId, roleName) {
    // 更新选中状态
    document.querySelectorAll('.role-item').forEach(item => {
        item.classList.remove('selected');
    });
    document.querySelector(`[data-role-id="${roleId}"]`).classList.add('selected');
    
    // 显示角色信息
    const infoContainer = document.getElementById('selected-role-info');
    infoContainer.innerHTML = `
        <div class="selected-info">
            <h5>已选择角色: ${escapeHtml(roleName)}</h5>
            <p>角色ID: ${roleId}</p>
        </div>
    `;
    
    // 加载角色权限
    try {
        const response = await fetch(`/api/admin/roles/${roleId}/permissions`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            renderRolePermissions(data.role_permissions || [], data.available_permissions || []);
            document.getElementById('save-role-permissions-btn').disabled = false;
        }
    } catch (error) {
        console.error('加载角色权限失败:', error);
        showNotification('加载角色权限失败', 'error');
    }
}

function renderRolePermissions(rolePermissions, availablePermissions) {
    const container = document.getElementById('role-permissions-container');
    if (!container) return;
    
    const rolePermissionIds = rolePermissions.map(p => p.id);
    
    // 按分组组织权限
    const permissionGroups = {};
    availablePermissions.forEach(permission => {
        const group = permission.group || '其他';
        if (!permissionGroups[group]) {
            permissionGroups[group] = [];
        }
        permissionGroups[group].push(permission);
    });
    
    const html = Object.entries(permissionGroups).map(([group, permissions]) => `
        <div class="permission-group">
            <h6>${escapeHtml(group)}</h6>
            ${permissions.map(permission => `
                <div class="permission-checkbox-item">
                    <input type="checkbox" 
                           id="role-permission-${permission.id}" 
                           value="${permission.id}" 
                           class="role-permission-checkbox"
                           ${rolePermissionIds.includes(permission.id) ? 'checked' : ''}>
                    <label for="role-permission-${permission.id}">
                        <strong>${escapeHtml(permission.name)}</strong>
                        ${permission.description ? `<br><small>${escapeHtml(permission.description)}</small>` : ''}
                    </label>
                </div>
            `).join('')}
        </div>
    `).join('');
    
    container.innerHTML = html;
}

// 保存角色权限
async function saveRolePermissions() {
    const selectedRole = document.querySelector('.role-item.selected');
    if (!selectedRole) {
        showNotification('请先选择一个角色', 'warning');
        return;
    }
    
    const roleId = selectedRole.getAttribute('data-role-id');
    const selectedPermissionIds = Array.from(document.querySelectorAll('.role-permission-checkbox:checked'))
        .map(cb => parseInt(cb.value));
    
    try {
        const response = await fetch(`/api/admin/roles/${roleId}/permissions`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                permission_ids: selectedPermissionIds
            })
        });
        
        if (response.ok) {
            showNotification('角色权限保存成功', 'success');
            loadRolePermissionData(); // 重新加载数据
        } else {
            const error = await response.json();
            showNotification(error.detail || '保存失败', 'error');
        }
    } catch (error) {
        console.error('保存角色权限失败:', error);
        showNotification('保存角色权限失败', 'error');
    }
}

// 管理角色功能
async function loadManageRolesData() {
    try {
        const response = await fetch('/api/admin/roles', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            renderRolesTable(data.roles || []);
        }
    } catch (error) {
        console.error('加载角色管理数据失败:', error);
        showNotification('加载角色管理数据失败', 'error');
    }
}

function renderRolesTable(roles) {
    const tbody = document.getElementById('roles-table-body');
    if (!tbody) return;
    
    if (roles.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-data">暂无角色数据</td></tr>';
        return;
    }
    
    const html = roles.map(role => `
        <tr>
            <td>
                ${escapeHtml(role.name)}
                ${role.is_default ? '<span class="default-tag">默认</span>' : ''}
            </td>
            <td>${escapeHtml(role.description || '')}</td>
            <td>${(role.permissions || []).length}</td>
            <td>${role.user_count || 0}</td>
            <td>
                <button class="btn-small btn-secondary" onclick="editRole(${role.id})">编辑</button>
                ${!role.is_default ? `<button class="btn-small btn-danger" onclick="deleteRole(${role.id})">删除</button>` : ''}
            </td>
        </tr>
    `).join('');
    
    tbody.innerHTML = html;
}

// 管理权限功能
async function loadManagePermissionsData() {
    try {
        const response = await fetch('/api/admin/permissions', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            renderPermissionsTable(data.permissions || []);
        }
    } catch (error) {
        console.error('加载权限管理数据失败:', error);
        showNotification('加载权限管理数据失败', 'error');
    }
}

function renderPermissionsTable(permissions) {
    const tbody = document.getElementById('permissions-table-body');
    if (!tbody) return;
    
    if (permissions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-data">暂无权限数据</td></tr>';
        return;
    }
    
    const html = permissions.map(permission => `
        <tr>
            <td>
                ${escapeHtml(permission.name)}
                ${permission.is_default ? '<span class="default-tag">默认</span>' : ''}
            </td>
            <td>${escapeHtml(permission.description || '')}</td>
            <td>${escapeHtml(permission.group || '其他')}</td>
            <td>${permission.role_count || 0}</td>
            <td>
                <button class="btn-small btn-secondary" onclick="editPermission(${permission.id})">编辑</button>
                ${!permission.is_default ? `<button class="btn-small btn-danger" onclick="deletePermission(${permission.id})">删除</button>` : ''}
            </td>
        </tr>
    `).join('');
    
    tbody.innerHTML = html;
}

// 绑定更多事件
document.addEventListener('DOMContentLoaded', function() {
    const saveRolePermissionsBtn = document.getElementById('save-role-permissions-btn');
    if (saveRolePermissionsBtn) {
        saveRolePermissionsBtn.addEventListener('click', saveRolePermissions);
    }
    
    // 添加角色按钮
    const addRoleBtn = document.getElementById('add-role-btn');
    if (addRoleBtn) {
        addRoleBtn.addEventListener('click', showAddRoleModal);
    }
    
    // 添加权限按钮
    const addPermissionBtn = document.getElementById('add-permission-btn');
    if (addPermissionBtn) {
        addPermissionBtn.addEventListener('click', showAddPermissionModal);
    }
});

// 显示添加权限模态框
function showAddPermissionModal() {
    const modalHtml = `
        <div class="modal-content" style="width: 500px; max-width: 90vw;">
            <div class="modal-header">
                <h3>添加新权限</h3>
                <button type="button" class="modal-close" onclick="closeAdminModal()">&times;</button>
            </div>
            <div class="modal-body" style="padding: 20px;">
                <form id="add-permission-form">
                    <div class="form-group">
                        <label for="add-permission-name">权限名称</label>
                        <input type="text" id="add-permission-name" name="name" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label for="add-permission-description">权限描述</label>
                        <textarea id="add-permission-description" name="description" class="form-control" rows="3"></textarea>
                    </div>
                    <div class="form-group">
                        <label for="add-permission-group">权限分组</label>
                        <select id="add-permission-group" name="group" class="form-control">
                            <option value="user">用户管理</option>
                            <option value="role">角色管理</option>
                            <option value="permission">权限管理</option>
                            <option value="system">系统管理</option>
                            <option value="file">文件管理</option>
                            <option value="build">构建权限</option>
                            <option value="content">内容管理</option>
                            <option value="backup">备份管理</option>
                            <option value="other">其他</option>
                        </select>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeAdminModal()">取消</button>
                <button type="button" class="btn btn-primary" onclick="submitAddPermission()">创建</button>
            </div>
        </div>
    `;
    
    showAdminModal(modalHtml);
}

// 提交添加权限表单
async function submitAddPermission() {
    const form = document.getElementById('add-permission-form');
    if (!form) return;
    
    const formData = new FormData(form);
    const permissionData = {
        name: formData.get('name'),
        description: formData.get('description') || '',
        group: formData.get('group') || 'other'
    };
    
    // 验证必填字段
    if (!permissionData.name) {
        showMessage('权限名称不能为空', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/admin/permissions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(permissionData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('权限创建成功', 'success');
            closeAdminModal();
            // 重新加载权限列表
            if (typeof loadManagePermissionsData === 'function') {
                loadManagePermissionsData();
            }
        } else {
            throw new Error(result.detail || '创建权限失败');
        }
    } catch (error) {
        console.error('创建权限失败:', error);
        showMessage(`创建权限失败: ${error.message}`, 'error');
    }
}

// 工具函数
function editRole(roleId) {
    // 获取角色信息
    const role = window.adminRoles?.find(r => r.id == roleId);
    if (!role) {
        showMessage('角色不存在', 'error');
        return;
    }
    
    // 检查是否为默认角色
    if (role.is_default) {
        showMessage('默认角色不能编辑', 'warning');
        return;
    }
    
    // 创建编辑角色模态框
    const modalHtml = `
        <div class="modal-content" style="width: 500px; max-width: 90vw;">
            <div class="modal-header">
                <h3>编辑角色</h3>
                <button type="button" class="modal-close" onclick="closeAdminModal()">&times;</button>
            </div>
            <div class="modal-body" style="padding: 20px;">
                <form id="edit-role-form">
                    <input type="hidden" id="edit-role-id" value="${role.id}">
                    <div class="form-group">
                        <label for="edit-role-name">角色名称</label>
                        <input type="text" id="edit-role-name" name="name" class="form-control" value="${escapeHtml(role.name)}" required>
                    </div>
                    <div class="form-group">
                        <label for="edit-role-description">角色描述</label>
                        <textarea id="edit-role-description" name="description" class="form-control" rows="3">${escapeHtml(role.description || '')}</textarea>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeAdminModal()">取消</button>
                <button type="button" class="btn btn-primary" onclick="submitEditRole()">保存</button>
            </div>
        </div>
    `;
    
    showAdminModal(modalHtml);
}

// 提交编辑角色表单
async function submitEditRole() {
    const form = document.getElementById('edit-role-form');
    if (!form) return;
    
    const formData = new FormData(form);
    const roleId = formData.get('role_id');
    const roleData = {
        name: formData.get('name'),
        description: formData.get('description') || ''
    };
    
    // 验证必填字段
    if (!roleData.name) {
        showMessage('角色名称不能为空', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/roles/${roleId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(roleData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('角色更新成功', 'success');
            closeAdminModal();
            // 重新加载角色列表
            if (typeof loadManageRolesData === 'function') {
                loadManageRolesData();
            }
        } else {
            throw new Error(result.detail || '更新角色失败');
        }
    } catch (error) {
        console.error('更新角色失败:', error);
        showMessage(`更新角色失败: ${error.message}`, 'error');
    }
}

// 显示添加角色模态框
function showAddRoleModal() {
    const modalHtml = `
        <div class="modal-content" style="width: 500px; max-width: 90vw;">
            <div class="modal-header">
                <h3>添加新角色</h3>
                <button type="button" class="modal-close" onclick="closeAdminModal()">&times;</button>
            </div>
            <div class="modal-body" style="padding: 20px;">
                <form id="add-role-form">
                    <div class="form-group">
                        <label for="add-role-name">角色名称</label>
                        <input type="text" id="add-role-name" name="name" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label for="add-role-description">角色描述</label>
                        <textarea id="add-role-description" name="description" class="form-control" rows="3"></textarea>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeAdminModal()">取消</button>
                <button type="button" class="btn btn-primary" onclick="submitAddRole()">创建</button>
            </div>
        </div>
    `;
    
    showAdminModal(modalHtml);
}

// 提交添加角色表单
async function submitAddRole() {
    const form = document.getElementById('add-role-form');
    if (!form) return;
    
    const formData = new FormData(form);
    const roleData = {
        name: formData.get('name'),
        description: formData.get('description') || ''
    };
    
    // 验证必填字段
    if (!roleData.name) {
        showMessage('角色名称不能为空', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/admin/roles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(roleData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('角色创建成功', 'success');
            closeAdminModal();
            // 重新加载角色列表
            if (typeof loadManageRolesData === 'function') {
                loadManageRolesData();
            }
        } else {
            throw new Error(result.detail || '创建角色失败');
        }
    } catch (error) {
        console.error('创建角色失败:', error);
        showMessage(`创建角色失败: ${error.message}`, 'error');
    }
}

function deleteRole(roleId) {
    // 获取角色信息
    const role = window.adminRoles?.find(r => r.id == roleId);
    if (!role) {
        showMessage('角色不存在', 'error');
        return;
    }
    
    // 检查是否为默认角色
    if (role.is_default) {
        showMessage('默认角色不能删除', 'warning');
        return;
    }
    
    // 确认删除
    if (!confirm(`确定要删除角色 "${role.name}" 吗？此操作不可恢复。`)) {
        return;
    }
    
    // 执行删除
    performDeleteRole(roleId);
}

// 执行删除角色
async function performDeleteRole(roleId) {
    try {
        const response = await fetch(`/api/admin/roles/${roleId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('删除失败');
        }
        
        showMessage('角色删除成功', 'success');
        
        // 重新加载角色列表
        if (typeof loadManageRolesData === 'function') {
            loadManageRolesData();
        }
    } catch (error) {
        console.error('删除角色失败:', error);
        showMessage(`删除角色失败: ${error.message}`, 'error');
    }
}

function editPermission(permissionId) {
    // 获取权限信息
    const permission = window.adminPermissions?.find(p => p.id == permissionId);
    if (!permission) {
        showMessage('权限不存在', 'error');
        return;
    }
    
    // 检查是否为默认权限
    if (permission.is_default) {
        showMessage('默认权限不能编辑', 'warning');
        return;
    }
    
    // 创建编辑权限模态框
    const modalHtml = `
        <div class="modal-content" style="width: 500px; max-width: 90vw;">
            <div class="modal-header">
                <h3>编辑权限</h3>
                <button type="button" class="modal-close" onclick="closeAdminModal()">&times;</button>
            </div>
            <div class="modal-body" style="padding: 20px;">
                <form id="edit-permission-form">
                    <input type="hidden" id="edit-permission-id" value="${permission.id}">
                    <div class="form-group">
                        <label for="edit-permission-name">权限名称</label>
                        <input type="text" id="edit-permission-name" name="name" class="form-control" value="${escapeHtml(permission.name)}" required>
                    </div>
                    <div class="form-group">
                        <label for="edit-permission-description">权限描述</label>
                        <textarea id="edit-permission-description" name="description" class="form-control" rows="3">${escapeHtml(permission.description || '')}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="edit-permission-group">权限分组</label>
                        <select id="edit-permission-group" name="group" class="form-control">
                            <option value="user" ${permission.group === 'user' ? 'selected' : ''}>用户管理</option>
                            <option value="role" ${permission.group === 'role' ? 'selected' : ''}>角色管理</option>
                            <option value="permission" ${permission.group === 'permission' ? 'selected' : ''}>权限管理</option>
                            <option value="system" ${permission.group === 'system' ? 'selected' : ''}>系统管理</option>
                            <option value="file" ${permission.group === 'file' ? 'selected' : ''}>文件管理</option>
                            <option value="build" ${permission.group === 'build' ? 'selected' : ''}>构建权限</option>
                            <option value="content" ${permission.group === 'content' ? 'selected' : ''}>内容管理</option>
                            <option value="backup" ${permission.group === 'backup' ? 'selected' : ''}>备份管理</option>
                            <option value="other" ${permission.group === 'other' || !permission.group ? 'selected' : ''}>其他</option>
                        </select>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeAdminModal()">取消</button>
                <button type="button" class="btn btn-primary" onclick="submitEditPermission()">保存</button>
            </div>
        </div>
    `;
    
    showAdminModal(modalHtml);
}

// 提交编辑权限表单
async function submitEditPermission() {
    const form = document.getElementById('edit-permission-form');
    if (!form) return;
    
    const formData = new FormData(form);
    const permissionId = formData.get('permission_id');
    const permissionData = {
        name: formData.get('name'),
        description: formData.get('description') || '',
        group: formData.get('group') || 'other'
    };
    
    // 验证必填字段
    if (!permissionData.name) {
        showMessage('权限名称不能为空', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/permissions/${permissionId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(permissionData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('权限更新成功', 'success');
            closeAdminModal();
            // 重新加载权限列表
            if (typeof loadManagePermissionsData === 'function') {
                loadManagePermissionsData();
            }
        } else {
            throw new Error(result.detail || '更新权限失败');
        }
    } catch (error) {
        console.error('更新权限失败:', error);
        showMessage(`更新权限失败: ${error.message}`, 'error');
    }
}

function deletePermission(permissionId) {
    // 获取权限信息
    const permission = window.adminPermissions?.find(p => p.id == permissionId);
    if (!permission) {
        showMessage('权限不存在', 'error');
        return;
    }
    
    // 检查是否为默认权限
    if (permission.is_default) {
        showMessage('默认权限不能删除', 'warning');
        return;
    }
    
    // 确认删除
    if (!confirm(`确定要删除权限 "${permission.name}" 吗？此操作不可恢复。`)) {
        return;
    }
    
    // 执行删除
    performDeletePermission(permissionId);
}

// 执行删除权限
async function performDeletePermission(permissionId) {
    try {
        const response = await fetch(`/api/admin/permissions/${permissionId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('删除失败');
        }
        
        showMessage('权限删除成功', 'success');
        
        // 重新加载权限列表
        if (typeof loadManagePermissionsData === 'function') {
            loadManagePermissionsData();
        }
    } catch (error) {
        console.error('删除权限失败:', error);
        showMessage(`删除权限失败: ${error.message}`, 'error');
    }
}