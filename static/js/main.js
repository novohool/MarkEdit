// 全局变量
let currentFilePath = null;
let currentFileType = null;
let currentFileEncoding = null;
let currentFileArea = null; // 'src' 或 'build'
let codeMirrorEditor = null; // CodeMirror 编辑器实例

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
// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化编辑器状态
    initializeEditor();
    
    // 初始化CodeMirror编辑器
    initializeCodeMirror();
    
    // 加载文件树
    loadFileTree();
    
    // 绑定保存按钮事件
    document.getElementById('save-btn').addEventListener('click', saveFile);
    
    // 绑定抽屉菜单事件
    document.getElementById('admin-menu-btn').addEventListener('click', toggleAdminDrawer);
    document.getElementById('close-drawer-btn').addEventListener('click', closeAdminDrawer);
    document.getElementById('drawer-overlay').addEventListener('click', closeAdminDrawer);
    
    // 绑定删除文件按钮事件
    document.getElementById('delete-btn').addEventListener('click', deleteFile);
    
    // 绑定预览按钮事件
    document.getElementById('preview-btn').addEventListener('click', togglePreview);
    
    // 绑定LLM按钮事件
    document.getElementById('llm-btn').addEventListener('click', showLLMDialog);
    
    // 绑定图书生成按钮事件
    document.getElementById('build-all-btn').addEventListener('click', function() {
        buildBook('build');
    });
    
    document.getElementById('build-epub-btn').addEventListener('click', function() {
        buildBook('build:epub');
    });
    
    document.getElementById('build-pdf-btn').addEventListener('click', function() {
        buildBook('build:pdf');
    });
});

// 加载文件树
async function loadFileTree() {
    try {
        const response = await fetch('/api/files');
        const fileData = await response.json();
        
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
        document.getElementById('refresh-btn').addEventListener('click', loadFileTree);
        
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
            
            fileItem.addEventListener('click', function(e) {
                if (e.target.classList.contains('tree-toggle')) {
                    e.stopPropagation();
                    const toggle = this.querySelector('.tree-toggle');
                    if (childrenContainer.style.display === 'none') {
                        childrenContainer.style.display = 'block';
                        toggle.textContent = '▼';
                    } else {
                        childrenContainer.style.display = 'none';
                        toggle.textContent = '▶';
                    }
                } else {
                    // 展开/折叠目录
                    const toggle = this.querySelector('.tree-toggle');
                    if (childrenContainer.style.display === 'none') {
                        childrenContainer.style.display = 'block';
                        toggle.textContent = '▼';
                    } else {
                        childrenContainer.style.display = 'none';
                        toggle.textContent = '▶';
                    }
                }
            });
            
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
            
            parentElement.appendChild(fileItem);
        }
    });
}

