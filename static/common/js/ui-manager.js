/**
 * MarkEdit UI管理工具库
 * 
 * 专门处理列表渲染、表单管理、模态框等UI相关的重复操作
 */

// ==========================================
// UI组件类定义
// ==========================================

/**
 * 列表渲染管理器
 */
class ListRenderer {
    constructor() {
        this.renderers = new Map();
    }
    
    /**
     * 注册列表渲染器
     */
    register(type, renderer) {
        this.renderers.set(type, renderer);
    }
    
    /**
     * 通用列表渲染方法
     */
    render(containerId, items, type, options = {}) {
        const container = DOMUtils.getElementById(containerId);
        if (!container) return;
        
        const renderer = this.renderers.get(type);
        if (!renderer) {
            console.error(`未找到类型为 ${type} 的列表渲染器`);
            return;
        }
        
        // 清空容器
        DOMUtils.clear(container);
        
        // 渲染列表
        if (Array.isArray(items) && items.length > 0) {
            items.forEach((item, index) => {
                const element = renderer(item, index, options);
                if (element) {
                    container.appendChild(element);
                }
            });
        } else {
            // 显示空状态
            const emptyElement = this.createEmptyState(options.emptyMessage || '暂无数据');
            container.appendChild(emptyElement);
        }
        
        // 绑定事件
        if (options.events) {
            this.bindListEvents(container, options.events);
        }
    }
    
    /**
     * 创建空状态元素
     */
    createEmptyState(message) {
        return DOMUtils.createElement('div', {
            className: 'empty-state'
        }, `<p>${message}</p>`);
    }
    
    /**
     * 绑定列表事件
     */
    bindListEvents(container, events) {
        Object.entries(events).forEach(([selector, handler]) => {
            DOMUtils.on(container, 'click', selector, handler);
        });
    }
}

/**
 * 表格渲染器
 */
class TableRenderer extends ListRenderer {
    /**
     * 渲染表格
     */
    renderTable(containerId, items, columns, options = {}) {
        const container = DOMUtils.getElementById(containerId);
        if (!container) return;
        
        // 创建表格结构
        const table = DOMUtils.createElement('table', {
            className: options.className || 'data-table'
        });
        
        // 创建表头
        if (options.showHeader !== false) {
            const thead = this.createTableHeader(columns);
            table.appendChild(thead);
        }
        
        // 创建表体
        const tbody = this.createTableBody(items, columns, options);
        table.appendChild(tbody);
        
        // 清空容器并添加表格
        DOMUtils.clear(container);
        container.appendChild(table);
        
        // 绑定事件
        if (options.events) {
            this.bindListEvents(container, options.events);
        }
        
        return table;
    }
    
    /**
     * 创建表头
     */
    createTableHeader(columns) {
        const thead = DOMUtils.createElement('thead');
        const headerRow = DOMUtils.createElement('tr');
        
        columns.forEach(column => {
            const th = DOMUtils.createElement('th', {}, column.label || column.key);
            if (column.width) {
                th.style.width = column.width;
            }
            headerRow.appendChild(th);
        });
        
        thead.appendChild(headerRow);
        return thead;
    }
    
    /**
     * 创建表体
     */
    createTableBody(items, columns, options) {
        const tbody = DOMUtils.createElement('tbody');
        
        if (items && items.length > 0) {
            items.forEach((item, index) => {
                const row = this.createTableRow(item, index, columns, options);
                tbody.appendChild(row);
            });
        } else {
            // 创建空数据行
            const emptyRow = DOMUtils.createElement('tr');
            const emptyCell = DOMUtils.createElement('td', {
                colspan: columns.length,
                className: 'empty-cell'
            }, options.emptyMessage || '暂无数据');
            emptyRow.appendChild(emptyCell);
            tbody.appendChild(emptyRow);
        }
        
        return tbody;
    }
    
    /**
     * 创建表格行
     */
    createTableRow(item, index, columns, options) {
        const row = DOMUtils.createElement('tr');
        
        columns.forEach(column => {
            const td = DOMUtils.createElement('td');
            
            let value = item[column.key];
            
            // 应用格式化
            if (column.formatter) {
                value = column.formatter(value, item, index);
            } else if (column.type === 'date') {
                value = FormatUtils.formatDate(value, column.format);
            } else if (column.type === 'bytes') {
                value = FormatUtils.formatBytes(value);
            }
            
            // 设置内容
            if (column.render) {
                // 自定义渲染
                const content = column.render(value, item, index);
                if (typeof content === 'string') {
                    td.innerHTML = content;
                } else {
                    td.appendChild(content);
                }
            } else {
                td.textContent = value || '';
            }
            
            row.appendChild(td);
        });
        
        return row;
    }
}

/**
 * 模态框管理器
 */
class ModalManager {
    constructor() {
        this.modals = new Map();
        this.currentModal = null;
    }
    
