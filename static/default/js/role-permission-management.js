/**
 * 角色权限管理系统 - 重构版本
 * 实现用户、角色、权限的完整管理功能
 */

class RolePermissionManager {
    constructor() {
        // 当前状态
        this.currentTab = 'users';
        this.data = {
            users: [],
            roles: [],
            permissions: [],
            auditLogs: [],
            stats: {
                totalUsers: 0,
                totalRoles: 0,
                totalPermissions: 0,
                activeUsers: 0
            }
        };
        
        // 分页配置
        this.pagination = {
            currentPage: 1,
            pageSize: 20,
            total: 0
        };

        // 编辑状态
        this.editing = {
            user: null,
            role: null,
            permission: null
        };

        this.init();
    }

    /**
     * 初始化管理器
     */
    async init() {
        this.bindEvents();
        await this.loadInitialData();
        this.updateStats();
    }

    /**
     * 绑定所有事件
     */
    bindEvents() {
        // 标签页切换
        this.bindTabEvents();
        
        // 搜索功能
        this.bindSearchEvents();
        
        // 按钮事件
        this.bindButtonEvents();
        
        // 表单事件
        this.bindFormEvents();
        
        // 抽屉菜单
        this.bindDrawerEvents();
        
        // 模态框事件
        this.bindModalEvents();
    }

