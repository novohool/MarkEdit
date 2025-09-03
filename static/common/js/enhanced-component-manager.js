/**
 * 增强版统一组件管理器
 * 提供更好的数据绑定、状态管理和组件通信
 */

class EnhancedComponentManager {
    constructor() {
        this.components = new Map();
        this.eventBus = new EventTarget();
        this.dataStore = new Map();
        this.bindings = new Map();
        this.observers = new Map();
        this.isInitialized = false;
        
        this.init();
    }

    /**
     * 初始化组件管理器
     */
    init() {
        if (this.isInitialized) return;
        
        console.log('初始化增强版组件管理器...');
        
        // 注册核心组件
        this.registerCoreComponents();
        
        // 初始化数据绑定系统
        this.initializeDataBinding();
        
        // 设置全局错误处理
        this.setupErrorHandling();
        
        this.isInitialized = true;
        console.log('增强版组件管理器初始化完成');
    }

    /**
     * 注册核心组件
     */
    registerCoreComponents() {
        // 消息组件
        this.registerComponent('message', new MessageComponent());
        
        // 模态框组件
        this.registerComponent('modal', new ModalComponent());
        
        // 抽屉组件
        this.registerComponent('drawer', new DrawerComponent());
        
        // 数据表格组件
        this.registerComponent('dataTable', new DataTableComponent());
        
        // 表单组件
        this.registerComponent('form', new FormComponent());
        
        // 加载组件
        this.registerComponent('loading', new LoadingComponent());
    }

    /**
     * 注册组件
     */
    registerComponent(name, component) {
        if (this.components.has(name)) {
            console.warn(`组件 ${name} 已存在，将被覆盖`);
        }
        
        this.components.set(name, component);
        
        // 如果组件有初始化方法，调用它
        if (typeof component.init === 'function') {
            component.init(this);
        }
        
        console.log(`组件 ${name} 注册成功`);
    }

    /**
     * 获取组件
     */
    getComponent(name) {
        const component = this.components.get(name);
        if (!component) {
            console.warn(`组件 ${name} 不存在`);
            return null;
        }
        return component;
    }

    /**
     * 初始化数据绑定系统
     */
    initializeDataBinding() {
        // 创建响应式数据代理
        this.createReactiveProxy();
        
        // 扫描并绑定DOM元素
        this.scanAndBindElements();
        
        // 设置变化观察器
        this.setupChangeObservers();
    }

    /**
     * 创建响应式数据代理
     */
    createReactiveProxy() {
        this.reactiveData = new Proxy({}, {
            set: (target, property, value) => {
                const oldValue = target[property];
                target[property] = value;
                
                // 触发数据变化事件
                this.notifyDataChange(property, value, oldValue);
                
                return true;
            },
            
            get: (target, property) => {
                return target[property];
            }
        });
    }

    /**
     * 扫描并绑定DOM元素
     */
    scanAndBindElements() {
        // 扫描具有数据绑定属性的元素
        const bindableElements = document.querySelectorAll('[data-bind], [data-model], [data-watch]');
        
        bindableElements.forEach(element => {
            this.bindElement(element);
        });
    }

    /**
     * 绑定单个元素
     */
    bindElement(element) {
        // 双向数据绑定
        const modelAttr = element.getAttribute('data-model');
        if (modelAttr) {
            this.bindModel(element, modelAttr);
        }
        
        // 单向数据绑定
        const bindAttr = element.getAttribute('data-bind');
        if (bindAttr) {
            this.bindData(element, bindAttr);
        }
        
        // 数据监听
        const watchAttr = element.getAttribute('data-watch');
        if (watchAttr) {
            this.bindWatcher(element, watchAttr);
        }
    }

    /**
     * 双向数据绑定
     */
    bindModel(element, modelPath) {
        // 设置初始值
        const initialValue = this.getNestedValue(this.reactiveData, modelPath);
        if (initialValue !== undefined) {
            this.setElementValue(element, initialValue);
        }
        
        // 监听数据变化
        this.watchData(modelPath, (newValue) => {
            this.setElementValue(element, newValue);
        });
        
        // 监听元素变化
        const eventType = this.getElementEventType(element);
        element.addEventListener(eventType, (e) => {
            const value = this.getElementValue(element);
            this.setNestedValue(this.reactiveData, modelPath, value);
        });
        
        console.log(`双向绑定: ${element.tagName} <-> ${modelPath}`);
    }

