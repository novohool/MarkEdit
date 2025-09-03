/**
 * 前端统一错误处理工具
 * 
 * 提供统一的错误处理、用户反馈和错误恢复机制
 */

class FrontendErrorHandler {
    constructor() {
        this.errorQueue = [];
        this.maxErrorQueue = 50;
        this.retryAttempts = new Map();
        this.maxRetryAttempts = 3;
        
        // 初始化全局错误处理
        this.initGlobalErrorHandling();
        
        // 创建错误显示容器
        this.createErrorContainer();
    }
    
    /**
     * 初始化全局错误处理
     */
    initGlobalErrorHandling() {
        // 捕获未处理的JavaScript错误
        window.addEventListener('error', (event) => {
            this.handleJavaScriptError(event.error, {
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno
            });
        });
        
        // 捕获未处理的Promise拒绝
        window.addEventListener('unhandledrejection', (event) => {
            this.handlePromiseRejection(event.reason);
        });
        
        // 捕获网络错误
        window.addEventListener('offline', () => {
            this.showNetworkError('网络连接已断开，请检查网络连接');
        });
        
        window.addEventListener('online', () => {
            this.showSuccessMessage('网络连接已恢复');
        });
    }
    
    /**
     * 创建错误显示容器
     */
    createErrorContainer() {
        if (document.getElementById('error-notification-container')) {
            return;
        }
        
        const container = document.createElement('div');
        container.id = 'error-notification-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
            pointer-events: none;
        `;
        
        document.body.appendChild(container);
    }
    
    /**
     * 处理API错误
     */
    async handleApiError(response, context = {}) {
        let errorData;
        
        try {
            errorData = await response.json();
        } catch (e) {
            errorData = {
                message: `HTTP ${response.status}: ${response.statusText}`,
                error_id: 'unknown',
                recovery_suggestions: ['请稍后重试', '如果问题持续存在，请联系管理员']
            };
        }
        
        const errorInfo = {
            type: 'api_error',
            status: response.status,
            url: response.url,
            message: errorData.message || errorData.detail || '未知错误',
            errorId: errorData.error_id,
            recoverySuggestions: errorData.recovery_suggestions || [],
            context: context,
            timestamp: new Date().toISOString()
        };
        
        this.logError(errorInfo);
        this.showErrorNotification(errorInfo);
        
        return errorInfo;
    }
    
    /**
     * 处理JavaScript错误
     */
    handleJavaScriptError(error, context = {}) {
        const errorInfo = {
            type: 'javascript_error',
            message: error.message || '未知JavaScript错误',
            stack: error.stack,
            context: context,
            timestamp: new Date().toISOString()
        };
        
        this.logError(errorInfo);
        
        // 对于严重错误，显示通知
        if (this.isCriticalError(error)) {
            this.showErrorNotification({
                ...errorInfo,
                recoverySuggestions: [
                    '请刷新页面重试',
                    '清除浏览器缓存',
                    '如果问题持续存在，请联系技术支持'
                ]
            });
        }
        
        return errorInfo;
    }
    
    /**
     * 处理Promise拒绝
     */
    handlePromiseRejection(reason) {
        const errorInfo = {
            type: 'promise_rejection',
            message: reason?.message || String(reason) || '未处理的Promise拒绝',
            stack: reason?.stack,
            timestamp: new Date().toISOString()
        };
        
        this.logError(errorInfo);
        
        return errorInfo;
    }
    
    /**
     * 显示网络错误
     */
    showNetworkError(message) {
        this.showErrorNotification({
            type: 'network_error',
            message: message,
            recoverySuggestions: [
                '检查网络连接',
                '尝试刷新页面',
                '联系网络管理员'
            ]
        });
    }
    
    /**
     * 显示错误通知
     */
    showErrorNotification(errorInfo) {
        const notification = this.createNotificationElement(errorInfo);
        const container = document.getElementById('error-notification-container');
        
        if (container) {
            container.appendChild(notification);
            
            // 自动移除通知
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 8080);
        }
    }
    
    /**
     * 显示成功消息
     */
    showSuccessMessage(message) {
        const notification = this.createNotificationElement({
            type: 'success',
            message: message
        });
        
        const container = document.getElementById('error-notification-container');
        if (container) {
            container.appendChild(notification);
            
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 3000);
        }
    }
    
    /**
     * 创建通知元素
     */
    createNotificationElement(errorInfo) {
        const notification = document.createElement('div');
        const isSuccess = errorInfo.type === 'success';
        
        notification.style.cssText = `
            background: ${isSuccess ? '#d4edda' : '#f8d7da'};
            color: ${isSuccess ? '#155724' : '#721c24'};
            border: 1px solid ${isSuccess ? '#c3e6cb' : '#f5c6cb'};
            border-radius: 6px;
            padding: 12px 16px;
            margin-bottom: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            pointer-events: auto;
            animation: slideIn 0.3s ease-out;
            position: relative;
            font-size: 14px;
            line-height: 1.4;
        `;
        
        const icon = isSuccess ? '✅' : '⚠️';
        let content = `
            <div style="display: flex; align-items: flex-start; gap: 8px;">
                <span style="font-size: 16px;">${icon}</span>
                <div style="flex: 1;">
                    <div style="font-weight: 600; margin-bottom: 4px;">
                        ${isSuccess ? '操作成功' : '操作失败'}
                    </div>
                    <div>${errorInfo.message}</div>
        `;
        
        if (errorInfo.recoverySuggestions && errorInfo.recoverySuggestions.length > 0) {
            content += `
                <div style="margin-top: 8px; font-size: 12px; opacity: 0.8;">
                    <strong>建议:</strong>
                    <ul style="margin: 4px 0 0 16px; padding: 0;">
                        ${errorInfo.recoverySuggestions.map(suggestion => 
                            `<li>${suggestion}</li>`
                        ).join('')}
                    </ul>
                </div>
            `;
        }
        
        if (errorInfo.errorId) {
            content += `
                <div style="margin-top: 8px; font-size: 11px; opacity: 0.6; font-family: monospace;">
                    错误ID: ${errorInfo.errorId}
                </div>
            `;
        }
        
        content += `
                </div>
                <button onclick="this.parentNode.parentNode.remove()" 
                        style="background: none; border: none; font-size: 18px; cursor: pointer; opacity: 0.6; padding: 0; margin-left: 8px;">
                    ×
                </button>
            </div>
        `;
        
        notification.innerHTML = content;
        
        return notification;
    }
    
    /**
     * 记录错误
     */
    logError(errorInfo) {
        // 添加到错误队列
        this.errorQueue.push(errorInfo);
        
        // 限制队列大小
        if (this.errorQueue.length > this.maxErrorQueue) {
            this.errorQueue.shift();
        }
        
        // 控制台输出
        console.error('Frontend Error:', errorInfo);
        
        // 发送到服务器（可选）
        this.sendErrorToServer(errorInfo);
    }
    
    /**
     * 发送错误到服务器
     */
    async sendErrorToServer(errorInfo) {
        try {
            await fetch('/api/frontend-error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(errorInfo)
            });
        } catch (e) {
            // 静默失败，避免无限循环
            console.warn('Failed to send error to server:', e);
        }
    }
    
    /**
     * 判断是否为严重错误
     */
    isCriticalError(error) {
        const criticalPatterns = [
            /cannot read property/i,
            /undefined is not a function/i,
            /network error/i,
            /failed to fetch/i
        ];
        
        return criticalPatterns.some(pattern => 
            pattern.test(error.message || '')
        );
    }
    
    /**
     * 带重试的API请求
     */
    async fetchWithRetry(url, options = {}, maxRetries = this.maxRetryAttempts) {
        const requestId = `${url}_${Date.now()}`;
        let lastError;
        
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                const response = await fetch(url, options);
                
                if (!response.ok) {
                    const errorInfo = await this.handleApiError(response, {
                        attempt: attempt + 1,
                        maxRetries: maxRetries + 1
                    });
                    
                    // 对于某些错误类型，不进行重试
                    if (response.status === 401 || response.status === 403 || response.status === 404) {
                        throw new Error(errorInfo.message);
                    }
                    
                    lastError = new Error(errorInfo.message);
                } else {
                    // 成功，清除重试计数
                    this.retryAttempts.delete(requestId);
                    return response;
                }
            } catch (error) {
                lastError = error;
                
                if (attempt < maxRetries) {
                    // 等待后重试
                    const delay = Math.pow(2, attempt) * 1000; // 指数退避
                    await new Promise(resolve => setTimeout(resolve, delay));
                    
                    console.log(`Retrying request to ${url}, attempt ${attempt + 2}/${maxRetries + 1}`);
                }
            }
        }
        
        // 所有重试都失败了
        this.retryAttempts.set(requestId, maxRetries + 1);
        throw lastError;
    }
    
    /**
     * 获取错误统计
     */
    getErrorStats() {
        const stats = {
            totalErrors: this.errorQueue.length,
            byType: {},
            recentErrors: this.errorQueue.slice(-10)
        };
        
        this.errorQueue.forEach(error => {
            stats.byType[error.type] = (stats.byType[error.type] || 0) + 1;
        });
        
        return stats;
    }
    
    /**
     * 清除错误队列
     */
    clearErrorQueue() {
        this.errorQueue = [];
        this.retryAttempts.clear();
    }
}

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);

// 创建全局实例
window.errorHandler = new FrontendErrorHandler();

// 导出工具函数
window.handleApiError = (response, context) => window.errorHandler.handleApiError(response, context);
window.showErrorMessage = (message, suggestions) => window.errorHandler.showErrorNotification({
    type: 'user_error',
    message: message,
    recoverySuggestions: suggestions || []
});
window.showSuccessMessage = (message) => window.errorHandler.showSuccessMessage(message);
window.fetchWithRetry = (url, options, maxRetries) => window.errorHandler.fetchWithRetry(url, options, maxRetries);