    /**
     * 创建模态框
     */
    create(id, options = {}) {
        const modal = DOMUtils.createElement('div', {
            id: id,
            className: 'modal'
        });
        
        const modalContent = DOMUtils.createElement('div', {
            className: 'modal-content'
        });
        
        // 创建头部
        if (options.title) {
            const header = DOMUtils.createElement('div', {
                className: 'modal-header'
            });
            
            const title = DOMUtils.createElement('h3', {}, options.title);
            const closeBtn = DOMUtils.createElement('button', {
                className: 'modal-close',
                type: 'button'
            }, '×');
            
            closeBtn.onclick = () => this.close(id);
            
            header.appendChild(title);
            header.appendChild(closeBtn);
            modalContent.appendChild(header);
        }
        
        // 创建主体
        const body = DOMUtils.createElement('div', {
            className: 'modal-body'
        });
        
        if (options.content) {
            if (typeof options.content === 'string') {
                body.innerHTML = options.content;
            } else {
                body.appendChild(options.content);
            }
        }
        
        modalContent.appendChild(body);
        
        // 创建底部
        if (options.buttons) {
            const footer = DOMUtils.createElement('div', {
                className: 'modal-footer'
            });
            
            options.buttons.forEach(button => {
                const btn = DOMUtils.createElement('button', {
                    className: button.className || 'btn',
                    type: 'button'
                }, button.text);
                
                if (button.onClick) {
                    btn.onclick = button.onClick;
                }
                
                footer.appendChild(btn);
            });
            
            modalContent.appendChild(footer);
        }
        
        modal.appendChild(modalContent);
        
        // 点击背景关闭
        modal.onclick = (e) => {
            if (e.target === modal) {
                this.close(id);
            }
        };
        
        this.modals.set(id, modal);
        return modal;
    }
    
    /**
     * 显示模态框
     */
    show(id) {
        const modal = this.modals.get(id);
        if (!modal) return;
        
        // 关闭当前模态框
        if (this.currentModal) {
            this.close(this.currentModal);
        }
        
        document.body.appendChild(modal);
        modal.classList.add('show');
        this.currentModal = id;
        
        // 阻止页面滚动（除非是管理页面）
        if (!document.body.classList.contains('admin-page') && !document.body.classList.contains('role-permission-page')) {
            document.body.style.overflow = 'hidden';
        }
    }
    
    /**
     * 关闭模态框
     */
    close(id) {
        const modal = this.modals.get(id);
        if (!modal) return;
        
        modal.classList.remove('show');
        setTimeout(() => {
            if (modal.parentNode) {
                modal.parentNode.removeChild(modal);
            }
        }, 300);
        
        this.currentModal = null;
        
        // 恢复页面滚动（除非是管理页面）
        if (!document.body.classList.contains('admin-page') && !document.body.classList.contains('role-permission-page')) {
            document.body.style.overflow = '';
        }
    }
    
    /**
     * 更新模态框内容
     */
    updateContent(id, content) {
        const modal = this.modals.get(id);
        if (!modal) return;
        
        const body = modal.querySelector('.modal-body');
        if (body) {
            if (typeof content === 'string') {
                body.innerHTML = content;
            } else {
                DOMUtils.clear(body);
                body.appendChild(content);
            }
        }
    }
    
    /**
     * 确认对话框
     */
    confirm(message, title = '确认', options = {}) {
        return new Promise((resolve) => {
            const modalId = 'confirm-modal';
            
            this.create(modalId, {
                title: title,
                content: `<p>${message}</p>`,
                buttons: [
                    {
                        text: options.cancelText || '取消',
                        className: 'btn btn-secondary',
                        onClick: () => {
                            this.close(modalId);
                            resolve(false);
                        }
                    },
                    {
                        text: options.confirmText || '确定',
                        className: 'btn btn-primary',
                        onClick: () => {
                            this.close(modalId);
                            resolve(true);
                        }
                    }
                ]
            });
            
            this.show(modalId);
        });
    }
    
    /**
     * 警告对话框
     */
    alert(message, title = '提示') {
        return new Promise((resolve) => {
            const modalId = 'alert-modal';
            
            this.create(modalId, {
                title: title,
                content: `<p>${message}</p>`,
                buttons: [
                    {
                        text: '确定',
                        className: 'btn btn-primary',
                        onClick: () => {
                            this.close(modalId);
                            resolve();
                        }
                    }
                ]
            });
            
            this.show(modalId);
        });
    }
}

/**
 * 表单管理器
 */
class FormManager {
    constructor() {
        this.forms = new Map();
    }
    
    /**
     * 注册表单
     */
    register(id, config) {
        this.forms.set(id, config);
        
        const form = document.getElementById(id);
        if (form) {
            this.bindFormEvents(form, config);
        }
    }
    