    /**
     * 单向数据绑定
     */
    bindData(element, bindExpression) {
        // 解析绑定表达式
        const binding = this.parseBindExpression(bindExpression);
        
        // 监听数据变化
        binding.dependencies.forEach(dep => {
            this.watchData(dep, () => {
                const value = this.evaluateBinding(binding);
                this.setElementValue(element, value);
            });
        });
        
        // 设置初始值
        const initialValue = this.evaluateBinding(binding);
        this.setElementValue(element, initialValue);
        
        console.log(`单向绑定: ${element.tagName} <- ${bindExpression}`);
    }

    /**
     * 数据监听绑定
     */
    bindWatcher(element, watchExpression) {
        const watchPaths = watchExpression.split(',').map(path => path.trim());
        
        watchPaths.forEach(path => {
            this.watchData(path, (newValue, oldValue) => {
                // 触发自定义事件
                const event = new CustomEvent('dataChanged', {
                    detail: { path, newValue, oldValue }
                });
                element.dispatchEvent(event);
            });
        });
        
        console.log(`数据监听: ${element.tagName} watches ${watchExpression}`);
    }

    /**
     * 监听数据变化
     */
    watchData(path, callback) {
        if (!this.observers.has(path)) {
            this.observers.set(path, new Set());
        }
        this.observers.get(path).add(callback);
    }

    /**
     * 通知数据变化
     */
    notifyDataChange(property, newValue, oldValue) {
        // 通知直接观察者
        if (this.observers.has(property)) {
            this.observers.get(property).forEach(callback => {
                try {
                    callback(newValue, oldValue);
                } catch (error) {
                    console.error(`数据观察者执行失败 (${property}):`, error);
                }
            });
        }
        
        // 通知嵌套路径观察者
        this.observers.forEach((callbacks, path) => {
            if (path.startsWith(property + '.')) {
                const nestedValue = this.getNestedValue(this.reactiveData, path);
                callbacks.forEach(callback => {
                    try {
                        callback(nestedValue, undefined);
                    } catch (error) {
                        console.error(`嵌套数据观察者执行失败 (${path}):`, error);
                    }
                });
            }
        });
        
        // 触发全局数据变化事件
        this.emit('dataChange', { property, newValue, oldValue });
    }

    /**
     * 设置数据
     */
    setData(path, value) {
        this.setNestedValue(this.reactiveData, path, value);
    }

    /**
     * 获取数据
     */
    getData(path) {
        return this.getNestedValue(this.reactiveData, path);
    }

    /**
     * 批量设置数据
     */
    setDataBatch(data) {
        Object.entries(data).forEach(([key, value]) => {
            this.setData(key, value);
        });
    }

    /**
     * 发射事件
     */
    emit(eventName, data) {
        const event = new CustomEvent(eventName, { detail: data });
        this.eventBus.dispatchEvent(event);
    }

    /**
     * 监听事件
     */
    on(eventName, callback) {
        this.eventBus.addEventListener(eventName, callback);
    }

    /**
     * 移除事件监听
     */
    off(eventName, callback) {
        this.eventBus.removeEventListener(eventName, callback);
    }

    // === 工具方法 ===

