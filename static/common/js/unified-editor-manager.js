/**
 * MarkEdit 统一编辑器管理器
 * 
 * 这个模块整合了所有编辑相关的功能，包括：
 * - 编辑器初始化和状态管理
 * - 文件加载和保存
 * - 编辑按钮响应处理
 * - 预览功能管理
 * - 事件绑定统一管理
 */

class UnifiedEditorManager {
    constructor() {
        // 编辑器状态
        this.currentFilePath = null;
        this.currentFileArea = null;
        this.currentFileType = null;
        this.currentFileEncoding = 'utf-8';
        this.codeMirrorEditor = null;
        
        // 初始化状态
        this.isInitialized = false;
        this.eventListenersSet = new Set();
        
        // 配置
        this.config = {
            autoSave: false,
            autoSaveInterval: 30000, // 30秒
            previewableExtensions: ['.epub', '.html', '.pdf', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.ico'],
            textExtensions: ['.md', '.markdown', '.txt', '.js', '.css', '.html', '.xml', '.json', '.yaml', '.yml']
        };
    }
    
    /**
     * 初始化编辑器管理器
     */
    initialize() {
        if (this.isInitialized) {
            console.warn('UnifiedEditorManager already initialized');
            return;
        }
        
        console.log('Initializing UnifiedEditorManager...');
        
        // 初始化CodeMirror编辑器
        this.initializeCodeMirror();
        
        // 绑定所有事件监听器
        this.bindAllEventListeners();
        
        // 初始化编辑器状态
        this.initializeEditorState();
        
        // 设置初始化标志
        this.isInitialized = true;
        
        console.log('UnifiedEditorManager initialized successfully');
    }
    
    /**
     * 初始化CodeMirror编辑器
     */
    initializeCodeMirror() {
        const editorElement = document.getElementById('codemirror-editor');
        if (!editorElement) {
            console.error('CodeMirror editor element not found');
            return;
        }
        
        if (this.codeMirrorEditor) {
            console.warn('CodeMirror already initialized');
            return;
        }
        
        // 创建CodeMirror实例
        this.codeMirrorEditor = CodeMirror(editorElement, {
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
        this.codeMirrorEditor.on("keydown", (cm, e) => {
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                this.saveFile();
            }
        });
        
        // 将编辑器实例设置为全局变量（兼容旧代码）
        window.codeMirrorEditor = this.codeMirrorEditor;
        
        console.log('CodeMirror editor initialized');
    }
    
    /**
     * 绑定所有事件监听器，统一管理避免重复绑定
     */
    bindAllEventListeners() {
        // 防止重复绑定
        if (document.body.dataset.unifiedEditorListenersSet) {
            console.log('Event listeners already bound by UnifiedEditorManager');
            return;
        }
        
        // 绑定保存按钮
        this.bindSaveButton();
        
        // 绑定预览按钮
        this.bindPreviewButton();
        
        // 绑定删除按钮
        this.bindDeleteButton();
        
        // 绑定LLM按钮
        this.bindLLMButton();
        
        // 绑定文件树点击事件
        this.bindFileTreeEvents();
        
        // 设置标记避免重复绑定
        document.body.dataset.unifiedEditorListenersSet = 'true';
        
        console.log('All event listeners bound by UnifiedEditorManager');
    }
    
    /**
     * 绑定保存按钮事件
     */
    bindSaveButton() {
        const saveBtn = document.getElementById('save-btn');
        if (saveBtn && !this.eventListenersSet.has('save-btn')) {
            saveBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.saveFile();
            });
            this.eventListenersSet.add('save-btn');
            console.log('Save button event bound');
        }
    }
    
