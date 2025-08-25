// MarkEdit 管理员公共函数库
// 包含所有主题共享的管理员功能JavaScript函数

// 全局变量
let chapterConfig = [];
let users = [];

// 根据用户权限设置UI元素显示
function setupPermissionBasedUI() {
    const permissions = window.userPermissions || [];
    
    // 用户管理相关权限
    const hasUserManagement = permissions.includes('user.list') || 
                             permissions.includes('user.create') || 
                             permissions.includes('user.edit') || 
                             permissions.includes('user.delete');
    
    // 角色管理相关权限
    const hasRoleManagement = permissions.includes('role.list') || 
                             permissions.includes('role.create') || 
                             permissions.includes('role.edit') || 
                             permissions.includes('role.delete');
    
    // 权限管理相关权限
    const hasPermissionManagement = permissions.includes('permission.list') || 
                                   permissions.includes('permission.create') || 
                                   permissions.includes('permission.edit') || 
                                   permissions.includes('permission.delete');
    
    // 系统管理相关权限
    const hasSystemManagement = permissions.includes('system.backup') || 
                               permissions.includes('system.config') || 
                               permissions.includes('manual_backup');
    
    // 内容编辑权限
    const hasContentEdit = permissions.includes('content.edit');
    
    // EPUB转换权限
    const hasEpubConversion = permissions.includes('epub_conversion');
    
    // 根据权限显示或隐藏相应的UI元素
    const userManagementSection = document.getElementById('user-management-section');
    if (userManagementSection) {
        userManagementSection.style.display = hasUserManagement ? 'block' : 'none';
    }
    
    const roleManagementSection = document.getElementById('role-management-section');
    if (roleManagementSection) {
        roleManagementSection.style.display = hasRoleManagement ? 'block' : 'none';
    }
    
    const permissionManagementSection = document.getElementById('permission-management-section');
    if (permissionManagementSection) {
        permissionManagementSection.style.display = hasPermissionManagement ? 'block' : 'none';
    }
    
    // 在用户列表中根据权限显示或隐藏按钮
    setTimeout(() => {
        document.querySelectorAll('.btn-edit').forEach(btn => {
            if (!permissions.includes('user.edit')) {
                btn.style.display = 'none';
            }
        });
        
        document.querySelectorAll('.btn-delete-user').forEach(btn => {
            if (!permissions.includes('user.delete')) {
                btn.style.display = 'none';
            }
        });
        
        document.querySelectorAll('.btn-manage-roles').forEach(btn => {
            if (!permissions.includes('user.edit')) {
                btn.style.display = 'none';
            }
        });
    }, 100); // 延迟执行，确保DOM元素已生成
    
    // 在菜单中根据权限显示或隐藏链接
    const adminDrawerLinks = document.querySelectorAll('#admin-drawer a');
    adminDrawerLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && href.includes('user') && !hasUserManagement) {
            link.style.display = 'none';
        }
        if (href && href.includes('role') && !hasRoleManagement) {
            link.style.display = 'none';
        }
        if (href && href.includes('permission') && !hasPermissionManagement) {
            link.style.display = 'none';
        }
        if (href && href.includes('backup') && !hasSystemManagement) {
            link.style.display = 'none';
        }
    });
    
    console.log('根据用户权限设置UI完成，用户权限:', permissions);
}

// 加载配置数据
async function loadConfigData() {
    try {
        // 加载章节配置数据
        const chapterConfigResponse = await fetch('/api/admin/chapter-config');
        const chapterConfigResult = await chapterConfigResponse.json();
        if (chapterConfigResponse.ok) {
            chapterConfig = chapterConfigResult.chapters;
            renderChapterList('chapters', chapterConfig);
        }
    } catch (error) {
        console.error('加载配置数据失败:', error);
        showMessage('加载配置数据失败: ' + error.message, 'error');
    }
    
    // 加载备份文件列表
    loadBackupFiles();
}

// 加载用户数据
async function loadUsers() {
    try {
        const response = await fetch('/api/admin/users');
        const result = await response.json();
        
        if (response.ok) {
            users = result.users;
            renderUserList(users);
        } else {
            throw new Error(result.detail || '获取用户列表失败');
        }
    } catch (error) {
        console.error('加载用户列表失败:', error);
        showMessage('加载用户列表失败: ' + error.message, 'error');
    }
}

// 显示用户角色管理界面函数已移至 /static/common/js/main-shared.js
// 使用统一的 showUserRoles 函数