    /**
     * 绑定表单事件
     */
    bindFormEvents(form, config) {
        // 提交事件
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (config.onSubmit) {
                const formData = FormUtils.getFormData(form);
                
                // 表单验证
                if (config.rules) {
                    const validation = FormUtils.validate(form, config.rules);
                    if (!validation.valid) {
                        messageManager.error(validation.errors.join('<br>'));
                        return;
                    }
                }
                
                try {
                    await config.onSubmit(formData, form);
                } catch (error) {
                    messageManager.error(error.message || '操作失败');
                }
            }
        });
        
        // 重置事件
        if (config.onReset) {
            form.addEventListener('reset', config.onReset);
        }
    }
    
    /**
     * 显示表单
     */
    show(id, data = {}) {
        const form = document.getElementById(id);
        if (form) {
            FormUtils.setFormData(form, data);
            DOMUtils.show(form);
        }
    }
    
    /**
     * 隐藏表单
     */
    hide(id) {
        const form = document.getElementById(id);
        if (form) {
            DOMUtils.hide(form);
            FormUtils.reset(form);
        }
    }
}

// ==========================================
// 全局实例
// ==========================================

const listRenderer = new ListRenderer();
const tableRenderer = new TableRenderer();
const modalManager = new ModalManager();
const formManager = new FormManager();

// ==========================================
// 注册通用列表渲染器
// ==========================================

// 用户列表渲染器
listRenderer.register('userList', (user, index, options) => {
    return DOMUtils.createElement('tr', {}, `
        <td>${user.id}</td>
        <td>${user.username}</td>
        <td>${FormatUtils.formatDate(user.created_at)}</td>
        <td>${user.login_time ? FormatUtils.formatDate(user.login_time) : '从未登录'}</td>
        <td>${user.theme || 'default'}</td>
        <td>
            <button class="btn-action btn-edit" data-id="${user.id}">编辑</button>
            <button class="btn-action btn-reset-password" data-id="${user.id}">重置密码</button>
            <button class="btn-action btn-manage-roles" data-id="${user.id}" data-username="${user.username}">管理角色</button>
            <button class="btn-action btn-delete-user" data-id="${user.id}">删除</button>
        </td>
    `);
});

// 角色列表渲染器
listRenderer.register('roleList', (role, index, options) => {
    return DOMUtils.createElement('tr', {}, `
        <td>${role.id}</td>
        <td>${role.name}</td>
        <td>${role.description || ''}</td>
        <td>${FormatUtils.formatDate(role.created_at)}</td>
        <td>
            <button class="btn-action btn-edit-role" data-id="${role.id}">编辑</button>
            <button class="btn-action btn-manage-permissions" data-id="${role.id}" data-name="${role.name}">管理权限</button>
            <button class="btn-action btn-delete-role" data-id="${role.id}">删除</button>
        </td>
    `);
});

// 权限列表渲染器
listRenderer.register('permissionList', (permission, index, options) => {
    return DOMUtils.createElement('tr', {}, `
        <td>${permission.id}</td>
        <td>${permission.name}</td>
        <td>${permission.description || ''}</td>
        <td>
            <button class="btn-action btn-edit-permission" data-id="${permission.id}">编辑</button>
            <button class="btn-action btn-delete-permission" data-id="${permission.id}">删除</button>
        </td>
    `);
});

// 备份列表渲染器
listRenderer.register('backupList', (backup, index, options) => {
    return DOMUtils.createElement('tr', {}, `
        <td>${backup.name}</td>
        <td>${FormatUtils.formatBytes(backup.size)}</td>
        <td>${backup.created_at}</td>
        <td>
            <button class="btn-action btn-download-backup" data-filename="${backup.name}">下载</button>
            <button class="btn-action btn-restore-backup" data-filename="${backup.name}">恢复</button>
            <button class="btn-action btn-delete-backup" data-filename="${backup.name}">删除</button>
        </td>
    `);
});

// ==========================================
// 便捷函数
// ==========================================

/**
 * 渲染用户列表 (向后兼容)
 */
function renderUserList(users) {
    listRenderer.render('user-list', users, 'userList');
}

/**
 * 渲染角色列表 (向后兼容)
 */
function renderRoleList(roles) {
    listRenderer.render('role-list', roles, 'roleList');
}

/**
 * 渲染权限列表 (向后兼容)
 */
function renderPermissionList(permissions) {
    listRenderer.render('permission-list', permissions, 'permissionList');
}

/**
 * 渲染备份列表 (向后兼容)
 */
function renderBackupList(backups) {
    listRenderer.render('backup-list', backups, 'backupList');
}

// ==========================================
// 导出到全局作用域
// ==========================================

// 添加UI工具到全局MarkEditUtils
if (window.MarkEditUtils) {
    Object.assign(window.MarkEditUtils, {
        ListRenderer,
        TableRenderer,
        ModalManager,
        FormManager,
        
        // 全局实例
        listRenderer,
        tableRenderer,
        modalManager,
        formManager
    });
} else {
    window.MarkEditUtils = {
        ListRenderer,
        TableRenderer,
        ModalManager,
        FormManager,
        listRenderer,
        tableRenderer,
        modalManager,
        formManager
    };
}

// 向后兼容的全局函数
window.renderUserList = renderUserList;
window.renderRoleList = renderRoleList;
window.renderPermissionList = renderPermissionList;
window.renderBackupList = renderBackupList;