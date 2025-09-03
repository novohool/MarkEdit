// MarkEdit 主题无关的共享主要功能函数
// 此模块包含所有主题都需要使用的核心业务逻辑函数
// 编辑器相关功能已迁移到 unified-editor-manager.js

// === 向后兼容的编辑器函数代理 ===
// 这些函数现在代理到统一编辑器管理器

// 加载文件内容 - 从main.js中提取的通用逻辑
async function loadFile(filePath, area) {
    try {
        currentFilePath = filePath;
        currentFileArea = area;
        document.getElementById('current-file').textContent = `${area}/${filePath}`;

        // 获取文件扩展名
        const extension = filePath.substring(filePath.lastIndexOf('.')).toLowerCase();
        const previewableExtensions = ['.epub', '.html', '.pdf', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.ico'];
        const isPreviewable = previewableExtensions.includes(extension);

        // 对于可预览的二进制文件，直接在iframe中显示
        if (area === 'build' && isPreviewable) {
            await loadPreviewableFile(filePath, area, extension);
        } else {
            // 对于其他文件，使用原来的逻辑
            await loadRegularFile(filePath, area);
        }

        // 启用删除按钮（仅src目录）
        document.getElementById('delete-btn').disabled = (area !== 'src');
    } catch (error) {
        console.error('加载文件失败:', error);
        window.ComponentManager.getComponent('message').error('加载文件失败: ' + error.message);
    }
}

// 加载可预览的文件（build目录下的特殊文件）
async function loadPreviewableFile(filePath, area, extension) {
    // 隐藏所有视图
    hideAllViews();

    // 显示预览容器
    const previewContainer = document.getElementById('preview-container');
    const encodedFilePath = encodeURIComponent(filePath);
    const fileUrl = `/api/file/${area}/${encodedFilePath}`;

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
        previewContainer.innerHTML = `
           <div class="file-preview">
               <h3>${filePath}</h3>
               <iframe src="/epub-viewer.html?url=${encodeURIComponent(fileUrl + '?raw=true')}" style="width:100%; height:80vh; border:none;"></iframe>
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
        const response = await fetch(`/api/file/${area}/${encodedFilePath}`);
        const data = await response.json();

        if (data.type === 'image') {
            // 显示在图片查看器中
            const imageViewer = document.getElementById('image-viewer');
            imageViewer.innerHTML = `<img src="data:${data.mime};base64,${data.content}" alt="${filePath}">`;
            imageViewer.style.display = 'flex';
            currentFileType = 'image';
        }
    } else if (['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.ico'].includes(extension)) {
        // 其他图片文件处理
        const response = await fetch(`/api/file/${area}/${encodedFilePath}`);
        const data = await response.json();

        if (data.type === 'image') {
            // 显示在图片查看器中
            const imageViewer = document.getElementById('image-viewer');
            imageViewer.innerHTML = `<img src="data:${data.mime};base64,${data.content}" alt="${filePath}">`;
            imageViewer.style.display = 'flex';
            currentFileType = 'image';
        }
    }

    // 显示预览按钮并设置初始状态为"预览"
    const previewBtn = document.getElementById('preview-btn');
    previewBtn.style.display = 'inline-block';
    previewBtn.textContent = '预览';
}

// 加载常规文件（文本、图片等）
async function loadRegularFile(filePath, area) {
    const response = await fetch(`/api/file/${area}/${filePath}`);

    // 检查响应的内容类型
    const contentType = response.headers.get('content-type');

    // 如果是JSON响应（文本文件、图片等）
    if (contentType && contentType.includes('application/json')) {
        const data = await response.json();

        // 隐藏所有视图
        hideAllViews();

        if (data.type === 'text') {
            await loadTextFile(data, filePath, area);
        } else if (data.type === 'image') {
            loadImageFile(data, filePath);
        } else {
            loadBinaryFile();
        }
    }
}

// 加载文本文件
async function loadTextFile(data, filePath, area) {
    const editor = document.getElementById('editor');
    const cmEditorContainer = document.getElementById('codemirror-editor');

    if (!editor || !cmEditorContainer) {
        console.error('编辑器元素不存在');
        return;
    }

    // 隐藏textarea编辑器
    editor.style.display = 'none';

    // 显示CodeMirror编辑器容器
    cmEditorContainer.style.display = 'block';

    // 设置CodeMirror编辑器内容
    if (typeof window.codeMirrorEditor !== 'undefined' && window.codeMirrorEditor) {
        try {
            window.codeMirrorEditor.setValue(data.content || '');

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
                '.tex': 'stex',
                '': 'text/plain'  // 无后缀文件
            };

            const mode = modeMap[extension] || 'text/plain';
            window.codeMirrorEditor.setOption('mode', mode);
            
            console.log('CodeMirror编辑器内容已设置');
        } catch (error) {
            console.error('设置CodeMirror内容失败:', error);
            // 回退到备用显示方式
            showFallbackEditor(cmEditorContainer, data, filePath);
        }
    } else {
        console.warn('CodeMirror编辑器不可用，使用备用显示方式');
        // 使用备用的文本显示方式
        showFallbackEditor(cmEditorContainer, data, filePath);
    }

    // 设置全局变量
    window.currentFileType = 'text';
    window.currentFileEncoding = data.encoding || 'utf-8';
    window.currentFilePath = filePath;
    window.currentFileArea = area;

    // 更新当前文件显示
    const currentFileEl = document.getElementById('current-file');
    if (currentFileEl) {
        currentFileEl.textContent = `${area}/${filePath}`;
    }

    // 如果是Markdown文件，显示预览按钮并设置初始状态为"预览"
    const previewBtn = document.getElementById('preview-btn');
    if (previewBtn) {
        if (filePath.endsWith('.md') || filePath.endsWith('.markdown')) {
            previewBtn.style.display = 'inline-block';
            previewBtn.textContent = '预览';
        } else {
            previewBtn.style.display = 'none';
        }
    }

    // 对于所有文本文件，显示LLM按钮（仅src目录）
    const llmBtn = document.getElementById('llm-btn');
    if (llmBtn) {
        if (area === 'src') {
            llmBtn.style.display = 'inline-block';
        } else {
            llmBtn.style.display = 'none';
        }
    }
}

// 备用编辑器显示方式
function showFallbackEditor(container, data, filePath) {
    const content = data.content || '文件内容为空';
    const extension = filePath.substring(filePath.lastIndexOf('.')).toLowerCase();
    
    // 根据文件类型选择合适的显示方式
    let displayContent;
    if (extension === '.json') {
        try {
            const parsed = JSON.parse(content);
            displayContent = JSON.stringify(parsed, null, 2);
        } catch (e) {
            displayContent = content;
        }
    } else {
        displayContent = content;
    }
    
    container.innerHTML = `
        <div style="width: 100%; height: 100%; min-height: 400px; display: flex; flex-direction: column;">
            <div style="padding: 0.75rem 1rem; background: #f8fafc; border-bottom: 1px solid #e2e8f0; font-weight: 600; color: #374151;">
                ${filePath} (${extension || '文本文件'})
            </div>
            <div style="flex: 1; padding: 0;">
                <textarea 
                    style="width: 100%; height: 100%; min-height: 350px; border: none; padding: 1rem; font-family: 'Fira Code', 'Monaco', 'Menlo', monospace; font-size: 14px; line-height: 1.5; resize: none; outline: none; background: white;"
                    placeholder="文件内容..."
                >${displayContent}</textarea>
            </div>
        </div>
    `;
    
    console.log('使用备用编辑器显示文件内容');
}

// 加载图片文件
function loadImageFile(data, filePath) {
    // 显示图片查看器
    const imageViewer = document.getElementById('image-viewer');
    imageViewer.innerHTML = `<img src="data:${data.mime};base64,${data.content}" alt="${filePath}">`;
    imageViewer.style.display = 'flex';
    currentFileType = 'image';

    // 隐藏预览按钮
    document.getElementById('preview-btn').style.display = 'none';
}

// 加载二进制文件
function loadBinaryFile() {
    // 显示二进制文件提示
    document.getElementById('binary-viewer').style.display = 'flex';
    currentFileType = 'binary';
    // 隐藏预览按钮
    document.getElementById('preview-btn').style.display = 'none';
    // 重置预览按钮文本
    document.getElementById('preview-btn').textContent = '预览';
}

// 隐藏所有视图的辅助函数
function hideAllViews() {
    const viewIds = ['editor', 'image-viewer', 'binary-viewer', 'preview-container', 'codemirror-editor'];
    
    viewIds.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.style.display = 'none';
        }
    });
    
    console.log('所有编辑器视图已隐藏');
}

// 切换预览模式 - 统一的预览切换逻辑
async function togglePreview() {
    try {
        console.log('togglePreview 被调用');
        console.log('当前文件:', currentFilePath, '区域:', currentFileArea, '类型:', currentFileType);
        
        const editor = document.getElementById('editor');
        const cmEditorContainer = document.getElementById('codemirror-editor');
        const previewContainer = document.getElementById('preview-container');
        const imageViewer = document.getElementById('image-viewer');
        const binaryViewer = document.getElementById('binary-viewer');

        // 调试编辑器状态
        console.log('编辑器状态检查:');
        console.log('- textarea editor存在:', !!editor);
        console.log('- CodeMirror容器存在:', !!cmEditorContainer);
        console.log('- window.codeMirrorEditor存在:', !!window.codeMirrorEditor);
        if (window.codeMirrorEditor) {
            const content = window.codeMirrorEditor.getValue();
            console.log('- CodeMirror内容长度:', content.length);
            console.log('- CodeMirror内容预览:', content.substring(0, 50));
        }
        if (editor) {
            console.log('- textarea内容长度:', editor.value.length);
            console.log('- textarea内容预览:', editor.value.substring(0, 50));
        }

        // 检查当前是否在预览模式
        const isInPreviewMode = previewContainer?.style.display === 'block' ||
                               imageViewer?.style.display === 'flex' ||
                               binaryViewer?.style.display === 'flex';

        console.log('当前预览状态:', isInPreviewMode);
        console.log('预览容器显示状态:', previewContainer?.style.display);
        console.log('图片查看器显示状态:', imageViewer?.style.display);

        if (!isInPreviewMode) {
            // 显示预览
            if (currentFileArea === 'src' && (currentFilePath?.endsWith('.md') || currentFilePath?.endsWith('.markdown'))) {
                console.log('显示Markdown预览');
                await showMarkdownPreview(editor, cmEditorContainer, previewContainer, imageViewer, binaryViewer);
            } else if (currentFileArea === 'build') {
                // Build目录下的文件预览
                console.log('显示Build文件预览');
                await previewBuildFile(currentFilePath);
                const previewBtn = document.getElementById('preview-btn');
                if (previewBtn) {
                    previewBtn.textContent = '编辑';
                }
            } else {
                console.log('不支持的文件类型预览:', currentFileArea, currentFilePath);
                if (window.ComponentManager) {
                    window.ComponentManager.getComponent('message').info('此文件类型不支持预览');
                }
            }
        } else {
            // 显示编辑器或文件内容
            console.log('隐藏预览，显示编辑器');
            await hidePreview(editor, cmEditorContainer, previewContainer);
        }
    } catch (error) {
        console.error('切换预览模式失败:', error);
        if (window.ComponentManager) {
            window.ComponentManager.getComponent('message').error('切换预览模式失败: ' + error.message);
        }
    }
}

// 显示Markdown预览
async function showMarkdownPreview(editor, cmEditorContainer, previewContainer, imageViewer, binaryViewer) {
    try {
        // Markdown文件预览
        // 从CodeMirror编辑器获取内容
        const content = window.codeMirrorEditor ? window.codeMirrorEditor.getValue() : (editor?.value || '');
        console.log('获取到的内容长度:', content.length);
        console.log('内容预览:', content.substring(0, 100));
        
        // 如果内容为空，添加一个测试内容
        if (!content || content.trim() === '') {
            console.warn('编辑器内容为空，使用测试内容');
            const testContent = '# 测试预览\n\n这是一个测试预览内容。\n\n- 项目 1\n- 项目 2\n- 项目 3\n\n**粗体文本** 和 *斜体文本*';
            
            // 使用marked.js库解析Markdown
            if (typeof marked !== 'undefined') {
                previewContainer.innerHTML = marked.parse(testContent);
                console.log('使用测试内容和marked.js解析');
            } else {
                console.warn('marked.js库未加载，使用纯文本显示');
                previewContainer.innerHTML = `<pre>${testContent}</pre>`;
            }
        } else {
            // 使用实际内容
            if (typeof marked !== 'undefined') {
                previewContainer.innerHTML = marked.parse(content);
                console.log('使用实际内容和marked.js解析');
            } else {
                console.warn('marked.js库未加载，使用纯文本显示');
                previewContainer.innerHTML = `<pre>${content}</pre>`;
            }
        }

        // 处理图片路径，将相对路径转换为正确的静态文件服务端点
        const images = previewContainer.querySelectorAll('img');

        // 获取当前用户信息以正确构建路径
        let currentUsername = null;
        try {
            // 尝试从全局变量获取当前用户名
            if (window.userInfo && window.userInfo.username) {
                currentUsername = window.userInfo.username;
            } else {
                // 如果没有用户信息，调用checkUserInfo获取
                if (typeof checkUserInfo === 'function') {
                    await checkUserInfo();
                    currentUsername = window.userInfo ? window.userInfo.username : null;
                }
            }
        } catch (error) {
            console.warn('获取用户信息失败，使用默认路径处理:', error);
        }

        images.forEach(img => {
            const src = img.getAttribute('src');
            if (src && src.startsWith('../illustrations/')) {
                // 将 ../illustrations/ 路径转换为 /user-illustrations/username/ 格式
                let newSrc;
                if (currentUsername) {
                    // 使用带用户名的路径
                    const filename = src.replace('../illustrations/', '');
                    newSrc = `/user-illustrations/${currentUsername}/${filename}`;
                } else {
                    // 向后兼容：如果无法获取用户名，使用旧格式
                    newSrc = src.replace('../illustrations/', '/user-illustrations/');
                }
                img.setAttribute('src', newSrc);
            }
        });

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
        
        console.log('预览容器已显示，内容长度:', previewContainer.innerHTML.length);
    } catch (error) {
        console.error('显示Markdown预览失败:', error);
        if (window.ComponentManager) {
            window.ComponentManager.getComponent('message').error('显示预览失败: ' + error.message);
        }
    }
}

// 隐藏预览，显示编辑器
async function hidePreview(editor, cmEditorContainer, previewContainer) {
    try {
        if (currentFileArea === 'src' && (currentFilePath?.endsWith('.md') || currentFilePath?.endsWith('.markdown'))) {
            // Markdown文件返回编辑模式
            if (previewContainer) previewContainer.style.display = 'none';
            if (editor) editor.style.display = 'none';
            if (cmEditorContainer) cmEditorContainer.style.display = 'block';
            
            const previewBtn = document.getElementById('preview-btn');
            if (previewBtn) {
                previewBtn.textContent = '预览';
            }
        } else if (currentFileArea === 'build') {
            // Build目录下的文件，重新加载文件内容
            await loadFile(currentFilePath, currentFileArea);
            const previewBtn = document.getElementById('preview-btn');
            if (previewBtn) {
                previewBtn.textContent = '预览';
            }
        } else if (currentFileType === 'preview') {
            // 对于预览模式的文件，重新加载文件内容
            await loadFile(currentFilePath, currentFileArea);
            const previewBtn = document.getElementById('preview-btn');
            if (previewBtn) {
                previewBtn.textContent = '预览';
            }
        }
    } catch (error) {
        console.error('隐藏预览失败:', error);
        if (window.ComponentManager) {
            window.ComponentManager.getComponent('message').error('切换到编辑模式失败: ' + error.message);
        }
    }
}

// 预览Build目录下的文件 - 统一的构建文件预览逻辑
async function previewBuildFile(filePath) {
    try {
        const extension = filePath.substring(filePath.lastIndexOf('.')).toLowerCase();

        // 统一使用iframe预览所有支持的文件类型
        const encodedFilePath = encodeURIComponent(filePath);
        const fileUrl = `/api/file/build/${encodedFilePath}`;
        const previewContainer = document.getElementById('preview-container');

        // 根据文件扩展名处理预览
        if (extension === '.html') {
            await previewHtmlFile(previewContainer, filePath, fileUrl);
        } else if (extension === '.svg') {
            await previewSvgFile(filePath, encodedFilePath);
        } else if (extension === '.pdf') {
            await previewPdfFile(previewContainer, filePath, fileUrl);
        } else if (extension === '.epub') {
            await previewEpubFile(previewContainer, filePath, fileUrl);
        } else if (['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.ico'].includes(extension)) {
            await previewImageFile(filePath, encodedFilePath);
        }
    } catch (error) {
        console.error('预览文件失败:', error);
        window.ComponentManager.getComponent('message').error('预览文件失败: ' + error.message);
    }
}

// 预览HTML文件
async function previewHtmlFile(previewContainer, filePath, fileUrl) {
    hideAllViews();
    previewContainer.innerHTML = `
        <div class="file-preview">
            <h3>${filePath}</h3>
            <iframe src="${fileUrl}?raw=true" style="width:100%; height:80vh; border:none;"></iframe>
        </div>
    `;
    previewContainer.style.display = 'block';
    updateCurrentFileInfo(filePath, 'build', 'preview');
}

// 预览SVG文件
async function previewSvgFile(filePath, encodedFilePath) {
    try {
        const response = await fetch(`/api/file/build/${encodedFilePath}`);
        const data = await response.json();

        if (data.type === 'image') {
            hideAllViews();
            const imageViewer = document.getElementById('image-viewer');
            imageViewer.innerHTML = `<img src="data:${data.mime};base64,${data.content}" alt="${filePath}">`;
            imageViewer.style.display = 'flex';
            updateCurrentFileInfo(filePath, 'build', 'image');
        }
    } catch (error) {
        console.error('预览SVG文件失败:', error);
        window.ComponentManager.getComponent('message').error('预览SVG文件失败: ' + error.message);
    }
}

// 预览PDF文件
async function previewPdfFile(previewContainer, filePath, fileUrl) {
    hideAllViews();
    previewContainer.innerHTML = `
        <div class="file-preview">
            <h3>${filePath}</h3>
            <iframe src="${fileUrl}" style="width:100%; height:80vh; border:none;"></iframe>
        </div>
    `;
    previewContainer.style.display = 'block';
    updateCurrentFileInfo(filePath, 'build', 'preview');
}

// 预览EPUB文件
async function previewEpubFile(previewContainer, filePath, fileUrl) {
    hideAllViews();
    previewContainer.innerHTML = `
        <div class="file-preview">
            <h3>${filePath}</h3>
            <iframe src="/epub-viewer.html?url=${encodeURIComponent(fileUrl + '?raw=true')}" style="width:100%; height:80vh; border:none;"></iframe>
        </div>
    `;
    previewContainer.style.display = 'block';
    updateCurrentFileInfo(filePath, 'build', 'preview');
}

// 预览图片文件
async function previewImageFile(filePath, encodedFilePath) {
    try {
        const response = await fetch(`/api/file/build/${encodedFilePath}`);
        const data = await response.json();

        if (data.type === 'image') {
            hideAllViews();
            const imageViewer = document.getElementById('image-viewer');
            imageViewer.innerHTML = `<img src="data:${data.mime};base64,${data.content}" alt="${filePath}">`;
            imageViewer.style.display = 'flex';
            updateCurrentFileInfo(filePath, 'build', 'image');
        }
    } catch (error) {
        console.error('预览图片文件失败:', error);
        window.ComponentManager.getComponent('message').error('预览图片文件失败: ' + error.message);
    }
}

// 更新当前文件信息的辅助函数
function updateCurrentFileInfo(filePath, area, fileType) {
    currentFilePath = filePath;
    currentFileArea = area;
    currentFileType = fileType;
    document.getElementById('current-file').textContent = `${area}/${filePath}`;
}

// 绑定主界面事件监听器 - 统一的事件绑定逻辑（用于主编辑界面）
function bindEventListeners() {
    console.log('bindEventListeners 被调用');
    // 绑定保存按钮事件
    bindSaveButton();

    // 绑定抽屉菜单事件
    bindDrawerMenuEvents();

    // 绑定用户面板事件
    bindUserPanelEvents();

    // 绑定侧边栏切换按钮事件
    bindSidebarToggleButton();



    // 绑定文件操作按钮事件
    bindFileOperationButtons();

    // 绑定图书生成按钮事件
    bindBuildButtons();

    // 绑定主题切换事件
    bindThemeSelector();

    // 绑定图书转换器事件
    bindBookConverter();

    // 初始化文件浏览器
    initializeFileBrowser();
}

// 初始化文件浏览器
function initializeFileBrowser() {
    // 如果是首次访问，设置默认状态为显示
    if (localStorage.getItem('fileBrowserVisible') === null) {
        localStorage.setItem('fileBrowserVisible', 'true');
    }
    
    // 创建文件浏览器切换按钮
    createFileBrowserToggleButton();

    // 初始化文件浏览器显示状态
    initializeFileBrowserState();
    
    // 初始化可调整分隔符
    initializeResizer();
    
    // 确保章节抽屉默认关闭
    initializeChapterDrawerState();
    
    // 初始化章节管理器
    initializeChapterManager();

    console.log('文件浏览器已初始化');
}

// 绑定保存按钮
function bindSaveButton() {
    const saveBtn = document.getElementById('save-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveFile);
    }
}

// 绑定侧边栏切换按钮
function bindSidebarToggleButton() {
    const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
    if (toggleSidebarBtn && !toggleSidebarBtn.dataset.mainSharedListenerAdded) {
        toggleSidebarBtn.addEventListener('click', function () {
            if (typeof toggleSidebar === 'function') {
                toggleSidebar();
            } else {
                console.warn('切换侧边栏功能未找到');
            }
        });
        toggleSidebarBtn.dataset.mainSharedListenerAdded = 'true';
        console.log('侧边栏切换按钮事件监听器已绑定');
    }
}

// === 文件浏览器显示/隐藏功能 ===

// 显示文件浏览器
function showFileBrowser() {
    const fileBrowser = document.querySelector('.file-browser');
    const appLayout = document.querySelector('.app-layout');
    
    if (fileBrowser) {
        fileBrowser.style.display = 'block';
        fileBrowser.classList.remove('hidden');

        // 移除body上的隐藏类，确保布局正确
        document.body.classList.remove('file-browser-hidden');

        // 恢复保存的宽度或使用默认宽度
        const savedWidth = localStorage.getItem('fileBrowserWidth');
        if (savedWidth && appLayout) {
            const width = parseInt(savedWidth);
            if (width >= 200 && width <= window.innerWidth * 0.6) {
                fileBrowser.style.width = savedWidth;
                appLayout.style.marginLeft = savedWidth;
            }
        }

        // 更新切换按钮状态
        updateFileBrowserToggleButton(true);

        // 保存状态到localStorage
        localStorage.setItem('fileBrowserVisible', 'true');

        console.log('文件浏览器已显示');
    }
}

// 隐藏文件浏览器
function hideFileBrowser() {
    const fileBrowser = document.querySelector('.file-browser');
    const appLayout = document.querySelector('.app-layout');
    
    if (fileBrowser) {
        fileBrowser.style.display = 'none';
        fileBrowser.classList.add('hidden');

        // 添加body上的隐藏类，调整布局
        document.body.classList.add('file-browser-hidden');

        // 重置app-layout的左边距
        if (appLayout) {
            appLayout.style.marginLeft = '0px';
        }

        // 更新切换按钮状态
        updateFileBrowserToggleButton(false);

        // 保存状态到localStorage
        localStorage.setItem('fileBrowserVisible', 'false');

        console.log('文件浏览器已隐藏');
    }
}

// 切换文件浏览器显示状态
function toggleFileBrowser() {
    const fileBrowser = document.querySelector('.file-browser');
    if (fileBrowser) {
        const isVisible = fileBrowser.style.display !== 'none' && !fileBrowser.classList.contains('hidden');

        if (isVisible) {
            hideFileBrowser();
        } else {
            showFileBrowser();
        }
    }
}

// 初始化文件浏览器状态
function initializeFileBrowserState() {
    const fileBrowser = document.querySelector('.file-browser');
    if (!fileBrowser) return;

    // 从localStorage读取状态，默认为显示
    let isVisible = localStorage.getItem('fileBrowserVisible');
    if (isVisible === null) {
        // 如果没有保存的状态，默认显示
        isVisible = 'true';
    }
    isVisible = isVisible === 'true';

    if (isVisible) {
        showFileBrowser();
    } else {
        hideFileBrowser();
    }

    console.log('文件浏览器状态已初始化:', isVisible ? '显示' : '隐藏');
}

// 创建文件浏览器切换按钮
function createFileBrowserToggleButton() {
    // 检查是否已存在
    if (document.getElementById('file-browser-toggle-btn')) return;

    const toggleBtn = document.createElement('button');
    toggleBtn.id = 'file-browser-toggle-btn';
    toggleBtn.className = 'file-browser-toggle';
    toggleBtn.innerHTML = '📁';
    toggleBtn.title = '切换文件浏览器';
    toggleBtn.onclick = toggleFileBrowser;

    document.body.appendChild(toggleBtn);

    console.log('文件浏览器切换按钮已创建');
}

// 更新文件浏览器切换按钮状态
function updateFileBrowserToggleButton(isVisible) {
    const toggleBtn = document.getElementById('file-browser-toggle-btn');
    if (toggleBtn) {
        if (isVisible) {
            toggleBtn.classList.add('active');
            toggleBtn.innerHTML = '✕';
            toggleBtn.title = '隐藏文件浏览器';
        } else {
            toggleBtn.classList.remove('active');
            toggleBtn.innerHTML = '📁';
            toggleBtn.title = '显示文件浏览器';
        }
    }
}



// 绑定抽屉菜单事件
function bindDrawerMenuEvents() {
    console.log('bindDrawerMenuEvents 被调用');

    // 确保所有抽屉菜单和下拉菜单默认为关闭状态
    const adminDropdown = document.getElementById('admin-panel-dropdown');
    const chapterDrawer = document.getElementById('chapter-drawer');
    const adminDrawerOverlay = document.getElementById('drawer-overlay');
    const chapterDrawerOverlay = document.getElementById('chapter-drawer-overlay');

    if (adminDropdown) {
        adminDropdown.classList.remove('open');
    }
    if (chapterDrawer) {
        chapterDrawer.classList.remove('open');
    }
    if (adminDrawerOverlay) {
        adminDrawerOverlay.classList.remove('open');
    }
    if (chapterDrawerOverlay) {
        chapterDrawerOverlay.classList.remove('open');
    }

    // 移除body上的抽屉打开类（下拉菜单不需要这些类）
    document.body.classList.remove('admin-drawer-open', 'drawer-left-open', 'chapter-drawer-open');

    console.log('所有抽屉菜单已设置为默认关闭状态');

    const adminPanelBtn = document.getElementById('admin-panel-btn');
    const closeDrawerBtn = document.getElementById('close-drawer-btn');
    const drawerOverlay = document.getElementById('drawer-overlay');

    // 章节抽屉相关按钮
    const closeChapterDrawerBtn = document.getElementById('close-chapter-drawer-btn');
    const drawerSaveChaptersBtn = document.getElementById('drawer-save-chapters-btn');
    const drawerResetChaptersBtn = document.getElementById('drawer-reset-chapters-btn');
    const drawerRefreshChaptersBtn = document.getElementById('drawer-refresh-chapters-btn');

    console.log('adminPanelBtn:', adminPanelBtn);
    console.log('closeDrawerBtn:', closeDrawerBtn);
    console.log('drawerOverlay:', drawerOverlay);

    if (adminPanelBtn && !adminPanelBtn.dataset.mainSharedListenerAdded) {
        console.log('绑定 admin-panel-btn 点击事件');
        adminPanelBtn.addEventListener('click', function (event) {
            console.log('admin-panel-btn 被点击!', event);
            toggleAdminPanelDropdown();
        });
        adminPanelBtn.dataset.mainSharedListenerAdded = 'true';
    } else if (adminPanelBtn) {
        console.log('admin-panel-btn 已经绑定过事件');
    }

    if (closeDrawerBtn && !closeDrawerBtn.dataset.mainSharedListenerAdded) {
        closeDrawerBtn.addEventListener('click', closeAdminDropdown);
        closeDrawerBtn.dataset.mainSharedListenerAdded = 'true';
    }

    if (drawerOverlay && !drawerOverlay.dataset.mainSharedListenerAdded) {
        drawerOverlay.addEventListener('click', closeAdminDropdown);
        drawerOverlay.dataset.mainSharedListenerAdded = 'true';
    }

    // 章节抽屉事件绑定
    if (closeChapterDrawerBtn && !closeChapterDrawerBtn.dataset.mainSharedListenerAdded) {
        closeChapterDrawerBtn.addEventListener('click', closeChapterDrawer);
        closeChapterDrawerBtn.dataset.mainSharedListenerAdded = 'true';
    }

    if (chapterDrawerOverlay && !chapterDrawerOverlay.dataset.mainSharedListenerAdded) {
        chapterDrawerOverlay.addEventListener('click', closeChapterDrawer);
        chapterDrawerOverlay.dataset.mainSharedListenerAdded = 'true';
    }

    if (drawerSaveChaptersBtn && !drawerSaveChaptersBtn.dataset.mainSharedListenerAdded) {
        drawerSaveChaptersBtn.addEventListener('click', function () {
            if (typeof saveChapterOrder === 'function') {
                saveChapterOrder();
            } else {
                console.warn('saveChapterOrder function not found');
            }
        });
        drawerSaveChaptersBtn.dataset.mainSharedListenerAdded = 'true';
    }

    if (drawerResetChaptersBtn && !drawerResetChaptersBtn.dataset.mainSharedListenerAdded) {
        drawerResetChaptersBtn.addEventListener('click', function () {
            if (typeof resetChapterOrder === 'function') {
                resetChapterOrder();
            } else {
                console.warn('resetChapterOrder function not found');
            }
        });
        drawerResetChaptersBtn.dataset.mainSharedListenerAdded = 'true';
    }

    if (drawerRefreshChaptersBtn && !drawerRefreshChaptersBtn.dataset.mainSharedListenerAdded) {
        drawerRefreshChaptersBtn.addEventListener('click', function () {
            loadChapterList();
        });
        drawerRefreshChaptersBtn.dataset.mainSharedListenerAdded = 'true';
    }
}

// 绑定用户面板事件
function bindUserPanelEvents() {
    const myAccountBtn = document.getElementById('myaccount-btn');
    const closeUserPanelBtn = document.getElementById('close-user-panel-btn');

    // 确保用户面板下拉菜单默认为关闭状态
    const userPanelDropdown = document.getElementById('user-panel-dropdown');
    if (userPanelDropdown) {
        userPanelDropdown.classList.remove('open');
    }

    if (myAccountBtn && !myAccountBtn.dataset.mainSharedListenerAdded) {
        myAccountBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            toggleUserPanelDropdown();
        }); // 修改为下拉菜单
        myAccountBtn.dataset.mainSharedListenerAdded = 'true';
    }
    if (closeUserPanelBtn && !closeUserPanelBtn.dataset.mainSharedListenerAdded) {
        closeUserPanelBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            closeUserPanelDropdown();
        }); // 修改为下拉菜单
        closeUserPanelBtn.dataset.mainSharedListenerAdded = 'true';
    }

    // 添加全局点击事件来关闭下拉菜单
    if (!document.body.dataset.dropdownGlobalListenerAdded) {
        document.addEventListener('click', function (e) {
            const userPanelDropdown = document.getElementById('user-panel-dropdown');
            const adminPanelDropdown = document.getElementById('admin-panel-dropdown');
            const myAccountBtn = document.getElementById('myaccount-btn');
            const adminPanelBtn = document.getElementById('admin-panel-btn');

            // 如果点击的不是用户面板按钮或下拉菜单内部，则关闭用户下拉菜单
            if (userPanelDropdown &&
                !myAccountBtn.contains(e.target) &&
                !userPanelDropdown.contains(e.target)) {
                closeUserPanelDropdown();
            }

            // 如果点击的不是管理员面板按钮或下拉菜单内部，则关闭管理员下拉菜单
            if (adminPanelDropdown &&
                !adminPanelBtn.contains(e.target) &&
                !adminPanelDropdown.contains(e.target)) {
                closeAdminPanelDropdown();
            }
        });
        document.body.dataset.dropdownGlobalListenerAdded = 'true';
    }

    // 绑定用户面板中的按钮事件
    const userPanelSaveThemeBtn = document.getElementById('user-panel-save-theme-btn');
    const userPanelSaveLlmConfigBtn = document.getElementById('user-panel-save-llm-config-btn');
    const userPanelResetLlmConfigBtn = document.getElementById('user-panel-reset-llm-config-btn');

    if (userPanelSaveThemeBtn && !userPanelSaveThemeBtn.dataset.mainSharedListenerAdded) {
        userPanelSaveThemeBtn.addEventListener('click', saveUserTheme);
        userPanelSaveThemeBtn.dataset.mainSharedListenerAdded = 'true';
    }
    if (userPanelSaveLlmConfigBtn && !userPanelSaveLlmConfigBtn.dataset.mainSharedListenerAdded) {
        userPanelSaveLlmConfigBtn.addEventListener('click', saveUserLlmConfig);
        userPanelSaveLlmConfigBtn.dataset.mainSharedListenerAdded = 'true';
    }
    if (userPanelResetLlmConfigBtn && !userPanelResetLlmConfigBtn.dataset.mainSharedListenerAdded) {
        userPanelResetLlmConfigBtn.addEventListener('click', resetUserLlmConfig);
        userPanelResetLlmConfigBtn.dataset.mainSharedListenerAdded = 'true';
    }

    // 为logout-btn和back-btn类添加事件委托支持（支持user-actions-section组件）
    if (!document.body.dataset.userActionsBtnListenerAdded) {
        document.body.addEventListener('click', function (e) {
            // 处理登出按钮
            if (e.target.classList.contains('logout-btn')) {
                e.preventDefault();
                e.stopPropagation();
                const handler = e.target.getAttribute('data-logout-handler') || 'handleUserPanelLogout';

                // 尝试调用指定的处理函数
                if (typeof window[handler] === 'function') {
                    window[handler]();
                } else {
                    // 回退到默认处理方式
                    if (confirm('确定要登出吗？')) {
                        window.location.href = '/logout';
                    }
                }
            }

            // 处理返回按钮
            if (e.target.classList.contains('back-btn') && e.target.getAttribute('data-action') === 'back') {
                e.preventDefault();
                e.stopPropagation();
                window.history.back();
            }

            // 处理通用抽屉关闭按钮
            if (e.target.classList.contains('drawer-close-btn') || e.target.id === 'close-drawer-btn' || e.target.id === 'close-chapter-drawer-btn') {
                e.preventDefault();
                e.stopPropagation();

                // 根据ID或父元素确定要关闭的抽屉
                if (e.target.id === 'close-chapter-drawer-btn' || e.target.closest('#chapter-drawer')) {
                    if (typeof closeChapterDrawer === 'function') {
                        closeChapterDrawer();
                    }
                } else if (e.target.id === 'close-drawer-btn' || e.target.closest('#admin-drawer')) {
                    if (typeof closeAdminDropdown === 'function') {
                        closeAdminDropdown();
                    }
                } else {
                    // 通用抽屉关闭
                    const drawer = e.target.closest('.drawer');
                    if (drawer) {
                        drawer.classList.remove('open');
                        const overlay = document.querySelector('.drawer-overlay');
                        if (overlay) {
                            overlay.classList.remove('open');
                        }
                    }
                }
            }

            // 处理章节编辑按钮
            if (e.target.classList.contains('btn-edit') && e.target.getAttribute('onclick')) {
                e.preventDefault();
                e.stopPropagation();
                // 获取onclick属性的函数调用
                const onclickValue = e.target.getAttribute('onclick');
                try {
                    // 安全执行函数调用
                    new Function(onclickValue).call(e.target);
                } catch (error) {
                    console.error('执行按钮事件失败:', error);
                }
            }
        });
        document.body.dataset.userActionsBtnListenerAdded = 'true';
        console.log('通用按钮事件委托已绑定');
    }
}

// 绑定文件操作按钮事件
function bindFileOperationButtons() {
    // 绑定删除文件按钮事件
    const deleteBtn = document.getElementById('delete-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', deleteFile);
    }

    // 绑定预览按钮事件
    const previewBtn = document.getElementById('preview-btn');
    if (previewBtn && !previewBtn.dataset.eventBound) {
        previewBtn.addEventListener('click', togglePreview);
        previewBtn.dataset.eventBound = 'true';
    }

    // 绑定LLM按钮事件
    const llmBtn = document.getElementById('llm-btn');
    if (llmBtn) {
        llmBtn.addEventListener('click', showLLMDialog);
    }
}

// 绑定图书生成按钮事件
function bindBuildButtons() {
    const buildAllBtn = document.getElementById('build-all-btn');
    const buildEpubBtn = document.getElementById('build-epub-btn');
    const buildPdfBtn = document.getElementById('build-pdf-btn');

    if (buildAllBtn) {
        buildAllBtn.addEventListener('click', function () {
            buildBook('build');
        });
    }

    if (buildEpubBtn) {
        buildEpubBtn.addEventListener('click', function () {
            buildBook('epub');
        });
    }

    if (buildPdfBtn) {
        buildPdfBtn.addEventListener('click', function () {
            buildBook('pdf');
        });
    }
}

// 绑定主题切换事件
function bindThemeSelector() {
    console.log('bindThemeSelector 被调用');
    const themeSelector = document.getElementById('theme-selector');
    if (themeSelector && !themeSelector.dataset.mainSharedListenerAdded) {
        themeSelector.addEventListener('change', function (e) {
            if (typeof switchTheme === 'function') {
                switchTheme(e);
            }
        });
        themeSelector.dataset.mainSharedListenerAdded = 'true';
        console.log('主题选择器事件监听器已绑定');
    }
}

// 删除文件函数 - 从common.js中移动过来的统一删除逻辑
async function deleteFile() {
    if (!currentFilePath || currentFileArea !== 'src') {
        window.ComponentManager.getComponent('message').warning('请选择一个src目录下的文件进行删除');
        return;
    }

    // 确认删除
    if (!confirm(`确定要删除 "${currentFilePath}" 吗？`)) {
        return;
    }

    await deleteFileAtPath(currentFilePath);
}

// 用于显示用户角色的统一函数（合并了admin-common.js中的重复函数）
function showUserRoles(userId, username, options = {}) {
    // 支持不同的UI模式
    const useModal = options.useModal !== false; // 默认使用模态框
    const useSectionView = options.useSectionView === true; // 可选使用部分视图

    if (useSectionView) {
        // 旧的admin-common.js中的部分视图模式
        try {
            // 设置当前用户信息
            const currentUserNameElement = document.getElementById('current-user-name');
            if (currentUserNameElement) {
                currentUserNameElement.textContent = username;
            }

            // 显示用户角色管理界面
            const userRolesSection = document.getElementById('user-roles-section');
            if (userRolesSection) {
                userRolesSection.style.display = 'block';
            }

            // 隐藏其他部分
            const adminContainer = document.querySelector('.admin-container');
            if (adminContainer) {
                adminContainer.querySelectorAll('.section:not(#user-roles-section)').forEach(section => {
                    section.style.display = 'none';
                });
            }

            // 加载用户角色数据
            loadUserRoles(userId, { renderMode: 'table' });
        } catch (error) {
            console.error('显示用户角色管理界面失败:', error);
            window.ComponentManager.getComponent('message').error('显示用户角色管理界面失败: ' + error.message);
        }
    } else if (useModal) {
        // 默认的模态框模式
        const modal = document.getElementById('user-roles-modal');
        const modalTitle = document.getElementById('user-roles-modal-title');

        if (modal) {
            if (modalTitle) {
                modalTitle.textContent = `用户角色管理 - ${username}`;
            }
            modal.style.display = 'block';

            // 存储当前用户ID以供后续操作使用
            window.currentUserId = userId;

            // 加载用户角色数据
            loadUserRoles(userId, { renderMode: 'card' });
        }
    }
}

// 加载用户角色数据（统一版本）
async function loadUserRoles(userId, options = {}) {
    try {
        const response = await fetch(`/api/admin/users/${userId}/roles`);
        const result = await response.json();

        if (response.ok) {
            renderUserRoles(result.roles, options);
        } else {
            throw new Error(result.detail || '获取用户角色失败');
        }
    } catch (error) {
        console.error('加载用户角色失败:', error);
        window.ComponentManager.getComponent('message').error('加载用户角色失败: ' + error.message);
    }
}

// 渲染用户角色（统一版本，支持多种渲染模式）
function renderUserRoles(roles, options = {}) {
    const renderMode = options.renderMode || 'card'; // 默认使用卡片模式

    if (renderMode === 'table') {
        // 表格模式（用于admin-common.js的原有界面）
        const rolesList = document.getElementById('user-roles-list');
        if (!rolesList) {
            console.warn('找不到user-roles-list元素，回退到卡片模式');
            return renderUserRoles(roles, { ...options, renderMode: 'card' });
        }

        rolesList.innerHTML = '';
        roles.forEach(role => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${role.id || ''}</td>
                <td>${role.name}</td>
                <td>${role.description || ''}</td>
                <td>${role.assigned_at ? formatDate(role.assigned_at) : ''}</td>
                <td>
                    <button class="btn-action btn-delete" data-role-id="${role.id}">移除</button>
                </td>
            `;
            rolesList.appendChild(row);
        });
    } else {
        // 卡片模式（默认模式，用于模态框）
        const container = document.getElementById('user-roles-content');
        if (!container) {
            console.error('找不到user-roles-content元素');
            return;
        }

        container.innerHTML = '';

        if (roles && roles.length > 0) {
            roles.forEach(role => {
                const roleItem = document.createElement('div');
                roleItem.className = 'role-item';
                roleItem.innerHTML = `
                    <span class="role-name">${role.name}</span>
                    <span class="role-description">${role.description || ''}</span>
                    <button class="btn-danger btn-sm" onclick="removeUserRole(${window.currentUserId}, '${role.name}')">移除</button>
                `;
                container.appendChild(roleItem);
            });
        } else {
            container.innerHTML = '<p>该用户暂无角色</p>';
        }
    }
}