// 渲染用户角色列表（重定向到统一函数）
function renderUserRolesList(roles) {
    // 调用统一的 renderUserRoles 函数，使用表格模式
    renderUserRoles(roles, { renderMode: 'table' });
}

// 返回用户管理界面
function returnToUserManagement() {
    // 隐藏用户角色管理界面
    document.getElementById('user-roles-section').style.display = 'none';
    
    // 显示其他部分
    document.querySelector('.admin-container').querySelectorAll('.section').forEach(section => {
        section.style.display = 'block';
    });
}

// 渲染用户列表
function renderUserList(users) {
    const userList = document.getElementById('user-list');
    userList.innerHTML = '';
    
    users.forEach(user => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${user.id}</td>
            <td>${user.username}</td>
            <td>${formatDate(user.created_at)}</td>
            <td>${user.login_time ? formatDate(user.login_time) : '从未登录'}</td>
            <td>${user.theme || 'default'}</td>
            <td>
                <button class="btn-action btn-edit" data-id="${user.id}">编辑</button>
                <button class="btn-action btn-reset-password" data-id="${user.id}">重置密码</button>
                <button class="btn-action btn-manage-roles" data-id="${user.id}" data-username="${user.username}">管理角色</button>
                <button class="btn-action btn-delete-user" data-id="${user.id}">删除</button>
            </td>
        `;
        userList.appendChild(row);
    });
    
    // 绑定管理角色按钮事件
    document.querySelectorAll('.btn-manage-roles').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.getAttribute('data-id');
            const username = this.getAttribute('data-username');
            showUserRoles(userId, username);
        });
    });
    
    // 重新设置权限控制
    setupPermissionBasedUI();
}

// 初始化管理员页面的权限检查和数据加载
function initializeAdminPage() {
    // 首先检查用户角色和权限
    fetch('/api/admin/role-info')
        .then(response => response.json())
        .then(roleData => {
            // 检查用户是否有管理员权限
            const hasAdminPermission = roleData.info && 
                                     roleData.info.permissions && 
                                     roleData.info.permissions.includes('admin_access');
            
            // 也检查传统的角色（向后兼容）
            const isTraditionalAdmin = roleData.role === 'admin';
            
            if (!hasAdminPermission && !isTraditionalAdmin) {
                // 如果没有管理员权限，重定向到首页或其他适当页面
                window.location.href = '/';
                return;
            }
            
            // 存储用户权限信息供后续使用
            window.userPermissions = roleData.info ? roleData.info.permissions : [];
            window.userRoles = roleData.info ? roleData.info.roles : [];
            
            // 如果有管理员权限，继续初始化页面
            // 加载所有配置数据
            loadConfigData();
            
            // 加载用户数据
            loadUsers();
            
            // 绑定事件监听器
            bindDrawerEvents();  // 绑定抽屉菜单事件
            bindAdminEventListeners();
            
            // 为抽屉菜单中的链接添加事件监听器，点击时关闭抽屉菜单
            const drawerLinks = document.querySelectorAll('#admin-drawer a');
            drawerLinks.forEach(link => {
                // 为登出链接添加确认对话框
                if (link.getAttribute('href') === '/logout') {
                    link.addEventListener('click', function(e) {
                        if (!confirm('确定要登出吗？')) {
                            e.preventDefault();
                        }
                    });
                }
                link.addEventListener('click', closeAdminDrawer);
            });
            
            // 绑定角色管理事件
            bindRoleEventListeners();
            
            // 绑定权限管理事件
            bindPermissionEventListeners();
            
            // 加载角色和权限数据
            loadRoles();
            loadPermissions();
            
            // 根据用户权限显示或隐藏功能
            setupPermissionBasedUI();
        })
        .catch(error => {
            console.error('获取用户角色信息失败:', error);
            // 如果获取角色信息失败，重定向到登录页面
            window.location.href = '/login';
        });
}

// 绑定管理界面事件监听器（专用于管理界面）
function bindAdminEventListeners() {
    // 绑定用户管理相关事件
    const addUserBtn = document.getElementById('add-user-btn');
    if (addUserBtn) {
        addUserBtn.addEventListener('click', function() {
            showUserForm();
        });
    }

    const cancelUserFormBtn = document.getElementById('cancel-user-form');
    if (cancelUserFormBtn) {
        cancelUserFormBtn.addEventListener('click', function() {
            hideUserForm();
        });
    }

    const userFormContent = document.getElementById('user-form-content');
    if (userFormContent) {
        userFormContent.addEventListener('submit', async function(e) {
            e.preventDefault();
            await saveUser();
        });
    }

    // 绑定全局事件委托
    document.addEventListener('click', function(e) {
        // 用户编辑按钮
        if (e.target.classList.contains('btn-edit') && e.target.hasAttribute('data-id')) {
            const userId = e.target.getAttribute('data-id');
            const userRow = e.target.closest('tr');
            if (userRow && userRow.cells.length > 1) {
                const username = userRow.cells[1].textContent;
                const theme = userRow.cells[4].textContent;
                showUserForm({
                    id: userId,
                    username: username,
                    theme: theme
                });
            }
        }
        
        // 用户删除按钮
        if (e.target.classList.contains('btn-delete-user')) {
            const userId = e.target.getAttribute('data-id');
            deleteUser(userId);
        }
        
        // 重置密码按钮
        if (e.target.classList.contains('btn-reset-password')) {
            const userId = e.target.getAttribute('data-id');
            resetPassword(userId);
        }
    });

    // 绑定用户角色管理相关按钮
    const assignRoleBtn = document.getElementById('assign-role-btn');
    if (assignRoleBtn) {
        assignRoleBtn.addEventListener('click', function() {
            assignRoleToUser();
        });
    }

    const closeUserRolesBtn = document.getElementById('close-user-roles-btn');
    if (closeUserRolesBtn) {
        closeUserRolesBtn.addEventListener('click', function() {
            hideUserRoles();
        });
    }

    // 绑定权限检查按钮
    const checkPermissionsBtn = document.getElementById('check-permissions-btn');
    if (checkPermissionsBtn) {
        checkPermissionsBtn.addEventListener('click', function() {
            checkUserPermissions();
        });
    }
}

// 绑定角色管理事件
function bindRoleEventListeners() {
    const addRoleBtn = document.getElementById('add-role-btn');
    if (addRoleBtn) {
        addRoleBtn.addEventListener('click', function() {
            showRoleForm();
        });
    }

    const cancelRoleFormBtn = document.getElementById('cancel-role-form');
    if (cancelRoleFormBtn) {
        cancelRoleFormBtn.addEventListener('click', function() {
            hideRoleForm();
        });
    }

    const roleFormContent = document.getElementById('role-form-content');
    if (roleFormContent) {
        roleFormContent.addEventListener('submit', async function(e) {
            e.preventDefault();
            await saveRole();
        });
    }
}

// 绑定权限管理事件
function bindPermissionEventListeners() {
    const addPermissionBtn = document.getElementById('add-permission-btn');
    if (addPermissionBtn) {
        addPermissionBtn.addEventListener('click', function() {
            showPermissionForm();
        });
    }

    const cancelPermissionFormBtn = document.getElementById('cancel-permission-form');
    if (cancelPermissionFormBtn) {
        cancelPermissionFormBtn.addEventListener('click', function() {
            hidePermissionForm();
        });
    }

    const permissionFormContent = document.getElementById('permission-form-content');
    if (permissionFormContent) {
        permissionFormContent.addEventListener('submit', async function(e) {
            e.preventDefault();
            await savePermission();
        });
    }

    // 绑定权限分配和关闭按钮
    const assignPermissionBtn = document.getElementById('assign-permission-btn');
    if (assignPermissionBtn) {
        assignPermissionBtn.addEventListener('click', function() {
            assignPermissionToRole();
        });
    }

    const closeRolePermissionsBtn = document.getElementById('close-role-permissions-btn');
    if (closeRolePermissionsBtn) {
        closeRolePermissionsBtn.addEventListener('click', function() {
            hideRolePermissions();
        });
    }
}

// 加载备份文件列表
async function loadBackupFiles() {
    try {
        const response = await fetch('/api/admin/backups');
        const result = await response.json();
        
        if (response.ok) {
            renderBackupList(result.backups);
        } else {
            throw new Error(result.detail || '获取备份文件列表失败');
        }
    } catch (error) {
        console.error('加载备份文件列表失败:', error);
        showMessage('加载备份文件列表失败: ' + error.message, 'error');
    }
}

// 绑定拖拽事件的函数
function bindDragEvents(container) {
    if (!container) return;
    
    let draggedItem = null;
    
    container.addEventListener('dragstart', function(e) {
        if (e.target.classList.contains('draggable')) {
            draggedItem = e.target;
            e.target.style.opacity = '0.5';
        }
    });
    
    container.addEventListener('dragend', function(e) {
        if (e.target.classList.contains('draggable')) {
            e.target.style.opacity = '1';
            draggedItem = null;
        }
    });
    
    container.addEventListener('dragover', function(e) {
        e.preventDefault();
    });
    
    container.addEventListener('dragenter', function(e) {
        if (e.target.classList.contains('draggable')) {
            e.target.style.backgroundColor = '#e9ecef';
        }
    });
    
    container.addEventListener('dragleave', function(e) {
        if (e.target.classList.contains('draggable')) {
            e.target.style.backgroundColor = '';
        }
    });
    
    container.addEventListener('drop', function(e) {
        e.preventDefault();
        if (e.target.classList.contains('draggable') && draggedItem) {
            e.target.style.backgroundColor = '';
            
            const allItems = Array.from(container.querySelectorAll('.draggable'));
            const draggedIndex = allItems.indexOf(draggedItem);
            const targetIndex = allItems.indexOf(e.target);
            
            if (draggedIndex !== targetIndex) {
                if (draggedIndex < targetIndex) {
                    container.insertBefore(draggedItem, e.target.nextSibling);
                } else {
                    container.insertBefore(draggedItem, e.target);
                }
            }
        }
    });
}

// 渲染章节列表
function renderChapterList(containerId, chapters) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = '';
    
    chapters.forEach((chapter, index) => {
        const item = document.createElement('div');
        item.className = 'chapter-item draggable';
        item.draggable = true;
        item.innerHTML = `
            <span class="chapter-title">${chapter.title}</span>
            <span class="chapter-file">${chapter.file}</span>
            <div class="chapter-actions">
                <button class="btn-action btn-edit-chapter" data-index="${index}">编辑</button>
                <button class="btn-action btn-delete-chapter" data-index="${index}">删除</button>
            </div>
        `;
        container.appendChild(item);
    });
    
    // 绑定拖拽事件
    bindDragEvents(container);
}

// 渲染备份列表
function renderBackupList(backups) {
    const backupList = document.getElementById('backup-list');
    if (!backupList) return;
    
    backupList.innerHTML = '';
    
    backups.forEach(backup => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${backup.name}</td>
            <td>${formatDate(backup.created_at)}</td>
            <td>${formatFileSize(backup.size)}</td>
            <td>
                <button class="btn-action btn-download" data-filename="${backup.name}">下载</button>
                <button class="btn-action btn-restore" data-filename="${backup.name}">恢复</button>
                <button class="btn-action btn-delete-backup" data-filename="${backup.name}">删除</button>
            </td>
        `;
        backupList.appendChild(row);
    });
}

