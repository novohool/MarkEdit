// MarkEdit 公共函数库
// 包含所有主题共享的JavaScript函数

// 全局变量
let currentFilePath = null;
let currentFileType = null;
let currentFileEncoding = null;
let currentFileArea = null; // 'src' 或 'build'
let codeMirrorEditor = null; // CodeMirror 编辑器实例
let userInfo = {
    username: null, // 用户名
    role: 'user', // 默认角色为普通用户
    isAdmin: false,
    permissions: [], // 用户权限列表
    roles: [], // 用户角色列表
    userType: 'user' // 用户类型
};

// 上传进度管理器
class UploadProgressManager {
    constructor() {
        this.activeUploads = new Map();
        this.progressContainer = null;
        // 等待DOM加载完成后再创建进度容器
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.createProgressContainer());
        } else {
            this.createProgressContainer();
        }
    }
    
    createProgressContainer() {
        if (this.progressContainer || !document.body) {
            return;
        }
        
        this.progressContainer = document.createElement('div');
        this.progressContainer.className = 'upload-progress';
        this.progressContainer.innerHTML = `
            <div class="upload-progress-header">
                <span class="upload-progress-icon">📄</span>
                <span class="upload-progress-title">文件上传</span>
            </div>
            <div class="upload-progress-content">
                <div class="upload-progress-text">正在准备...</div>
                <div class="upload-progress-bar">
                    <div class="upload-progress-fill" style="width: 0%"></div>
                </div>
                <div class="upload-progress-details">
                    <span class="upload-current">0</span> / <span class="upload-total">0</span>
                    <span class="upload-percentage">0%</span>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.progressContainer);
    }
    
    showProgress(uploadId, fileName, total = 1) {
        // 确保进度容器已创建
        if (!this.progressContainer) {
            this.createProgressContainer();
        }
        
        // 如果仍然没有进度容器（DOM未准备好），则等待
        if (!this.progressContainer) {
            setTimeout(() => this.showProgress(uploadId, fileName, total), 100);
            return;
        }
        
        this.activeUploads.set(uploadId, {
            fileName,
            total,
            current: 0,
            status: 'preparing'
        });
        
        this.updateDisplay();
        this.progressContainer.classList.add('show');
    }
    
    updateProgress(uploadId, current, status = 'uploading') {
        const upload = this.activeUploads.get(uploadId);
        if (upload) {
            upload.current = current;
            upload.status = status;
            this.updateDisplay();
        }
    }
    
    completeUpload(uploadId, success = true) {
        const upload = this.activeUploads.get(uploadId);
        if (upload) {
            upload.status = success ? 'completed' : 'error';
            upload.current = upload.total;
            this.updateDisplay();
            
            // 延迟隐藏，让用户看到结果
            setTimeout(() => {
                this.activeUploads.delete(uploadId);
                if (this.activeUploads.size === 0) {
                    this.hideProgress();
                } else {
                    this.updateDisplay();
                }
            }, 2000);
        }
    }
    
    updateDisplay() {
        if (this.activeUploads.size === 0 || !this.progressContainer) {
            return;
        }
        
        const uploads = Array.from(this.activeUploads.values());
        const totalFiles = uploads.reduce((sum, upload) => sum + upload.total, 0);
        const completedFiles = uploads.reduce((sum, upload) => sum + upload.current, 0);
        const percentage = totalFiles > 0 ? Math.round((completedFiles / totalFiles) * 100) : 0;
        
        const textElement = this.progressContainer.querySelector('.upload-progress-text');
        const fillElement = this.progressContainer.querySelector('.upload-progress-fill');
        const currentElement = this.progressContainer.querySelector('.upload-current');
        const totalElement = this.progressContainer.querySelector('.upload-total');
        const percentageElement = this.progressContainer.querySelector('.upload-percentage');
        
        if (uploads.length === 1) {
            const upload = uploads[0];
            textElement.textContent = `正在上传: ${upload.fileName}`;
        } else {
            textElement.textContent = `批量上传进行中...`;
        }
        
        fillElement.style.width = `${percentage}%`;
        currentElement.textContent = completedFiles;
        totalElement.textContent = totalFiles;
        percentageElement.textContent = `${percentage}%`;
    }
    
    hideProgress() {
        if (this.progressContainer) {
            this.progressContainer.classList.remove('show');
        }
    }
}

// 创建全局上传进度管理器
const uploadProgressManager = new UploadProgressManager();

// 显示消息函数
function showMessage(message, type) {
    // 创建消息元素
    const messageElement = document.createElement('div');
    messageElement.className = `message message-${type}`;
    messageElement.textContent = message;
    
    // 确保document.body存在后再添加到页面
    function addToBody() {
        if (document.body) {
            document.body.appendChild(messageElement);
            
            // 3秒后自动移除
            setTimeout(() => {
                if (messageElement.parentNode) {
                    messageElement.parentNode.removeChild(messageElement);
                }
            }, 3000);
        } else {
            // 如果body还未加载，等待100ms后重试
            setTimeout(addToBody, 100);
        }
    }
    
    addToBody();
}

// 管理面板下拉菜单控制函数 - 完全模仿用户面板
function toggleAdminPanelDropdown() {
    const dropdown = document.getElementById('admin-panel-dropdown');
    if (dropdown) {
        const isOpen = dropdown.classList.contains('open');
        if (isOpen) {
            closeAdminPanelDropdown();
        } else {
            openAdminPanelDropdown();
        }
    }
}

// 打开管理面板下拉菜单
function openAdminPanelDropdown() {
    const dropdown = document.getElementById('admin-panel-dropdown');
    console.log('common.js openAdminPanelDropdown 被调用，dropdown:', dropdown);
    
    if (dropdown) {
        console.log('common.js dropdown 存在，添加 open 类');
        
        // 关闭其他下拉菜单
        document.querySelectorAll('.dropdown.open').forEach(otherDropdown => {
            if (otherDropdown !== dropdown) {
                otherDropdown.classList.remove('open');
            }
        });

        dropdown.classList.add('open');
        console.log('common.js dropdown 类名:', dropdown.className);
        
        // 检查dropdown-content元素
        const dropdownContent = dropdown.querySelector('.dropdown-content');
        console.log('common.js dropdown-content:', dropdownContent);
        if (dropdownContent) {
            console.log('common.js dropdown-content 样式:', window.getComputedStyle(dropdownContent).display);
            console.log('common.js dropdown-content 可见性:', window.getComputedStyle(dropdownContent).visibility);
            console.log('common.js dropdown-content 透明度:', window.getComputedStyle(dropdownContent).opacity);
        }
    } else {
        console.error('common.js admin-panel-dropdown 元素未找到');
    }
}

// 关闭管理面板下拉菜单
function closeAdminPanelDropdown() {
    const dropdown = document.getElementById('admin-panel-dropdown');
    if (dropdown) {
        dropdown.classList.remove('open');
    }
}

// 初始化编辑器状态 - 现在由统一编辑器管理器处理
function initializeEditor() {
    // 检查统一编辑器管理器是否可用
    if (window.unifiedEditorManager && window.unifiedEditorManager.isInitialized) {
        console.log('Using UnifiedEditorManager for editor initialization');
        return;
    }
    
    // 向后兼容：如果统一管理器不可用，使用原有逻辑
    console.log('Falling back to legacy editor initialization');
    
    // 隐藏所有视图
    const elements = ['editor', 'image-viewer', 'binary-viewer', 'preview-container'];
    elements.forEach(id => {
        const element = document.getElementById(id);
        if (element) element.style.display = 'none';
    });
    
    // 隐藏预览按钮
    const previewBtn = document.getElementById('preview-btn');
    if (previewBtn) previewBtn.style.display = 'none';
    
    // 禁用删除按钮
    const deleteBtn = document.getElementById('delete-btn');
    if (deleteBtn) deleteBtn.disabled = true;
}

// 初始化CodeMirror编辑器 - 现在由统一编辑器管理器处理
function initializeCodeMirror() {
    // 检查统一编辑器管理器是否可用
    if (window.unifiedEditorManager && window.unifiedEditorManager.codeMirrorEditor) {
        console.log('CodeMirror already initialized by UnifiedEditorManager');
        return;
    }
    
    // 向后兼容：如果统一管理器不可用，使用原有逻辑
    console.log('Falling back to legacy CodeMirror initialization');
    
    const editorElement = document.getElementById('codemirror-editor');
    if (!editorElement) return;
    
    // 创建CodeMirror实例
    codeMirrorEditor = CodeMirror(editorElement, {
        value: "",
        mode: "text/plain",
        lineNumbers: true,
        theme: "default",
        indentUnit: 4,
        smartIndent: true,
        tabSize: 4,
        indentWithTabs: false,
        electricChars: true,
        autoCloseBrackets: true,
        matchBrackets: true,
        viewportMargin: Infinity,
        lineWrapping: true
    });
    
    // 绑定编辑器键盘事件（Ctrl+S保存）
    codeMirrorEditor.on("keydown", function(cm, e) {
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            saveFile();
        }
    });
}

// 检查用户信息
async function checkUserInfo() {
    try {
        const response = await fetch('/api/admin/role-info');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const roleData = await response.json();
        
        // 更新全局用户信息
        userInfo.role = roleData.role;
        
        // 检查用户是否有管理员权限（RBAC系统）
        const hasAdminPermission = roleData.info && 
                                 roleData.info.permissions && 
                                 roleData.info.permissions.includes('admin_access');
        
        // 也检查传统的角色（向后兼容）
        const isTraditionalAdmin = roleData.role === 'admin';
        
        // 统一的管理员权限检查
        userInfo.isAdmin = hasAdminPermission || isTraditionalAdmin;
        
        // 存储用户权限和角色信息
        userInfo.permissions = roleData.info ? roleData.info.permissions : [];
        userInfo.roles = roleData.info ? roleData.info.roles : [];
        userInfo.userType = roleData.info ? roleData.info.user_type : 'user';
        
        // 获取用户名信息（包含系统用户名）
        userInfo.username = roleData.info ? roleData.info.username : null;
        
        return userInfo;
    } catch (error) {
        console.error('获取用户角色信息失败:', error);
        // 即使获取角色信息失败，也要返回默认用户信息
        userInfo.isAdmin = false;
        userInfo.permissions = [];
        userInfo.roles = [];
        userInfo.userType = 'user';
        userInfo.username = null;
        return userInfo;
    }
}

// 加载文件树
async function loadFileTree() {
    try {
        const response = await fetch('/api/files');
        const fileData = await response.json();
        
        // 如果src数据存在，查找并处理chapters目录
        if (fileData.src) {
            // 查找chapters目录
            const chaptersDir = findChaptersDirectory(fileData.src);
            if (chaptersDir && chaptersDir.children) {
                try {
                    // 获取章节配置
                    const chapterConfigResponse = await fetch('/api/admin/chapter-config');
                    if (chapterConfigResponse.ok) {
                        const chapterConfig = await chapterConfigResponse.json();
                        // 根据章节配置重新排序chapters目录下的文件
                        chaptersDir.children = reorderChapters(chaptersDir.children, chapterConfig.chapters);
                    }
                } catch (error) {
                    // 如果获取章节配置失败（例如权限不足），则跳过重新排序
                    console.warn('获取章节配置失败，跳过重新排序:', error);
                }
            }
        }
        
        const fileTreeElement = document.getElementById('file-tree');
        fileTreeElement.innerHTML = '';
        
        // 创建文件区域容器
        const fileAreasContainer = document.createElement('div');
        fileAreasContainer.className = 'file-areas-container';
        
        // 创建src文件树容器
        const srcContainer = document.createElement('div');
        srcContainer.className = 'file-area';
        srcContainer.innerHTML = `
            <div class="area-header">
                <h3>Src</h3>
                <button id="directory-btn" class="btn-secondary btn-compact" title="目录">
                    <i class="btn-icon">📋</i>
                </button>
                <button id="src-upload-btn" class="btn-secondary area-upload-btn btn-compact" title="上传文档文件（EPUB、Word、文本等，自动转换为Markdown）">
                    <i class="btn-icon">📝</i>
                    <span class="btn-text">上传文档</span>
                </button>
            </div>
        `;
        fileAreasContainer.appendChild(srcContainer);
        
        // 添加目录按钮事件（移到DOM元素创建之后）
        const directoryBtn = srcContainer.querySelector('#directory-btn');
        if (directoryBtn) {
            directoryBtn.addEventListener('click', showChapterManagement);
        }
        
        const srcTreeContainer = document.createElement('div');
        srcTreeContainer.id = 'src-tree-container';
        srcTreeContainer.className = 'tree-container';
        srcContainer.appendChild(srcTreeContainer);
        
        // 创建build文件树容器
        const buildContainer = document.createElement('div');
        buildContainer.className = 'file-area';
        buildContainer.innerHTML = `
            <div class="area-header">
                <h3>Build</h3>
                <button id="build-refresh-btn" class="btn-secondary btn-compact" title="刷新文件树">
                    <i class="btn-icon">🔄</i>
                </button>
                <button id="build-upload-btn" class="btn-secondary area-upload-btn btn-compact" title="上传电子书文件">
                    <i class="btn-icon">📖</i>
                    <span class="btn-text">上传文件</span>
                </button>
            </div>
        `;
        fileAreasContainer.appendChild(buildContainer);
        
        // 添加build刷新按钮事件
        const buildRefreshBtn = buildContainer.querySelector('#build-refresh-btn');
        if (buildRefreshBtn) {
            buildRefreshBtn.addEventListener('click', loadFileTree);
        }

        // 将文件区域容器添加到主容器
        fileTreeElement.appendChild(fileAreasContainer);
        
        const buildTreeContainer = document.createElement('div');
        buildTreeContainer.id = 'build-tree-container';
        buildTreeContainer.className = 'tree-container';
        buildContainer.appendChild(buildTreeContainer);
        
        // 为src目录添加上传按钮事件监听器
        const srcUploadBtn = document.getElementById('src-upload-btn');
        if (srcUploadBtn) {
            srcUploadBtn.addEventListener('click', () => showAreaUploadDialog('src'));
        }
        
        // 为build目录添加上传按钮事件监听器
        const buildUploadBtn = document.getElementById('build-upload-btn');
        if (buildUploadBtn) {
            buildUploadBtn.addEventListener('click', () => showAreaUploadDialog('build'));
        }
        
        // 递归渲染文件树
        if (fileData.src) {
            renderFileTree(fileData.src, srcTreeContainer, 'src');
        }
        
        if (fileData.build) {
            renderFileTree(fileData.build, buildTreeContainer, 'build');
        }
        
        // 初始化拖拽上传功能
        initializeDragAndDropUpload();
    } catch (error) {
        console.error('加载文件树失败:', error);
        window.ComponentManager.getComponent('message').error('加载文件树失败: ' + error.message);
    }
}

// 保存文件
async function saveFile() {
    if (!currentFilePath || currentFileType !== 'text' || currentFileArea !== 'src') {
        window.ComponentManager.getComponent('message').warning('请选择一个src目录下的文本文件进行保存');
        return;
    }
    
    try {
        // 从CodeMirror编辑器获取内容
        const content = codeMirrorEditor ? codeMirrorEditor.getValue() : document.getElementById('editor').value;
        
        const response = await fetch(`/api/file/src/${currentFilePath}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'text/plain; charset=utf-8'
            },
            body: content
        });
        
        const result = await response.json();
        
        if (response.ok) {
            window.ComponentManager.getComponent('message').success('文件保存成功');
        } else {
            throw new Error(result.detail || '保存失败');
        }
    } catch (error) {
        console.error('保存文件失败:', error);
        window.ComponentManager.getComponent('message').error('保存文件失败: ' + error.message);
    }
}

