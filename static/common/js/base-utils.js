/**
 * MarkEdit 统一JavaScript工具库
 * 
 * 这个模块提供统一的基础功能，减少代码重复，提高代码质量和可维护性
 */

// ==========================================
// 工具类定义
// ==========================================

/**
 * 消息显示管理器
 */
class MessageManager {
    constructor() {
        this.messageContainer = null;
        // 延迟初始化，等DOM加载完成
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initMessageContainer());
        } else {
            this.initMessageContainer();
        }
    }
    
    initMessageContainer() {
        // 创建消息容器
        if (!this.messageContainer && document.body) {
            this.messageContainer = document.createElement('div');
            this.messageContainer.id = 'message-container';
            this.messageContainer.className = 'message-container';
            document.body.appendChild(this.messageContainer);
        }
    }
    
    /**
     * 显示消息
     * @param {string} message 消息内容
     * @param {string} type 消息类型: success, error, warning, info
     * @param {number} duration 显示时长(毫秒)，0表示不自动消失
     */
    show(message, type = 'info', duration = 3000) {
        // 确保消息容器已初始化
        if (!this.messageContainer) {
            this.initMessageContainer();
            // 如果仍然没有初始化成功，可能是DOM还没准备好
            if (!this.messageContainer) {
                console.warn('消息容器初始化失败，DOM可能还没有准备好');
                return null;
            }
        }
        
        const messageElement = document.createElement('div');
        messageElement.className = `message message-${type}`;
        
        // 创建消息内容
        const content = document.createElement('div');
        content.className = 'message-content';
        content.textContent = message;
        
        // 创建关闭按钮
        const closeButton = document.createElement('button');
        closeButton.className = 'message-close';
        closeButton.innerHTML = '×';
        closeButton.onclick = () => this.remove(messageElement);
        
        messageElement.appendChild(content);
        messageElement.appendChild(closeButton);
        
        // 添加到容器
        this.messageContainer.appendChild(messageElement);
        
        // 添加显示动画
        setTimeout(() => messageElement.classList.add('show'), 10);
        
        // 自动移除
        if (duration > 0) {
            setTimeout(() => this.remove(messageElement), duration);
        }
        
        return messageElement;
    }
    
    /**
     * 移除消息
     */
    remove(messageElement) {
        if (messageElement && messageElement.parentNode) {
            messageElement.classList.add('hide');
            setTimeout(() => {
                if (messageElement.parentNode) {
                    messageElement.parentNode.removeChild(messageElement);
                }
            }, 300);
        }
    }
    
    /**
     * 清除所有消息
     */
    clear() {
        if (this.messageContainer) {
            this.messageContainer.innerHTML = '';
        }
    }
    
    // 便捷方法
    success(message, duration = 3000) {
        return this.show(message, 'success', duration);
    }
    
    error(message, duration = 5000) {
        return this.show(message, 'error', duration);
    }
    
    warning(message, duration = 4000) {
        return this.show(message, 'warning', duration);
    }
    
    info(message, duration = 3000) {
        return this.show(message, 'info', duration);
    }
}

/**
 * API请求管理器
 */
class APIManager {
    constructor() {
        this.baseURL = '';
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };
    }
    
    /**
     * 通用API请求方法
     */
    async request(url, options = {}) {
        const config = {
            headers: { ...this.defaultHeaders, ...options.headers },
            ...options
        };
        
        try {
            const response = await fetch(this.baseURL + url, config);
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.detail || result.message || `HTTP ${response.status}`);
            }
            
            return result;
        } catch (error) {
            console.error(`API请求失败 [${config.method || 'GET'}] ${url}:`, error);
            throw error;
        }
    }
    
    // HTTP方法的便捷封装
    async get(url, params = {}) {
        const searchParams = new URLSearchParams(params);
        const urlWithParams = searchParams.toString() ? `${url}?${searchParams}` : url;
        return this.request(urlWithParams, { method: 'GET' });
    }
    
    async post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    async put(url, data = {}) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }
    
    async delete(url) {
        return this.request(url, { method: 'DELETE' });
    }
    
    /**
     * 文件上传请求
     */
    async uploadFile(url, formData, onProgress = null) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            // 上传进度监听
            if (onProgress && xhr.upload) {
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        onProgress(percentComplete, e.loaded, e.total);
                    }
                });
            }
            
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const result = JSON.parse(xhr.responseText);
                        resolve(result);
                    } catch (e) {
                        resolve(xhr.responseText);
                    }
                } else {
                    try {
                        const error = JSON.parse(xhr.responseText);
                        reject(new Error(error.detail || error.message || `HTTP ${xhr.status}`));
                    } catch (e) {
                        reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                    }
                }
            });
            
            xhr.addEventListener('error', () => {
                reject(new Error('网络错误'));
            });
            
            xhr.open('POST', this.baseURL + url);
            xhr.send(formData);
        });
    }
}

/**
 * DOM操作工具类
 */