    /**
     * 绑定预览按钮事件
     */
    bindPreviewButton() {
        const previewBtn = document.getElementById('preview-btn');
        if (previewBtn && !this.eventListenersSet.has('preview-btn')) {
            previewBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.togglePreview();
            });
            this.eventListenersSet.add('preview-btn');
            console.log('Preview button event bound');
        }
    }
    
    /**
     * 绑定删除按钮事件
     */
    bindDeleteButton() {
        const deleteBtn = document.getElementById('delete-btn');
        if (deleteBtn && !this.eventListenersSet.has('delete-btn')) {
            deleteBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.deleteFile();
            });
            this.eventListenersSet.add('delete-btn');
            console.log('Delete button event bound');
        }
    }
    
    /**
     * 绑定LLM按钮事件
     */
    bindLLMButton() {
        const llmBtn = document.getElementById('llm-btn');
        if (llmBtn && !this.eventListenersSet.has('llm-btn')) {
            llmBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.showLLMDialog();
            });
            this.eventListenersSet.add('llm-btn');
            console.log('LLM button event bound');
        }
    }
    
    /**
     * 绑定文件树事件
     */
    bindFileTreeEvents() {
        const fileTree = document.getElementById('file-tree');
        if (fileTree && !this.eventListenersSet.has('file-tree')) {
            // 使用事件委托处理文件点击
            fileTree.addEventListener('click', (e) => {
                const fileLink = e.target.closest('[data-file-path]');
                if (fileLink) {
                    e.preventDefault();
                    const filePath = fileLink.getAttribute('data-file-path');
                    const area = fileLink.getAttribute('data-area') || 'src';
                    this.loadFile(filePath, area);
                }
            });
            this.eventListenersSet.add('file-tree');
            console.log('File tree events bound');
        }
    }
    
    /**
     * 初始化编辑器状态
     */
    initializeEditorState() {
        // 隐藏所有视图
        this.hideAllViews();
        
        // 重置按钮状态
        this.resetButtonStates();
        
        // 更新文件信息显示
        this.updateCurrentFileInfo('未选择文件');
        
        console.log('Editor state initialized');
    }
    
    /**
     * 加载文件
     */
    async loadFile(filePath, area) {
        try {
            console.log(`Loading file: ${area}/${filePath}`);
            
            this.currentFilePath = filePath;
            this.currentFileArea = area;
            this.updateCurrentFileInfo(`${area}/${filePath}`);
            
            // 获取文件扩展名
            const extension = filePath.substring(filePath.lastIndexOf('.')).toLowerCase();
            const isPreviewable = this.config.previewableExtensions.includes(extension);
            
            // 对于可预览的二进制文件，直接在iframe中显示
            if (area === 'build' && isPreviewable) {
                await this.loadPreviewableFile(filePath, area, extension);
            } else {
                // 对于其他文件，使用原来的逻辑
                await this.loadRegularFile(filePath, area);
            }
            
            // 启用删除按钮（仅src目录）
            const deleteBtn = document.getElementById('delete-btn');
            if (deleteBtn) {
                deleteBtn.disabled = (area !== 'src');
            }
            
        } catch (error) {
            console.error('加载文件失败:', error);
            this.window.ComponentManager.getComponent('message').error('加载文件失败: ' + error.message);
        }
    }
    
    /**
     * 加载可预览文件
     */
    async loadPreviewableFile(filePath, area, extension) {
        // 隐藏所有视图
        this.hideAllViews();
        
        // 显示预览容器
        const previewContainer = document.getElementById('preview-container');
        const encodedFilePath = encodeURIComponent(filePath);
        const fileUrl = `/api/file/${area}/${encodedFilePath}`;
        
        if (extension === '.pdf') {
            previewContainer.innerHTML = `
                <div class="file-preview">
                    <h3>${filePath}</h3>
                    <iframe src="${fileUrl}" style="width:100%; height:80vh; border:none;"></iframe>
                </div>
            `;
            previewContainer.style.display = 'block';
            this.currentFileType = 'preview';
        } else if (extension === '.epub') {
            previewContainer.innerHTML = `
                <div class="file-preview">
                    <h3>${filePath}</h3>
                    <iframe src="/epub-viewer.html?url=${encodeURIComponent(fileUrl + '?raw=true')}" style="width:100%; height:80vh; border:none;"></iframe>
                </div>
            `;
            previewContainer.style.display = 'block';
            this.currentFileType = 'preview';
        } else if (extension === '.html') {
            previewContainer.innerHTML = `
                <div class="file-preview">
                    <h3>${filePath}</h3>
                    <iframe src="${fileUrl}?raw=true" style="width:100%; height:80vh; border:none;"></iframe>
                </div>
            `;
            previewContainer.style.display = 'block';
            this.currentFileType = 'preview';
        } else if (['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.ico', '.svg'].includes(extension)) {
            const response = await fetch(`/api/file/${area}/${encodedFilePath}`);
            const data = await response.json();
            
            if (data.type === 'image') {
                const imageViewer = document.getElementById('image-viewer');
                imageViewer.innerHTML = `<img src="data:${data.mime};base64,${data.content}" alt="${filePath}">`;
                imageViewer.style.display = 'flex';
                this.currentFileType = 'image';
            }
        }
        
        // 显示预览按钮并设置初始状态为"预览"
        const previewBtn = document.getElementById('preview-btn');
        if (previewBtn) {
            previewBtn.style.display = 'inline-block';
            previewBtn.textContent = '预览';
        }
    }
    
    /**
     * 加载常规文件
     */
    async loadRegularFile(filePath, area) {
        const response = await fetch(`/api/file/${area}/${filePath}`);
        
        // 检查响应的内容类型
        const contentType = response.headers.get('content-type');
        
        // 如果是JSON响应（文本文件、图片等）
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            
            // 隐藏所有视图
            this.hideAllViews();
            
            if (data.type === 'text') {
                await this.loadTextFile(data, filePath, area);
            } else if (data.type === 'image') {
                this.loadImageFile(data, filePath);
            } else {
                this.loadBinaryFile();
            }
        }
    }
    
    /**
     * 加载文本文件
     */
    async loadTextFile(data, filePath, area) {
        const editor = document.getElementById('editor');
        const cmEditorContainer = document.getElementById('codemirror-editor');
        
        // 隐藏textarea编辑器
        if (editor) {
            editor.style.display = 'none';
        }
        
        // 显示CodeMirror编辑器
        if (cmEditorContainer) {
            cmEditorContainer.style.display = 'block';
        }
        
        // 设置CodeMirror编辑器内容
        if (this.codeMirrorEditor) {
            this.codeMirrorEditor.setValue(data.content || '');
            
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
            this.codeMirrorEditor.setOption('mode', mode);
        }
        
        this.currentFileType = 'text';
        this.currentFileEncoding = data.encoding || 'utf-8';
        
        // 如果是Markdown文件，显示预览按钮并设置初始状态为"预览"
        const previewBtn = document.getElementById('preview-btn');
        if (filePath.endsWith('.md') || filePath.endsWith('.markdown')) {
            if (previewBtn) {
                previewBtn.style.display = 'inline-block';
                previewBtn.textContent = '预览';
            }
        } else {
            if (previewBtn) {
                previewBtn.style.display = 'none';
            }
        }
        
        // 对于所有文本文件，显示LLM按钮（仅src目录）
        const llmBtn = document.getElementById('llm-btn');
        if (area === 'src' && llmBtn) {
            llmBtn.style.display = 'inline-block';
        } else if (llmBtn) {
            llmBtn.style.display = 'none';
        }
    }
    
    /**
     * 加载图片文件
     */
    loadImageFile(data, filePath) {
        const imageViewer = document.getElementById('image-viewer');
        if (imageViewer) {
            imageViewer.innerHTML = `<img src="data:${data.mime};base64,${data.content}" alt="${filePath}">`;
            imageViewer.style.display = 'flex';
        }
        this.currentFileType = 'image';
        
        // 隐藏预览按钮
        const previewBtn = document.getElementById('preview-btn');
        if (previewBtn) {
            previewBtn.style.display = 'none';
        }
    }
    
    /**
     * 加载二进制文件
     */
    loadBinaryFile() {
        const binaryViewer = document.getElementById('binary-viewer');
        if (binaryViewer) {
            binaryViewer.style.display = 'flex';
        }
        this.currentFileType = 'binary';
        
        // 隐藏预览按钮
        const previewBtn = document.getElementById('preview-btn');
        if (previewBtn) {
            previewBtn.style.display = 'none';
            previewBtn.textContent = '预览';
        }
    }
    
    /**
     * 保存文件
     */
    async saveFile() {
        if (!this.currentFilePath || this.currentFileArea !== 'src') {
            this.window.ComponentManager.getComponent('message').warning('没有可保存的文件');
            return;
        }
        
        try {
            // 从CodeMirror编辑器获取内容
            const content = this.codeMirrorEditor ? 
                this.codeMirrorEditor.getValue() : 
                document.getElementById('editor')?.value || '';
            
            const response = await fetch(`/api/file/src/${this.currentFilePath}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'text/plain; charset=utf-8'
                },
                body: content
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.window.ComponentManager.getComponent('message').success('文件保存成功');
            } else {
                throw new Error(result.detail || '保存失败');
            }
        } catch (error) {
            console.error('保存文件失败:', error);
            this.window.ComponentManager.getComponent('message').error('保存文件失败: ' + error.message);
        }
    }
    
    /**
     * 切换预览模式
     */
    async togglePreview() {
        const previewContainer = document.getElementById('preview-container');
        const imageViewer = document.getElementById('image-viewer');
        const binaryViewer = document.getElementById('binary-viewer');
        
        // 检查当前是否在预览模式
        const isInPreviewMode = previewContainer?.style.display === 'block' ||
                               imageViewer?.style.display === 'flex' ||
                               binaryViewer?.style.display === 'flex';
        
        if (!isInPreviewMode) {
            // 显示预览
            if (this.currentFileArea === 'src' && 
                (this.currentFilePath?.endsWith('.md') || this.currentFilePath?.endsWith('.markdown'))) {
                await this.showMarkdownPreview();
            } else if (this.currentFileArea === 'build') {
                // Build目录下的文件预览
                await this.previewBuildFile(this.currentFilePath);
                const previewBtn = document.getElementById('preview-btn');
                if (previewBtn) {
                    previewBtn.textContent = '编辑';
                }
            }
        } else {
            // 显示编辑器或文件内容
            await this.hidePreview();
        }
    }
    
    /**
     * 显示Markdown预览
     */
    async showMarkdownPreview() {
        const editor = document.getElementById('editor');
        const cmEditorContainer = document.getElementById('codemirror-editor');
        const previewContainer = document.getElementById('preview-container');
        const imageViewer = document.getElementById('image-viewer');
        const binaryViewer = document.getElementById('binary-viewer');
        
        if (!previewContainer) return;
        
        // 从CodeMirror编辑器获取内容
        const content = this.codeMirrorEditor ? this.codeMirrorEditor.getValue() : (editor?.value || '');
        console.log('统一编辑器管理器 - 获取到的内容长度:', content.length);
        console.log('统一编辑器管理器 - 内容预览:', content.substring(0, 100));
        console.log('统一编辑器管理器 - codeMirrorEditor存在:', !!this.codeMirrorEditor);
        
        // 如果内容为空，添加一个测试内容
        if (!content || content.trim() === '') {
            console.warn('统一编辑器管理器 - 编辑器内容为空，使用测试内容');
            const testContent = '# 测试预览\n\n这是一个测试预览内容。\n\n- 项目 1\n- 项目 2\n- 项目 3\n\n**粗体文本** 和 *斜体文本*';
            
            // 使用marked.js库解析Markdown
            if (typeof marked !== 'undefined') {
                previewContainer.innerHTML = marked.parse(testContent);
                console.log('统一编辑器管理器 - 使用测试内容和marked.js解析');
            } else {
                previewContainer.innerHTML = `<pre>${testContent}</pre>`;
                console.log('统一编辑器管理器 - marked.js未加载，使用纯文本显示');
            }
        } else {
            // 使用实际内容
            if (typeof marked !== 'undefined') {
                previewContainer.innerHTML = marked.parse(content);
                console.log('统一编辑器管理器 - 使用实际内容和marked.js解析');
            } else {
                previewContainer.innerHTML = `<pre>${content}</pre>`;
                console.log('统一编辑器管理器 - marked.js未加载，使用纯文本显示');
            }
        }
        
        // 处理图片路径
        await this.processImagePaths(previewContainer);
        
        // 添加代码高亮
        if (typeof Prism !== 'undefined') {
            Prism.highlightAllUnder(previewContainer);
        }
        
        // 显示预览容器并强制设置样式
        previewContainer.style.display = 'block';
        previewContainer.style.width = '100%';
        previewContainer.style.height = '100%';
        previewContainer.style.padding = '1rem';
        previewContainer.style.backgroundColor = '#fff';
        previewContainer.style.overflow = 'auto';
        previewContainer.style.position = 'relative';
        previewContainer.style.zIndex = '1';
        
        if (editor) editor.style.display = 'none';
        if (cmEditorContainer) cmEditorContainer.style.display = 'none';
        if (imageViewer) imageViewer.style.display = 'none';
        if (binaryViewer) binaryViewer.style.display = 'none';
        
        const previewBtn = document.getElementById('preview-btn');
        if (previewBtn) {
            previewBtn.textContent = '编辑';
        }
        
        console.log('统一编辑器管理器 - 预览容器已显示，内容长度:', previewContainer.innerHTML.length);
    }
    
    /**
     * 隐藏预览
     */
    async hidePreview() {
        const editor = document.getElementById('editor');
        const cmEditorContainer = document.getElementById('codemirror-editor');
        const previewContainer = document.getElementById('preview-container');
        
        if (this.currentFileArea === 'src' && 
            (this.currentFilePath?.endsWith('.md') || this.currentFilePath?.endsWith('.markdown'))) {
            // Markdown文件返回编辑模式
            if (previewContainer) previewContainer.style.display = 'none';
            if (editor) editor.style.display = 'none';
            if (cmEditorContainer) cmEditorContainer.style.display = 'block';
            
            const previewBtn = document.getElementById('preview-btn');
            if (previewBtn) {
                previewBtn.textContent = '预览';
            }
        } else if (this.currentFileArea === 'build') {
            // Build目录下的文件，重新加载文件内容
            await this.loadFile(this.currentFilePath, this.currentFileArea);
            const previewBtn = document.getElementById('preview-btn');
            if (previewBtn) {
                previewBtn.textContent = '预览';
            }
        } else if (this.currentFileType === 'preview') {
            // 对于预览模式的文件，重新加载文件内容
            await this.loadFile(this.currentFilePath, this.currentFileArea);
            const previewBtn = document.getElementById('preview-btn');
            if (previewBtn) {
                previewBtn.textContent = '预览';
            }
        }
    }
    
    /**
     * 删除文件
     */
    async deleteFile() {
        if (!this.currentFilePath || this.currentFileArea !== 'src') {
            this.window.ComponentManager.getComponent('message').warning('只能删除src目录下的文件');
            return;
        }
        
        if (confirm(`确定要删除文件 "${this.currentFilePath}" 吗？`)) {
            try {
                const response = await fetch(`/api/file/src/${this.currentFilePath}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    this.window.ComponentManager.getComponent('message').success('文件删除成功');
                    
                    // 清空编辑器
                    this.initializeEditorState();
                    
                    // 刷新文件树
                    if (typeof loadFileTree === 'function') {
                        loadFileTree();
                    }
                } else {
                    throw new Error(result.detail || '删除失败');
                }
            } catch (error) {
                console.error('删除文件失败:', error);
                this.window.ComponentManager.getComponent('message').error('删除文件失败: ' + error.message);
            }
        }
    }
    
    /**
     * 显示LLM对话框
     */
    showLLMDialog() {
        // 调用现有的LLM功能
        if (typeof showLLMDialog === 'function') {
            showLLMDialog();
        } else {
            this.window.ComponentManager.getComponent('message').info('LLM功能暂未实现');
        }
    }
    
    /**
     * 隐藏所有视图
     */
    hideAllViews() {
        const elements = [
            'editor', 'image-viewer', 'binary-viewer', 
            'preview-container', 'codemirror-editor'
        ];
        
        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.style.display = 'none';
            }
        });
    }
    
    /**
     * 重置按钮状态
     */
    resetButtonStates() {
        const previewBtn = document.getElementById('preview-btn');
        const deleteBtn = document.getElementById('delete-btn');
        const llmBtn = document.getElementById('llm-btn');
        
        if (previewBtn) {
            previewBtn.style.display = 'none';
            previewBtn.textContent = '预览';
        }
        
        if (deleteBtn) {
            deleteBtn.disabled = true;
        }
        
        if (llmBtn) {
            llmBtn.style.display = 'none';
        }
    }
    
    /**
     * 更新当前文件信息显示
     */
    updateCurrentFileInfo(info) {
        const currentFileElement = document.getElementById('current-file');
        if (currentFileElement) {
            currentFileElement.textContent = info;
        }
    }
    
    /**
     * 处理预览中的图片路径
     */
    async processImagePaths(container) {
        const images = container.querySelectorAll('img');
        
        // 获取当前用户信息
        let currentUsername = null;
        try {
            if (window.userInfo && window.userInfo.username) {
                currentUsername = window.userInfo.username;
            } else if (typeof checkUserInfo === 'function') {
                await checkUserInfo();
                currentUsername = window.userInfo ? window.userInfo.username : null;
            }
        } catch (error) {
            console.warn('获取用户信息失败，使用默认路径处理:', error);
        }
        
        images.forEach(img => {
            const src = img.getAttribute('src');
            if (src && src.startsWith('../illustrations/')) {
                let newSrc;
                if (currentUsername) {
                    const filename = src.replace('../illustrations/', '');
                    newSrc = `/user-illustrations/${currentUsername}/${filename}`;
                } else {
                    // 向后兼容：如果无法获取用户名，使用旧格式
                    newSrc = src.replace('../illustrations/', '/user-illustrations/');
                }
                img.setAttribute('src', newSrc);
            }
        });
    }
    
    /**
     * 预览Build目录文件
     */
    async previewBuildFile(filePath) {
        // 调用现有的预览功能
        if (typeof previewBuildFile === 'function') {
            await previewBuildFile(filePath);
        }
    }
    
    /**
     * 显示消息
     */
    showMessage(message, type = 'info') {
        if (typeof showMessage === 'function') {
            showMessage(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }
}

// 创建全局实例
window.unifiedEditorManager = new UnifiedEditorManager();

// 在DOM加载完成后自动初始化
document.addEventListener('DOMContentLoaded', () => {
    if (window.unifiedEditorManager) {
        window.unifiedEditorManager.initialize();
    }
});

// 兼容性：导出主要函数供现有代码使用
window.loadFile = (filePath, area) => window.unifiedEditorManager?.loadFile(filePath, area);
window.saveFile = () => window.unifiedEditorManager?.saveFile();
window.togglePreview = () => window.unifiedEditorManager?.togglePreview();
window.deleteFile = () => window.unifiedEditorManager?.deleteFile();