// ============================================================================
// 文件删除功能已移至 main-shared.js 中的统一实现
// 这里保留deleteFileAtPath函数，因为它是底层API调用
// ============================================================================

// 删除指定路径的文件
async function deleteFileAtPath(filePath) {
    try {
        const response = await fetch(`/api/file/src/${filePath}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            window.ComponentManager.getComponent('message').success('文件删除成功');
            // 清空当前文件
            currentFilePath = null;
            currentFileType = null;
            currentFileEncoding = null;
            currentFileArea = null;
            document.getElementById('current-file').textContent = '未选择文件';
            
            // 隐藏所有视图
            document.getElementById('editor').style.display = 'none';
            document.getElementById('image-viewer').style.display = 'none';
            document.getElementById('binary-viewer').style.display = 'none';
            document.getElementById('preview-container').style.display = 'none';
            
            // 禁用删除按钮
            document.getElementById('delete-btn').disabled = true;
            
            // 刷新文件树
            loadFileTree();
        } else {
            throw new Error(result.detail || '删除失败');
        }
    } catch (error) {
        console.error('删除文件失败:', error);
        window.ComponentManager.getComponent('message').error('删除文件失败: ' + error.message);
    }
}

// 下载Src目录
async function downloadSrc() {
    try {
        console.log('开始下载Src目录');
        window.ComponentManager.getComponent('message').info('正在准备下载Src目录...');
        
        // 创建一个隐藏的iframe来触发下载
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = '/api/admin/download-src';
        document.body.appendChild(iframe);
        
        console.log('已创建iframe并添加到页面');
        
        // 一段时间后移除iframe
        setTimeout(() => {
            document.body.removeChild(iframe);
            console.log('已移除iframe');
        }, 1000);
    } catch (error) {
        console.error('下载Src目录失败:', error);
        window.ComponentManager.getComponent('message').error('下载Src目录失败: ' + error.message);
    }
}

// 下载build区域文件
async function downloadBuildFile(filePath) {
    try {
        console.log('开始下载文件:', filePath);
        window.ComponentManager.getComponent('message').info(`正在下载 ${filePath}...`);
        
        // 创建一个隐藏的a标签来触发下载
        const link = document.createElement('a');
        const encodedFilePath = encodeURIComponent(filePath);
        link.href = `/api/file/build/${encodedFilePath}?raw=true&download=true`;
        link.download = filePath.split('/').pop(); // 使用文件名作为下载名
        link.style.display = 'none';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        console.log('已触发下载');
        window.ComponentManager.getComponent('message').success('下载已开始');
    } catch (error) {
        console.error('下载文件失败:', error);
        window.ComponentManager.getComponent('message').error('下载文件失败: ' + error.message);
    }
}

// 删除build区域文件
async function deleteBuildFile(filePath) {
    try {
        console.log('开始删除build文件:', filePath);
        window.ComponentManager.getComponent('message').info(`正在删除 ${filePath}...`);
        
        const response = await fetch(`/api/file/build/${filePath}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            window.ComponentManager.getComponent('message').success('文件删除成功');
            
            // 如果当前正在查看被删除的文件，清空显示
            if (currentFilePath === filePath && currentFileArea === 'build') {
                currentFilePath = null;
                currentFileType = null;
                currentFileEncoding = null;
                currentFileArea = null;
                document.getElementById('current-file').textContent = '未选择文件';
                
                // 隐藏所有视图
                const editor = document.getElementById('editor');
                const imageViewer = document.getElementById('image-viewer');
                const binaryViewer = document.getElementById('binary-viewer');
                const previewContainer = document.getElementById('preview-container');
                
                if (editor) editor.style.display = 'none';
                if (imageViewer) imageViewer.style.display = 'none';
                if (binaryViewer) binaryViewer.style.display = 'none';
                if (previewContainer) previewContainer.style.display = 'none';
                
                // 禁用删除按钮
                const deleteBtn = document.getElementById('delete-btn');
                if (deleteBtn) deleteBtn.disabled = true;
            }
            
            // 刷新文件树
            loadFileTree();
        } else {
            throw new Error(result.detail || '删除失败');
        }
    } catch (error) {
        console.error('删除build文件失败:', error);
        let errorMessage = '删除文件失败: ' + error.message;
        
        // 根据错误类型提供更友好的错误信息
        if (error.message.includes('403') || error.message.includes('权限不足')) {
            errorMessage = '权限不足，无法删除该文件。请联系管理员获取file.manage权限。';
        } else if (error.message.includes('404')) {
            errorMessage = '文件不存在或已被删除。';
        }
        
        window.ComponentManager.getComponent('message').error(errorMessage);
    }
}

// 切换主题
async function switchTheme(themeOrEvent) {
    try {
        // 支持两种调用方式：
        // 1. 直接传递主题名称：switchTheme('wooden')
        // 2. 作为事件处理器：addEventListener('change', switchTheme)
        let theme;
        if (typeof themeOrEvent === 'string') {
            // 直接传递主题名称
            theme = themeOrEvent;
        } else if (themeOrEvent && themeOrEvent.target) {
            // 事件对象，从target获取值
            theme = themeOrEvent.target.value;
        } else {
            // 尝试从页面上的主题选择器获取当前值
            const themeSelector = document.getElementById('theme-selector');
            if (themeSelector) {
                theme = themeSelector.value;
            } else {
                throw new Error('无法确定要切换的主题');
            }
        }
        
        // 发送请求更新用户主题
        const response = await fetch('/api/user/theme', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ theme: theme })
        });
        
        if (!response.ok) {
            throw new Error('Failed to update theme');
        }
        
        // 根据选择的主题切换CSS文件
        const linkElement = document.getElementById('theme-link');
        if (linkElement) {
            linkElement.href = `/static/${theme}/css/style.css`;
        } else {
            // 如果link元素不存在，创建一个新的
            const newLinkElement = document.createElement('link');
            newLinkElement.id = 'theme-link';
            newLinkElement.rel = 'stylesheet';
            newLinkElement.href = `/static/${theme}/css/style.css`;
            document.head.appendChild(newLinkElement);
        }
        
        window.ComponentManager.getComponent('message').success('主题切换成功');
    } catch (error) {
        console.error('切换主题失败:', error);
        window.ComponentManager.getComponent('message').error('切换主题失败: ' + error.message);
    }
}

