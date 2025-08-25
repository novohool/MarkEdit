// MarkEdit 公共函数库
// 包含所有主题共享的JavaScript函数

// 全局变量
let currentFilePath = null;
let currentFileType = null;
let currentFileEncoding = null;
let currentFileArea = null; // 'src' 或 'build'
let codeMirrorEditor = null; // CodeMirror 编辑器实例
let userInfo = {
    role: 'user', // 默认角色为普通用户
    isAdmin: false,
    permissions: [], // 用户权限列表
    roles: [], // 用户角色列表
    userType: 'user' // 用户类型
};

// 显示消息函数
function showMessage(message, type) {
    // 创建消息元素
    const messageElement = document.createElement('div');
    messageElement.className = `message message-${type}`;
    messageElement.textContent = message;
    
    // 添加到页面
    document.body.appendChild(messageElement);
    
    // 3秒后自动移除
    setTimeout(() => {
        if (messageElement.parentNode) {
            messageElement.parentNode.removeChild(messageElement);
        }
    }, 3000);
}

// 抽屉菜单控制函数
function toggleAdminDrawer() {
    console.log('toggleAdminDrawer 被调用');
    const drawer = document.getElementById('admin-drawer');
    const overlay = document.getElementById('drawer-overlay');
    
    console.log('drawer 元素:', drawer);
    console.log('overlay 元素:', overlay);
    
    if (drawer) {
        drawer.classList.toggle('open');
        console.log('drawer 添加/移除 open 类后的 classList:', drawer.classList.toString());
    }
    if (overlay) {
        overlay.classList.toggle('open');
        console.log('overlay 添加/移除 open 类后的 classList:', overlay.classList.toString());
    }
}

function closeAdminDrawer() {
    const drawer = document.getElementById('admin-drawer');
    const overlay = document.getElementById('drawer-overlay');
    
    drawer.classList.remove('open');
    overlay.classList.remove('open');
}

// 初始化编辑器状态
function initializeEditor() {
    // 隐藏所有视图
    document.getElementById('editor').style.display = 'none';
    document.getElementById('image-viewer').style.display = 'none';
    document.getElementById('binary-viewer').style.display = 'none';
    document.getElementById('preview-container').style.display = 'none';
    
    // 隐藏预览按钮
    document.getElementById('preview-btn').style.display = 'none';
    
    // 禁用删除按钮
    document.getElementById('delete-btn').disabled = true;
}

// 初始化CodeMirror编辑器
function initializeCodeMirror() {
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
        
        return userInfo;
    } catch (error) {
        console.error('获取用户角色信息失败:', error);
        // 即使获取角色信息失败，也要返回默认用户信息
        userInfo.isAdmin = false;
        userInfo.permissions = [];
        userInfo.roles = [];
        userInfo.userType = 'user';
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
        
        // 添加工具栏
        const toolbar = document.createElement('div');
        toolbar.className = 'toolbar';
        toolbar.innerHTML = `
            <button id="create-file-btn" class="btn-secondary">新建文件</button>
            <button id="refresh-btn" class="btn-secondary">刷新</button>
        `;
        fileTreeElement.appendChild(toolbar);
        
        // 添加刷新按钮事件
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', loadFileTree);
        }
        
        // 添加创建文件按钮事件
        const createFileBtn = document.getElementById('create-file-btn');
        if (createFileBtn) {
            createFileBtn.addEventListener('click', showCreateFileDialog);
        }
        
        // 创建src文件树容器
        const srcContainer = document.createElement('div');
        srcContainer.className = 'file-area';
        srcContainer.innerHTML = '<h3>Src</h3>';
        fileTreeElement.appendChild(srcContainer);
        
        const srcTreeContainer = document.createElement('div');
        srcTreeContainer.id = 'src-tree-container';
        srcTreeContainer.className = 'tree-container';
        srcContainer.appendChild(srcTreeContainer);
        
        // 创建build文件树容器
        const buildContainer = document.createElement('div');
        buildContainer.className = 'file-area';
        buildContainer.innerHTML = '<h3>Build</h3>';
        fileTreeElement.appendChild(buildContainer);
        
        const buildTreeContainer = document.createElement('div');
        buildTreeContainer.id = 'build-tree-container';
        buildTreeContainer.className = 'tree-container';
        buildContainer.appendChild(buildTreeContainer);
        
        // 递归渲染文件树
        if (fileData.src) {
            renderFileTree(fileData.src, srcTreeContainer, 'src');
        }
        
        if (fileData.build) {
            renderFileTree(fileData.build, buildTreeContainer, 'build');
        }
    } catch (error) {
        console.error('加载文件树失败:', error);
        showMessage('加载文件树失败: ' + error.message, 'error');
    }
}