// 移除用户角色
async function removeUserRole(userId, roleName) {
    if (!confirm(`确定要移除用户的 "${roleName}" 角色吗？`)) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/users/${userId}/roles/${roleName}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (response.ok) {
            window.ComponentManager.getComponent('message').success('角色移除成功');
            // 重新加载用户角色
            loadUserRoles(userId);
        } else {
            throw new Error(result.detail || '移除角色失败');
        }
    } catch (error) {
        console.error('移除用户角色失败:', error);
        window.ComponentManager.getComponent('message').error('移除用户角色失败: ' + error.message);
    }
}

// 为编辑器中的代码添加高亮（统一函数，由两个主题共享）
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

// 绑定图书转换器事件
function bindBookConverter() {
    console.log('bindBookConverter 被调用');
    const bookConverterSelect = document.getElementById('book-converter-select');
    if (bookConverterSelect && !bookConverterSelect.dataset.listenerAdded) {
        bookConverterSelect.addEventListener('change', function (e) {
            if (typeof handleBookConverterChange === 'function') {
                handleBookConverterChange(e);
            } else {
                console.warn('图书转换器处理函数未找到');
            }
        });
        bookConverterSelect.dataset.listenerAdded = 'true';
        console.log('图书转换器事件监听器已绑定');
    }
}