// 格式化日期
function formatDate(dateString) {
    if (!dateString) return '未知';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 查找chapters目录
function findChaptersDirectory(files) {
    for (const file of files) {
        if (file.type === 'directory' && file.name === 'chapters') {
            return file;
        }
        if (file.type === 'directory' && file.children) {
            const found = findChaptersDirectory(file.children);
            if (found) {
                return found;
            }
        }
    }
    return null;
}

// 根据章节配置重新排序chapters目录下的文件
function reorderChapters(chapterFiles, chapterConfig) {
    // 创建一个映射，将文件名映射到配置中的索引
    const fileIndexMap = {};
    chapterConfig.forEach((chapter, index) => {
        fileIndexMap[chapter.file] = index;
    });
    
    // 创建一个映射，将文件名映射到文件对象
    const fileMap = {};
    chapterFiles.forEach(file => {
        if (file.type === 'file') {
            fileMap[file.name] = file;
        }
    });
    
    // 根据配置顺序创建新的文件列表
    const reorderedFiles = [];
    
    // 首先按照配置顺序添加文件
    chapterConfig.forEach(chapter => {
        if (fileMap[chapter.file]) {
            // 更新文件名显示为章节标题
            const file = {...fileMap[chapter.file]};
            file.name = chapter.title;
            reorderedFiles.push(file);
            // 从fileMap中删除已处理的文件
            delete fileMap[chapter.file];
        }
    });
    
    // 添加剩余的文件（不在配置中的文件）
    Object.values(fileMap).forEach(file => {
        reorderedFiles.push(file);
    });
    
    return reorderedFiles;
}

// 渲染文件树
function renderFileTree(files, parentElement, area) {
    files.forEach(file => {
        const fileItem = document.createElement('div');
        fileItem.className = `file-item ${file.type}`;
        fileItem.dataset.path = file.path;
        fileItem.dataset.extension = file.extension || '';
        fileItem.dataset.area = area;
        
        if (file.type === 'directory') {
            // 目录项
            fileItem.innerHTML = `
                <span class="tree-toggle">▶</span>
                <span class="file-name">${file.name}</span>
            `;
            
            const childrenContainer = document.createElement('div');
            childrenContainer.className = 'children';
            childrenContainer.style.display = 'none';
            
            // 添加右键菜单事件监听器
            fileItem.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                showContextMenu(e.clientX, e.clientY, file.path, area, 'directory');
            });
            
            // 使用通用的目录点击处理函数
            addDirectoryClickHandler(fileItem, childrenContainer);
            
            parentElement.appendChild(fileItem);
            parentElement.appendChild(childrenContainer);
            
            // 递归渲染子目录
            if (file.children) {
                renderFileTree(file.children, childrenContainer, area);
            }
        } else {
            // 文件项
            let fileDisplayName = file.name;
            let fileIcon = '';
            
            // 根据文件类型添加图标和标识
            if (file.file_category === 'epub') {
                fileIcon = '📚 ';
                fileDisplayName = `${fileIcon}${file.name}`;
            } else if (file.file_category === 'pdf') {
                fileIcon = '📄 ';
                fileDisplayName = `${fileIcon}${file.name}`;
            } else if (file.file_category === 'image') {
                fileIcon = '🖼️ ';
                fileDisplayName = `${fileIcon}${file.name}`;
            } else if (file.extension === '.md') {
                fileIcon = '📝 ';
                fileDisplayName = `${fileIcon}${file.name}`;
            }
            
            fileItem.innerHTML = `
                <span class="file-name">${fileDisplayName}</span>
            `;
            
            // 为EPUB文件添加特殊样式类
            if (file.file_category === 'epub') {
                fileItem.classList.add('epub-file');
            } else if (file.previewable) {
                fileItem.classList.add('previewable-file');
            }
            
            // 添加右键菜单事件监听器
            fileItem.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                showContextMenu(e.clientX, e.clientY, file.path, area, 'file');
            });
            
            // 使用通用的文件点击处理函数
            addFileClickHandler(fileItem, file, area);
            
            parentElement.appendChild(fileItem);
        }
    });
}

// 目录点击处理函数
function addDirectoryClickHandler(fileItem, childrenContainer) {
    fileItem.addEventListener('click', function(e) {
        if (e.target.classList.contains('tree-toggle')) {
            e.stopPropagation();
            toggleDirectory(this, childrenContainer);
        } else {
            // 展开/折叠目录
            toggleDirectory(this, childrenContainer);
        }
    });
}

// 切换目录展开状态
function toggleDirectory(fileItem, childrenContainer) {
    const toggle = fileItem.querySelector('.tree-toggle');
    if (childrenContainer.style.display === 'none') {
        childrenContainer.style.display = 'block';
        toggle.textContent = '▼';
    } else {
        childrenContainer.style.display = 'none';
        toggle.textContent = '▶';
    }
}