// 显示用户表单
function showUserForm(user = null) {
    const form = document.getElementById('user-form');
    const formTitle = document.getElementById('form-title');
    const userIdInput = document.getElementById('user-id');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const themeSelect = document.getElementById('theme');
    
    if (!form) return;
    
    if (user) {
        // 编辑用户
        if (formTitle) formTitle.textContent = '编辑用户';
        if (userIdInput) userIdInput.value = user.id;
        if (usernameInput) usernameInput.value = user.username;
        if (passwordInput) passwordInput.value = ''; // 不显示密码
        if (themeSelect) themeSelect.value = user.theme || 'default';
    } else {
        // 新建用户
        if (formTitle) formTitle.textContent = '新建用户';
        if (userIdInput) userIdInput.value = '';
        if (usernameInput) usernameInput.value = '';
        if (passwordInput) passwordInput.value = '';
        if (themeSelect) themeSelect.value = 'default';
    }
    
    form.style.display = 'block';
}

// 隐藏用户表单
function hideUserForm() {
    const form = document.getElementById('user-form');
    if (form) {
        form.style.display = 'none';
    }
}

// 保存用户
async function saveUser() {
    try {
        const userIdInput = document.getElementById('user-id');
        const usernameInput = document.getElementById('username');
        const passwordInput = document.getElementById('password');
        const themeSelect = document.getElementById('theme');
        
        const userId = userIdInput ? userIdInput.value : '';
        const username = usernameInput ? usernameInput.value : '';
        const password = passwordInput ? passwordInput.value : '';
        const theme = themeSelect ? themeSelect.value : 'default';
        
        if (!username) {
            showMessage('用户名不能为空', 'error');
            return;
        }
        
        const userData = {
            username: username,
            theme: theme
        };
        
        if (password) {
            userData.password = password;
        }
        
        let response;
        if (userId) {
            // 更新用户
            response = await fetch(`/api/admin/users/${userId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(userData)
            });
        } else {
            // 创建用户
            if (!password) {
                showMessage('新建用户时密码不能为空', 'error');
                return;
            }
            response = await fetch('/api/admin/users', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(userData)
            });
        }
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage(userId ? '用户更新成功' : '用户创建成功', 'success');
            hideUserForm();
            // 重新加载用户列表
            loadUsers();
        } else {
            throw new Error(result.detail || '保存用户失败');
        }
    } catch (error) {
        console.error('保存用户失败:', error);
        showMessage('保存用户失败: ' + error.message, 'error');
    }
}

// 删除用户
async function deleteUser(userId) {
    if (!confirm('确定要删除这个用户吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('用户删除成功', 'success');
            // 重新加载用户列表
            loadUsers();
        } else {
            throw new Error(result.detail || '删除用户失败');
        }
    } catch (error) {
        console.error('删除用户失败:', error);
        showMessage('删除用户失败: ' + error.message, 'error');
    }
}

// 重置用户密码
async function resetPassword(userId) {
    const newPassword = prompt('请输入新密码:');
    if (!newPassword) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}/reset-password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ password: newPassword })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('密码重置成功', 'success');
        } else {
            throw new Error(result.detail || '密码重置失败');
        }
    } catch (error) {
        console.error('密码重置失败:', error);
        showMessage('密码重置失败: ' + error.message, 'error');
    }
}

// 加载角色数据
async function loadRoles() {
    try {
        const response = await fetch('/api/admin/roles');
        const result = await response.json();
        
        if (response.ok) {
            renderRoleList(result.roles);
        } else {
            throw new Error(result.detail || '获取角色列表失败');
        }
    } catch (error) {
        console.error('加载角色列表失败:', error);
        showMessage('加载角色列表失败: ' + error.message, 'error');
    }
}

// 渲染角色列表
function renderRoleList(roles) {
    const roleList = document.getElementById('role-list');
    if (!roleList) return;
    
    roleList.innerHTML = '';
    
    roles.forEach(role => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${role.id}</td>
            <td>${role.name}</td>
            <td>${role.description}</td>
            <td>${formatDate(role.created_at)}</td>
            <td>
                <button class="btn-action btn-edit-role" data-id="${role.id}" data-name="${role.name}" data-description="${role.description}">编辑</button>
                <button class="btn-action btn-manage-permissions" data-id="${role.id}" data-name="${role.name}">管理权限</button>
                <button class="btn-action btn-delete-role" data-id="${role.id}">删除</button>
            </td>
        `;
        roleList.appendChild(row);
    });
}

// 显示角色表单
function showRoleForm(role = null) {
    const form = document.getElementById('role-form');
    const formTitle = document.getElementById('role-form-title');
    const roleIdInput = document.getElementById('role-id');
    const roleNameInput = document.getElementById('role-name');
    const roleDescriptionInput = document.getElementById('role-description');
    
    if (!form) return;
    
    if (role) {
        // 编辑角色
        if (formTitle) formTitle.textContent = '编辑角色';
        if (roleIdInput) roleIdInput.value = role.id;
        if (roleNameInput) roleNameInput.value = role.name;
        if (roleDescriptionInput) roleDescriptionInput.value = role.description;
    } else {
        // 新建角色
        if (formTitle) formTitle.textContent = '新建角色';
        if (roleIdInput) roleIdInput.value = '';
        if (roleNameInput) roleNameInput.value = '';
        if (roleDescriptionInput) roleDescriptionInput.value = '';
    }
    
    form.style.display = 'block';
}

// 隐藏角色表单
function hideRoleForm() {
    const form = document.getElementById('role-form');
    if (form) {
        form.style.display = 'none';
    }
}

// 保存角色
async function saveRole() {
    try {
        const roleIdInput = document.getElementById('role-id');
        const roleNameInput = document.getElementById('role-name');
        const roleDescriptionInput = document.getElementById('role-description');
        
        const roleId = roleIdInput ? roleIdInput.value : '';
        const roleName = roleNameInput ? roleNameInput.value : '';
        const roleDescription = roleDescriptionInput ? roleDescriptionInput.value : '';
        
        if (!roleName) {
            showMessage('角色名称不能为空', 'error');
            return;
        }
        
        const roleData = {
            name: roleName,
            description: roleDescription
        };
        
        let response;
        if (roleId) {
            // 更新角色
            response = await fetch(`/api/admin/roles/${roleId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(roleData)
            });
        } else {
            // 创建角色
            response = await fetch('/api/admin/roles', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(roleData)
            });
        }
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage(roleId ? '角色更新成功' : '角色创建成功', 'success');
            hideRoleForm();
            // 重新加载角色列表
            loadRoles();
        } else {
            throw new Error(result.detail || '保存角色失败');
        }
    } catch (error) {
        console.error('保存角色失败:', error);
        showMessage('保存角色失败: ' + error.message, 'error');
    }
}

// 加载权限数据
async function loadPermissions() {
    try {
        const response = await fetch('/api/admin/permissions');
        const result = await response.json();
        
        if (response.ok) {
            renderPermissionList(result.permissions);
        } else {
            throw new Error(result.detail || '获取权限列表失败');
        }
    } catch (error) {
        console.error('加载权限列表失败:', error);
        showMessage('加载权限列表失败: ' + error.message, 'error');
    }
}

// 渲染权限列表
function renderPermissionList(permissions) {
    const permissionList = document.getElementById('permission-list');
    if (!permissionList) return;
    
    permissionList.innerHTML = '';
    
    permissions.forEach(permission => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${permission.id}</td>
            <td>${permission.name}</td>
            <td>${permission.description}</td>
            <td>${formatDate(permission.created_at)}</td>
            <td>
                <button class="btn-action btn-edit-permission" data-id="${permission.id}" data-name="${permission.name}" data-description="${permission.description}">编辑</button>
                <button class="btn-action btn-delete-permission" data-id="${permission.id}">删除</button>
            </td>
        `;
        permissionList.appendChild(row);
    });
}

// 显示权限表单
function showPermissionForm(permission = null) {
    const form = document.getElementById('permission-form');
    const formTitle = document.getElementById('permission-form-title');
    const permissionIdInput = document.getElementById('permission-id');
    const permissionNameInput = document.getElementById('permission-name');
    const permissionDescriptionInput = document.getElementById('permission-description');
    
    if (!form) return;
    
    if (permission) {
        // 编辑权限
        if (formTitle) formTitle.textContent = '编辑权限';
        if (permissionIdInput) permissionIdInput.value = permission.id;
        if (permissionNameInput) permissionNameInput.value = permission.name;
        if (permissionDescriptionInput) permissionDescriptionInput.value = permission.description;
    } else {
        // 新建权限
        if (formTitle) formTitle.textContent = '新建权限';
        if (permissionIdInput) permissionIdInput.value = '';
        if (permissionNameInput) permissionNameInput.value = '';
        if (permissionDescriptionInput) permissionDescriptionInput.value = '';
    }
    
    form.style.display = 'block';
}

// 隐藏权限表单
function hidePermissionForm() {
    const form = document.getElementById('permission-form');
    if (form) {
        form.style.display = 'none';
    }
}

// 保存权限
async function savePermission() {
    try {
        const permissionIdInput = document.getElementById('permission-id');
        const permissionNameInput = document.getElementById('permission-name');
        const permissionDescriptionInput = document.getElementById('permission-description');
        
        const permissionId = permissionIdInput ? permissionIdInput.value : '';
        const permissionName = permissionNameInput ? permissionNameInput.value : '';
        const permissionDescription = permissionDescriptionInput ? permissionDescriptionInput.value : '';
        
        if (!permissionName) {
            showMessage('权限名称不能为空', 'error');
            return;
        }
        
        const permissionData = {
            name: permissionName,
            description: permissionDescription
        };
        
        let response;
        if (permissionId) {
            // 更新权限
            response = await fetch(`/api/admin/permissions/${permissionId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(permissionData)
            });
        } else {
            // 创建权限
            response = await fetch('/api/admin/permissions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(permissionData)
            });
        }
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage(permissionId ? '权限更新成功' : '权限创建成功', 'success');
            hidePermissionForm();
            // 重新加载权限列表
            loadPermissions();
        } else {
            throw new Error(result.detail || '保存权限失败');
        }
    } catch (error) {
        console.error('保存权限失败:', error);
        showMessage('保存权限失败: ' + error.message, 'error');
    }
}

// 权限检查函数
async function checkUserPermissions() {
    try {
        const response = await fetch('/api/admin/check-permissions');
        const result = await response.json();
        
        if (response.ok) {
            showMessage('权限检查完成', 'success');
            console.log('权限检查结果:', result);
        } else {
            throw new Error(result.detail || '权限检查失败');
        }
    } catch (error) {
        console.error('权限检查失败:', error);
        showMessage('权限检查失败: ' + error.message, 'error');
    }
}

// 用户角色管理函数已移至 /static/common/js/main-shared.js 以避免重复
// 包括: showUserRoles, loadUserRoles, renderUserRoles

function hideUserRoles() {
    const modal = document.getElementById('user-roles-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function assignRoleToUser() {
    const modal = document.getElementById('user-roles-modal');
    const userId = modal ? modal.dataset.userId : null;
    const roleSelect = document.getElementById('user-role-select');
    const roleId = roleSelect ? roleSelect.value : null;
    
    if (!userId || !roleId) {
        showMessage('请选择角色', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}/roles`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ role_id: roleId })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('角色分配成功', 'success');
            loadUserRoles(userId);
        } else {
            throw new Error(result.detail || '角色分配失败');
        }
    } catch (error) {
        console.error('角色分配失败:', error);
        showMessage('角色分配失败: ' + error.message, 'error');
    }
}

// 角色权限管理函数
function showRolePermissions(roleId, roleName) {
    const modal = document.getElementById('role-permissions-modal');
    if (modal) {
        modal.style.display = 'block';
        // 设置角色信息
        const roleNameElement = document.getElementById('role-permissions-name');
        if (roleNameElement) {
            roleNameElement.textContent = roleName;
        }
        // 存储当前角色ID供后续使用
        modal.dataset.roleId = roleId;
        
        // 加载角色权限信息
        loadRolePermissions(roleId);
    }
}

function hideRolePermissions() {
    const modal = document.getElementById('role-permissions-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function loadRolePermissions(roleId) {
    try {
        const response = await fetch(`/api/admin/roles/${roleId}/permissions`);
        const result = await response.json();
        
        if (response.ok) {
            renderRolePermissions(result.permissions);
        } else {
            throw new Error(result.detail || '获取角色权限失败');
        }
    } catch (error) {
        console.error('加载角色权限失败:', error);
        showMessage('加载角色权限失败: ' + error.message, 'error');
    }
}

function renderRolePermissions(permissions) {
    const container = document.getElementById('role-permissions-list');
    if (!container) return;
    
    container.innerHTML = '';
    permissions.forEach(permission => {
        const permissionElement = document.createElement('div');
        permissionElement.className = 'permission-item';
        permissionElement.innerHTML = `
            <span>${permission.name}</span>
            <button class="btn-action btn-remove-permission" data-permission-id="${permission.id}">移除</button>
        `;
        container.appendChild(permissionElement);
    });
}

async function assignPermissionToRole() {
    const modal = document.getElementById('role-permissions-modal');
    const roleId = modal ? modal.dataset.roleId : null;
    const permissionSelect = document.getElementById('role-permission-select');
    const permissionId = permissionSelect ? permissionSelect.value : null;
    
    if (!roleId || !permissionId) {
        showMessage('请选择权限', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/roles/${roleId}/permissions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ permission_id: permissionId })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('权限分配成功', 'success');
            loadRolePermissions(roleId);
        } else {
            throw new Error(result.detail || '权限分配失败');
        }
    } catch (error) {
        console.error('权限分配失败:', error);
        showMessage('权限分配失败: ' + error.message, 'error');
    }
}