// 章节抽屉管理功能

// 切换章节抽屉显示/隐藏
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
    } else {
        console.warn('章节抽屉元素未找到');
    }
}

// 打开章节抽屉
function openChapterDrawer() {
    const drawer = document.getElementById('chapter-drawer');
    const overlay = document.getElementById('chapter-drawer-overlay');

    if (drawer && overlay) {
        drawer.classList.add('open');
        overlay.classList.add('open');
        document.body.classList.add('chapter-drawer-open');

        // 加载章节列表
        loadChapterList();
    }
}

// 关闭章节抽屉
function closeChapterDrawer() {
    const drawer = document.getElementById('chapter-drawer');
    const overlay = document.getElementById('chapter-drawer-overlay');

    if (drawer && overlay) {
        drawer.classList.remove('open');
        overlay.classList.remove('open');
        document.body.classList.remove('chapter-drawer-open');
    }
}

// 加载章节列表
async function loadChapterList() {
    try {
        const response = await fetch('/api/admin/chapter-config');
        const config = await response.json();

        const chapterList = document.getElementById('drawer-chapters');
        if (!chapterList) {
            console.warn('章节列表元素未找到');
            return;
        }

        chapterList.innerHTML = '';

        if (config.chapters && config.chapters.length > 0) {
            config.chapters.forEach((chapter, index) => {
                const listItem = document.createElement('li');
                listItem.className = 'chapter-item';
                listItem.draggable = true;
                listItem.innerHTML = `
                    <span class="chapter-handle">↕️</span>
                    <span class="chapter-title">${chapter.title}</span>
                    <div class="chapter-actions">
                        <button class="btn-edit btn-secondary btn-sm" onclick="editChapterFile('${chapter.file}')">编辑</button>
                        <button class="btn-remove btn-danger btn-sm">移除</button>
                    </div>
                `;

                // 绑定拖拽事件
                listItem.addEventListener('dragstart', handleDragStart);
                listItem.addEventListener('dragover', handleDragOver);
                listItem.addEventListener('drop', handleDrop);
                listItem.addEventListener('dragend', handleDragEnd);

                chapterList.appendChild(listItem);
            });
        } else {
            chapterList.innerHTML = '<li class="no-chapters">暂无章节</li>';
        }

    } catch (error) {
        console.error('加载章节列表失败:', error);
        const chapterList = document.getElementById('drawer-chapters');
        if (chapterList) {
            chapterList.innerHTML = '<li class="error">加载失败</li>';
        }
    }
}