// 文件点击处理函数
function addFileClickHandler(fileItem, file, area) {
    fileItem.addEventListener('click', function() {
        // 移除其他文件项的激活状态
        document.querySelectorAll('.file-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // 激活当前文件项
        this.classList.add('active');
        
        // 如果是build区域的文件，优先预览可预览的文件；其余文本文件直接在编辑器中打开
        if (area === 'build' && file.type === 'file') {
            const extension = file.path.substring(file.path.lastIndexOf('.')).toLowerCase();
            const previewableExtensions = ['.epub', '.html', '.pdf', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.ico'];
            const openableTextExtensions = ['.md', '.markdown', '.txt', '.json', '.yml', '.yaml', '.css', '.html', '.js', '.xml', '.csv', '.tex', ''];
            
            if (previewableExtensions.includes(extension)) {
                // 对于可预览的文件，使用loadFile函数进行预览
                loadFile(file.path, area);
            } else if (openableTextExtensions.includes(extension)) {
                // 对于文本类文件（包括Markdown），在编辑器中打开并启用语法高亮
                loadFile(file.path, area);
            } else {
                // 对于不可预览的文件，直接下载
                downloadBuildFile(file.path);
            }
        } else {
            // 对于src区域的文件或build区域的目录，正常加载
            loadFile(file.path, area);
        }
    });
}

// 显示右键菜单
function showContextMenu(x, y, path, area, type) {
    // 移除已存在的菜单
    const existingMenu = document.querySelector('.context-menu');
    if (existingMenu) {
        existingMenu.remove();
    }
    
    // 创建右键菜单
    const contextMenu = document.createElement('div');
    contextMenu.className = 'context-menu';
    contextMenu.style.position = 'absolute';
    contextMenu.style.left = `${x}px`;
    contextMenu.style.top = `${y}px`;
    contextMenu.style.zIndex = '10000';
    
    // 根据文件类型和区域添加菜单项
    if (area === 'src') {
        if (type === 'directory') {
            contextMenu.innerHTML = `
                <div class="context-menu-item" data-action="create-file">新建文件</div>
                <div class="context-menu-item" data-action="upload-file">上传文件</div>
                <div class="context-menu-item" data-action="create-directory">新建目录</div>
                <div class="context-menu-item" data-action="delete">删除目录</div>
            `;
        } else if (type === 'file') {
            contextMenu.innerHTML = `
                <div class="context-menu-item" data-action="upload-file-replace">替换文件</div>
                <div class="context-menu-item" data-action="delete">删除文件</div>
            `;
        }
    } else if (area === 'build') {
        if (type === 'file') {
            const extension = path.substring(path.lastIndexOf('.')).toLowerCase();
            const previewableExtensions = ['.epub', '.html', '.pdf', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.ico'];
            if (previewableExtensions.includes(extension)) {
                contextMenu.innerHTML = `
                    <div class="context-menu-item" data-action="preview">预览</div>
                    <div class="context-menu-item" data-action="download">下载</div>
                    <div class="context-menu-item" data-action="delete-build">删除</div>
                `;
            } else {
                contextMenu.innerHTML = `
                    <div class="context-menu-item" data-action="download">下载</div>
                    <div class="context-menu-item" data-action="delete-build">删除</div>
                `;
            }
        } else {
            contextMenu.innerHTML = `
                <div class="context-menu-item disabled">不支持的操作</div>
            `;
        }
    } else {
        contextMenu.innerHTML = `
            <div class="context-menu-item disabled">不支持的操作</div>
        `;
    }
    
    // 添加到页面
    document.body.appendChild(contextMenu);
    
    // 绑定菜单项事件
    contextMenu.querySelectorAll('.context-menu-item').forEach(item => {
        if (!item.classList.contains('disabled')) {
            item.addEventListener('click', function() {
                const action = this.dataset.action;
                handleContextMenuAction(action, path, area, type);
                contextMenu.remove();
            });
        }
    });
    
    // 点击其他地方关闭菜单
    document.addEventListener('click', function closeMenu(e) {
        if (!contextMenu.contains(e.target)) {
            contextMenu.remove();
            document.removeEventListener('click', closeMenu);
        }
    });
    
    // 阻止右键菜单冒泡
    contextMenu.addEventListener('contextmenu', function(e) {
        e.stopPropagation();
        e.preventDefault();
    });
}

// 处理右键菜单操作
function handleContextMenuAction(action, path, area, type) {
    switch (action) {
        case 'create-file':
            showCreateFileDialog(path);
            break;
        case 'upload-file':
            showUploadFileDialog(path, false);
            break;
        case 'upload-file-replace':
            showUploadFileDialog(path, true);
            break;
        case 'create-directory':
            showCreateDirectoryDialog(path);
            break;
        case 'delete':
            if (confirm(`确定要删除文件 "${path}" 吗？`)) {
                deleteFileAtPath(path);
            }
            break;
        case 'delete-build':
            if (confirm(`确定要删除构建文件 "${path}" 吗？`)) {
                deleteBuildFile(path);
            }
            break;
        case 'preview':
            if (typeof previewBuildFile === 'function') {
                previewBuildFile(path);
            }
            break;
        case 'download':
            downloadBuildFile(path);
            break;
    }
}

// 显示创建文件对话框
function showCreateFileDialog(directoryPath = '') {
    const fileName = prompt('请输入文件名（包括扩展名）:');
    if (fileName) {
        createFile(directoryPath, fileName);
    }
}

// 显示创建目录对话框
function showCreateDirectoryDialog(directoryPath = '') {
    const dirName = prompt('请输入目录名:');
    if (dirName) {
        createDirectory(directoryPath, dirName);
    }
}

// 显示区域特定的文件上传对话框
function showAreaUploadDialog(area) {
    // 创建文件输入元素
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.multiple = true; // 支持多文件选择
    fileInput.style.display = 'none';
    
    // 根据区域设置文件类型限制和说明
    if (area === 'src') {
        fileInput.accept = '.epub,.md,.txt,.json,.yml,.yaml,.css,.html,.js,.xml,.csv,.docx,.doc,.rtf';
        fileInput.title = '选择文件上传到src目录（EPUB等电子书文件将自动转换为Markdown）';
    } else if (area === 'build') {
        fileInput.accept = '.epub,.pdf,.html,.zip,.tar,.gz';
        fileInput.title = '选择电子书或构建文件上传到build目录';
    }
    
    fileInput.addEventListener('change', function(e) {
        const files = Array.from(e.target.files);
        if (files.length > 0) {
            // 支持批量上传
            uploadMultipleFilesToArea(area, files);
        }
        // 移除临时元素
        document.body.removeChild(fileInput);
    });
    
    // 添加到页面并触发点击
    document.body.appendChild(fileInput);
    fileInput.click();
}

// 上传文件到指定区域
async function uploadFileToArea(area, file) {
    const uploadId = Date.now() + Math.random();
    
    try {
        const fileName = file.name;
        const fileExtension = fileName.toLowerCase().substring(fileName.lastIndexOf('.'));
        
        // 定义支持的文件类型
        const srcSupportedTypes = ['.epub', '.md', '.txt', '.json', '.yml', '.yaml', '.css', '.html', '.js', '.xml', '.csv', '.docx', '.doc', '.rtf'];
        const buildSupportedTypes = ['.epub', '.pdf', '.html', '.zip', '.tar', '.gz'];
        
        // 验证文件类型
        if (area === 'src' && !srcSupportedTypes.includes(fileExtension)) {
            showMessage(`不支持的文件类型: ${fileExtension}\n支持的类型: ${srcSupportedTypes.join(', ')}`, 'error');
            return;
        }
        
        if (area === 'build' && !buildSupportedTypes.includes(fileExtension)) {
            showMessage(`不支持的文件类型: ${fileExtension}\n支持的类型: ${buildSupportedTypes.join(', ')}`, 'error');
            return;
        }
        
        // 显示上传进度
        uploadProgressManager.showProgress(uploadId, fileName, 1);
        
        // 创建 FormData
        const formData = new FormData();
        formData.append('file', file);
        
        // 选择上传端点
        const uploadUrl = `/api/upload-file/${area}/${fileName}`;
        
        uploadProgressManager.updateProgress(uploadId, 0, 'uploading');
        
        const response = await fetch(uploadUrl, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            uploadProgressManager.updateProgress(uploadId, 1, 'completed');
            
            let message = `文件上传成功: ${fileName}`;
            
            // 对于电子书和文档文件，根据目标目录添加特殊提示
            const documentFormats = ['.epub', '.docx', '.doc', '.rtf'];
            if (documentFormats.includes(fileExtension)) {
                if (area === 'src') {
                    if (result.conversion_status === 'success') {
                        message += ` （已转换为Markdown格式，共${result.chapters_count || 0}章）`;
                    } else {
                        message += ' （已转换为Markdown格式用于编辑）';
                    }
                } else if (area === 'build') {
                    message += ' （可直接阅读和预览）';
                }
            }
            
            window.ComponentManager.getComponent('message').success(message);
            uploadProgressManager.completeUpload(uploadId, true);
            
            // 刷新文件树
            await loadFileTree();
        } else {
            uploadProgressManager.completeUpload(uploadId, false);
            
            // 解析错误信息
            let errorMessage = result.detail || '上传失败';
            
            if (response.status === 400 && result.detail.includes('文件已存在')) {
                // 文件已存在，直接覆盖
                await uploadFileToAreaWithOverwrite(area, file);
                return; // 返回，不显示错误信息
            } else if (documentFormats.includes(fileExtension)) {
                // 电子书和文档文件特殊错误处理
                if (fileExtension === '.epub' && (errorMessage.includes('不是有效的ZIP') || errorMessage.includes('ZIP格式错误'))) {
                    errorMessage = 'EPUB文件损坏或格式错误，请检查文件是否完整且符合EPUB标准。';
                } else if (errorMessage.includes('缺少必需的结构')) {
                    errorMessage = '文件不是有效的格式，缺少必需的组件。';
                } else if (errorMessage.includes('转换失败')) {
                    errorMessage = '文件转换失败，可能是文件内部结构问题或缺少必要的组件。请尝试使用其他文件或联系管理员。';
                } else if (errorMessage.includes('文件为空')) {
                    errorMessage = '上传的文件为空或损坏，请检查文件是否完整。';
                }
            }
            
            throw new Error(errorMessage);
        }
    } catch (error) {
        uploadProgressManager.completeUpload(uploadId, false);
        console.error('上传文件失败:', error);
        window.ComponentManager.getComponent('message').error('上传文件失败: ' + error.message);
    }
}

// 批量上传文件到指定区域
async function uploadMultipleFilesToArea(area, files) {
    if (!files || files.length === 0) {
        window.ComponentManager.getComponent('message').warning('未选择文件');
        return;
    }
    
    const uploadId = Date.now() + Math.random();
    const totalFiles = files.length;
    let successCount = 0;
    let failCount = 0;
    
    // 初始化进度显示
    uploadProgressManager.showProgress(uploadId, `${totalFiles}个文件`, totalFiles);
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        try {
            // 创建单独的上传ID处理单个文件
            const singleUploadId = uploadId + '_' + i;
            
            // 验证文件类型
            const fileName = file.name;
            const fileExtension = fileName.toLowerCase().substring(fileName.lastIndexOf('.'));
            const srcSupportedTypes = ['.epub', '.md', '.txt', '.json', '.yml', '.yaml', '.css', '.html', '.js', '.xml', '.csv', '.docx', '.doc', '.rtf'];
            const buildSupportedTypes = ['.epub', '.pdf', '.html', '.zip', '.tar', '.gz'];
            
            if ((area === 'src' && !srcSupportedTypes.includes(fileExtension)) ||
                (area === 'build' && !buildSupportedTypes.includes(fileExtension))) {
                console.warn(`跳过不支持的文件类型: ${fileName}`);
                failCount++;
                continue;
            }
            
            // 创建 FormData
            const formData = new FormData();
            formData.append('file', file);
            
            // 上传文件
            const uploadUrl = `/api/upload-file/${area}/${fileName}`;
            const response = await fetch(uploadUrl, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                successCount++;
            } else if (response.status === 400 && result.detail.includes('文件已存在')) {
                // 自动覆盖已存在的文件
                const overwriteUrl = `/api/upload-file/${area}/${fileName}/overwrite`;
                const overwriteResponse = await fetch(overwriteUrl, {
                    method: 'POST',
                    body: formData
                });
                
                if (overwriteResponse.ok) {
                    successCount++;
                } else {
                    failCount++;
                }
            } else {
                failCount++;
            }
            
            // 更新进度
            uploadProgressManager.updateProgress(uploadId, i + 1, 'uploading');
            
            // 等待一小段时间避免服务器过载
            if (i < files.length - 1) {
                await new Promise(resolve => setTimeout(resolve, 300));
            }
        } catch (error) {
            console.error(`上传文件 ${file.name} 失败:`, error);
            failCount++;
        }
    }
    
    // 完成上传并显示结果
    uploadProgressManager.completeUpload(uploadId, failCount === 0);
    
    if (failCount === 0) {
        window.ComponentManager.getComponent('message').success(`批量上传完成! 成功上传 ${successCount} 个文件`);
    } else {
        showMessage(`批量上传完成! 成功: ${successCount}, 失败: ${failCount}`, 'warning');
    }
    
    // 刷新文件树
    await loadFileTree();
}

// 初始化拖拽上传功能
function initializeDragAndDropUpload() {
    // 为src和build区域添加拖拽上传
    const srcContainer = document.getElementById('src-tree-container');
    const buildContainer = document.getElementById('build-tree-container');
    
    if (srcContainer) {
        setupDragAndDrop(srcContainer, 'src');
    }
    
    if (buildContainer) {
        setupDragAndDrop(buildContainer, 'build');
    }
}

// 为指定容器设置拖拽上传
function setupDragAndDrop(container, area) {
    // 防止默认行为
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        container.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // 进入拖拽区域时的效果
    ['dragenter', 'dragover'].forEach(eventName => {
        container.addEventListener(eventName, () => {
            container.classList.add('drag-over');
        }, false);
    });
    
    // 离开拖拽区域时的效果
    ['dragleave', 'drop'].forEach(eventName => {
        container.addEventListener(eventName, () => {
            container.classList.remove('drag-over');
        }, false);
    });
    
    // 处理文件放置
    container.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = Array.from(dt.files);
        
        if (files.length > 0) {
            if (files.length === 1) {
                uploadFileToArea(area, files[0]);
            } else {
                uploadMultipleFilesToArea(area, files);
            }
        }
    }, false);
    
    // 添加拖拽区域的视觉提示
    if (!container.querySelector('.drag-drop-hint')) {
        const hint = document.createElement('div');
        hint.className = 'drag-drop-hint';
        hint.innerHTML = `
            <div class="drag-drop-content">
                <i class="drag-icon">📁</i>
                <p>拖拽文件到此处上传</p>
                <small>${area === 'src' ? '支持: EPUB, MD, TXT, JSON, YML, CSS, HTML, JS, XML, CSV' : '支持: EPUB, PDF, HTML, ZIP, TAR, GZ'}</small>
            </div>
        `;
        container.appendChild(hint);
    }
}
async function uploadFileToAreaWithOverwrite(area, file) {
    try {
        const fileName = file.name;
        
        // 创建 FormData
        const formData = new FormData();
        formData.append('file', file);
        
        // 选择覆盖上传端点
        const uploadUrl = `/api/upload-file/${area}/${fileName}/overwrite`;
        
        const response = await fetch(uploadUrl, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            const targetDisplay = area === 'src' ? 'Src' : 'Build';
            let message = `文件替换成功: ${fileName} (在${targetDisplay}目录)`;
            
            const fileExtension = fileName.toLowerCase().substring(fileName.lastIndexOf('.'));
            if (fileExtension === '.epub') {
                if (area === 'src') {
                    if (result.conversion_status === 'success') {
                        message += ` （已转换为Markdown格式，共${result.chapters_count || 0}章）`;
                    } else {
                        message += ' （已转换为Markdown格式用于编辑）';
                    }
                } else if (area === 'build') {
                    message += ' （可直接阅读和预览）';
                }
            }
            
            window.ComponentManager.getComponent('message').success(message);
            // 刷新文件树
            await loadFileTree();
        } else {
            throw new Error(result.detail || '替换失败');
        }
    } catch (error) {
        console.error('替换文件失败:', error);
        window.ComponentManager.getComponent('message').error('替换文件失败: ' + error.message);
    }
}