// 绑定管理员面板特有的事件（用于admin-panel页面）
function bindAdminPanelEvents() {
    // 构建按钮事件
    const buildAllBtn = document.getElementById('build-all-btn');
    const buildEpubBtn = document.getElementById('build-epub-btn');
    const buildPdfBtn = document.getElementById('build-pdf-btn');
    
    if (buildAllBtn) {
        buildAllBtn.addEventListener('click', () => buildBook('build'));
    }
    if (buildEpubBtn) {
        buildEpubBtn.addEventListener('click', () => buildBook('epub'));
    }
    if (buildPdfBtn) {
        buildPdfBtn.addEventListener('click', () => buildBook('pdf'));
    }
    
    // 章节管理按钮事件
    const saveChaptersBtn = document.getElementById('save-chapters-btn');
    const resetChaptersBtn = document.getElementById('reset-chapters-btn');
    
    if (saveChaptersBtn) {
        saveChaptersBtn.addEventListener('click', saveChapterOrder);
    }
    if (resetChaptersBtn) {
        resetChaptersBtn.addEventListener('click', resetChapterOrder);
    }
    
    // Src目录管理事件
    const uploadSrcBtn = document.getElementById('upload-src-btn');
    const downloadSrcBtn = document.getElementById('download-src-btn');
    const resetSrcBtn = document.getElementById('reset-src-btn');
    
    if (uploadSrcBtn) {
        uploadSrcBtn.addEventListener('click', uploadSrc);
    }
    if (downloadSrcBtn) {
        downloadSrcBtn.addEventListener('click', downloadSrc);
    }
    if (resetSrcBtn) {
        resetSrcBtn.addEventListener('click', resetSrc);
    }
    
    // EPUB转换事件
    const convertEpubBtn = document.getElementById('convert-epub-btn');
    const downloadConvertedBtn = document.getElementById('download-converted-btn');
    
    if (convertEpubBtn) {
        convertEpubBtn.addEventListener('click', convertEpubToMarkdown);
    }
    if (downloadConvertedBtn) {
        downloadConvertedBtn.addEventListener('click', downloadConvertedFiles);
    }
    
    // 手动备份事件
    const manualBackupBtn = document.getElementById('manual-backup-btn');
    if (manualBackupBtn) {
        manualBackupBtn.addEventListener('click', createManualBackup);
    }
    
    // 全局事件委托
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('download-backup-btn')) {
            const filename = e.target.getAttribute('data-filename');
            downloadBackupFile(filename);
        }
        
        if (e.target.classList.contains('delete-backup-btn')) {
            const filename = e.target.getAttribute('data-filename');
            deleteBackupFile(filename);
        }
        
        if (e.target.classList.contains('remove-chapter-btn')) {
            const chapterItem = e.target.closest('.chapter-item');
            if (chapterItem) {
                chapterItem.remove();
            }
        }
    });
}