// 编辑章节文件
function editChapterFile(filename) {
    // 关闭抽屉
    closeChapterDrawer();

    // 加载文件进入编辑器
    const filePath = `chapters/${filename}`;
    if (typeof loadFile === 'function') {
        loadFile(filePath, 'src');
    } else {
        console.warn('加载文件函数未找到');
    }
}

// 拖拽事件处理函数
let draggedElement = null;

function handleDragStart(e) {
    draggedElement = this;
    this.style.opacity = '0.5';
}

function handleDragOver(e) {
    e.preventDefault();
}

function handleDrop(e) {
    e.preventDefault();

    if (draggedElement !== this) {
        const allItems = Array.from(this.parentNode.children);
        const draggedIndex = allItems.indexOf(draggedElement);
        const targetIndex = allItems.indexOf(this);

        if (draggedIndex < targetIndex) {
            this.parentNode.insertBefore(draggedElement, this.nextSibling);
        } else {
            this.parentNode.insertBefore(draggedElement, this);
        }
    }
}

function handleDragEnd(e) {
    this.style.opacity = '';
    draggedElement = null;
}

// 用户面板相关函数

// 切换用户面板下拉菜单
function toggleUserPanelDropdown() {
    const dropdown = document.getElementById('user-panel-dropdown');
    if (dropdown) {
        const isOpen = dropdown.classList.contains('open');
        if (isOpen) {
            closeUserPanelDropdown();
        } else {
            openUserPanelDropdown();
        }
    }
}