// 保存文件
async function saveFile() {
    if (!currentFilePath || currentFileType !== 'text' || currentFileArea !== 'src') {
        showMessage('请选择一个src目录下的文本文件进行保存', 'warning');
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
            showMessage('文件保存成功', 'success');
        } else {
            throw new Error(result.detail || '保存失败');
        }
    } catch (error) {
        console.error('保存文件失败:', error);
        showMessage('保存文件失败: ' + error.message, 'error');
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
            showMessage('文件删除成功', 'success');
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
        showMessage('删除文件失败: ' + error.message, 'error');
    }
}

// 下载Src目录
async function downloadSrc() {
    try {
        console.log('开始下载Src目录');
        showMessage('正在准备下载Src目录...', 'info');
        
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
        showMessage('下载Src目录失败: ' + error.message, 'error');
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
        
        showMessage('主题切换成功', 'success');
    } catch (error) {
        console.error('切换主题失败:', error);
        showMessage('切换主题失败: ' + error.message, 'error');
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
            fileItem.innerHTML = `
                <span class="file-name">${file.name}</span>
            `;
            
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
        
        // 加载文件内容
        loadFile(file.path, area);
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
                <div class="context-menu-item" data-action="create-directory">新建目录</div>
                <div class="context-menu-item" data-action="delete">删除目录</div>
            `;
        } else if (type === 'file') {
            contextMenu.innerHTML = `
                <div class="context-menu-item" data-action="delete">删除文件</div>
            `;
        }
    } else if (area === 'build') {
        if (type === 'file') {
            const extension = path.substring(path.lastIndexOf('.')).toLowerCase();
            const previewableExtensions = ['.epub', '.html', '.pdf', '.svg'];
            if (previewableExtensions.includes(extension)) {
                contextMenu.innerHTML = `
                    <div class="context-menu-item" data-action="preview">预览</div>
                `;
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
        case 'create-directory':
            showCreateDirectoryDialog(path);
            break;
        case 'delete':
            if (confirm(`确定要删除文件 "${path}" 吗？`)) {
                deleteFileAtPath(path);
            }
            break;
        case 'preview':
            if (typeof previewBuildFile === 'function') {
                previewBuildFile(path);
            }
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
    const adminMenuBtn = document.getElementById('admin-menu-btn');
    const closeDrawerBtn = document.getElementById('close-drawer-btn');
    const closeUserPanelBtn = document.getElementById('close-user-panel-btn');
    const drawerOverlay = document.getElementById('drawer-overlay');
    const adminDrawer = document.getElementById('admin-drawer');
    const userPanelDrawer = document.getElementById('user-panel-drawer');
    
    console.log('按钮状态检查:', {
        adminMenuBtn: !!adminMenuBtn,
        closeDrawerBtn: !!closeDrawerBtn,
        drawerOverlay: !!drawerOverlay,
        adminDrawer: !!adminDrawer,
        adminMenuBtnListenerAdded: adminMenuBtn ? adminMenuBtn.dataset.listenerAdded : 'N/A'
    });
    
    // 确保只绑定一次事件监听器
    if (adminMenuBtn && adminDrawer && !adminMenuBtn.dataset.listenerAdded) {
        adminMenuBtn.addEventListener('click', function() {
            console.log('admin-menu-btn 被点击，调用 toggleAdminDrawer');
            toggleAdminDrawer();
        });
        adminMenuBtn.dataset.listenerAdded = 'true';
    }
    
    if (closeDrawerBtn && adminDrawer && !closeDrawerBtn.dataset.listenerAdded) {
        closeDrawerBtn.addEventListener('click', function() {
            console.log('close-drawer-btn 被点击，调用 closeAdminDrawer');
            closeAdminDrawer();
        });
        closeDrawerBtn.dataset.listenerAdded = 'true';
    }
    
    if (closeUserPanelBtn && userPanelDrawer && !closeUserPanelBtn.dataset.listenerAdded) {
        closeUserPanelBtn.addEventListener('click', function() {
            userPanelDrawer.classList.remove('open');
            if (drawerOverlay) {
                drawerOverlay.classList.remove('open');
            }
        });
        closeUserPanelBtn.dataset.listenerAdded = 'true';
    }
    
    if (drawerOverlay && !drawerOverlay.dataset.listenerAdded) {
        drawerOverlay.addEventListener('click', function() {
            console.log('drawer-overlay 被点击，关闭所有抽屉');
            closeAdminDrawer();
            if (typeof closeUserPanelDrawer === 'function') {
                closeUserPanelDrawer();
            }
        });
        drawerOverlay.dataset.listenerAdded = 'true';
    }
    
    // 为抽屉菜单中的链接添加事件监听器（只在管理抽屉存在时）
    if (adminDrawer) {
        const drawerLinks = document.querySelectorAll('#admin-drawer a');
        drawerLinks.forEach(link => {
            if (!link.dataset.listenerAdded) {
                // 为登出链接添加确认对话框
                if (link.getAttribute('href') === '/logout') {
                    link.addEventListener('click', function(e) {
                        if (!confirm('确定要登出吗？')) {
                            e.preventDefault();
                        }
                    });
                }
                
                // 点击链接时关闭抽屉菜单
                link.addEventListener('click', function() {
                    closeAdminDrawer();
                });
                
                link.dataset.listenerAdded = 'true';
            }
        });
        
        // 为用户面板链接添加事件监听器
        const drawerMyAccountLink = document.getElementById('drawer-myaccount-link');
        if (drawerMyAccountLink && !drawerMyAccountLink.dataset.listenerAdded) {
            drawerMyAccountLink.addEventListener('click', function(e) {
                e.preventDefault();
                // 显示用户面板下拉菜单
                if (typeof toggleUserPanelDrawer === 'function') {
                    toggleUserPanelDrawer();
                }
            });
            drawerMyAccountLink.dataset.listenerAdded = 'true';
        }
    }
    
    console.log('bindDrawerEvents 函数执行完成');
}

// 图书生成函数
async function buildBook(scriptName) {
    try {
        // 显示正在处理的消息
        showMessage(`正在执行 ${scriptName}...`, 'info');
        
        // 调用API
        const response = await fetch(`/api/admin/build/${scriptName}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok && result.status === 'success') {
            showMessage(`${scriptName} 执行成功`, 'success');
            console.log('stdout:', result.stdout);
            console.log('stderr:', result.stderr);
            
            // 构建成功后刷新文件树
            await loadFileTree();
        } else {
            showMessage(`${scriptName} 执行失败: ${result.message}`, 'error');
            console.error('stdout:', result.stdout);
            console.error('stderr:', result.stderr);
        }
    } catch (error) {
        console.error('执行图书生成失败:', error);
        showMessage(`执行图书生成失败: ${error.message}`, 'error');
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
            showMessage('主题设置保存成功', 'success');
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
        showMessage('保存主题设置失败: ' + error.message, 'error');
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
            showMessage('LLM配置必须是有效的JSON格式', 'warning');
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
            showMessage('LLM配置保存成功', 'success');
        } else {
            throw new Error(result.detail || '保存LLM配置失败');
        }
    } catch (error) {
        console.error('保存LLM配置失败:', error);
        showMessage('保存LLM配置失败: ' + error.message, 'error');
    }
}