// EPUB转换为Markdown
async function convertEpubToMarkdown() {
    const fileInput = document.getElementById('epub-upload');
    const file = fileInput.files[0];
    
    if (!file) {
        showMessage('请选择一个EPUB文件', 'warning');
        return;
    }
    
    if (!file.name.endsWith('.epub')) {
        showMessage('只允许上传.epub文件', 'error');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        showMessage('正在转换EPUB文件...', 'info');
        
        const response = await fetch('/api/admin/epub/convert', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('EPUB转换成功', 'success');
            // 显示转换结果
            const conversionResult = document.getElementById('conversion-result');
            if (conversionResult) {
                conversionResult.classList.remove('hidden');
                conversionResult.style.display = 'block';
            }
        } else {
            throw new Error(result.detail || '转换失败');
        }
    } catch (error) {
        console.error('EPUB转换失败:', error);
        showMessage('EPUB转换失败: ' + error.message, 'error');
    }
}

// 下载转换后的文件
async function downloadConvertedFiles() {
    try {
        showMessage('正在准备下载转换结果...', 'info');
        
        // 创建一个隐藏的iframe来触发下载
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = '/api/admin/epub/download-converted';
        document.body.appendChild(iframe);
        
        // 一段时间后移除iframe
        setTimeout(() => {
            document.body.removeChild(iframe);
        }, 1000);
    } catch (error) {
        console.error('下载转换文件失败:', error);
        showMessage('下载转换文件失败: ' + error.message, 'error');
    }
}