// 打开用户面板下拉菜单
function openUserPanelDropdown() {
    const dropdown = document.getElementById('user-panel-dropdown');
    if (dropdown) {
        // 关闭其他下拉菜单
        document.querySelectorAll('.dropdown.open').forEach(otherDropdown => {
            if (otherDropdown !== dropdown) {
                otherDropdown.classList.remove('open');
            }
        });

        dropdown.classList.add('open');

        // 加载用户信息
        loadUserPanelInfo();
    }
}

// 关闭用户面板下拉菜单
function closeUserPanelDropdown() {
    const dropdown = document.getElementById('user-panel-dropdown');
    if (dropdown) {
        dropdown.classList.remove('open');
    }
}

// 加载用户面板信息
async function loadUserPanelInfo() {
    try {
        // 加载用户信息
        if (typeof checkUserInfo === 'function') {
            await checkUserInfo();
        }

        // 更新用户名显示
        const usernameElement = document.getElementById('user-panel-username');
        if (usernameElement && window.userInfo && window.userInfo.username) {
            usernameElement.textContent = window.userInfo.username;
        }

        // 更新用户角色显示
        const roleElement = document.getElementById('user-panel-role');
        if (roleElement && window.userInfo) {
            if (window.userInfo.isAdmin) {
                roleElement.textContent = '管理员';
            } else {
                roleElement.textContent = '用户';
            }
        }

        // 加载用户主题设置
        const themeSelect = document.getElementById('user-panel-theme-selector');
        if (themeSelect) {
            try {
                const response = await fetch('/api/user/theme');
                if (response.ok) {
                    const data = await response.json();
                    themeSelect.value = data.theme || 'default';
                }
            } catch (error) {
                console.warn('加载用户主题设置失败:', error);
            }
        }

    } catch (error) {
        console.error('加载用户面板信息失败:', error);
    }
}