    /**
     * 获取嵌套值
     */
    getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => {
            return current && current[key] !== undefined ? current[key] : undefined;
        }, obj);
    }

    /**
     * 设置嵌套值
     */
    setNestedValue(obj, path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        const target = keys.reduce((current, key) => {
            if (!current[key] || typeof current[key] !== 'object') {
                current[key] = {};
            }
            return current[key];
        }, obj);
        
        target[lastKey] = value;
    }

    /**
     * 获取元素值
     */
    getElementValue(element) {
        switch (element.type) {
            case 'checkbox':
                return element.checked;
            case 'radio':
                return element.checked ? element.value : undefined;
            case 'number':
                return parseFloat(element.value) || 0;
            default:
                return element.value;
        }
    }

    /**
     * 设置元素值
     */
    setElementValue(element, value) {
        switch (element.type) {
            case 'checkbox':
                element.checked = Boolean(value);
                break;
            case 'radio':
                element.checked = element.value === String(value);
                break;
            default:
                if (element.tagName === 'SELECT') {
                    element.value = value;
                } else if (element.hasAttribute('contenteditable')) {
                    element.textContent = value;
                } else {
                    element.textContent = value;
                }
        }
    }

    /**
     * 获取元素事件类型
     */
    getElementEventType(element) {
        switch (element.type) {
            case 'checkbox':
            case 'radio':
                return 'change';
            case 'range':
                return 'input';
            default:
                return element.tagName === 'SELECT' ? 'change' : 'input';
        }
    }

    /**
     * 解析绑定表达式
     */
    parseBindExpression(expression) {
        // 简单的表达式解析，支持基本的属性访问和函数调用
        const dependencies = [];
        const regex = /\b([a-zA-Z_$][a-zA-Z0-9_$]*(?:\.[a-zA-Z_$][a-zA-Z0-9_$]*)*)\b/g;
        let match;
        
        while ((match = regex.exec(expression)) !== null) {
            dependencies.push(match[1]);
        }
        
        return {
            expression,
            dependencies: [...new Set(dependencies)]
        };
    }

    /**
     * 评估绑定表达式
     */
    evaluateBinding(binding) {
        try {
            // 创建安全的执行上下文
            const context = { ...this.reactiveData };
            
            // 使用Function构造器安全地执行表达式
            const func = new Function('context', `with(context) { return ${binding.expression}; }`);
            return func(context);
        } catch (error) {
            console.error('绑定表达式执行失败:', binding.expression, error);
            return '';
        }
    }

    /**
     * 设置错误处理
     */
    setupErrorHandling() {
        window.addEventListener('error', (event) => {
            console.error('全局错误:', event.error);
            this.emit('globalError', { error: event.error, event });
        });

        window.addEventListener('unhandledrejection', (event) => {
            console.error('未处理的Promise拒绝:', event.reason);
            this.emit('unhandledRejection', { reason: event.reason, event });
        });
    }
}

// === 核心组件实现 ===

/**
 * 消息组件
 */
class MessageComponent {
    constructor() {
        this.container = null;
        this.messages = new Map();
        this.messageId = 0;
    }

    init(manager) {
        this.manager = manager;
        this.createContainer();
    }

    createContainer() {
        this.container = document.createElement('div');
        this.container.className = 'message-container';
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 5000) {
        const id = ++this.messageId;
        const messageEl = this.createMessageElement(message, type, id);
        
        this.container.appendChild(messageEl);
        this.messages.set(id, messageEl);
        
        // 自动移除
        if (duration > 0) {
            setTimeout(() => this.remove(id), duration);
        }
        
        return id;
    }

    createMessageElement(message, type, id) {
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;
        messageEl.innerHTML = `
            <div class="message-content">
                <span class="message-text">${this.escapeHtml(message)}</span>
                <button class="message-close" onclick="window.ComponentManager.getComponent('message').remove(${id})">&times;</button>
            </div>
        `;
        
        // 添加动画
        messageEl.style.animation = 'slideInRight 0.3s ease';
        
        return messageEl;
    }

    remove(id) {
        const messageEl = this.messages.get(id);
        if (messageEl) {
            messageEl.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (messageEl.parentNode) {
                    messageEl.parentNode.removeChild(messageEl);
                }
                this.messages.delete(id);
            }, 300);
        }
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

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

/**
 * 模态框组件
 */
class ModalComponent {
    constructor() {
        this.modals = new Map();
        this.modalId = 0;
    }

    init(manager) {
        this.manager = manager;
    }

    show(options) {
        const id = ++this.modalId;
        const modal = this.createModal(options, id);
        
        document.body.appendChild(modal);
        this.modals.set(id, modal);
        
        // 显示动画
        setTimeout(() => modal.classList.add('show'), 10);
        
        // 阻止背景滚动
        document.body.classList.add('modal-open');
        
        return id;
    }