// 显示文件上传对话框
function showUploadFileDialog(directoryPath = '', overwrite = false) {
    // 创建文件输入元素
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.multiple = false;
    fileInput.style.display = 'none';
    
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            uploadFileToDirectory(directoryPath, file, overwrite);
        }
        // 移除临时元素
        document.body.removeChild(fileInput);
    });
    
    // 添加到页面并触发点击
    document.body.appendChild(fileInput);
    fileInput.click();
}

// 上传文件到指定目录
async function uploadFileToDirectory(directoryPath, file, overwrite = false) {
    try {
        const fileName = file.name;
        const filePath = directoryPath ? `${directoryPath}/${fileName}` : fileName;
        
        // 确定目标目录类型，默认为src
        const targetArea = currentFileArea || 'src';
        
        // 显示上传进度
        window.ComponentManager.getComponent('message').info(`正在上传文件 "${fileName}" 到 ${targetArea} 目录...`);
        
        // 创建 FormData
        const formData = new FormData();
        formData.append('file', file);
        
        // 选择上传端点，包含目录类型
        const uploadUrl = overwrite 
            ? `/api/upload-file/${targetArea}/${filePath}/overwrite`
            : `/api/upload-file/${targetArea}/${filePath}`;
        
        const response = await fetch(uploadUrl, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            const action = result.overwritten ? '替换' : '上传';
            let message = `文件${action}成功: ${fileName}`;
            
            // 对于EPUB文件，根据目标目录添加特殊提示
            if (fileName.toLowerCase().endsWith('.epub')) {
                if (result.target_directory === 'src') {
                    if (result.conversion_status === 'success') {
                        message += ` (已转换为Markdown格式，共${result.chapters_count || 0}章)`;
                    } else {
                        message += ' (转换为Markdown格式用于编辑)';
                    }
                } else if (result.target_directory === 'build') {
                    message += ' (可直接阅读和预览)';
                }
            }
            
            window.ComponentManager.getComponent('message').success(message);
            // 刷新文件树
            await loadFileTree();
        } else {
            if (response.status === 400 && result.detail.includes('文件已存在')) {
                // 文件已存在，直接覆盖
                await uploadFileToDirectory(directoryPath, file, true);
            } else {
                throw new Error(result.detail || '上传失败');
            }
        }
    } catch (error) {
        console.error('上传文件失败:', error);
        window.ComponentManager.getComponent('message').error('上传文件失败: ' + error.message);
    }
}

// 拖拽事件处理函数
let draggedItem = null;

function addDragAndDropHandlers(container) {
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

// 抽屉菜单事件绑定函数
function bindDrawerEvents() {
    console.log('bindDrawerEvents 函数开始执行');
    const adminPanelBtn = document.getElementById('admin-panel-btn');
    const closeDrawerBtn = document.getElementById('close-drawer-btn');
    const closeUserPanelBtn = document.getElementById('close-user-panel-btn');
    const drawerOverlay = document.getElementById('drawer-overlay');
    const adminDropdown = document.getElementById('admin-dropdown'); // 改为下拉菜单
    const userPanelDropdown = document.getElementById('user-panel-dropdown'); // 修改为下拉菜单
    
    console.log('按钮状态检查:', {
        adminPanelBtn: !!adminPanelBtn,
        closeDrawerBtn: !!closeDrawerBtn,
        drawerOverlay: !!drawerOverlay,
        adminDropdown: !!adminDropdown,
        adminPanelBtnListenerAdded: adminPanelBtn ? adminPanelBtn.dataset.listenerAdded : 'N/A'
    });
    
    // 确保只绑定一次事件监听器 - 现在使用管理面板下拉菜单
    const adminPanelDropdown = document.getElementById('admin-panel-dropdown');
    if (adminPanelBtn && adminPanelDropdown && !adminPanelBtn.dataset.listenerAdded && !adminPanelBtn.dataset.mainSharedListenerAdded) {
        adminPanelBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('admin-panel-btn 被点击，调用 toggleAdminPanelDropdown');
            toggleAdminPanelDropdown();
        });
        adminPanelBtn.dataset.listenerAdded = 'true';
        console.log('管理面板按钮事件已绑定');
    }
    
    // 下拉菜单不需要关闭按钮，通过点击外部区域关闭
    
    if (closeUserPanelBtn && userPanelDropdown && !closeUserPanelBtn.dataset.listenerAdded) {
        closeUserPanelBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('close-user-panel-btn 被点击，调用 closeUserPanelDropdown');
            closeUserPanelDropdown();
        });
        closeUserPanelBtn.dataset.listenerAdded = 'true';
        console.log('用户面板关闭按钮事件已绑定');
    }
    
    if (drawerOverlay && !drawerOverlay.dataset.listenerAdded) {
        drawerOverlay.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('drawer-overlay 被点击，关闭所有抽屉和下拉菜单');
            closeAdminPanelDropdown();
            if (typeof closeUserPanelDropdown === 'function') {
                closeUserPanelDropdown();
            }
            if (typeof closeChapterDrawer === 'function') {
                closeChapterDrawer();
            }
            // 清除所有可能的body类
            document.body.classList.remove('drawer-right-open', 'drawer-left-open');
        });
        drawerOverlay.dataset.listenerAdded = 'true';
        console.log('抽屉遮罩层事件已绑定');
    }
    
    // 为下拉菜单中的链接添加事件监听器（只在管理下拉菜单存在时）
    if (adminDropdown) {
        bindDropdownLinkEvents();
    }
    
    // 绑定章节管理抽屉菜单事件
    bindChapterDrawerEvents();
    
    console.log('bindDrawerEvents 函数执行完成');
}

// 图书生成函数
async function buildBook(scriptName) {
    try {
        // 显示正在处理的消息
        window.ComponentManager.getComponent('message').info(`正在执行 ${scriptName}...`);
        
        // 调用API
        const response = await fetch(`/api/admin/build/${scriptName}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok && result.status === 'success') {
            window.ComponentManager.getComponent('message').success(`${scriptName} 执行成功`);
            console.log('stdout:', result.stdout);
            console.log('stderr:', result.stderr);
            
            // 构建成功后刷新文件树
            await loadFileTree();
        } else {
            window.ComponentManager.getComponent('message').error(`${scriptName} 执行失败: ${result.message}`);
            console.error('stdout:', result.stdout);
            console.error('stderr:', result.stderr);
        }
    } catch (error) {
        console.error('执行图书生成失败:', error);
        window.ComponentManager.getComponent('message').error(`执行图书生成失败: ${error.message}`);
    }
}

// 处理图书转换器select change事件
function handleBookConverterChange(event) {
    const selectedValue = event.target.value;
    
    if (selectedValue) {
        let convertTypeName;
        switch(selectedValue) {
            case 'build':
                convertTypeName = '所有格式';
                break;
            case 'epub':
                convertTypeName = 'EPUB格式';
                break;
            case 'pdf':
                convertTypeName = 'PDF格式(Pandoc)';
                break;
            case 'pdf-wkhtmltopdf':
                convertTypeName = 'PDF格式(wkhtmltopdf)';
                break;
            case 'html':
                convertTypeName = 'HTML格式';
                break;
            default:
                convertTypeName = selectedValue;
        }
        
        // 确认是否要进行转换
        if (confirm(`确定要开始生成${convertTypeName}吗？`)) {
            buildBook(selectedValue);
        }
        
        // 重置select到默认选项
        event.target.value = '';
    }
}

// 初始化公共配置
function initializeCommonSettings() {
    // 配置marked.js（如果存在）
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true, // 转换段落中的\n为<br>
            smartypants: true, // 启用智能标点符号
            smartLists: true // 启用智能列表
        });
    }
}

// 用户面板相关函数
// 保存用户主题设置
async function saveUserTheme() {
    try {
        const theme = document.getElementById('user-panel-theme-selector').value;
        
        const response = await fetch('/api/user/theme', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ theme: theme })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            window.ComponentManager.getComponent('message').success('主题设置保存成功');
            // 更新页面上的主题显示
            document.getElementById('user-panel-current-theme').textContent = theme;
            
            // 应用主题CSS
            const linkElement = document.getElementById('theme-link');
            if (linkElement) {
                linkElement.href = `/static/${theme}/css/style.css`;
            }
            
            // 同时更新顶部主题选择器的值
            const themeSelector = document.getElementById('theme-selector');
            if (themeSelector) {
                themeSelector.value = theme;
            }
        } else {
            throw new Error(result.detail || '保存主题设置失败');
        }
    } catch (error) {
        console.error('保存主题设置失败:', error);
        window.ComponentManager.getComponent('message').error('保存主题设置失败: ' + error.message);
    }
}

// 保存用户LLM配置
async function saveUserLlmConfig() {
    try {
        const llmConfig = document.getElementById('user-panel-llm-config').value;
        
        // 验证是否为有效的JSON
        try {
            JSON.parse(llmConfig);
        } catch (e) {
            window.ComponentManager.getComponent('message').warning('LLM配置必须是有效的JSON格式');
            return;
        }
        
        const response = await fetch('/api/user/llm-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ llm_config: llmConfig })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            window.ComponentManager.getComponent('message').success('LLM配置保存成功');
        } else {
            throw new Error(result.detail || '保存LLM配置失败');
        }
    } catch (error) {
        console.error('保存LLM配置失败:', error);
        window.ComponentManager.getComponent('message').error('保存LLM配置失败: ' + error.message);
    }
}

// 重置用户LLM配置
async function resetUserLlmConfig() {
    try {
        const response = await fetch('/api/user/info');
        const result = await response.json();
        
        if (response.ok) {
            document.getElementById('user-panel-llm-config').value = result.llm_config;
            window.ComponentManager.getComponent('message').success('LLM配置已重置');
        } else {
            throw new Error(result.detail || '重置LLM配置失败');
        }
    } catch (error) {
        console.error('重置LLM配置失败:', error);
        window.ComponentManager.getComponent('message').error('重置LLM配置失败: ' + error.message);
    }
}

// 加载用户信息
async function loadUserInfo() {
    try {
        // 调用用户信息接口
        const response = await fetch('/api/user/info');
        const result = await response.json();
        
        if (response.ok) {
            // 填充用户信息
            document.getElementById('user-panel-username').textContent = result.username;
            document.getElementById('user-panel-created-at').textContent = new Date(result.created_at).toLocaleString('zh-CN');
            document.getElementById('user-panel-login-time').textContent = new Date(result.login_time).toLocaleString('zh-CN');
            document.getElementById('user-panel-current-theme').textContent = result.theme;
            
            // 设置主题选择器的值
            document.getElementById('user-panel-theme-selector').value = result.theme;
            
            // 设置LLM配置
            document.getElementById('user-panel-llm-config').value = result.llm_config;
        } else {
            throw new Error(result.detail || '获取用户信息失败');
        }
    } catch (error) {
        console.error('加载用户信息失败:', error);
        window.ComponentManager.getComponent('message').error('加载用户信息失败: ' + error.message);
    }
}

// 创建文件函数
async function createFile(directoryPath, fileName) {
    if (!fileName) {
        window.ComponentManager.getComponent('message').warning('文件名不能为空');
        return;
    }
    
    try {
        const filePath = directoryPath ? `${directoryPath}/${fileName}` : fileName;
        
        const response = await fetch(`/api/file/src/${filePath}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'text/plain; charset=utf-8'
            },
            body: '' // 创建空文件
        });
        
        const result = await response.json();
        
        if (response.ok) {
            window.ComponentManager.getComponent('message').success('文件创建成功');
            // 刷新文件树
            loadFileTree();
        } else {
            throw new Error(result.detail || '创建文件失败');
        }
    } catch (error) {
        console.error('创建文件失败:', error);
        window.ComponentManager.getComponent('message').error('创建文件失败: ' + error.message);
    }
}