// 保存用户主题设置
async function saveUserTheme() {
    const themeSelect = document.getElementById('user-panel-theme-selector');
    if (!themeSelect) {
        window.ComponentManager.getComponent('message').error('主题选择器未找到');
        return;
    }

    try {
        const theme = themeSelect.value;
        const response = await fetch('/api/user/theme', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ theme: theme })
        });

        if (response.ok) {
            window.ComponentManager.getComponent('message').success('主题设置保存成功');
            // 刷新页面以应用新主题
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            throw new Error('保存失败');
        }
    } catch (error) {
        console.error('保存用户主题失败:', error);
        window.ComponentManager.getComponent('message').error('保存主题设置失败: ' + error.message);
    }
}

// 保存用户LLM配置
async function saveUserLlmConfig() {
    const configTextarea = document.getElementById('user-panel-llm-config');
    if (!configTextarea) {
        window.ComponentManager.getComponent('message').error('LLM配置输入框未找到');
        return;
    }

    try {
        const config = configTextarea.value.trim();
        let parsedConfig = {};

        if (config) {
            parsedConfig = JSON.parse(config);
        }

        const response = await fetch('/api/user/llm-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ config: parsedConfig })
        });

        if (response.ok) {
            window.ComponentManager.getComponent('message').success('LLM配置保存成功');
        } else {
            throw new Error('保存失败');
        }
    } catch (error) {
        console.error('保存LLM配置失败:', error);
        if (error instanceof SyntaxError) {
            window.ComponentManager.getComponent('message').error('LLM配置格式错误，请检查JSON格式');
        } else {
            window.ComponentManager.getComponent('message').error('保存LLM配置失败: ' + error.message);
        }
    }
}

