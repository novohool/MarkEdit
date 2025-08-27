// 管理员面板页面 - Default 主题
// 使用统一的主题加载器，避免代码重复

// 全局变量用于存储权限信息
window.userPermissions = null;
window.permissionFlags = null;
window.currentUser = null;

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', async function() {
    // 使用主题加载器初始化管理员面板页面
    await initThemeLoader('admin_panel');
    
    // 初始化权限信息
    initPermissions();
    
    // 初始化用户权限管理功能
    initUserManagement();
    
    // 初始化统计信息
    initStats();
    
    // 初始化角色权限分配器
    initRoleAssignment();
    
    // 初始化权限分组预览
    initPermissionGroups();
});

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
}

// 初始化统计信息
async function initStats() {
    try {
        const [usersResponse, rolesResponse, permissionsResponse] = await Promise.all([
            fetch('/api/admin/users'),
            fetch('/api/admin/roles'),
            fetch('/api/admin/permissions')
        ]);
        
        const usersData = await usersResponse.json();
        const rolesData = await rolesResponse.json();
        const permissionsData = await permissionsResponse.json();
        
        const users = usersData.users || [];
        const roles = rolesData.roles || [];
        const permissions = permissionsData.permissions || [];
        
        // 计算默认数据数量
        const defaultUsers = users.filter(u => u.is_default).length;
        const defaultRoles = roles.filter(r => r.is_default).length;
        const defaultPermissions = permissions.filter(p => p.is_default).length;
        const defaultDataCount = defaultUsers + defaultRoles + defaultPermissions;
        
        // 更新统计显示
        updateElement('stats-total-users', users.length);
        updateElement('stats-total-roles', roles.length);
        updateElement('stats-total-permissions', permissions.length);
        updateElement('stats-default-items', defaultDataCount);
        
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// 初始化用户权限管理功能
function initUserManagement() {
    // 进入角色权限管理按钮
    const gotoRolePermissionBtn = document.getElementById('goto-role-permission-btn');
    if (gotoRolePermissionBtn) {
        gotoRolePermissionBtn.addEventListener('click', function() {
            window.location.href = '/admin/role-permission';
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

// 初始化角色权限分配器
async function initRoleAssignment() {
    try {
        // 加载用户和角色数据
        const [usersResponse, rolesResponse] = await Promise.all([
            fetch('/api/admin/users'),
            fetch('/api/admin/roles')
        ]);
        
        const usersData = await usersResponse.json();
        const rolesData = await rolesResponse.json();
        
        const users = usersData.users || [];
        const roles = rolesData.roles || [];
        
        // 填充用户选择器
        const userSelect = document.getElementById('admin-user-select');
        if (userSelect) {
            userSelect.innerHTML = '<option value="">请选择用户</option>';
            users.forEach(user => {
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = `${user.username}${user.is_default ? ' (默认)' : ''}`;
                if (user.is_default) {
                    option.style.color = '#f59e0b';
                    option.style.fontWeight = 'bold';
                }
                userSelect.appendChild(option);
            });
            
            // 绑定用户选择事件
            userSelect.addEventListener('change', function() {
                loadUserRoles(this.value, roles);
            });
        }
        
        // 保存用户角色按钮
        const saveRolesBtn = document.getElementById('admin-save-user-roles-btn');
        if (saveRolesBtn) {
            saveRolesBtn.addEventListener('click', function() {
                saveUserRoles();
            });
        }
        
    } catch (error) {
        console.error('Error initializing role assignment:', error);
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
            throw new Error(`HTTP error! status: ${response.status}`);
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

// 加载用户角色
async function loadUserRoles(userId, allRoles) {
    const currentRolesDiv = document.getElementById('admin-user-current-roles');
    const availableRolesDiv = document.getElementById('admin-available-roles');
    
    if (!currentRolesDiv || !availableRolesDiv) return;
    
    if (!userId) {
        currentRolesDiv.innerHTML = '请先选择用户';
        availableRolesDiv.innerHTML = '请先选择用户';
        return;
    }
    
    try {
        // 获取用户当前角色
        const response = await fetch(`/api/admin/users/${userId}/roles`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        const userRoles = data.roles || [];
        
        // 显示当前角色
        if (userRoles.length === 0) {
            currentRolesDiv.innerHTML = '<p>该用户暂无角色</p>';
        } else {
            let html = '<div class="current-roles">';
            userRoles.forEach(role => {
                html += `<span class="role-tag ${role.name === 'super_admin' || role.name === 'admin' ? 'default' : ''}">`;
                html += role.name;
                if (role.name === 'super_admin' || role.name === 'admin') {
                    html += ' (默认)';
                }
                html += '</span>';
            });
            html += '</div>';
            currentRolesDiv.innerHTML = html;
        }
        
        // 显示可用角色
        const userRoleIds = userRoles.map(r => r.id);
        let html = '<div class="available-roles">';
        allRoles.forEach(role => {
            const isAssigned = userRoleIds.includes(role.id);
            const isDefault = role.is_default;
            
            html += `<label class="role-checkbox ${isDefault ? 'default' : ''}">`;
            html += `<input type="checkbox" value="${role.id}" ${isAssigned ? 'checked' : ''}>`;
            html += `<span>${role.name}</span>`;
            if (isDefault) {
                html += ` <span class="default-tag">默认</span>`;
            }
            html += `<small>${role.description}</small>`;
            html += '</label>';
        });
        html += '</div>';
        availableRolesDiv.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading user roles:', error);
        currentRolesDiv.innerHTML = `<p style="color: red;">加载失败：${error.message}</p>`;
        availableRolesDiv.innerHTML = '';
    }
}

// 保存用户角色
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
    
    try {
        const response = await fetch(`/api/admin/users/${userId}/roles`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ role_ids: roleIds })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        showMessage('用户角色分配成功', 'success');
        
        // 刷新用户角色显示
        const allRoles = await fetch('/api/admin/roles').then(r => r.json()).then(d => d.roles);
        loadUserRoles(userId, allRoles);
        
        // 刷新用户列表
        loadAdminUserList();
        
    } catch (error) {
        console.error('Error saving user roles:', error);
        showMessage(`保存失败：${error.message}`, 'error');
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
        showMessage('系统默认数据初始化成功', 'success');
        
        // 刷新页面数据
        await initStats();
        await initRoleAssignment();
        await initPermissionGroups();
        
    } catch (error) {
        console.error('Error initializing system defaults:', error);
        showMessage(`初始化失败：${error.message}`, 'error');
    }
}

// 显示消息
function showMessage(message, type = 'info') {
    // 使用简单的alert，可以后续替换为更好的通知组件
    alert(message);
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