/**
 * 角色权限管理JavaScript功能
 */

class RolePermissionManager {
    constructor() {
        this.currentTab = 'users';
        this.currentEditingUser = null;
        this.currentEditingRole = null;
        this.currentEditingPermission = null;
        this.users = [];
        this.roles = [];
        this.permissions = [];
        this.permissionGroups = {};
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadInitialData();
    }
    
    bindEvents() {
        // 标签页切换
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                this.switchTab(e.target.getAttribute('data-tab'));
            });
        });
        
        // 返回管理面板
        document.getElementById('back-to-admin').addEventListener('click', () => {
            window.location.href = '/admin';
        });
        
        // 抽屉菜单
        this.bindDrawerEvents();
        
        // 模态框关闭事件
        this.bindModalEvents();
        
        // 表单提交事件
        this.bindFormEvents();
        
        // 按钮点击事件
        this.bindButtonEvents();
    }
    
    bindDrawerEvents() {
        const adminMenuBtn = document.getElementById('admin-menu-btn');
        const drawer = document.getElementById('admin-drawer');
        const overlay = document.getElementById('drawer-overlay');
        const closeBtn = document.getElementById('close-drawer-btn');
        
        if (adminMenuBtn) {
            adminMenuBtn.addEventListener('click', () => {
                drawer.classList.add('open');
                overlay.classList.add('active');
            });
        }
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                drawer.classList.remove('open');
                overlay.classList.remove('active');
            });
        }
        
        if (overlay) {
            overlay.addEventListener('click', () => {
                drawer.classList.remove('open');
                overlay.classList.remove('active');
            });
        }
    }
    
    bindModalEvents() {
        // 用户模态框
        document.getElementById('user-modal-close').addEventListener('click', () => {
            this.closeModal('user-modal');
        });
        document.getElementById('user-modal-cancel').addEventListener('click', () => {
            this.closeModal('user-modal');
        });
        
        // 角色模态框
        document.getElementById('role-modal-close').addEventListener('click', () => {
            this.closeModal('role-modal');
        });
        document.getElementById('role-modal-cancel').addEventListener('click', () => {
            this.closeModal('role-modal');
        });
        
        // 权限模态框
        document.getElementById('permission-modal-close').addEventListener('click', () => {
            this.closeModal('permission-modal');
        });
        document.getElementById('permission-modal-cancel').addEventListener('click', () => {
            this.closeModal('permission-modal');
        });
        
        // 点击模态框外部关闭
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.style.display = 'none';
            }
        });
    }
    
    bindFormEvents() {
        // 用户表单提交
        document.getElementById('user-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleUserFormSubmit();
        });
        
        // 角色表单提交
        document.getElementById('role-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRoleFormSubmit();
        });
        
        // 权限表单提交
        document.getElementById('permission-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handlePermissionFormSubmit();
        });
    }
    
    bindButtonEvents() {
        // 创建按钮
        document.getElementById('create-user-btn').addEventListener('click', () => {
            this.showCreateUserModal();
        });
        document.getElementById('create-role-btn').addEventListener('click', () => {
            this.showCreateRoleModal();
        });
        document.getElementById('create-permission-btn').addEventListener('click', () => {
            this.showCreatePermissionModal();
        });
        
        // 初始化默认角色
        document.getElementById('init-default-roles-btn').addEventListener('click', () => {
            this.initializeDefaultRoles();
        });
        
        // 批量操作
        document.getElementById('batch-assign-btn').addEventListener('click', () => {
            this.handleBatchAssign();
        });
        document.getElementById('batch-remove-btn').addEventListener('click', () => {
            this.handleBatchRemove();
        });
    }
    
    switchTab(tabName) {
        // 隐藏所有标签页内容
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        // 移除所有按钮的激活状态
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active');
        });
        
        // 显示选中的标签页
        document.getElementById(tabName + '-tab').classList.add('active');
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        this.currentTab = tabName;
        
        // 根据标签页加载对应数据
        switch (tabName) {
            case 'users':
                this.loadUsers();
                break;
            case 'roles':
                this.loadRoles();
                this.loadRoleHierarchy();
                break;
            case 'permissions':
                this.loadPermissions();
                break;
            case 'assignments':
                this.loadAssignments();
                break;
            case 'batch':
                this.loadBatchData();
                break;
        }
    }
    
    async loadInitialData() {
        await this.loadUsers();
        await this.loadRoles();
        await this.loadPermissions();
    }
    
    // ==========================================
    // 用户管理相关方法
    // ==========================================
    
    async loadUsers() {
        try {
            this.showLoading('users-loading');
            this.hideError('users-error');
            
            const response = await fetch('/api/admin/users', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.users = data.users || [];
                this.renderUsersTable();
                this.hideLoading('users-loading');
                document.getElementById('users-table').style.display = 'table';
            } else {
                throw new Error('获取用户列表失败');
            }
        } catch (error) {
            this.showError('users-error', error.message);
            this.hideLoading('users-loading');
        }
    }
    
    renderUsersTable() {
        const tbody = document.getElementById('users-tbody');
        tbody.innerHTML = '';
        
        this.users.forEach(user => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.user_type || 'user'}</td>
                <td>${user.roles ? user.roles.join(', ') : '无'}</td>
                <td>${user.theme || 'default'}</td>
                <td>${user.created_at ? new Date(user.created_at).toLocaleString() : '未知'}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn-small btn-edit" onclick="rolePermissionManager.editUser(${user.id})">编辑</button>
                        <button class="btn-small btn-assign" onclick="rolePermissionManager.assignUserRoles(${user.id})">分配角色</button>
                        <button class="btn-small btn-delete" onclick="rolePermissionManager.deleteUser(${user.id})">删除</button>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
    }
    
    showCreateUserModal() {
        this.currentEditingUser = null;
        document.getElementById('user-modal-title').textContent = '创建用户';
        document.getElementById('user-form').reset();
        this.loadRolesForUserModal();
        this.showModal('user-modal');
    }
    
    async editUser(userId) {
        const user = this.users.find(u => u.id === userId);
        if (!user) {
            this.showMessage('用户不存在', 'error');
            return;
        }
        
        this.currentEditingUser = user;
        document.getElementById('user-modal-title').textContent = '编辑用户';
        document.getElementById('user-username').value = user.username;
        document.getElementById('user-password').value = '';
        document.getElementById('user-theme').value = user.theme || 'default';
        
        // 加载用户的角色信息
        await this.loadUserRoles(userId);
        await this.loadRolesForUserModal();
        
        this.showModal('user-modal');
    }
    
    // 工具方法
    showModal(modalId) {
        document.getElementById(modalId).style.display = 'block';
    }
    
    closeModal(modalId) {
        document.getElementById(modalId).style.display = 'none';
    }
    
    showLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = 'block';
        }
    }
    
    hideLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = 'none';
        }
    }
    
    showError(elementId, message) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = message;
            element.style.display = 'block';
        }
    }
    
    hideError(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = 'none';
        }
    }
    
    showMessage(message, type = 'info') {
        // 显示临时消息
        const messageDiv = document.createElement('div');
        messageDiv.className = type;
        messageDiv.textContent = message;
        messageDiv.style.position = 'fixed';
        messageDiv.style.top = '20px';
        messageDiv.style.right = '20px';
        messageDiv.style.zIndex = '9999';
        messageDiv.style.padding = '10px 20px';
        messageDiv.style.borderRadius = '5px';
        
        document.body.appendChild(messageDiv);
        
        setTimeout(() => {
            document.body.removeChild(messageDiv);
        }, 3000);
    }
}

// 初始化管理器
let rolePermissionManager;
document.addEventListener('DOMContentLoaded', () => {
    rolePermissionManager = new RolePermissionManager();
});