// 重置用户LLM配置
function resetUserLlmConfig() {
    const configTextarea = document.getElementById('user-panel-llm-config');
    if (configTextarea) {
        configTextarea.value = '';
        window.ComponentManager.getComponent('message').info('LLM配置已重置');
    }
}

// 用户面板登出处理
function handleUserPanelLogout() {
    if (confirm('确定要登出吗？')) {
        window.location.href = '/logout';
    }
}

// 管理员面板登出处理
function handleAdminPanelLogout() {
    if (confirm('确定要登出吗？')) {
        window.location.href = '/logout';
    }
}

// === 管理员面板下拉菜单功能 ===

// 切换管理员面板下拉菜单
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

// 打开管理员面板下拉菜单
function openAdminPanelDropdown() {
    const dropdown = document.getElementById('admin-panel-dropdown');
    console.log('openAdminPanelDropdown 被调用，dropdown:', dropdown);
    
    if (dropdown) {
        console.log('dropdown 存在，添加 open 类');
        
        // 关闭其他下拉菜单
        document.querySelectorAll('.dropdown.open').forEach(otherDropdown => {
            if (otherDropdown !== dropdown) {
                otherDropdown.classList.remove('open');
            }
        });
        
        dropdown.classList.add('open');
        console.log('dropdown 类名:', dropdown.className);
        
        // 检查下拉内容元素
        const dropdownContent = dropdown.querySelector('.dropdown-content');
        console.log('dropdown-content 元素:', dropdownContent);
        if (dropdownContent) {
            console.log('dropdown-content 样式:', {
                display: window.getComputedStyle(dropdownContent).display,
                opacity: window.getComputedStyle(dropdownContent).opacity,
                visibility: window.getComputedStyle(dropdownContent).visibility,
                zIndex: window.getComputedStyle(dropdownContent).zIndex,
                position: window.getComputedStyle(dropdownContent).position
            });
            
            // 强制显示下拉内容（调试用）
            dropdownContent.style.display = 'block';
            dropdownContent.style.opacity = '1';
            dropdownContent.style.visibility = 'visible';
            console.log('强制显示下拉内容');
        }
        
        // 加载管理员信息
        loadAdminPanelInfo();
    } else {
        console.error('admin-panel-dropdown 元素未找到');
        // 尝试查找所有包含 admin-panel 的元素
        const allAdminElements = document.querySelectorAll('[id*="admin-panel"]');
        console.log('所有包含 admin-panel 的元素:', allAdminElements);
    }
}

// 关闭管理员面板下拉菜单
function closeAdminPanelDropdown() {
    const dropdown = document.getElementById('admin-panel-dropdown');
    if (dropdown) {
        dropdown.classList.remove('open');
    }
}

// 加载管理员面板信息
async function loadAdminPanelInfo() {
    try {
        // 加载用户信息
        if (typeof checkUserInfo === 'function') {
            await checkUserInfo();
        }

        // 更新管理员信息显示
        const usernameElement = document.getElementById('admin-panel-username');
        if (usernameElement && window.userInfo && window.userInfo.username) {
            usernameElement.textContent = window.userInfo.username;
        }

        // 更新管理员角色显示
        const roleElement = document.getElementById('admin-panel-role');
        if (roleElement && window.userInfo) {
            if (window.userInfo.isAdmin) {
                roleElement.textContent = '管理员';
            } else {
                roleElement.textContent = '用户';
            }
        }

        console.log('管理员面板信息已加载');
    } catch (error) {
        console.error('加载管理员面板信息失败:', error);
    }
}

// 为了向后兼容，保留旧函数名
const toggleAdminDropdown = toggleAdminPanelDropdown;
const openAdminDropdown = openAdminPanelDropdown;
const closeAdminDropdown = closeAdminPanelDropdown;

// LLM对话框功能

// 显示LLM对话框
function showLLMDialog() {
    // 这里可以实现LLM对话框功能
    // 暂时显示一个简单的提示
    window.ComponentManager.getComponent('message').info('LLM功能正在开发中...');

    // TODO: 实现完整的LLM对话框
    // 可以包括：
    // - 文本处理
    // - AI对话
    // - 代码生成
    // - 等等
}

// 侧边栏切换功能

// 切换侧边栏显示/隐藏 - 使用新的文件浏览器功能
function toggleSidebar() {
    // 直接调用文件浏览器切换功能
    toggleFileBrowser();

    // 更新传统的侧边栏切换按钮状态
    const toggleBtn = document.getElementById('toggle-sidebar-btn');
    const fileBrowser = document.querySelector('.file-browser');

    if (toggleBtn && fileBrowser) {
        const isVisible = fileBrowser.style.display !== 'none' && !fileBrowser.classList.contains('hidden');

        if (isVisible) {
            toggleBtn.innerHTML = '<i class="btn-icon">🖼️</i><span class="btn-text-short">侧边栏</span>';
            toggleBtn.title = '隐藏侧边栏';
        } else {
            toggleBtn.innerHTML = '<i class="btn-icon">▶</i><span class="btn-text-short">显示</span>';
            toggleBtn.title = '显示侧边栏';
        }
    }
}

// 初始化侧边栏状态 - 使用新的文件浏览器功能
function initializeSidebarState() {
    // 直接调用文件浏览器状态初始化
    initializeFileBrowserState();

    // 更新传统的侧边栏切换按钮状态
    const toggleBtn = document.getElementById('toggle-sidebar-btn');
    const fileBrowser = document.querySelector('.file-browser');

    if (toggleBtn && fileBrowser) {
        const isVisible = fileBrowser.style.display !== 'none' && !fileBrowser.classList.contains('hidden');

        if (isVisible) {
            toggleBtn.innerHTML = '<i class="btn-icon">🖼️</i><span class="btn-text-short">侧边栏</span>';
            toggleBtn.title = '隐藏侧边栏';
        } else {
            toggleBtn.innerHTML = '<i class="btn-icon">▶</i><span class="btn-text-short">显示</span>';
            toggleBtn.title = '显示侧边栏';
        }
    }
}


// 初始化章节抽屉状态
function initializeChapterDrawerState() {
    const chapterDrawer = document.getElementById('chapter-drawer');
    const chapterDrawerOverlay = document.getElementById('chapter-drawer-overlay');

    if (chapterDrawer) {
        // 强制移除open类
        chapterDrawer.classList.remove('open');
        console.log('章节抽屉已设置为关闭状态');
    }

    if (chapterDrawerOverlay) {
        // 强制移除open类
        chapterDrawerOverlay.classList.remove('open');
    }

    // 确保body上没有相关的打开类
    document.body.classList.remove('drawer-left-open', 'chapter-drawer-open');
}