    createModal(options, id) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${options.title || '提示'}</h3>
                    <button class="modal-close" onclick="window.ComponentManager.getComponent('modal').close(${id})">&times;</button>
                </div>
                <div class="modal-body">
                    ${options.content || ''}
                </div>
                <div class="modal-footer">
                    ${this.createFooterButtons(options, id)}
                </div>
            </div>
        `;
        
        // 点击背景关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.close(id);
            }
        });
        
        return modal;
    }

    createFooterButtons(options, id) {
        let buttons = '';
        
        if (options.buttons) {
            buttons = options.buttons.map(btn => 
                `<button class="btn ${btn.class || 'btn-secondary'}" onclick="${btn.onclick || ''}">${btn.text}</button>`
            ).join('');
        } else {
            buttons = `<button class="btn btn-secondary" onclick="window.ComponentManager.getComponent('modal').close(${id})">关闭</button>`;
        }
        
        return buttons;
    }

    close(id) {
        const modal = this.modals.get(id);
        if (modal) {
            modal.classList.remove('show');
            setTimeout(() => {
                if (modal.parentNode) {
                    modal.parentNode.removeChild(modal);
                }
                this.modals.delete(id);
                
                // 如果没有其他模态框，恢复背景滚动
                if (this.modals.size === 0) {
                    document.body.classList.remove('modal-open');
                }
            }, 300);
        }
    }
}

/**
 * 抽屉组件
 */
class DrawerComponent {
    constructor() {
        this.drawers = new Map();
    }

    init(manager) {
        this.manager = manager;
    }

    open(drawerId) {
        const drawer = document.getElementById(drawerId);
        const overlay = document.getElementById('drawer-overlay');
        
        if (drawer && overlay) {
            drawer.classList.add('open');
            overlay.classList.add('open');
            document.body.classList.add('drawer-open');
        }
    }

    close(drawerId) {
        const drawer = document.getElementById(drawerId);
        const overlay = document.getElementById('drawer-overlay');
        
        if (drawer && overlay) {
            drawer.classList.remove('open');
            overlay.classList.remove('open');
            document.body.classList.remove('drawer-open');
        }
    }

    toggle(drawerId) {
        const drawer = document.getElementById(drawerId);
        if (drawer) {
            if (drawer.classList.contains('open')) {
                this.close(drawerId);
            } else {
                this.open(drawerId);
            }
        }
    }
}

/**
 * 数据表格组件
 */
class DataTableComponent {
    constructor() {
        this.tables = new Map();
    }

    init(manager) {
        this.manager = manager;
    }

    create(containerId, options) {
        const container = document.getElementById(containerId);
        if (!container) return null;
        
        const table = new DataTable(container, options, this.manager);
        this.tables.set(containerId, table);
        
        return table;
    }

    get(containerId) {
        return this.tables.get(containerId);
    }
}

/**
 * 数据表格类
 */
class DataTable {
    constructor(container, options, manager) {
        this.container = container;
        this.options = options;
        this.manager = manager;
        this.data = [];
        this.filteredData = [];
        this.currentPage = 1;
        this.pageSize = options.pageSize || 20;
        
        this.init();
    }

    init() {
        this.createTable();
        this.bindEvents();
    }

    createTable() {
        this.container.innerHTML = `
            <div class="data-table-wrapper">
                <table class="data-table">
                    <thead>
                        <tr>
                            ${this.options.columns.map(col => 
                                `<th>${col.title}</th>`
                            ).join('')}
                        </tr>
                    </thead>
                    <tbody class="data-table-body">
                    </tbody>
                </table>
                <div class="data-table-pagination">
                    <button class="btn btn-sm" onclick="this.previousPage()">上一页</button>
                    <span class="pagination-info"></span>
                    <button class="btn btn-sm" onclick="this.nextPage()">下一页</button>
                </div>
            </div>
        `;
    }

    setData(data) {
        this.data = data;
        this.filteredData = [...data];
        this.render();
    }

    render() {
        const tbody = this.container.querySelector('.data-table-body');
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const pageData = this.filteredData.slice(startIndex, endIndex);
        
        tbody.innerHTML = pageData.map(row => 
            `<tr>${this.options.columns.map(col => 
                `<td>${this.renderCell(row, col)}</td>`
            ).join('')}</tr>`
        ).join('');
        
        this.updatePagination();
    }

    renderCell(row, column) {
        if (column.render) {
            return column.render(row[column.key], row);
        }
        return row[column.key] || '';
    }

    updatePagination() {
        const totalPages = Math.ceil(this.filteredData.length / this.pageSize);
        const paginationInfo = this.container.querySelector('.pagination-info');
        paginationInfo.textContent = `第 ${this.currentPage} 页，共 ${totalPages} 页`;
    }

    filter(filterFn) {
        this.filteredData = this.data.filter(filterFn);
        this.currentPage = 1;
        this.render();
    }

    bindEvents() {
        // 绑定分页事件等
    }
}

/**
 * 表单组件
 */
class FormComponent {
    constructor() {
        this.forms = new Map();
    }

    init(manager) {
        this.manager = manager;
    }

    create(formId, options) {
        const form = document.getElementById(formId);
        if (!form) return null;
        
        const formInstance = new Form(form, options, this.manager);
        this.forms.set(formId, formInstance);
        
        return formInstance;
    }

    get(formId) {
        return this.forms.get(formId);
    }
}

/**
 * 表单类
 */
class Form {
    constructor(element, options, manager) {
        this.element = element;
        this.options = options;
        this.manager = manager;
        this.validators = new Map();
        
        this.init();
    }

    init() {
        this.bindValidation();
        this.bindSubmit();
    }

    bindValidation() {
        const inputs = this.element.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('input', () => this.clearFieldError(input));
        });
    }

    bindSubmit() {
        this.element.addEventListener('submit', (e) => {
            e.preventDefault();
            if (this.validate()) {
                if (this.options.onSubmit) {
                    this.options.onSubmit(this.getData());
                }
            }
        });
    }

    validateField(field) {
        const rules = this.options.rules && this.options.rules[field.name];
        if (!rules) return true;
        
        for (const rule of rules) {
            if (!this.checkRule(field.value, rule)) {
                this.showFieldError(field, rule.message);
                return false;
            }
        }
        
        this.clearFieldError(field);
        return true;
    }

    checkRule(value, rule) {
        switch (rule.type) {
            case 'required':
                return value.trim() !== '';
            case 'email':
                return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
            case 'minLength':
                return value.length >= rule.value;
            case 'maxLength':
                return value.length <= rule.value;
            default:
                return true;
        }
    }

    showFieldError(field, message) {
        this.clearFieldError(field);
        
        const errorEl = document.createElement('span');
        errorEl.className = 'field-error';
        errorEl.textContent = message;
        
        field.classList.add('error');
        field.parentNode.appendChild(errorEl);
    }

    clearFieldError(field) {
        field.classList.remove('error');
        const errorEl = field.parentNode.querySelector('.field-error');
        if (errorEl) {
            errorEl.remove();
        }
    }

    validate() {
        const inputs = this.element.querySelectorAll('input, select, textarea');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });
        
        return isValid;
    }

    getData() {
        const formData = new FormData(this.element);
        const data = {};
        
        for (const [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        return data;
    }

    setData(data) {
        Object.entries(data).forEach(([key, value]) => {
            const field = this.element.querySelector(`[name="${key}"]`);
            if (field) {
                field.value = value;
            }
        });
    }
}

/**
 * 加载组件
 */
class LoadingComponent {
    constructor() {
        this.loadingElements = new Set();
    }

    init(manager) {
        this.manager = manager;
    }

    show(target) {
        const element = typeof target === 'string' ? document.getElementById(target) : target;
        if (!element) return;
        
        element.classList.add('loading');
        this.loadingElements.add(element);
    }

    hide(target) {
        const element = typeof target === 'string' ? document.getElementById(target) : target;
        if (!element) return;
        
        element.classList.remove('loading');
        this.loadingElements.delete(element);
    }

    hideAll() {
        this.loadingElements.forEach(element => {
            element.classList.remove('loading');
        });
        this.loadingElements.clear();
    }
}

// 创建全局实例
window.ComponentManager = new EnhancedComponentManager();

// 兼容性：保持原有接口
if (!window.ComponentManager.getComponent('message')) {
    console.warn('消息组件未正确初始化，使用兼容模式');
}

console.log('增强版组件管理器已加载');