class DOMUtils {
    /**
     * 安全地获取元素
     */
    static getElementById(id) {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(`Element with id '${id}' not found`);
        }
        return element;
    }
    
    /**
     * 显示/隐藏元素
     */
    static show(element, display = 'block') {
        if (typeof element === 'string') {
            element = this.getElementById(element);
        }
        if (element) {
            element.style.display = display;
        }
    }
    
    static hide(element) {
        if (typeof element === 'string') {
            element = this.getElementById(element);
        }
        if (element) {
            element.style.display = 'none';
        }
    }
    
    static toggle(element, display = 'block') {
        if (typeof element === 'string') {
            element = this.getElementById(element);
        }
        if (element) {
            if (element.style.display === 'none' || !element.style.display) {
                this.show(element, display);
            } else {
                this.hide(element);
            }
        }
    }
    
    /**
     * 批量显示/隐藏元素
     */
    static showAll(elements, display = 'block') {
        elements.forEach(el => this.show(el, display));
    }
    
    static hideAll(elements) {
        elements.forEach(el => this.hide(el));
    }
    
    /**
     * 清空元素内容
     */
    static clear(element) {
        if (typeof element === 'string') {
            element = this.getElementById(element);
        }
        if (element) {
            element.innerHTML = '';
        }
    }
    
    /**
     * 添加事件监听器（支持事件委托）
     */
    static on(element, event, selector, handler) {
        if (typeof selector === 'function') {
            // 直接事件绑定
            handler = selector;
            selector = null;
        }
        
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) return;
        
        if (selector) {
            // 事件委托
            element.addEventListener(event, (e) => {
                const target = e.target.closest(selector);
                if (target) {
                    handler.call(target, e);
                }
            });
        } else {
            // 直接绑定
            element.addEventListener(event, handler);
        }
    }
    
    /**
     * 创建元素
     */
    static createElement(tag, attributes = {}, content = '') {
        const element = document.createElement(tag);
        
        // 设置属性
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className' || key === 'class') {
                element.className = value;
            } else if (key.startsWith('data-')) {
                element.setAttribute(key, value);
            } else {
                element[key] = value;
            }
        });
        
        // 设置内容
        if (content) {
            if (typeof content === 'string') {
                element.innerHTML = content;
            } else {
                element.appendChild(content);
            }
        }
        
        return element;
    }
}

/**
 * 表单工具类
 */
class FormUtils {
    /**
     * 获取表单数据
     */
    static getFormData(form) {
        if (typeof form === 'string') {
            form = document.getElementById(form) || document.querySelector(form);
        }
        
        if (!form) return {};
        
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            // 处理复选框和单选按钮
            if (form.elements[key]) {
                const element = form.elements[key];
                if (element.type === 'checkbox') {
                    if (!data[key]) data[key] = [];
                    if (element.checked) {
                        data[key].push(value);
                    }
                } else if (element.type === 'radio') {
                    if (element.checked) {
                        data[key] = value;
                    }
                } else {
                    data[key] = value;
                }
            } else {
                data[key] = value;
            }
        }
        
        return data;
    }
    
    /**
     * 设置表单数据
     */
    static setFormData(form, data) {
        if (typeof form === 'string') {
            form = document.getElementById(form) || document.querySelector(form);
        }
        
        if (!form || !data) return;
        
        Object.entries(data).forEach(([key, value]) => {
            const element = form.elements[key];
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = Array.isArray(value) ? value.includes(element.value) : !!value;
                } else if (element.type === 'radio') {
                    if (element.value === value) {
                        element.checked = true;
                    }
                } else {
                    element.value = value || '';
                }
            }
        });
    }
    
    /**
     * 重置表单
     */
    static reset(form) {
        if (typeof form === 'string') {
            form = document.getElementById(form) || document.querySelector(form);
        }
        
        if (form) {
            form.reset();
        }
    }
    
    /**
     * 表单验证
     */
    static validate(form, rules = {}) {
        if (typeof form === 'string') {
            form = document.getElementById(form) || document.querySelector(form);
        }
        
        if (!form) return { valid: false, errors: ['表单不存在'] };
        
        const data = this.getFormData(form);
        const errors = [];
        
        Object.entries(rules).forEach(([field, rule]) => {
            const value = data[field];
            
            if (rule.required && (!value || value.toString().trim() === '')) {
                errors.push(`${rule.label || field} 为必填项`);
            }
            
            if (value && rule.minLength && value.length < rule.minLength) {
                errors.push(`${rule.label || field} 至少需要 ${rule.minLength} 个字符`);
            }
            
            if (value && rule.maxLength && value.length > rule.maxLength) {
                errors.push(`${rule.label || field} 不能超过 ${rule.maxLength} 个字符`);
            }
            
            if (value && rule.pattern && !rule.pattern.test(value)) {
                errors.push(`${rule.label || field} 格式不正确`);
            }
            
            if (value && rule.validator && !rule.validator(value)) {
                errors.push(`${rule.label || field} ${rule.message || '验证失败'}`);
            }
        });
        
        return {
            valid: errors.length === 0,
            errors: errors,
            data: data
        };
    }
}