// 创建手动备份
async function createManualBackup() {
    if (!confirm('确定要创建手动备份吗？')) {
        return;
    }
    
    try {
        showMessage('正在创建备份...', 'info');
        
        const response = await fetch('/api/admin/backup/create', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('备份创建成功', 'success');
            // 重新加载备份列表
            loadBackupFiles();
        } else {
            throw new Error(result.detail || '备份创建失败');
        }
    } catch (error) {
        console.error('创建备份失败:', error);
        showMessage('创建备份失败: ' + error.message, 'error');
    }
}

// 下载备份文件
async function downloadBackupFile(filename) {
    try {
        showMessage('正在准备下载备份文件...', 'info');
        
        // 创建一个隐藏的iframe来触发下载
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = `/api/admin/backup/download/${encodeURIComponent(filename)}`;
        document.body.appendChild(iframe);
        
        // 一段时间后移除iframe
        setTimeout(() => {
            document.body.removeChild(iframe);
        }, 1000);
    } catch (error) {
        console.error('下载备份文件失败:', error);
        showMessage('下载备份文件失败: ' + error.message, 'error');
    }
}

// 删除备份文件
async function deleteBackupFile(filename) {
    if (!confirm(`确定要删除备份文件 "${filename}" 吗？`)) {
        return;
    }
    
    try {
        showMessage('正在删除备份文件...', 'info');
        
        const response = await fetch(`/api/admin/backup/delete/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('备份文件删除成功', 'success');
            // 重新加载备份列表
            loadBackupFiles();
        } else {
            throw new Error(result.detail || '删除备份文件失败');
        }
    } catch (error) {
        console.error('删除备份文件失败:', error);
        showMessage('删除备份文件失败: ' + error.message, 'error');
    }
}