// 章节抽屉控制函数
function toggleChapterDrawer() {
    const drawer = document.getElementById('chapter-drawer');
    const overlay = document.getElementById('chapter-drawer-overlay');
    
    if (!drawer) {
        console.warn('章节抽屉元素未找到');
        return;
    }
    
    const isOpen = drawer.classList.contains('open');
    
    if (isOpen) {
        closeChapterDrawer();
    } else {
        openChapterDrawer();
    }
}

function openChapterDrawer() {
    const drawer = document.getElementById('chapter-drawer');
    const overlay = document.getElementById('chapter-drawer-overlay');
    
    if (!drawer) return;
    
    // 创建遮罩层（如果不存在）
    if (!overlay) {
        const newOverlay = document.createElement('div');
        newOverlay.id = 'chapter-drawer-overlay';
        newOverlay.className = 'drawer-overlay';
        newOverlay.addEventListener('click', closeChapterDrawer);
        document.body.appendChild(newOverlay);
    }
    
    // 打开抽屉
    drawer.classList.add('open');
    if (overlay) overlay.classList.add('open');
    document.body.classList.add('drawer-right-open');
    
    console.log('章节抽屉已打开');
}

function closeChapterDrawer() {
    const drawer = document.getElementById('chapter-drawer');
    const overlay = document.getElementById('chapter-drawer-overlay');
    
    if (drawer) {
        drawer.classList.remove('open');
    }
    
    if (overlay) {
        overlay.classList.remove('open');
    }
    
    document.body.classList.remove('drawer-right-open');
    
    console.log('章节抽屉已关闭');
}

// 初始化章节管理按钮
function initializeChapterManager() {
    const chapterBtn = document.getElementById('chapter-manager-btn');
    if (chapterBtn) {
        chapterBtn.addEventListener('click', toggleChapterDrawer);
        console.log('章节管理按钮已初始化');
    }
    
    // 初始化抽屉关闭按钮
    const drawer = document.getElementById('chapter-drawer');
    if (drawer) {
        const closeBtn = drawer.querySelector('[data-drawer-close]');
        if (closeBtn) {
            closeBtn.addEventListener('click', closeChapterDrawer);
        }
    }
}



// 可调整分隔符功能

// 初始化可调整分隔符
function initializeResizer() {
    const resizer = document.getElementById('sidebar-resizer');
    const fileBrowser = document.querySelector('.file-browser');
    const appLayout = document.querySelector('.app-layout');

    if (resizer && fileBrowser && appLayout) {
        let isResizing = false;

        // 更新resizer位置和可见性
        function updateResizerState() {
            const isFileBrowserVisible = !fileBrowser.classList.contains('hidden') &&
                                       fileBrowser.style.display !== 'none' &&
                                       !document.body.classList.contains('file-browser-hidden');
            
            if (isFileBrowserVisible) {
                const fileBrowserWidth = fileBrowser.offsetWidth || 320;
                resizer.style.left = fileBrowserWidth + 'px';
                resizer.style.display = 'block';
            } else {
                resizer.style.display = 'none';
            }
        }

        // 自适应函数，在窗口大小改变时调整侧边栏和resizer的位置
        function adaptToWindowResize() {
            // 获取保存的宽度
            const savedWidth = localStorage.getItem('fileBrowserWidth');
            if (savedWidth) {
                // 修复：正确解析保存的宽度（去除'px'）
                const width = parseInt(savedWidth, 10);
                // 设置最小和最大宽度
                const minWidth = 200;
                const maxWidth = window.innerWidth * 0.6;
                
                // 确保宽度在有效范围内
                let newWidth = width;
                if (newWidth < minWidth) newWidth = minWidth;
                if (newWidth > maxWidth) newWidth = maxWidth;
                
                // 更新文件浏览器宽度
                fileBrowser.style.width = newWidth + 'px';
                
                // 更新app-layout的左边距
                appLayout.style.marginLeft = newWidth + 'px';
                
                // 更新resizer位置
                resizer.style.left = newWidth + 'px';
            } else {
                // 如果没有保存的宽度，使用默认宽度
                const defaultWidth = 320;
                const maxWidth = window.innerWidth * 0.6;
                const newWidth = defaultWidth > maxWidth ? maxWidth : defaultWidth;
                
                fileBrowser.style.width = newWidth + 'px';
                appLayout.style.marginLeft = newWidth + 'px';
                resizer.style.left = newWidth + 'px';
            }
        }

        resizer.addEventListener('mousedown', function (e) {
            // 只有在文件浏览器可见时才允许拖动
            if (document.body.classList.contains('file-browser-hidden') ||
                fileBrowser.classList.contains('hidden')) {
                return;
            }
            
            isResizing = true;
            document.body.style.cursor = 'ew-resize';
            document.body.style.userSelect = 'none';
            e.preventDefault();
        });

        document.addEventListener('mousemove', function (e) {
            if (!isResizing) return;

            // 计算新宽度（相对于视口左边缘）
            const newWidth = e.clientX;

            // 设置最小和最大宽度
            const minWidth = 200;
            const maxWidth = window.innerWidth * 0.6;

            if (newWidth >= minWidth && newWidth <= maxWidth) {
                // 更新文件浏览器宽度
                fileBrowser.style.width = newWidth + 'px';
                
                // 更新app-layout的左边距
                appLayout.style.marginLeft = newWidth + 'px';
                
                // 更新resizer位置
                resizer.style.left = newWidth + 'px';

                // 修复：保存宽度到 localStorage（只保存数字，不保存'px'）
                localStorage.setItem('fileBrowserWidth', newWidth.toString());
            }
        });

        document.addEventListener('mouseup', function () {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });

        // 添加窗口resize事件监听器
        window.addEventListener('resize', adaptToWindowResize);

        // 初始化文件浏览器宽度
        const savedWidth = localStorage.getItem('fileBrowserWidth');
        if (savedWidth) {
            // 修复：正确解析保存的宽度（去除'px'）
            const width = parseInt(savedWidth, 10);
            if (width >= 200 && width <= window.innerWidth * 0.6) {
                fileBrowser.style.width = width + 'px';
                appLayout.style.marginLeft = width + 'px';
                resizer.style.left = width + 'px';
            }
        } else {
            // 如果没有保存的宽度，使用默认宽度
            const defaultWidth = 320;
            fileBrowser.style.width = defaultWidth + 'px';
            appLayout.style.marginLeft = defaultWidth + 'px';
            resizer.style.left = defaultWidth + 'px';
        }

        // 初始更新resizer状态
        updateResizerState();

        // 在初始化时调用一次自适应函数
        setTimeout(adaptToWindowResize, 0);

        // 监听文件浏览器状态变化
        const observer = new MutationObserver(updateResizerState);
        observer.observe(fileBrowser, {
            attributes: true,
            attributeFilter: ['class', 'style']
        });
        observer.observe(document.body, {
            attributes: true,
            attributeFilter: ['class']
        });
    }
}
// ======
//======================================================================
// 全局函数导出 - 确保关键函数在全局作用域中可用
// ============================================================================

// 将关键函数导出到全局作用域，供主题加载器和其他模块使用
window.loadFileTree = loadFileTree;
window.bindEventListeners = bindEventListeners;
window.initializeSidebarState = initializeSidebarState;
window.toggleSidebar = toggleSidebar;
window.initializeResizer = initializeResizer;
window.toggleAdminPanelDropdown = toggleAdminPanelDropdown;
window.openAdminPanelDropdown = openAdminPanelDropdown;
window.closeAdminPanelDropdown = closeAdminPanelDropdown;
window.handleAdminPanelLogout = handleAdminPanelLogout;

// 为了向后兼容，保留旧函数名
window.toggleAdminDropdown = toggleAdminPanelDropdown;
window.openAdminDropdown = openAdminPanelDropdown;
window.closeAdminDropdown = closeAdminPanelDropdown;
window.toggleChapterDrawer = toggleChapterDrawer;
window.closeChapterDrawer = closeChapterDrawer;
window.toggleUserPanelDropdown = toggleUserPanelDropdown;
window.closeUserPanelDropdown = closeUserPanelDropdown;
window.saveFile = saveFile;
window.deleteFile = deleteFile;
window.togglePreview = togglePreview;
window.showLLMDialog = showLLMDialog;
window.buildBook = buildBook;

console.log('Main-shared.js: 所有关键函数已导出到全局作用域');