// 创建目录函数
async function createDirectory(directoryPath, dirName) {
    if (!dirName) {
        window.ComponentManager.getComponent('message').warning('目录名不能为空');
        return;
    }
    
    try {
        const fullPath = directoryPath ? `${directoryPath}/${dirName}` : dirName;
        
        const response = await fetch(`/api/directory/src/${fullPath}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            window.ComponentManager.getComponent('message').success('目录创建成功');
            // 刷新文件树
            loadFileTree();
        } else {
            throw new Error(result.detail || '创建目录失败');
        }
    } catch (error) {
        console.error('创建目录失败:', error);
        window.ComponentManager.getComponent('message').error('创建目录失败: ' + error.message);
    }
}

// 用户面板下拉菜单控制函数
function toggleUserPanelDropdown() {
    const dropdown = document.getElementById('user-panel-dropdown');
    
    if (dropdown) {
        const isOpen = dropdown.classList.contains('open');
        
        // 关闭所有其他下拉菜单
        document.querySelectorAll('.dropdown.open').forEach(otherDropdown => {
            if (otherDropdown !== dropdown) {
                otherDropdown.classList.remove('open');
            }
        });
        
        // 切换当前下拉菜单
        dropdown.classList.toggle('open');
        
        // 加载用户信息
        if (!isOpen && typeof loadUserInfo === 'function') {
            loadUserInfo();
        }
    }
}

function closeUserPanelDropdown() {
    const dropdown = document.getElementById('user-panel-dropdown');
    
    if (dropdown) {
        dropdown.classList.remove('open');
    }
}

// 为了向后兼容，保留旧函数名但调用新函数
function toggleUserPanelDrawer() {
    toggleUserPanelDropdown();
}

function closeUserPanelDrawer() {
    closeUserPanelDropdown();
}

// 处理用户面板登出
function handleUserPanelLogout() {
    if (confirm('确定要登出吗？')) {
        window.location.href = '/logout';
    }
}

// 处理管理员面板登出
function handleAdminPanelLogout() {
    if (confirm('确定要登出吗？')) {
        window.location.href = '/logout';
    }
}

// 显示LLM对话框
function showLLMDialog() {
    // 创建对话框元素
    const dialog = document.createElement('div');
    dialog.className = 'llm-dialog';
    dialog.innerHTML = `
        <div class="llm-dialog-overlay"></div>
        <div class="llm-dialog-content">
            <div class="llm-dialog-header">
                <h3>LLM内容处理</h3>
                <button class="llm-dialog-close">&times;</button>
            </div>
            <div class="llm-dialog-body">
                <div class="form-group">
                    <label for="llm-prompt">处理指令：</label>
                    <textarea id="llm-prompt" placeholder="请输入你想要对当前编辑内容进行的操作指令，例如：'翻译成英文'、'优化语法'、'总结要点'等" rows="3"></textarea>
                </div>
                <div class="form-group">
                    <button id="llm-process-btn" class="btn-primary">开始处理</button>
                    <button class="llm-dialog-close btn-secondary">取消</button>
                </div>
            </div>
        </div>
    `;
    
    // 添加到页面
    document.body.appendChild(dialog);
    
    // 绑定事件
    const closeButtons = dialog.querySelectorAll('.llm-dialog-close');
    closeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            document.body.removeChild(dialog);
        });
    });
    
    const processBtn = dialog.querySelector('#llm-process-btn');
    processBtn.addEventListener('click', processWithLLM);
    
    // 点击遮罩关闭
    const overlay = dialog.querySelector('.llm-dialog-overlay');
    overlay.addEventListener('click', () => {
        document.body.removeChild(dialog);
    });
}

// 使用LLM处理内容
async function processWithLLM() {
    const prompt = document.getElementById('llm-prompt').value;
    // 从CodeMirror编辑器获取内容
    const content = codeMirrorEditor ? codeMirrorEditor.getValue() : document.getElementById('editor').value;
    
    if (!prompt.trim()) {
        window.ComponentManager.getComponent('message').warning('请输入处理指令');
        return;
    }
    
    if (!content.trim()) {
        window.ComponentManager.getComponent('message').warning('编辑器内容为空');
        return;
    }
    
    try {
        // 显示处理中消息
        window.ComponentManager.getComponent('message').info('正在处理中...');
        
        // 调用LLM API
        const response = await fetch('/api/admin/llm/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt: prompt,
                content: content,
                model: 'gpt-4o'
            })
        });
        
        const result = await response.json();
        
        if (response.ok && result.status === 'success') {
            // 更新编辑器内容
            if (codeMirrorEditor) {
                codeMirrorEditor.setValue(result.processed_content);
            } else {
                document.getElementById('editor').value = result.processed_content;
            }
            window.ComponentManager.getComponent('message').success('处理完成');
            
            // 关闭对话框
            const dialog = document.querySelector('.llm-dialog');
            if (dialog) {
                document.body.removeChild(dialog);
            }
        } else {
            throw new Error(result.detail || '处理失败');
        }
    } catch (error) {
        console.error('LLM处理失败:', error);
        window.ComponentManager.getComponent('message').error('处理失败: ' + error.message);
    } finally {
        // 确保在任何情况下都关闭对话框
        const dialog = document.querySelector('.llm-dialog');
        if (dialog) {
            document.body.removeChild(dialog);
        }
    }
}

// 保存章节顺序
async function saveChapterOrder() {
    try {
        const chapterItems = document.querySelectorAll('#chapters .chapter-item');
        const chapters = Array.from(chapterItems).map(item => {
            const title = item.querySelector('.chapter-title').textContent;
            const file = item.querySelector('.chapter-file').textContent;
            return { title, file };
        });
        
        const response = await fetch('/api/admin/chapter-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ chapters })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            window.ComponentManager.getComponent('message').success('章节顺序保存成功');
        } else {
            throw new Error(result.detail || '保存章节顺序失败');
        }
    } catch (error) {
        console.error('保存章节顺序失败:', error);
        window.ComponentManager.getComponent('message').error('保存章节顺序失败: ' + error.message);
    }
}

// 重置章节顺序
function resetChapterOrder() {
    if (confirm('确定要重置章节顺序吗？')) {
        if (typeof loadConfigData === 'function') {
            loadConfigData();
        }
    }
}

// 上传Src目录
async function uploadSrc() {
    const fileInput = document.getElementById('src-upload');
    const file = fileInput.files[0];
    
    if (!file) {
        window.ComponentManager.getComponent('message').warning('请选择一个文件');
        return;
    }
    
    if (!file.name.endsWith('.zip')) {
        window.ComponentManager.getComponent('message').error('只允许上传.zip文件');
        return;
    }
    
    // 确认上传
    if (!confirm('上传新的Src目录将会替换当前的Src目录，确定要继续吗？')) {
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        window.ComponentManager.getComponent('message').info('正在上传Src目录...');
        
        const response = await fetch('/api/admin/upload-src', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            window.ComponentManager.getComponent('message').success('Src目录上传成功');
            // 刷新文件树
            await loadFileTree();
        } else {
            const result = await response.json();
            throw new Error(result.detail || '上传失败');
        }
    } catch (error) {
        console.error('上传Src目录失败:', error);
        window.ComponentManager.getComponent('message').error('上传Src目录失败: ' + error.message);
    }
}

// 重置Src目录
async function resetSrc() {
    // 确认重置
    if (!confirm('确定要重置Src目录到默认状态吗？\n\n这将会：\n1. 自动备份当前的Src目录\n2. 删除当前的Src目录内容\n3. 从公共src目录复制默认文件')) {
        console.log('用户取消了重置操作');
        return;
    }
    
    try {
        console.log('开始重置Src目录');
        window.ComponentManager.getComponent('message').info('正在重置Src目录...');
        
        const response = await fetch('/api/admin/reset-src', {
            method: 'POST'
        });
        
        console.log('收到重置响应:', response);
        
        if (response.ok) {
            const result = await response.json();
            window.ComponentManager.getComponent('message').success('Src目录重置成功');
            console.log('Src目录重置成功:', result);
            
            // 显示详细的重置结果信息
            if (result.statistics) {
                const stats = result.statistics;
                const detailMessage = `重置完成！\n复制了 ${stats.files_copied} 个文件，创建了 ${stats.directories_created} 个目录`;
                setTimeout(() => {
                    window.ComponentManager.getComponent('message').success(detailMessage);
                }, 1000);
            }
            
            // 刷新文件树
            await loadFileTree();
        } else {
            const result = await response.json();
            console.error('重置失败:', result);
            throw new Error(result.detail || '重置失败');
        }
    } catch (error) {
        console.error('重置Src目录失败:', error);
        window.ComponentManager.getComponent('message').error('重置Src目录失败: ' + error.message);
    }
}

// =============================================================================
// 侧边栏显示/隐藏功能
// =============================================================================

// 切换文件浏览器显示状态
function toggleSidebar() {
    const fileBrowser = document.querySelector('.file-browser');
    const resizer = document.getElementById('sidebar-resizer');
    const mainContent = document.querySelector('.main-content');
    const appLayout = document.querySelector('.app-layout');
    
    if (!fileBrowser) {
        console.warn('未找到文件浏览器元素');
        return;
    }
    
    const isHidden = fileBrowser.style.display === 'none' || fileBrowser.classList.contains('hidden');
    
    if (isHidden) {
        // 显示文件浏览器
        fileBrowser.style.display = 'block';
        fileBrowser.classList.remove('hidden');
        
        // 获取保存的宽度或使用默认宽度
        const savedWidth = sessionStorage.getItem('sidebar-width');
        const width = savedWidth ? parseInt(savedWidth) : 320;
        fileBrowser.style.width = width + 'px';
        
        if (resizer) {
            resizer.style.display = 'block';
            resizer.style.left = width + 'px';
        }
        
        if (appLayout) {
            appLayout.style.marginLeft = width + 'px';
        }
        
        if (mainContent) {
            mainContent.style.marginLeft = '';
            mainContent.style.width = '';
        }
        
        window.ComponentManager.getComponent('message').info('文件浏览器已显示');
        // 保存状态到sessionStorage
        sessionStorage.setItem('sidebar-visible', 'true');
    } else {
        // 隐藏文件浏览器
        fileBrowser.style.display = 'none';
        fileBrowser.classList.add('hidden');
        
        if (resizer) {
            resizer.style.display = 'none';
        }
        
        if (appLayout) {
            appLayout.style.marginLeft = '0';
        }
        
        if (mainContent) {
            mainContent.style.marginLeft = '0';
            mainContent.style.width = '100%';
        }
        
        window.ComponentManager.getComponent('message').info('文件浏览器已隐藏');
        // 保存状态到sessionStorage
        sessionStorage.setItem('sidebar-visible', 'false');
    }
}

// 隐藏文件浏览器
function hideSidebar() {
    const fileBrowser = document.querySelector('.file-browser');
    const resizer = document.getElementById('sidebar-resizer');
    const mainContent = document.querySelector('.main-content');
    const appLayout = document.querySelector('.app-layout');
    
    if (!fileBrowser) return;
    
    fileBrowser.style.display = 'none';
    fileBrowser.classList.add('hidden');
    
    if (resizer) {
        resizer.style.display = 'none';
    }
    
    if (appLayout) {
        appLayout.style.marginLeft = '0';
    }
    
    if (mainContent) {
        mainContent.style.marginLeft = '0';
        mainContent.style.width = '100%';
    }
    
    sessionStorage.setItem('sidebar-visible', 'false');
}

// 显示文件浏览器
function showSidebar() {
    const fileBrowser = document.querySelector('.file-browser');
    const resizer = document.getElementById('sidebar-resizer');
    const mainContent = document.querySelector('.main-content');
    const appLayout = document.querySelector('.app-layout');
    
    if (!fileBrowser) return;
    
    fileBrowser.style.display = 'block';
    fileBrowser.classList.remove('hidden');
    
    // 获取保存的宽度或使用默认宽度
    const savedWidth = sessionStorage.getItem('sidebar-width');
    const width = savedWidth ? parseInt(savedWidth) : 320;
    fileBrowser.style.width = width + 'px';
    
    if (resizer) {
        resizer.style.display = 'block';
        resizer.style.left = width + 'px';
    }
    
    if (appLayout) {
        appLayout.style.marginLeft = width + 'px';
    }
    
    if (mainContent) {
        mainContent.style.marginLeft = '';
        mainContent.style.width = '';
    }
    
    sessionStorage.setItem('sidebar-visible', 'true');
}

// 初始化侧边栏状态
function initializeSidebarState() {
    const sidebarVisible = sessionStorage.getItem('sidebar-visible');
    
    // 如果之前设置为隐藏，则恢复隐藏状态
    if (sidebarVisible === 'false') {
        hideSidebar();
    }
}

// =============================================================================
// 可调整分隔符功能
// =============================================================================

// 初始化可调整分隔符
function initializeResizer() {
    const resizer = document.getElementById('sidebar-resizer');
    const fileBrowser = document.querySelector('.file-browser');
    const mainContent = document.querySelector('.main-content');
    const appLayout = document.querySelector('.app-layout');
    
    if (!resizer || !fileBrowser || !mainContent) {
        console.warn('找不到必要的元素，无法初始化分隔符');
        return;
    }
    
    let isResizing = false;
    let startX = 0;
    let startFileBrowserWidth = 0;
    
    // 更新所有相关元素的位置和大小
    function updateLayout(width) {
        // 更新文件浏览器宽度
        fileBrowser.style.width = width + 'px';
        
        // 更新调整器位置
        resizer.style.left = width + 'px';
        
        // 更新app-layout的左边距
        if (appLayout) {
            appLayout.style.marginLeft = width + 'px';
        }
        
        // 保存到sessionStorage
        sessionStorage.setItem('sidebar-width', width.toString());
    }
    
    // 从sessionStorage读取保存的宽度并应用
    const savedWidth = sessionStorage.getItem('sidebar-width');
    if (savedWidth) {
        const width = parseInt(savedWidth);
        if (width >= 250 && width <= 700) { // 限制合理范围
            updateLayout(width);
        }
    }
    
    resizer.addEventListener('mousedown', (e) => {
        isResizing = true;
        startX = e.clientX;
        startFileBrowserWidth = fileBrowser.offsetWidth;
        
        // 添加拖拽时的视觉反馈
        document.body.style.cursor = 'ew-resize';
        document.body.style.userSelect = 'none';
        resizer.style.background = 'linear-gradient(90deg, rgba(33, 150, 243, 0.4) 0%, rgba(33, 150, 243, 0.8) 50%, rgba(33, 150, 243, 0.4) 100%)';
        
        // 防止选中文本
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        
        const deltaX = e.clientX - startX;
        const newWidth = startFileBrowserWidth + deltaX;
        
        // 限制最小和最大宽度
        const minWidth = 250;
        const maxWidth = Math.min(700, window.innerWidth * 0.6); // 最大不超过屏幕宽度的60%
        
        if (newWidth >= minWidth && newWidth <= maxWidth) {
            updateLayout(newWidth);
        }
        
        e.preventDefault();
    });
    
    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            
            // 恢复鼠标样式
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            resizer.style.background = '';
        }
    });
    
    // 双击重置宽度
    resizer.addEventListener('dblclick', () => {
        const defaultWidth = 320; // 默认宽度
        updateLayout(defaultWidth);
        window.ComponentManager.getComponent('message').info('已重置文件浏览器宽度');
    });
    
    console.log('可调整分隔符初始化成功');
}

// =============================================================================
// 章节管理抽屉菜单功能
// =============================================================================

// 显示章节管理抽屉菜单
function showChapterManagement() {
    console.log('显示章节管理抽屉菜单');
    toggleChapterDrawer();
}

// 切换章节管理抽屉菜单显示状态
function toggleChapterDrawer() {
    const drawer = document.getElementById('chapter-drawer');
    const overlay = document.getElementById('chapter-drawer-overlay');
    
    if (drawer && overlay) {
        const isOpen = drawer.classList.contains('open');
        
        if (isOpen) {
            closeChapterDrawer();
        } else {
            openChapterDrawer();
        }
    }
}

// 打开章节管理抽屉菜单
function openChapterDrawer() {
    const drawer = document.getElementById('chapter-drawer');
    const overlay = document.getElementById('chapter-drawer-overlay');
    
    if (drawer && overlay) {
        drawer.classList.add('open');
        overlay.classList.add('open');
        document.body.classList.add('drawer-left-open');
        
        // 加载章节管理数据
        loadChapterManagementData();
        
        console.log('章节管理抽屉菜单已打开');
    }
}

// 关闭章节管理抽屉菜单
function closeChapterDrawer() {
    const drawer = document.getElementById('chapter-drawer');
    const overlay = document.getElementById('chapter-drawer-overlay');
    
    if (drawer && overlay) {
        drawer.classList.remove('open');
        overlay.classList.remove('open');
        document.body.classList.remove('drawer-left-open');
        
        console.log('章节管理抽屉菜单已关闭');
    }
}

// 加载章节管理数据
async function loadChapterManagementData() {
    try {
        console.log('开始加载章节管理数据');
        
        // 获取章节配置
        const response = await fetch('/api/admin/chapter-config');
        if (response.ok) {
            const data = await response.json();
            renderChapterList(data.chapters || []);
        } else {
            console.warn('获取章节配置失败，使用默认配置');
            renderChapterList([]);
        }
    } catch (error) {
        console.error('加载章节管理数据失败:', error);
        renderChapterList([]);
    }
}

// 渲染章节列表
function renderChapterList(chapters) {
    const chaptersList = document.getElementById('drawer-chapters');
    if (!chaptersList) return;
    
    chaptersList.innerHTML = '';
    
    if (chapters.length === 0) {
        chaptersList.innerHTML = '<li class="no-chapters">暂无章节数据</li>';
        return;
    }
    
    chapters.forEach((chapter, index) => {
        const li = document.createElement('li');
        li.className = 'chapter-item';
        li.draggable = true;
        li.dataset.index = index;
        
        li.innerHTML = `
            <div class="chapter-info">
                <span class="chapter-order">${index + 1}.</span>
                <span class="chapter-title">${chapter.title || '未命名章节'}</span>
                <span class="chapter-file">${chapter.file || ''}</span>
            </div>
            <div class="chapter-actions">
                <button class="btn-action btn-edit" onclick="editChapterInDrawer(${index})" title="编辑">
                    ✏️
                </button>
                <button class="btn-action btn-delete" onclick="deleteChapterInDrawer(${index})" title="删除">
                    🗑️
                </button>
            </div>
        `;
        
        chaptersList.appendChild(li);
    });
    
    // 添加拖拽排序功能
    enableChapterDragSort();
}

// 启用章节拖拽排序
function enableChapterDragSort() {
    const chaptersList = document.getElementById('drawer-chapters');
    if (!chaptersList) return;
    
    let draggedElement = null;
    
    chaptersList.addEventListener('dragstart', function(e) {
        draggedElement = e.target.closest('.chapter-item');
        e.target.style.opacity = '0.5';
    });
    
    chaptersList.addEventListener('dragend', function(e) {
        e.target.style.opacity = '';
        draggedElement = null;
    });
    
    chaptersList.addEventListener('dragover', function(e) {
        e.preventDefault();
    });
    
    chaptersList.addEventListener('drop', function(e) {
        e.preventDefault();
        const dropTarget = e.target.closest('.chapter-item');
        
        if (draggedElement && dropTarget && draggedElement !== dropTarget) {
            const parent = dropTarget.parentNode;
            const allItems = Array.from(parent.children);
            const draggedIndex = allItems.indexOf(draggedElement);
            const targetIndex = allItems.indexOf(dropTarget);
            
            if (draggedIndex < targetIndex) {
                parent.insertBefore(draggedElement, dropTarget.nextSibling);
            } else {
                parent.insertBefore(draggedElement, dropTarget);
            }
            
            // 更新章节顺序
            updateChapterOrder();
        }
    });
}

// 更新章节顺序
function updateChapterOrder() {
    const chapterItems = document.querySelectorAll('#drawer-chapters .chapter-item');
    chapterItems.forEach((item, index) => {
        const orderSpan = item.querySelector('.chapter-order');
        if (orderSpan) {
            orderSpan.textContent = `${index + 1}.`;
        }
        item.dataset.index = index;
    });
}

// 编辑章节（在抽屉中）
function editChapterInDrawer(index) {
    console.log('编辑章节:', index);
    window.ComponentManager.getComponent('message').info('章节编辑功能待实现');
}

// 删除章节（在抽屉中）
function deleteChapterInDrawer(index) {
    if (confirm('确定要删除这个章节吗？')) {
        console.log('删除章节:', index);
        window.ComponentManager.getComponent('message').info('章节删除功能待实现');
    }
}

// 保存章节顺序（抽屉版本）
async function saveChapterOrderInDrawer() {
    try {
        window.ComponentManager.getComponent('message').info('正在保存章节顺序...');
        
        const chapterItems = document.querySelectorAll('#drawer-chapters .chapter-item');
        const chapters = Array.from(chapterItems).map((item, index) => {
            const titleElement = item.querySelector('.chapter-title');
            const fileElement = item.querySelector('.chapter-file');
            
            return {
                title: titleElement ? titleElement.textContent : '',
                file: fileElement ? fileElement.textContent : '',
                order: index + 1
            };
        });
        
        const response = await fetch('/api/admin/chapter-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ chapters })
        });
        
        if (response.ok) {
            window.ComponentManager.getComponent('message').success('章节顺序保存成功');
            // 刷新文件树以反映更改
            if (typeof loadFileTree === 'function') {
                loadFileTree();
            }
        } else {
            throw new Error('保存失败');
        }
    } catch (error) {
        console.error('保存章节顺序失败:', error);
        window.ComponentManager.getComponent('message').error('保存章节顺序失败: ' + error.message);
    }
}

// 重置章节顺序（抽屉版本）
async function resetChapterOrderInDrawer() {
    if (confirm('确定要重置章节顺序吗？这将会恢复到默认排序。')) {
        try {
            window.ComponentManager.getComponent('message').info('正在重置章节顺序...');
            
            const response = await fetch('/api/admin/reset-chapters', {
                method: 'POST'
            });
            
            if (response.ok) {
                window.ComponentManager.getComponent('message').success('章节顺序重置成功');
                // 重新加载章节数据
                loadChapterManagementData();
                // 刷新文件树
                if (typeof loadFileTree === 'function') {
                    loadFileTree();
                }
            } else {
                throw new Error('重置失败');
            }
        } catch (error) {
            console.error('重置章节顺序失败:', error);
            window.ComponentManager.getComponent('message').error('重置章节顺序失败: ' + error.message);
        }
    }
}

// 绑定章节管理抽屉菜单事件
function bindChapterDrawerEvents() {
    console.log('绑定章节管理抽屉菜单事件');
    
    // 关闭按钮 - 统一使用closeChapterDrawer函数
    const closeBtn = document.getElementById('close-chapter-drawer-btn');
    if (closeBtn && !closeBtn.dataset.listenerAdded) {
        closeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            closeChapterDrawer();
        });
        closeBtn.dataset.listenerAdded = 'true';
        console.log('章节抽屉关闭按钮事件已绑定');
    }
    
    // 遮罩层点击关闭
    const overlay = document.getElementById('chapter-drawer-overlay');
    if (overlay && !overlay.dataset.listenerAdded) {
        overlay.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            closeChapterDrawer();
        });
        overlay.dataset.listenerAdded = 'true';
        console.log('章节抽屉遮罩层事件已绑定');
    }
    
    // 保存按钮
    const saveBtn = document.getElementById('drawer-save-chapters-btn');
    if (saveBtn && !saveBtn.dataset.listenerAdded) {
        saveBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            saveChapterOrderInDrawer();
        });
        saveBtn.dataset.listenerAdded = 'true';
        console.log('章节保存按钮事件已绑定');
    }
    
    // 重置按钮
    const resetBtn = document.getElementById('drawer-reset-chapters-btn');
    if (resetBtn && !resetBtn.dataset.listenerAdded) {
        resetBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            resetChapterOrderInDrawer();
        });
        resetBtn.dataset.listenerAdded = 'true';
        console.log('章节重置按钮事件已绑定');
    }
    
    // 刷新按钮
    const refreshBtn = document.getElementById('drawer-refresh-chapters-btn');
    if (refreshBtn && !refreshBtn.dataset.listenerAdded) {
        refreshBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            loadChapterManagementData();
        });
        refreshBtn.dataset.listenerAdded = 'true';
        console.log('章节刷新按钮事件已绑定');
    }
    
    // 快速操作按钮
    const createChapterBtn = document.getElementById('drawer-create-chapter');
    if (createChapterBtn && !createChapterBtn.dataset.listenerAdded) {
        createChapterBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            window.ComponentManager.getComponent('message').info('新建章节功能待实现');
        });
        createChapterBtn.dataset.listenerAdded = 'true';
        console.log('新建章节按钮事件已绑定');
    }
    
    const importChaptersBtn = document.getElementById('drawer-import-chapters');
    if (importChaptersBtn && !importChaptersBtn.dataset.listenerAdded) {
        importChaptersBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            window.ComponentManager.getComponent('message').info('导入章节功能待实现');
        });
        importChaptersBtn.dataset.listenerAdded = 'true';
        console.log('导入章节按钮事件已绑定');
    }
}

// ============================================================================
// 全局函数导出 - 确保关键函数在全局作用域中可用
// ============================================================================

// 将loadFileTree函数导出到全局作用域
window.loadFileTree = loadFileTree;

console.log('Common.js: loadFileTree函数已导出到全局作用域');

// 全局点击事件处理 - 关闭下拉菜单
document.addEventListener('click', function(e) {
    // 检查点击是否在管理面板下拉菜单外部
    const adminPanelDropdown = document.getElementById('admin-panel-dropdown');
    const adminPanelBtn = document.getElementById('admin-panel-btn');
    
    if (adminPanelDropdown && adminPanelBtn) {
        const isClickInsideDropdown = adminPanelDropdown.contains(e.target);
        const isClickOnButton = adminPanelBtn.contains(e.target);
        
        if (!isClickInsideDropdown && !isClickOnButton) {
            closeAdminPanelDropdown();
        }
    }
    
    // 检查点击是否在用户面板下拉菜单外部
    const userPanelDropdown = document.getElementById('user-panel-dropdown');
    const myAccountBtn = document.getElementById('myaccount-btn');
    
    if (userPanelDropdown && myAccountBtn) {
        const isClickInsideUserDropdown = userPanelDropdown.contains(e.target);
        const isClickOnUserButton = myAccountBtn.contains(e.target);
        
        if (!isClickInsideUserDropdown && !isClickOnUserButton) {
            if (typeof closeUserPanelDropdown === 'function') {
                closeUserPanelDropdown();
            }
        }
    }
});

// 为下拉菜单中的链接添加点击关闭功能
function bindDropdownLinkEvents() {
    const adminPanelDropdown = document.getElementById('admin-panel-dropdown');
    if (adminPanelDropdown) {
        const dropdownLinks = adminPanelDropdown.querySelectorAll('a');
        dropdownLinks.forEach(link => {
            if (!link.dataset.dropdownListenerAdded) {
                // 为登出链接添加确认对话框
                if (link.getAttribute('href') === '/logout') {
                    link.addEventListener('click', function(e) {
                        if (!confirm('确定要登出吗？')) {
                            e.preventDefault();
                        } else {
                            closeAdminPanelDropdown();
                        }
                    });
                } else {
                    // 点击其他链接时关闭下拉菜单
                    link.addEventListener('click', function() {
                        closeAdminPanelDropdown();
                    });
                }
                link.dataset.dropdownListenerAdded = 'true';
            }
        });
    }
}

// 在页面加载完成后绑定下拉菜单链接事件
document.addEventListener('DOMContentLoaded', function() {
    bindDropdownLinkEvents();
});

// 将管理面板下拉菜单函数暴露到全局作用域
window.toggleAdminPanelDropdown = toggleAdminPanelDropdown;
window.openAdminPanelDropdown = openAdminPanelDropdown;
window.closeAdminPanelDropdown = closeAdminPanelDropdown;
window.handleAdminPanelLogout = handleAdminPanelLogout;

// === 章节抽屉管理功能 ===

// 显示章节管理抽屉
function showChapterManagement() {
    console.log('显示章节管理抽屉');
    
    const chapterDrawer = document.getElementById('chapter-drawer');
    if (!chapterDrawer) {
        console.error('章节抽屉元素不存在');
        return;
    }
    
    // 打开章节抽屉
    chapterDrawer.classList.add('open');
    
    // 添加body类来调整布局
    document.body.classList.add('drawer-left-open');
    
    // 创建并显示遮罩层
    let overlay = document.getElementById('chapter-drawer-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'chapter-drawer-overlay';
        overlay.className = 'drawer-overlay';
        document.body.appendChild(overlay);
        
        // 点击遮罩层关闭抽屉
        overlay.addEventListener('click', hideChapterManagement);
    }
    overlay.classList.add('open');
    
    // 绑定关闭按钮事件
    const closeBtn = chapterDrawer.querySelector('[data-drawer-close]');
    if (closeBtn && !closeBtn.dataset.listenerAdded) {
        closeBtn.addEventListener('click', hideChapterManagement);
        closeBtn.dataset.listenerAdded = 'true';
    }
    
    console.log('章节管理抽屉已打开');
}

// 隐藏章节管理抽屉
function hideChapterManagement() {
    console.log('隐藏章节管理抽屉');
    
    const chapterDrawer = document.getElementById('chapter-drawer');
    const overlay = document.getElementById('chapter-drawer-overlay');
    
    if (chapterDrawer) {
        chapterDrawer.classList.remove('open');
    }
    
    if (overlay) {
        overlay.classList.remove('open');
    }
    
    // 移除body类来恢复布局
    document.body.classList.remove('drawer-left-open');
    
    console.log('章节管理抽屉已关闭');
}

// 切换章节管理抽屉
function toggleChapterManagement() {
    const chapterDrawer = document.getElementById('chapter-drawer');
    if (chapterDrawer && chapterDrawer.classList.contains('open')) {
        hideChapterManagement();
    } else {
        showChapterManagement();
    }
}

// 初始化章节抽屉
function initializeChapterDrawer() {
    // 确保章节抽屉默认关闭
    const chapterDrawer = document.getElementById('chapter-drawer');
    if (chapterDrawer) {
        chapterDrawer.classList.remove('open');
    }
    
    // 确保body没有抽屉打开的类
    document.body.classList.remove('drawer-left-open');
    
    // 移除可能存在的遮罩层
    const overlay = document.getElementById('chapter-drawer-overlay');
    if (overlay) {
        overlay.classList.remove('open');
    }
    
    console.log('章节抽屉已初始化为关闭状态');
}

// 页面加载时初始化章节抽屉
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeChapterDrawer);
} else {
    initializeChapterDrawer();
}