    /**
     * 绑定标签页事件
     */
    bindTabEvents() {
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const tab = e.currentTarget.getAttribute('data-tab');
                this.switchTab(tab);
            });
        });
    }

    /**
     * 绑定搜索事件
     */
    bindSearchEvents() {
        // 用户搜索
        const userSearch = document.getElementById('user-search');
        if (userSearch) {
            userSearch.addEventListener('input', debounce(() => {
                this.searchUsers(userSearch.value);
            }, 300));
        }

        // 角色搜索
        const roleSearch = document.getElementById('role-search');
        if (roleSearch) {
            roleSearch.addEventListener('input', debounce(() => {
                this.searchRoles(roleSearch.value);
            }, 300));
        }

        // 权限搜索
        const permissionSearch = document.getElementById('permission-search');
        if (permissionSearch) {
            permissionSearch.addEventListener('input', debounce(() => {
                this.searchPermissions(permissionSearch.value);
            }, 300));
        }

        // 审计日志搜索
        const auditSearch = document.getElementById('audit-search');
        if (auditSearch) {
            auditSearch.addEventListener('input', debounce(() => {
                this.searchAuditLogs(auditSearch.value);
            }, 300));
        }
    }

    /**
     * 绑定按钮事件
     */
    bindButtonEvents() {
        // 返回按钮
        const backBtn = document.getElementById('back-to-admin');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                window.location.href = '/admin';
            });
        }

        // 创建按钮
        this.bindCreateButtons();
        
        // 刷新按钮
        this.bindRefreshButtons();
        
        // 批量操作按钮
        this.bindBatchButtons();
        
        // 分配按钮
        this.bindAssignmentButtons();
    }

    /**
     * 绑定创建按钮
     */
    bindCreateButtons() {
        // 创建用户
        const createUserBtn = document.getElementById('create-user-btn');
        if (createUserBtn) {
            createUserBtn.addEventListener('click', () => this.showCreateUserModal());
        }

        // 创建角色
        const createRoleBtn = document.getElementById('create-role-btn');
        if (createRoleBtn) {
            createRoleBtn.addEventListener('click', () => this.showCreateRoleModal());
        }

        // 创建权限
        const createPermissionBtn = document.getElementById('create-permission-btn');
        if (createPermissionBtn) {
            createPermissionBtn.addEventListener('click', () => this.showCreatePermissionModal());
        }
    }

    /**
     * 绑定刷新按钮
     */
    bindRefreshButtons() {
        const refreshButtons = [
            { id: 'refresh-users-btn', action: () => this.loadUsers() },
            { id: 'refresh-roles-btn', action: () => this.loadRoles() },
            { id: 'refresh-permissions-btn', action: () => this.loadPermissions() },
            { id: 'refresh-audit-btn', action: () => this.loadAuditLogs() }
        ];

        refreshButtons.forEach(({id, action}) => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.addEventListener('click', action);
            }
        });
    }

    /**
     * 绑定批量操作按钮
     */
    bindBatchButtons() {
        const batchAssignBtn = document.getElementById('batch-assign-btn');
        if (batchAssignBtn) {
            batchAssignBtn.addEventListener('click', () => this.handleBatchAssign());
        }

        const batchRemoveBtn = document.getElementById('batch-remove-btn');
        if (batchRemoveBtn) {
            batchRemoveBtn.addEventListener('click', () => this.handleBatchRemove());
        }
    }

    /**
     * 绑定分配按钮
     */
    bindAssignmentButtons() {
        // 保存用户角色
        const saveUserRolesBtn = document.getElementById('save-user-roles-btn');
        if (saveUserRolesBtn) {
            saveUserRolesBtn.addEventListener('click', () => this.saveUserRoles());
        }

        // 保存角色权限
        const saveRolePermissionsBtn = document.getElementById('save-role-permissions-btn');
        if (saveRolePermissionsBtn) {
            saveRolePermissionsBtn.addEventListener('click', () => this.saveRolePermissions());
        }

        // 分配选择器变化
        const assignmentUserSelect = document.getElementById('assignment-user-select');
        if (assignmentUserSelect) {
            assignmentUserSelect.addEventListener('change', () => this.onUserSelectionChange());
        }

        const assignmentRoleSelect = document.getElementById('assignment-role-select');
        if (assignmentRoleSelect) {
            assignmentRoleSelect.addEventListener('change', () => this.onRoleSelectionChange());
        }

        const batchRoleSelect = document.getElementById('batch-role-select');
        if (batchRoleSelect) {
            batchRoleSelect.addEventListener('change', () => this.onBatchRoleSelectionChange());
        }
    }

    /**
     * 绑定表单事件
     */
    bindFormEvents() {
        // 全选复选框
        const selectAllUsers = document.getElementById('select-all-users');
        if (selectAllUsers) {
            selectAllUsers.addEventListener('change', (e) => {
                this.toggleSelectAllUsers(e.target.checked);
            });
        }

        // 审计过滤器
        const auditFilter = document.getElementById('audit-filter');
        if (auditFilter) {
            auditFilter.addEventListener('change', () => {
                this.filterAuditLogs(auditFilter.value);
            });
        }
    }

    /**
     * 绑定抽屉菜单事件
     */
    bindDrawerEvents() {
        const adminMenuBtn = document.getElementById('admin-menu-btn');
        const drawer = document.getElementById('admin-drawer');
        const overlay = document.getElementById('drawer-overlay');
        const closeBtn = document.getElementById('close-drawer-btn');

        if (adminMenuBtn && drawer && overlay) {
            adminMenuBtn.addEventListener('click', () => {
                drawer.classList.add('open');
                overlay.classList.add('active');
            });

            closeBtn?.addEventListener('click', () => {
                drawer.classList.remove('open');
                overlay.classList.remove('active');
            });

            overlay.addEventListener('click', () => {
                drawer.classList.remove('open');
                overlay.classList.remove('active');
            });
        }
    }

    /**
     * 绑定模态框事件
     */
    bindModalEvents() {
        // 点击外部关闭模态框
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal(e.target);
            }
        });
    }

    /**
     * 切换标签页
     */
    switchTab(tabName) {
        // 更新导航状态
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // 更新内容显示
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        this.currentTab = tabName;

        // 加载对应数据
        this.loadTabData(tabName);
    }

    /**
     * 加载标签页数据
     */
    async loadTabData(tabName) {
        switch (tabName) {
            case 'users':
                await this.loadUsers();
                break;
            case 'roles':
                await this.loadRoles();
                break;
            case 'permissions':
                await this.loadPermissions();
                break;
            case 'assignments':
                await this.loadAssignments();
                break;
            case 'batch':
                await this.loadBatchData();
                break;
            case 'audit':
                await this.loadAuditLogs();
                break;
        }
    }

    /**
     * 加载初始数据
     */
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadUsers(),
                this.loadRoles(),
                this.loadPermissions()
            ]);
        } catch (error) {
            console.error('加载初始数据失败:', error);
            this.showMessage('加载数据失败，请刷新页面重试', 'error');
        }
    }

    /**
     * 加载用户数据
     */
    async loadUsers() {
        try {
            const response = await fetch('/api/admin/users');
            const result = await response.json();
            
            if (response.ok) {
                this.data.users = result.users || [];
                this.renderUsersTable();
                this.updateStats();
            } else {
                throw new Error(result.detail || '获取用户列表失败');
            }
        } catch (error) {
            console.error('加载用户失败:', error);
            this.showMessage('加载用户数据失败', 'error');
        }
    }

    /**
     * 加载角色数据
     */
    async loadRoles() {
        try {
            const response = await fetch('/api/admin/roles');
            const result = await response.json();
            
            if (response.ok) {
                this.data.roles = result.roles || [];
                this.renderRolesTable();
                this.updateRoleSelectors();
                this.updateStats();
            } else {
                throw new Error(result.detail || '获取角色列表失败');
            }
        } catch (error) {
            console.error('加载角色失败:', error);
            this.showMessage('加载角色数据失败', 'error');
        }
    }

    /**
     * 加载权限数据
     */
    async loadPermissions() {
        try {
            const response = await fetch('/api/admin/permissions');
            const result = await response.json();
            
            if (response.ok) {
                this.data.permissions = result.permissions || [];
                this.renderPermissionsTable();
                this.updateStats();
            } else {
                throw new Error(result.detail || '获取权限列表失败');
            }
        } catch (error) {
            console.error('加载权限失败:', error);
            this.showMessage('加载权限数据失败', 'error');
        }
    }

    /**
     * 加载分配数据
     */
    async loadAssignments() {
        await this.updateUserSelector();
        await this.updateRoleSelectors();
    }

    /**
     * 加载批量操作数据
     */
    async loadBatchData() {
        await this.updateRoleSelectors();
    }

    /**
     * 加载审计日志
     */
    async loadAuditLogs() {
        try {
            const response = await fetch('/api/admin/audit-log/permissions');
            const result = await response.json();
            
            if (response.ok) {
                this.data.auditLogs = result.logs || [];
                this.renderAuditLogsTable();
            } else {
                throw new Error(result.detail || '获取审计日志失败');
            }
        } catch (error) {
            console.error('加载审计日志失败:', error);
            this.showMessage('加载审计日志失败', 'error');
        }
    }

    /**
     * 渲染用户表格
     */
    renderUsersTable() {
        const tbody = document.getElementById('users-table-body');
        if (!tbody) return;

        if (this.data.users.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">
                        <div>暂无用户数据</div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.data.users.map(user => `
            <tr>
                <td><input type="checkbox" class="user-checkbox" data-user-id="${user.id}"></td>
                <td>${escapeHtml(user.username)}</td>
                <td>
                    <div class="roles-tags">
                        ${(user.roles || []).map(role => 
                            `<span class="role-tag">${escapeHtml(role.name)}</span>`
                        ).join('')}
                    </div>
                </td>
                <td>
                    <span class="status-badge ${user.is_active ? 'status-active' : 'status-inactive'}">
                        ${user.is_active ? '活跃' : '非活跃'}
                    </span>
                </td>
                <td>${user.last_login ? formatDateTime(user.last_login) : '从未登录'}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-primary" onclick="rolePermissionManager.editUser(${user.id})">
                            编辑
                        </button>
                        <button class="btn btn-sm btn-warning" onclick="rolePermissionManager.manageUserRoles(${user.id})">
                            角色
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="rolePermissionManager.deleteUser(${user.id})">
                            删除
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        this.updateUserSelector();
    }

    /**
     * 渲染角色表格
     */
    renderRolesTable() {
        const tbody = document.getElementById('roles-table-body');
        if (!tbody) return;

        if (this.data.roles.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-state">
                        <div>暂无角色数据</div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.data.roles.map(role => `
            <tr>
                <td>${escapeHtml(role.name)}</td>
                <td>${escapeHtml(role.description || '')}</td>
                <td>${role.permission_count || 0}</td>
                <td>${role.user_count || 0}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-primary" onclick="rolePermissionManager.editRole(${role.id})">
                            编辑
                        </button>
                        <button class="btn btn-sm btn-warning" onclick="rolePermissionManager.manageRolePermissions(${role.id})">
                            权限
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="rolePermissionManager.deleteRole(${role.id})">
                            删除
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    /**
     * 渲染权限表格
     */
    renderPermissionsTable() {
        const tbody = document.getElementById('permissions-table-body');
        if (!tbody) return;

        if (this.data.permissions.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-state">
                        <div>暂无权限数据</div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.data.permissions.map(permission => `
            <tr>
                <td>${escapeHtml(permission.name)}</td>
                <td>${escapeHtml(permission.description || '')}</td>
                <td>${this.getPermissionGroup(permission.name)}</td>
                <td>${permission.role_count || 0}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-primary" onclick="rolePermissionManager.editPermission(${permission.id})">
                            编辑
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="rolePermissionManager.deletePermission(${permission.id})">
                            删除
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    /**
     * 渲染审计日志表格
     */
    renderAuditLogsTable() {
        const tbody = document.getElementById('audit-table-body');
        if (!tbody) return;

        if (this.data.auditLogs.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-state">
                        <div>暂无审计日志</div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.data.auditLogs.map(log => `
            <tr>
                <td>${formatDateTime(log.timestamp)}</td>
                <td>${escapeHtml(log.operator)}</td>
                <td>
                    <span class="operation-badge operation-${log.operation}">
                        ${this.getOperationText(log.operation)}
                    </span>
                </td>
                <td>${escapeHtml(log.target_object)}</td>
                <td>${escapeHtml(log.description)}</td>
            </tr>
        `).join('');
    }

    /**
     * 更新统计信息
     */
    updateStats() {
        this.data.stats.totalUsers = this.data.users.length;
        this.data.stats.totalRoles = this.data.roles.length;
        this.data.stats.totalPermissions = this.data.permissions.length;
        this.data.stats.activeUsers = this.data.users.filter(u => u.is_active).length;

        // 更新DOM
        const elements = {
            'total-users': this.data.stats.totalUsers,
            'total-roles': this.data.stats.totalRoles,
            'total-permissions': this.data.stats.totalPermissions,
            'active-users': this.data.stats.activeUsers
        };

        Object.entries(elements).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        });
    }

    /**
     * 更新用户选择器
     */
    updateUserSelector() {
        const selector = document.getElementById('assignment-user-select');
        if (!selector) return;

        selector.innerHTML = '<option value="">请选择用户</option>' +
            this.data.users.map(user => 
                `<option value="${user.id}">${escapeHtml(user.username)}</option>`
            ).join('');
    }

    /**
     * 更新角色选择器
     */
    updateRoleSelectors() {
        const selectors = [
            'assignment-role-select',
            'batch-role-select'
        ];

        selectors.forEach(id => {
            const selector = document.getElementById(id);
            if (selector) {
                selector.innerHTML = '<option value="">请选择角色</option>' +
                    this.data.roles.map(role => 
                        `<option value="${role.id}">${escapeHtml(role.name)}</option>`
                    ).join('');
            }
        });
    }

    // ===== 模态框相关方法 =====

    /**
     * 显示创建用户模态框
     */
    showCreateUserModal() {
        this.showModal('创建用户', this.getUserFormHTML(), () => this.handleCreateUser());
    }

    /**
     * 显示创建角色模态框
     */
    showCreateRoleModal() {
        this.showModal('创建角色', this.getRoleFormHTML(), () => this.handleCreateRole());
    }

    /**
     * 显示创建权限模态框
     */
    showCreatePermissionModal() {
        this.showModal('创建权限', this.getPermissionFormHTML(), () => this.handleCreatePermission());
    }

    /**
     * 获取用户表单HTML
     */
    getUserFormHTML(user = null) {
        return `
            <form id="user-form">
                <div class="form-group">
                    <label class="form-label">用户名 *</label>
                    <input type="text" class="form-input" name="username" value="${user?.username || ''}" required>
                </div>
                <div class="form-group">
                    <label class="form-label">密码 ${user ? '' : '*'}</label>
                    <input type="password" class="form-input" name="password" ${user ? '' : 'required'}>
                    ${user ? '<small>留空则不修改密码</small>' : ''}
                </div>
                <div class="form-group">
                    <label class="form-label">邮箱</label>
                    <input type="email" class="form-input" name="email" value="${user?.email || ''}">
                </div>
                <div class="form-group">
                    <label class="form-label">状态</label>
                    <select class="form-select" name="is_active">
                        <option value="true" ${user?.is_active !== false ? 'selected' : ''}>活跃</option>
                        <option value="false" ${user?.is_active === false ? 'selected' : ''}>非活跃</option>
                    </select>
                </div>
            </form>
        `;
    }

    /**
     * 获取角色表单HTML
     */
    getRoleFormHTML(role = null) {
        return `
            <form id="role-form">
                <div class="form-group">
                    <label class="form-label">角色名称 *</label>
                    <input type="text" class="form-input" name="name" value="${role?.name || ''}" required>
                </div>
                <div class="form-group">
                    <label class="form-label">描述</label>
                    <textarea class="form-textarea" name="description" rows="3">${role?.description || ''}</textarea>
                </div>
            </form>
        `;
    }

    /**
     * 获取权限表单HTML
     */
    getPermissionFormHTML(permission = null) {
        return `
            <form id="permission-form">
                <div class="form-group">
                    <label class="form-label">权限名称 *</label>
                    <input type="text" class="form-input" name="name" value="${permission?.name || ''}" required>
                </div>
                <div class="form-group">
                    <label class="form-label">描述</label>
                    <textarea class="form-textarea" name="description" rows="3">${permission?.description || ''}</textarea>
                </div>
            </form>
        `;
    }

    /**
     * 显示通用模态框
     */
    showModal(title, content, onSave) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3 class="modal-title">${title}</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary modal-cancel">取消</button>
                    <button class="btn btn-primary modal-save">保存</button>
                </div>
            </div>
        `;

        // 绑定事件
        modal.querySelector('.modal-close').addEventListener('click', () => this.closeModal(modal));
        modal.querySelector('.modal-cancel').addEventListener('click', () => this.closeModal(modal));
        modal.querySelector('.modal-save').addEventListener('click', () => {
            onSave();
            this.closeModal(modal);
        });

        document.body.appendChild(modal);
        modal.style.display = 'block';
    }

    /**
     * 关闭模态框
     */
    closeModal(modal) {
        if (modal) {
            modal.style.display = 'none';
            setTimeout(() => {
                if (modal.parentNode) {
                    modal.parentNode.removeChild(modal);
                }
            }, 300);
        }
    }

    // ===== 工具方法 =====

    /**
     * 获取权限分组
     */
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
        return '其他';
    }

    /**
     * 获取操作类型文本
     */
    getOperationText(operation) {
        const texts = {
            'create': '创建',
            'update': '更新',
            'delete': '删除',
            'assign': '分配',
            'remove': '移除'
        };
        return texts[operation] || operation;
    }

    /**
     * 显示消息
     */
    showMessage(message, type = 'info') {
        // 这里可以实现消息提示功能
        console.log(`[${type.toUpperCase()}] ${message}`);
        
        // 简单的alert实现，可以后续改为更美观的提示组件
        if (type === 'error') {
            alert(`错误: ${message}`);
        } else if (type === 'success') {
            alert(`成功: ${message}`);
        } else {
            alert(message);
        }
    }

    // ===== 用户管理方法 =====

    /**
     * 处理创建用户
     */
    async handleCreateUser() {
        const form = document.getElementById('user-form');
        const formData = new FormData(form);
        
        try {
            const response = await fetch('/api/admin/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: formData.get('username'),
                    password: formData.get('password'),
                    email: formData.get('email'),
                    is_active: formData.get('is_active') === 'true'
                })
            });
            
            const result = await response.json();
            if (response.ok) {
                this.showMessage('用户创建成功', 'success');
                await this.loadUsers();
            } else {
                throw new Error(result.detail || '创建用户失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    /**
     * 编辑用户
     */
    async editUser(userId) {
        const user = this.data.users.find(u => u.id === userId);
        if (!user) return;
        
        this.editing.user = user;
        this.showModal('编辑用户', this.getUserFormHTML(user), () => this.handleUpdateUser());
    }

    /**
     * 处理更新用户
     */
    async handleUpdateUser() {
        const form = document.getElementById('user-form');
        const formData = new FormData(form);
        const userId = this.editing.user.id;
        
        try {
            const updateData = {
                username: formData.get('username'),
                email: formData.get('email'),
                is_active: formData.get('is_active') === 'true'
            };
            
            const password = formData.get('password');
            if (password) {
                updateData.password = password;
            }
            
            const response = await fetch(`/api/admin/users/${userId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updateData)
            });
            
            const result = await response.json();
            if (response.ok) {
                this.showMessage('用户更新成功', 'success');
                await this.loadUsers();
            } else {
                throw new Error(result.detail || '更新用户失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    /**
     * 删除用户
     */
    async deleteUser(userId) {
        if (!confirm('确定要删除这个用户吗？此操作不可撤销。')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/admin/user/${userId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            if (response.ok) {
                this.showMessage('用户删除成功', 'success');
                await this.loadUsers();
            } else {
                throw new Error(result.detail || '删除用户失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    // ===== 角色管理方法 =====

    /**
     * 处理创建角色
     */
    async handleCreateRole() {
        const form = document.getElementById('role-form');
        const formData = new FormData(form);
        
        try {
            const response = await fetch('/api/admin/roles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: formData.get('name'),
                    description: formData.get('description')
                })
            });
            
            const result = await response.json();
            if (response.ok) {
                this.showMessage('角色创建成功', 'success');
                await this.loadRoles();
            } else {
                throw new Error(result.detail || '创建角色失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    /**
     * 编辑角色
     */
    async editRole(roleId) {
        const role = this.data.roles.find(r => r.id === roleId);
        if (!role) return;
        
        this.editing.role = role;
        this.showModal('编辑角色', this.getRoleFormHTML(role), () => this.handleUpdateRole());
    }

    /**
     * 处理更新角色
     */
    async handleUpdateRole() {
        const form = document.getElementById('role-form');
        const formData = new FormData(form);
        const roleId = this.editing.role.id;
        
        try {
            const response = await fetch(`/api/admin/roles/${roleId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: formData.get('name'),
                    description: formData.get('description')
                })
            });
            
            const result = await response.json();
            if (response.ok) {
                this.showMessage('角色更新成功', 'success');
                await this.loadRoles();
            } else {
                throw new Error(result.detail || '更新角色失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    /**
     * 删除角色
     */
    async deleteRole(roleId) {
        if (!confirm('确定要删除这个角色吗？此操作将移除所有用户的该角色。')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/admin/roles/${roleId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            if (response.ok) {
                this.showMessage('角色删除成功', 'success');
                await this.loadRoles();
            } else {
                throw new Error(result.detail || '删除角色失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    // ===== 权限管理方法 =====

    /**
     * 处理创建权限
     */
    async handleCreatePermission() {
        const form = document.getElementById('permission-form');
        const formData = new FormData(form);
        
        try {
            const response = await fetch('/api/admin/permissions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: formData.get('name'),
                    description: formData.get('description')
                })
            });
            
            const result = await response.json();
            if (response.ok) {
                this.showMessage('权限创建成功', 'success');
                await this.loadPermissions();
            } else {
                throw new Error(result.detail || '创建权限失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    /**
     * 编辑权限
     */
    async editPermission(permissionId) {
        const permission = this.data.permissions.find(p => p.id === permissionId);
        if (!permission) return;
        
        this.editing.permission = permission;
        this.showModal('编辑权限', this.getPermissionFormHTML(permission), () => this.handleUpdatePermission());
    }

    /**
     * 处理更新权限
     */
    async handleUpdatePermission() {
        const form = document.getElementById('permission-form');
        const formData = new FormData(form);
        const permissionId = this.editing.permission.id;
        
        try {
            const response = await fetch(`/api/admin/permissions/${permissionId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: formData.get('name'),
                    description: formData.get('description')
                })
            });
            
            const result = await response.json();
            if (response.ok) {
                this.showMessage('权限更新成功', 'success');
                await this.loadPermissions();
            } else {
                throw new Error(result.detail || '更新权限失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    /**
     * 删除权限
     */
    async deletePermission(permissionId) {
        if (!confirm('确定要删除这个权限吗？此操作将从所有角色中移除该权限。')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/admin/permissions/${permissionId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            if (response.ok) {
                this.showMessage('权限删除成功', 'success');
                await this.loadPermissions();
            } else {
                throw new Error(result.detail || '删除权限失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    // ===== 分配管理方法 =====

    /**
     * 用户选择变化
     */
    async onUserSelectionChange() {
        const userSelect = document.getElementById('assignment-user-select');
        const userId = userSelect.value;
        
        if (!userId) {
            document.getElementById('user-current-roles').innerHTML = '请先选择用户';
            document.getElementById('user-available-roles').innerHTML = '请先选择用户';
            return;
        }
        
        await this.loadUserRoles(userId);
    }

    /**
     * 角色选择变化
     */
    async onRoleSelectionChange() {
        const roleSelect = document.getElementById('assignment-role-select');
        const roleId = roleSelect.value;
        
        if (!roleId) {
            document.getElementById('role-permissions-container').innerHTML = '请先选择角色';
            return;
        }
        
        await this.loadRolePermissions(roleId);
    }

    /**
     * 批量角色选择变化
     */
    async onBatchRoleSelectionChange() {
        const roleSelect = document.getElementById('batch-role-select');
        const roleId = roleSelect.value;
        
        if (!roleId) {
            document.getElementById('batch-users-container').innerHTML = '请先选择角色';
            return;
        }
        
        await this.loadBatchUsers(roleId);
    }

    /**
     * 加载用户角色
     */
    async loadUserRoles(userId) {
        try {
            const response = await fetch(`/api/admin/users/${userId}/roles`);
            const result = await response.json();
            
            if (response.ok) {
                this.renderUserRoles(result.roles || []);
            } else {
                throw new Error(result.detail || '获取用户角色失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    /**
     * 加载角色权限
     */
    async loadRolePermissions(roleId) {
        try {
            const response = await fetch(`/api/admin/roles/${roleId}/permissions`);
            const result = await response.json();
            
            if (response.ok) {
                this.renderRolePermissions(result.permissions || []);
            } else {
                throw new Error(result.detail || '获取角色权限失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    /**
     * 渲染用户角色
     */
    renderUserRoles(userRoles) {
        const currentRolesContainer = document.getElementById('user-current-roles');
        const availableRolesContainer = document.getElementById('user-available-roles');
        
        // 当前角色
        if (userRoles.length === 0) {
            currentRolesContainer.innerHTML = '<div class="empty-state">该用户暂无角色</div>';
        } else {
            currentRolesContainer.innerHTML = userRoles.map(role => `
                <div class="role-item">
                    <span>${escapeHtml(role.name)}</span>
                    <button class="btn btn-sm btn-danger" onclick="rolePermissionManager.removeUserRole(${role.user_id}, '${role.name}')">
                        移除
                    </button>
                </div>
            `).join('');
        }
        
        // 可用角色
        const assignedRoleIds = userRoles.map(r => r.id);
        const availableRoles = this.data.roles.filter(r => !assignedRoleIds.includes(r.id));
        
        if (availableRoles.length === 0) {
            availableRolesContainer.innerHTML = '<div class="empty-state">没有可分配的角色</div>';
        } else {
            availableRolesContainer.innerHTML = availableRoles.map(role => `
                <div class="checkbox-item">
                    <input type="checkbox" id="role-${role.id}" value="${role.id}" class="available-role-checkbox">
                    <label for="role-${role.id}">${escapeHtml(role.name)}</label>
                </div>
            `).join('');
        }
    }

    /**
     * 渲染角色权限
     */
    renderRolePermissions(rolePermissions) {
        const container = document.getElementById('role-permissions-container');
        const assignedPermissionIds = rolePermissions.map(p => p.id);
        
        // 按分组显示权限
        const groups = {};
        this.data.permissions.forEach(permission => {
            const group = this.getPermissionGroup(permission.name);
            if (!groups[group]) groups[group] = [];
            groups[group].push(permission);
        });
        
        container.innerHTML = Object.entries(groups).map(([group, permissions]) => `
            <div class="permission-group">
                <div class="permission-group-header">${group}</div>
                <div class="permission-items">
                    ${permissions.map(permission => `
                        <div class="permission-item">
                            <input type="checkbox" 
                                   id="permission-${permission.id}" 
                                   value="${permission.id}" 
                                   class="role-permission-checkbox"
                                   ${assignedPermissionIds.includes(permission.id) ? 'checked' : ''}>
                            <div class="permission-info">
                                <div class="permission-name">${escapeHtml(permission.name)}</div>
                                <div class="permission-desc">${escapeHtml(permission.description || '')}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
    }

    // ===== 搜索功能 =====

    /**
     * 搜索用户
     */
    searchUsers(query) {
        // 实现用户搜索逻辑
        console.log('搜索用户:', query);
    }

    /**
     * 搜索角色
     */
    searchRoles(query) {
        // 实现角色搜索逻辑
        console.log('搜索角色:', query);
    }

    /**
     * 搜索权限
     */
    searchPermissions(query) {
        // 实现权限搜索逻辑
        console.log('搜索权限:', query);
    }

    /**
     * 搜索审计日志
     */
    searchAuditLogs(query) {
        // 实现审计日志搜索逻辑
        console.log('搜索审计日志:', query);
    }

    /**
     * 过滤审计日志
     */
    filterAuditLogs(operation) {
        // 实现审计日志过滤逻辑
        console.log('过滤审计日志:', operation);
    }

    /**
     * 切换全选用户
     */
    toggleSelectAllUsers(checked) {
        document.querySelectorAll('.user-checkbox').forEach(checkbox => {
            checkbox.checked = checked;
        });
    }

    /**
     * 处理批量分配
     */
    async handleBatchAssign() {
        const roleId = document.getElementById('batch-role-select').value;
        const userIds = Array.from(document.querySelectorAll('.batch-user-checkbox:checked'))
            .map(cb => parseInt(cb.value));
        
        if (!roleId || userIds.length === 0) {
            this.showMessage('请选择角色和用户', 'error');
            return;
        }
        
        try {
            const response = await fetch('/api/admin/batch-assign-role', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ role_id: parseInt(roleId), user_ids: userIds })
            });
            
            const result = await response.json();
            if (response.ok) {
                this.showMessage('批量分配成功', 'success');
                await this.loadUsers();
            } else {
                throw new Error(result.detail || '批量分配失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    /**
     * 处理批量移除
     */
    async handleBatchRemove() {
        const roleId = document.getElementById('batch-role-select').value;
        const userIds = Array.from(document.querySelectorAll('.batch-user-checkbox:checked'))
            .map(cb => parseInt(cb.value));
        
        if (!roleId || userIds.length === 0) {
            this.showMessage('请选择角色和用户', 'error');
            return;
        }
        
        try {
            const response = await fetch('/api/admin/batch-remove-role', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ role_id: parseInt(roleId), user_ids: userIds })
            });
            
            const result = await response.json();
            if (response.ok) {
                this.showMessage('批量移除成功', 'success');
                await this.loadUsers();
            } else {
                throw new Error(result.detail || '批量移除失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    /**
     * 保存用户角色
     */
    async saveUserRoles() {
        const userId = document.getElementById('assignment-user-select').value;
        const selectedRoleIds = Array.from(document.querySelectorAll('.available-role-checkbox:checked'))
            .map(cb => parseInt(cb.value));
        
        if (!userId) {
            this.showMessage('请选择用户', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/admin/users/${userId}/roles`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ role_ids: selectedRoleIds })
            });
            
            const result = await response.json();
            if (response.ok) {
                this.showMessage('用户角色保存成功', 'success');
                await this.loadUserRoles(userId);
                await this.loadUsers();
            } else {
                throw new Error(result.detail || '保存用户角色失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    /**
     * 保存角色权限
     */
    async saveRolePermissions() {
        const roleId = document.getElementById('assignment-role-select').value;
        const selectedPermissionIds = Array.from(document.querySelectorAll('.role-permission-checkbox:checked'))
            .map(cb => parseInt(cb.value));
        
        if (!roleId) {
            this.showMessage('请选择角色', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/admin/roles/${roleId}/permissions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ permission_ids: selectedPermissionIds })
            });
            
            const result = await response.json();
            if (response.ok) {
                this.showMessage('角色权限保存成功', 'success');
                await this.loadRolePermissions(roleId);
                await this.loadRoles();
            } else {
                throw new Error(result.detail || '保存角色权限失败');
            }
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }
}

// 工具函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDateTime(dateTime) {
    if (!dateTime) return '';
    const date = new Date(dateTime);
    return date.toLocaleString('zh-CN');
}

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

// 初始化
let rolePermissionManager;
document.addEventListener('DOMContentLoaded', () => {
    rolePermissionManager = new RolePermissionManager();
});