// 加载文件内容
async function loadFile(filePath, area) {
    try {
        currentFilePath = filePath;
        currentFileArea = area;
        document.getElementById('current-file').textContent = `${area}/${filePath}`;
        
        // 获取文件扩展名
        const extension = filePath.substring(filePath.lastIndexOf('.')).toLowerCase();
        const previewableExtensions = ['.epub', '.html', '.pdf', '.svg'];
        const isPreviewable = previewableExtensions.includes(extension);
        
        // 对于可预览的二进制文件，直接在iframe中显示
        if (area === 'build' && isPreviewable) {
            // 隐藏所有视图
            document.getElementById('editor').style.display = 'none';
            document.getElementById('image-viewer').style.display = 'none';
            document.getElementById('binary-viewer').style.display = 'none';
            document.getElementById('codemirror-editor').style.display = 'none';
            
            // 显示预览容器
            const previewContainer = document.getElementById('preview-container');
            const fileUrl = `/api/file/${area}/${filePath}`;
            
            if (extension === '.pdf') {
                // PDF文件通过iframe预览
                previewContainer.innerHTML = `
                    <div class="file-preview">
                        <h3>${filePath}</h3>
                        <iframe src="${fileUrl}" style="width:100%; height:80vh; border:none;"></iframe>
                    </div>
                `;
                previewContainer.style.display = 'block';
                currentFileType = 'preview';
            } else if (extension === '.epub') {
                // EPUB文件通过iframe和EPUB.js预览
                // 添加raw=true参数以确保后端直接返回文件内容而不是JSON
                previewContainer.innerHTML = `
                    <div class="file-preview">
                        <h3>${filePath}</h3>
                        <iframe src="/epub-viewer.html?file=${encodeURIComponent(fileUrl + '?raw=true')}" style="width:100%; height:80vh; border:none;"></iframe>
                    </div>
                `;
                previewContainer.style.display = 'block';
                currentFileType = 'preview';
            } else if (extension === '.html') {
                // HTML文件通过iframe预览以隔离样式
                previewContainer.innerHTML = `
                    <div class="file-preview">
                        <h3>${filePath}</h3>
                        <iframe src="${fileUrl}?raw=true" style="width:100%; height:80vh; border:none;"></iframe>
                    </div>
                `;
                previewContainer.style.display = 'block';
                currentFileType = 'preview';
            } else if (extension === '.svg') {
                // SVG文件可以作为图片显示
                // 直接在图片查看器中显示SVG文件
                const imageViewer = document.getElementById('image-viewer');
                imageViewer.innerHTML = `<img src="/api/file/${area}/${filePath}?raw=true" alt="${filePath}">`;
                imageViewer.style.display = 'flex';
                currentFileType = 'image';
            }
            
            // 显示预览按钮
            document.getElementById('preview-btn').style.display = 'inline-block';
            document.getElementById('preview-btn').textContent = '编辑';
        } else {
            // 对于其他文件，使用原来的逻辑
            const response = await fetch(`/api/file/${area}/${filePath}`);
            
            // 检查响应的内容类型
            const contentType = response.headers.get('content-type');
            
            // 如果是JSON响应（文本文件、图片等）
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                
                // 隐藏所有视图
                document.getElementById('editor').style.display = 'none';
                document.getElementById('image-viewer').style.display = 'none';
                document.getElementById('binary-viewer').style.display = 'none';
                document.getElementById('preview-container').style.display = 'none';
                
                if (data.type === 'text') {
                    // 显示文本编辑器
                    const editor = document.getElementById('editor');
                    const cmEditorContainer = document.getElementById('codemirror-editor');
                    
                    // 隐藏textarea编辑器
                    editor.style.display = 'none';
                    
                    // 显示CodeMirror编辑器
                    cmEditorContainer.style.display = 'block';
                    
                    // 设置CodeMirror编辑器内容
                    if (codeMirrorEditor) {
                        codeMirrorEditor.setValue(data.content || '');
                        
                        // 根据文件扩展名设置语法高亮模式
                        const extension = filePath.substring(filePath.lastIndexOf('.')).toLowerCase();
                        const modeMap = {
                            '.js': 'javascript',
                            '.css': 'css',
                            '.html': 'htmlmixed',
                            '.xml': 'xml',
                            '.json': { name: 'javascript', json: true },
                            '.yaml': 'yaml',
                            '.yml': 'yaml',
                            '.md': 'markdown',
                            '.markdown': 'markdown',
                            '': 'text/plain'  // 无后缀文件
                        };
                        
                        const mode = modeMap[extension] || 'text/plain';
                        codeMirrorEditor.setOption('mode', mode);
                    }
                    
                    currentFileType = 'text';
                    currentFileEncoding = data.encoding || 'utf-8';
                    
                    // 如果是Markdown文件，显示预览按钮
                    if (filePath.endsWith('.md') || filePath.endsWith('.markdown')) {
                        document.getElementById('preview-btn').style.display = 'inline-block';
                    } else {
                        document.getElementById('preview-btn').style.display = 'none';
                    }
                    
                    // 对于所有文本文件，显示LLM按钮（仅src目录）
                    if (area === 'src') {
                        document.getElementById('llm-btn').style.display = 'inline-block';
                    } else {
                        document.getElementById('llm-btn').style.display = 'none';
                    }
                } else if (data.type === 'image') {
                    // 显示图片查看器
                    const imageViewer = document.getElementById('image-viewer');
                    imageViewer.innerHTML = `<img src="data:${data.mime};base64,${data.content}" alt="${filePath}">`;
                    imageViewer.style.display = 'flex';
                    currentFileType = 'image';
                    
                    // 隐藏预览按钮
                    document.getElementById('preview-btn').style.display = 'none';
                } else {
                    // 显示二进制文件提示
                    document.getElementById('binary-viewer').style.display = 'flex';
                    currentFileType = 'binary';
                    
                    // 隐藏预览按钮
                    document.getElementById('preview-btn').style.display = 'none';
                }
            } else {
                // 对于二进制文件（如PDF、EPUB等），直接显示在预览容器中
                // 隐藏所有视图
                document.getElementById('editor').style.display = 'none';
                document.getElementById('image-viewer').style.display = 'none';
                document.getElementById('binary-viewer').style.display = 'none';
                document.getElementById('codemirror-editor').style.display = 'none';
                
                // 显示预览容器
                const previewContainer = document.getElementById('preview-container');
                const fileUrl = `/api/file/${area}/${filePath}`;
                
                if (extension === '.pdf') {
                    // PDF文件通过iframe预览
                    previewContainer.innerHTML = `
                        <div class="file-preview">
                            <h3>${filePath}</h3>
                            <iframe src="${fileUrl}" style="width:100%; height:80vh; border:none;"></iframe>
                        </div>
                    `;
                    previewContainer.style.display = 'block';
                    currentFileType = 'preview';
                } else {
                    // 其他二进制文件显示为下载链接
                    previewContainer.innerHTML = `
                        <div class="file-preview">
                            <h3>${filePath}</h3>
                            <p>这是一个二进制文件，您可以<a href="${fileUrl}" target="_blank">点击这里下载</a></p>
                        </div>
                    `;
                    previewContainer.style.display = 'block';
                    currentFileType = 'binary';
                }
                
                // 显示预览按钮
                document.getElementById('preview-btn').style.display = 'inline-block';
                document.getElementById('preview-btn').textContent = '编辑';
            }
        }
        
        // 启用删除按钮（仅src目录）
        document.getElementById('delete-btn').disabled = (area !== 'src');
    } catch (error) {
        console.error('加载文件失败:', error);
        showMessage('加载文件失败: ' + error.message, 'error');
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

// 切换预览模式
async function togglePreview() {
    const editor = document.getElementById('editor');
    const cmEditorContainer = document.getElementById('codemirror-editor');
    const previewContainer = document.getElementById('preview-container');
    const imageViewer = document.getElementById('image-viewer');
    const binaryViewer = document.getElementById('binary-viewer');
    
    if (previewContainer.style.display === 'none' || previewContainer.style.display === '' ||
        imageViewer.style.display === 'flex' || binaryViewer.style.display === 'flex') {
        // 显示预览
        if (currentFileArea === 'src' && (currentFilePath.endsWith('.md') || currentFilePath.endsWith('.markdown'))) {
            // Markdown文件预览
            // 从CodeMirror编辑器获取内容
            const content = codeMirrorEditor ? codeMirrorEditor.getValue() : editor.value;
            // 使用marked.js库解析Markdown
            previewContainer.innerHTML = marked.parse(content);
            
            // 添加代码高亮
            if (typeof Prism !== 'undefined') {
                Prism.highlightAllUnder(previewContainer);
            }
            
            // 显示预览容器
            previewContainer.style.display = 'block';
            editor.style.display = 'none';
            cmEditorContainer.style.display = 'none';
            imageViewer.style.display = 'none';
            binaryViewer.style.display = 'none';
            document.getElementById('preview-btn').textContent = '编辑';
        } else if (currentFileArea === 'build') {
            // Build目录下的文件预览
            await previewBuildFile(currentFilePath);
            document.getElementById('preview-btn').textContent = '编辑';
        }
    } else {
        // 显示编辑器或文件内容
        if (currentFileArea === 'src' && (currentFilePath.endsWith('.md') || currentFilePath.endsWith('.markdown'))) {
            // Markdown文件返回编辑模式
            previewContainer.style.display = 'none';
            editor.style.display = 'none';
            cmEditorContainer.style.display = 'block';
            document.getElementById('preview-btn').textContent = '预览';
        } else if (currentFileArea === 'build') {
            // Build目录下的文件，重新加载文件内容
            await loadFile(currentFilePath, currentFileArea);
            document.getElementById('preview-btn').textContent = '预览';
        } else if (currentFileType === 'preview') {
            // 对于预览模式的文件，重新加载文件内容
            await loadFile(currentFilePath, currentFileArea);
            document.getElementById('preview-btn').textContent = '预览';
        }
    }
}

// 显示创建文件对话框
function showCreateFileDialog() {
    const fileName = prompt('请输入文件名（包括扩展名）:');
    if (fileName) {
        createFile(fileName);
    }
}

// 创建文件
async function createFile(fileName) {
    try {
        // 简单验证文件名
        if (!fileName || fileName.trim() === '') {
            showMessage('文件名不能为空', 'warning');
            return;
        }
        
        // 构造文件路径（在src根目录下）
        const filePath = fileName;
        
        const response = await fetch(`/api/create-file/${filePath}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'text/plain; charset=utf-8'
            },
            body: ''
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('文件创建成功', 'success');
            // 刷新文件树
            loadFileTree();
        } else {
            throw new Error(result.detail || '创建失败');
        }
    } catch (error) {
        console.error('创建文件失败:', error);
        showMessage('创建文件失败: ' + error.message, 'error');
    }
}

// 删除文件（通过删除按钮）
async function deleteFile() {
    if (!currentFilePath || currentFileArea !== 'src') {
        showMessage('请选择一个src目录下的文件进行删除', 'warning');
        return;
    }
    
    // 确认删除
    if (!confirm(`确定要删除文件 "${currentFilePath}" 吗？`)) {
        return;
    }
    
    // 调用删除文件函数
    await deleteFileAtPath(currentFilePath);
}

// 删除文件
async function deleteFileAtPath(filePath) {
    try {
        const response = await fetch(`/api/file/src/${filePath}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('文件删除成功', 'success');
            // 如果删除的是当前文件，清空当前文件
            if (currentFilePath === filePath) {
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
                document.getElementById('codemirror-editor').style.display = 'none';
                
                // 禁用删除按钮
                document.getElementById('delete-btn').disabled = true;
            }
            
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
    contextMenu.style.zIndex = '1000';
    
    // 添加菜单项
    if (type === 'directory' && area === 'src') {
        // 目录菜单项（仅src目录）
        contextMenu.innerHTML = `
            <div class="context-menu-item" data-action="create-file">新建文件</div>
            <div class="context-menu-item" data-action="create-directory">新建目录</div>
        `;
    } else if (type === 'file' && area === 'src') {
        // 文件菜单项（仅src目录）
        contextMenu.innerHTML = `
            <div class="context-menu-item" data-action="delete">删除</div>
        `;
    } else if (type === 'file' && area === 'build') {
        // 文件菜单项（build目录）
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
        // 不支持的操作
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
            previewBuildFile(path);
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

// 创建文件
async function createFile(directoryPath, fileName) {
    try {
        // 简单验证文件名
        if (!fileName || fileName.trim() === '') {
            showMessage('文件名不能为空', 'warning');
            return;
        }
        
        // 构造文件路径
        const filePath = directoryPath ? `${directoryPath}/${fileName}` : fileName;
        
        const response = await fetch(`/api/create-file/${filePath}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'text/plain; charset=utf-8'
            },
            body: ''
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('文件创建成功', 'success');
            // 刷新文件树
            loadFileTree();
        } else {
            throw new Error(result.detail || '创建失败');
        }
    } catch (error) {
        console.error('创建文件失败:', error);
        showMessage('创建文件失败: ' + error.message, 'error');
    }
}

// 创建目录
async function createDirectory(directoryPath, dirName) {
    try {
        // 简单验证目录名
        if (!dirName || dirName.trim() === '') {
            showMessage('目录名不能为空', 'warning');
            return;
        }
        
        // 构造目录路径
        const dirPath = directoryPath ? `${directoryPath}/${dirName}` : dirName;
        
        const response = await fetch(`/api/create-directory/${dirPath}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('目录创建成功', 'success');
            // 刷新文件树
            loadFileTree();
        } else {
            throw new Error(result.detail || '创建失败');
        }
    } catch (error) {
        console.error('创建目录失败:', error);
        showMessage('创建目录失败: ' + error.message, 'error');
    }
}

// 删除文件
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

// 预览Build目录下的文件
async function previewBuildFile(filePath) {
    try {
        const extension = filePath.substring(filePath.lastIndexOf('.')).toLowerCase();
        
        // 统一使用iframe预览所有支持的文件类型
        const fileUrl = `/api/file/build/${filePath}`;
        const previewContainer = document.getElementById('preview-container');
        
        // 根据文件扩展名处理预览
        if (extension === '.html') {
            // HTML文件通过iframe预览以隔离样式
            previewContainer.innerHTML = `
                <div class="file-preview">
                    <h3>${filePath}</h3>
                    <iframe src="${fileUrl}?raw=true" style="width:100%; height:80vh; border:none;"></iframe>
                </div>
            `;
            previewContainer.style.display = 'block';
            
            // 隐藏其他视图
            document.getElementById('editor').style.display = 'none';
            document.getElementById('image-viewer').style.display = 'none';
            document.getElementById('binary-viewer').style.display = 'none';
            document.getElementById('codemirror-editor').style.display = 'none';
            
            // 更新当前文件信息
            currentFilePath = filePath;
            currentFileArea = 'build';
            currentFileType = 'preview';
            document.getElementById('current-file').textContent = `build/${filePath}`;
        } else if (extension === '.svg') {
            // SVG文件可以作为图片显示
            const response = await fetch(`/api/file/build/${filePath}`);
            const data = await response.json();
            
            if (data.type === 'image') {
                // 显示在图片查看器中
                const imageViewer = document.getElementById('image-viewer');
                imageViewer.innerHTML = `<img src="data:${data.mime};base64,${data.content}" alt="${filePath}">`;
                imageViewer.style.display = 'flex';
                
                // 隐藏其他视图
                document.getElementById('editor').style.display = 'none';
                document.getElementById('preview-container').style.display = 'none';
                document.getElementById('binary-viewer').style.display = 'none';
                document.getElementById('codemirror-editor').style.display = 'none';
                
                // 更新当前文件信息
                currentFilePath = filePath;
                currentFileArea = 'build';
                currentFileType = 'image';
                document.getElementById('current-file').textContent = `build/${filePath}`;
            }
        } else if (extension === '.pdf') {
           // PDF文件通过iframe预览
           previewContainer.innerHTML = `
               <div class="file-preview">
                   <h3>${filePath}</h3>
                   <iframe src="${fileUrl}" style="width:100%; height:80vh; border:none;"></iframe>
               </div>
           `;
           previewContainer.style.display = 'block';
           
           // 隐藏其他视图
           document.getElementById('editor').style.display = 'none';
           document.getElementById('image-viewer').style.display = 'none';
           document.getElementById('binary-viewer').style.display = 'none';
           document.getElementById('codemirror-editor').style.display = 'none';
           
           // 更新当前文件信息
           currentFilePath = filePath;
           currentFileArea = 'build';
           currentFileType = 'preview';
           document.getElementById('current-file').textContent = `build/${filePath}`;
       } else if (extension === '.epub') {
          // EPUB文件通过iframe和EPUB.js预览
          // 添加raw=true参数以确保后端直接返回文件内容而不是JSON
          previewContainer.innerHTML = `
              <div class="file-preview">
                  <h3>${filePath}</h3>
                  <iframe src="/epub-viewer.html?file=${encodeURIComponent(fileUrl + '?raw=true')}" style="width:100%; height:80vh; border:none;"></iframe>
              </div>
          `;
          previewContainer.style.display = 'block';
          
          // 隐藏其他视图
          document.getElementById('editor').style.display = 'none';
          document.getElementById('image-viewer').style.display = 'none';
          document.getElementById('binary-viewer').style.display = 'none';
          document.getElementById('codemirror-editor').style.display = 'none';
          
          // 更新当前文件信息
          currentFilePath = filePath;
          currentFileArea = 'build';
          currentFileType = 'preview';
          document.getElementById('current-file').textContent = `build/${filePath}`;
      }
    } catch (error) {
        console.error('预览文件失败:', error);
        showMessage('预览文件失败: ' + error.message, 'error');
    }
}

// 显示消息
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

// 页面加载完成后配置marked.js
document.addEventListener('DOMContentLoaded', function() {
    // 配置marked.js
    marked.setOptions({
        breaks: true, // 转换段落中的\n为<br>
        smartypants: true, // 启用智能标点符号
        smartLists: true // 启用智能列表
    });
});

// 抽屉菜单控制函数
function toggleAdminDrawer() {
    const drawer = document.getElementById('admin-drawer');
    const overlay = document.getElementById('drawer-overlay');
    
    drawer.classList.toggle('open');
    overlay.classList.toggle('open');
}

function closeAdminDrawer() {
    const drawer = document.getElementById('admin-drawer');
    const overlay = document.getElementById('drawer-overlay');
    
    drawer.classList.remove('open');
    overlay.classList.remove('open');
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
                <label for="llm-prompt">请输入处理指令：</label>
                <textarea id="llm-prompt" placeholder="例如：请优化这段代码的结构..."></textarea>
                <div class="llm-dialog-buttons">
                    <button id="llm-process-btn" class="btn-primary">处理</button>
                    <button id="llm-cancel-btn" class="btn-secondary">取消</button>
                </div>
            </div>
        </div>
    `;
    
    // 添加到页面
    document.body.appendChild(dialog);
    
    // 绑定事件
    dialog.querySelector('.llm-dialog-close').addEventListener('click', () => {
        document.body.removeChild(dialog);
    });
    
    dialog.querySelector('#llm-cancel-btn').addEventListener('click', () => {
        document.body.removeChild(dialog);
    });
    
    dialog.querySelector('#llm-process-btn').addEventListener('click', processWithLLM);
    
    // 点击遮罩层关闭对话框
    dialog.querySelector('.llm-dialog-overlay').addEventListener('click', () => {
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

// 为编辑器中的代码添加高亮
function highlightCodeInEditor() {
    const editor = document.getElementById('editor');
    if (!editor || editor.style.display === 'none') return;
    
    const filePath = document.getElementById('current-file').textContent;
    if (filePath === '未选择文件') return;
    
    // 获取文件扩展名
    const extension = filePath.substring(filePath.lastIndexOf('.')).toLowerCase();
    
    // 定义语言映射
    const languageMap = {
        '.css': 'css',
        '.js': 'javascript',
        '.html': 'html',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml'
    };
    
    const language = languageMap[extension];
    if (!language) return;
    
    // 创建一个临时的pre/code元素用于高亮
    const tempPre = document.createElement('pre');
    const tempCode = document.createElement('code');
    tempCode.className = `language-${language}`;
    tempCode.textContent = editor.value;
    tempPre.appendChild(tempCode);
    
    // 应用Prism高亮
    if (typeof Prism !== 'undefined') {
        Prism.highlightElement(tempCode);
    }
    
    // 注意：由于textarea不能直接显示HTML格式，我们不会将高亮结果应用到编辑器中
    // 但在预览模式下代码会正确高亮
}