/**
 * 格式化工具类
 */
class FormatUtils {
    /**
     * 格式化日期
     */
    static formatDate(dateString, format = 'YYYY-MM-DD HH:mm:ss') {
        if (!dateString) return '';
        
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return dateString;
        
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        
        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    }
    
    /**
     * 格式化文件大小
     */
    static formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
    
    /**
     * 格式化时间持续
     */
    static formatDuration(seconds) {
        if (seconds < 60) return `${seconds}秒`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时`;
        return `${Math.floor(seconds / 86400)}天`;
    }
    
    /**
     * 截断文本
     */
    static truncate(text, maxLength = 50, suffix = '...') {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength - suffix.length) + suffix;
    }
}

// ==========================================
// 全局实例
// ==========================================

// 延迟创建全局实例，避免DOM未加载完成时的错误
let messageManager = null;
let apiManager = null;

// 获取MessageManager实例的函数
function getMessageManager() {
    if (!messageManager) {
        messageManager = new MessageManager();
    }
    return messageManager;
}

// 获取APIManager实例的函数
function getAPIManager() {
    if (!apiManager) {
        apiManager = new APIManager();
    }
    return apiManager;
}

// 兼容性：创建属性来模拟直接访问
Object.defineProperty(window, 'messageManager', {
    get: getMessageManager
});

Object.defineProperty(window, 'apiManager', {
    get: getAPIManager
});

// ==========================================
// 向后兼容的全局函数
// ==========================================

/**
 * 显示消息 (向后兼容)
 */
function showMessage(message, type = 'info', duration = 3000) {
    return getMessageManager().show(message, type, duration);
}

/**
 * 格式化日期 (向后兼容)
 */
function formatDate(dateString, format = 'YYYY-MM-DD HH:mm:ss') {
    return FormatUtils.formatDate(dateString, format);
}

/**
 * 格式化文件大小 (向后兼容)
 */
function formatBytes(bytes, decimals = 2) {
    return FormatUtils.formatBytes(bytes, decimals);
}

// ==========================================
// 统一的事件绑定工具
// ==========================================

/**
 * 统一的事件绑定管理器
 */
class EventBindingManager {
    constructor() {
        this.bindings = new Map();
    }
    
    /**
     * 绑定按钮组事件
     */
    bindButtonGroup(container, config) {
        const containerElement = typeof container === 'string' 
            ? document.querySelector(container) 
            : container;
            
        if (!containerElement) return;
        
        // 绑定编辑按钮
        if (config.edit) {
            DOMUtils.on(containerElement, 'click', '.btn-edit', config.edit);
        }
        
        // 绑定删除按钮
        if (config.delete) {
            DOMUtils.on(containerElement, 'click', '.btn-delete', config.delete);
        }
        
        // 绑定其他自定义按钮
        if (config.custom) {
            Object.entries(config.custom).forEach(([selector, handler]) => {
                DOMUtils.on(containerElement, 'click', selector, handler);
            });
        }
    }
    
    /**
     * 绑定表单事件
     */
    bindForm(form, config) {
        const formElement = typeof form === 'string' 
            ? document.querySelector(form) 
            : form;
            
        if (!formElement) return;
        
        // 绑定提交事件
        if (config.submit) {
            formElement.addEventListener('submit', (e) => {
                e.preventDefault();
                config.submit(e, FormUtils.getFormData(formElement));
            });
        }
        
        // 绑定重置事件
        if (config.reset) {
            formElement.addEventListener('reset', config.reset);
        }
        
        // 绑定字段变化事件
        if (config.fieldChange) {
            Object.entries(config.fieldChange).forEach(([field, handler]) => {
                const fieldElement = formElement.elements[field];
                if (fieldElement) {
                    fieldElement.addEventListener('change', handler);
                }
            });
        }
    }
}

// 全局事件绑定管理器
let eventBindingManager = null;

// 获取EventBindingManager实例的函数
function getEventBindingManager() {
    if (!eventBindingManager) {
        eventBindingManager = new EventBindingManager();
    }
    return eventBindingManager;
}

// 兼容性：创建属性来模拟直接访问
Object.defineProperty(window, 'eventBindingManager', {
    get: getEventBindingManager
});

// ==========================================
// 导出到全局作用域
// ==========================================

// 将工具类添加到全局作用域
window.MarkEditUtils = {
    MessageManager,
    APIManager,
    DOMUtils,
    FormUtils,
    FormatUtils,
    EventBindingManager,
    
    // 全局实例获取函数
    get messageManager() { return getMessageManager(); },
    get apiManager() { return getAPIManager(); },
    get eventBindingManager() { return getEventBindingManager(); }
};

// 向后兼容的全局函数
window.showMessage = showMessage;
window.formatDate = formatDate;
window.formatBytes = formatBytes;