// 重置用户LLM配置
async function resetUserLlmConfig() {
    try {
        const response = await fetch('/api/user/info');
        const result = await response.json();
        
        if (response.ok) {
            document.getElementById('user-panel-llm-config').value = result.llm_config;
            showMessage('LLM配置已重置', 'success');
        } else {
            throw new Error(result.detail || '重置LLM配置失败');
        }
    } catch (error) {
        console.error('重置LLM配置失败:', error);
        showMessage('重置LLM配置失败: ' + error.message, 'error');
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
        showMessage('加载用户信息失败: ' + error.message, 'error');
    }
}

// 创建文件函数
async function createFile(directoryPath, fileName) {
    if (!fileName) {
        showMessage('文件名不能为空', 'warning');
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
            showMessage('文件创建成功', 'success');
            // 刷新文件树
            loadFileTree();
        } else {
            throw new Error(result.detail || '创建文件失败');
        }
    } catch (error) {
        console.error('创建文件失败:', error);
        showMessage('创建文件失败: ' + error.message, 'error');
    }
}

// 创建目录函数
async function createDirectory(directoryPath, dirName) {
    if (!dirName) {
        showMessage('目录名不能为空', 'warning');
        return;
    }
    
    try {
        const fullPath = directoryPath ? `${directoryPath}/${dirName}` : dirName;
        
        const response = await fetch(`/api/directory/src/${fullPath}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('目录创建成功', 'success');
            // 刷新文件树
            loadFileTree();
        } else {
            throw new Error(result.detail || '创建目录失败');
        }
    } catch (error) {
        console.error('创建目录失败:', error);
        showMessage('创建目录失败: ' + error.message, 'error');
    }
}

// 用户面板下拉菜单控制函数
function toggleUserPanelDrawer() {
    const drawer = document.getElementById('user-panel-drawer');
    const overlay = document.getElementById('drawer-overlay');
    
    if (drawer && overlay) {
        drawer.classList.toggle('open');
        overlay.classList.toggle('open');
        // 加载用户信息
        if (typeof loadUserInfo === 'function') {
            loadUserInfo();
        }
    }
}

function closeUserPanelDrawer() {
    const drawer = document.getElementById('user-panel-drawer');
    const overlay = document.getElementById('drawer-overlay');
    
    if (drawer && overlay) {
        drawer.classList.remove('open');
        overlay.classList.remove('open');
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
        showMessage('请输入处理指令', 'warning');
        return;
    }
    
    if (!content.trim()) {
        showMessage('编辑器内容为空', 'warning');
        return;
    }
    
    try {
        // 显示处理中消息
        showMessage('正在处理中...', 'info');
        
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
            showMessage('处理完成', 'success');
            
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
        showMessage('处理失败: ' + error.message, 'error');
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
            const fileInput = item.querySelector('input[type="hidden"]');
            const file = fileInput ? fileInput.value : '';
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
            showMessage('章节顺序保存成功', 'success');
        } else {
            throw new Error(result.detail || '保存章节顺序失败');
        }
    } catch (error) {
        console.error('保存章节顺序失败:', error);
        showMessage('保存章节顺序失败: ' + error.message, 'error');
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
        showMessage('请选择一个文件', 'warning');
        return;
    }
    
    if (!file.name.endsWith('.zip')) {
        showMessage('只允许上传.zip文件', 'error');
        return;
    }
    
    // 确认上传
    if (!confirm('上传新的Src目录将会替换当前的Src目录，确定要继续吗？')) {
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        showMessage('正在上传Src目录...', 'info');
        
        const response = await fetch('/api/admin/upload-src', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            showMessage('Src目录上传成功', 'success');
            // 刷新文件树
            await loadFileTree();
        } else {
            const result = await response.json();
            throw new Error(result.detail || '上传失败');
        }
    } catch (error) {
        console.error('上传Src目录失败:', error);
        showMessage('上传Src目录失败: ' + error.message, 'error');
    }
}

// 重置Src目录
async function resetSrc() {
    // 确认重置
    if (!confirm('确定要重置Src目录到最新备份吗？这将删除当前的Src目录并恢复到最新备份。')) {
        console.log('用户取消了重置操作');
        return;
    }
    
    try {
        console.log('开始重置Src目录');
        showMessage('正在重置Src目录...', 'info');
        
        const response = await fetch('/api/admin/reset-src', {
            method: 'POST'
        });
        
        console.log('收到重置响应:', response);
        
        if (response.ok) {
            showMessage('Src目录重置成功', 'success');
            console.log('Src目录重置成功');
            // 刷新文件树
            await loadFileTree();
        } else {
            const result = await response.json();
            console.error('重置失败:', result);
            throw new Error(result.detail || '重置失败');
        }
    } catch (error) {
        console.error('重置Src目录失败:', error);
        showMessage('重置Src目录失败: ' + error.message, 'error');
    }
}