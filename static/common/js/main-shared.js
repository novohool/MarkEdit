// MarkEdit 主题无关的共享主要功能函数
// 此模块包含所有主题都需要使用的核心业务逻辑函数

// 加载文件内容 - 从main.js中提取的通用逻辑
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
            await loadPreviewableFile(filePath, area, extension);
        } else {
            // 对于其他文件，使用原来的逻辑
            await loadRegularFile(filePath, area);
        }
        
        // 启用删除按钮（仅src目录）
        document.getElementById('delete-btn').disabled = (area !== 'src');
    } catch (error) {
        console.error('加载文件失败:', error);
        showMessage('加载文件失败: ' + error.message, 'error');
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
    
    // 如果是Markdown文件，显示预览按钮并设置初始状态为"预览"
    if (filePath.endsWith('.md') || filePath.endsWith('.markdown')) {
        const previewBtn = document.getElementById('preview-btn');
        previewBtn.style.display = 'inline-block';
        previewBtn.textContent = '预览';
    } else {
        document.getElementById('preview-btn').style.display = 'none';
    }
    
    // 对于所有文本文件，显示LLM按钮（仅src目录）
    if (area === 'src') {
        document.getElementById('llm-btn').style.display = 'inline-block';
    } else {
        document.getElementById('llm-btn').style.display = 'none';
    }
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
    document.getElementById('editor').style.display = 'none';
    document.getElementById('image-viewer').style.display = 'none';
    document.getElementById('binary-viewer').style.display = 'none';
    document.getElementById('preview-container').style.display = 'none';
    document.getElementById('codemirror-editor').style.display = 'none';
}

// 切换预览模式 - 统一的预览切换逻辑
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
            await showMarkdownPreview(editor, cmEditorContainer, previewContainer, imageViewer, binaryViewer);
        } else if (currentFileArea === 'build') {
            // Build目录下的文件预览
            await previewBuildFile(currentFilePath);
            document.getElementById('preview-btn').textContent = '编辑';
        }
    } else {
        // 显示编辑器或文件内容
        await hidePreview(editor, cmEditorContainer, previewContainer);
    }
}

// 显示Markdown预览
async function showMarkdownPreview(editor, cmEditorContainer, previewContainer, imageViewer, binaryViewer) {
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
}

// 隐藏预览，显示编辑器
async function hidePreview(editor, cmEditorContainer, previewContainer) {
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
        }
    } catch (error) {
        console.error('预览文件失败:', error);
        showMessage('预览文件失败: ' + error.message, 'error');
    }
}

// 预览HTML文件
async function previewHtmlFile(previewContainer, filePath, fileUrl) {
    previewContainer.innerHTML = `
        <div class="file-preview">
            <h3>${filePath}</h3>
            <iframe src="${fileUrl}?raw=true" style="width:100%; height:80vh; border:none;"></iframe>
        </div>
    `;
    previewContainer.style.display = 'block';
    hideAllViews();
    previewContainer.style.display = 'block';
    updateCurrentFileInfo(filePath, 'build', 'preview');
}

// 预览SVG文件
async function previewSvgFile(filePath, encodedFilePath) {
    const response = await fetch(`/api/file/build/${encodedFilePath}`);
    const data = await response.json();
    
    if (data.type === 'image') {
        const imageViewer = document.getElementById('image-viewer');
        imageViewer.innerHTML = `<img src="data:${data.mime};base64,${data.content}" alt="${filePath}">`;
        imageViewer.style.display = 'flex';
        hideAllViews();
        imageViewer.style.display = 'flex';
        updateCurrentFileInfo(filePath, 'build', 'image');
    }
}

// 预览PDF文件
async function previewPdfFile(previewContainer, filePath, fileUrl) {
    previewContainer.innerHTML = `
        <div class="file-preview">
            <h3>${filePath}</h3>
            <iframe src="${fileUrl}" style="width:100%; height:80vh; border:none;"></iframe>
        </div>
    `;
    previewContainer.style.display = 'block';
    hideAllViews();
    previewContainer.style.display = 'block';
    updateCurrentFileInfo(filePath, 'build', 'preview');
}

// 预览EPUB文件
async function previewEpubFile(previewContainer, filePath, fileUrl) {
    previewContainer.innerHTML = `
        <div class="file-preview">
            <h3>${filePath}</h3>
            <iframe src="/epub-viewer.html?file=${encodeURIComponent(fileUrl + '?raw=true')}" style="width:100%; height:80vh; border:none;"></iframe>
        </div>
    `;
    previewContainer.style.display = 'block';
    hideAllViews();
    previewContainer.style.display = 'block';
    updateCurrentFileInfo(filePath, 'build', 'preview');
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
    
    // 绑定文件操作按钮事件
    bindFileOperationButtons();
    
    // 绑定图书生成按钮事件
    bindBuildButtons();
    
    // 绑定主题切换事件
    bindThemeSelector();
}

// 绑定保存按钮
function bindSaveButton() {
    const saveBtn = document.getElementById('save-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveFile);
    }
}

// 绑定抽屉菜单事件
function bindDrawerMenuEvents() {
    console.log('bindDrawerMenuEvents 被调用');
    const adminMenuBtn = document.getElementById('admin-menu-btn');
    const closeDrawerBtn = document.getElementById('close-drawer-btn');
    const drawerOverlay = document.getElementById('drawer-overlay');
    
    console.log('adminMenuBtn:', adminMenuBtn);
    console.log('closeDrawerBtn:', closeDrawerBtn);
    console.log('drawerOverlay:', drawerOverlay);
    
    if (adminMenuBtn && !adminMenuBtn.dataset.mainSharedListenerAdded) {
        console.log('绑定 admin-menu-btn 点击事件');
        adminMenuBtn.addEventListener('click', function(event) {
            console.log('admin-menu-btn 被点击!', event);
            toggleAdminDrawer();
        });
        adminMenuBtn.dataset.mainSharedListenerAdded = 'true';
    } else if (adminMenuBtn) {
        console.log('admin-menu-btn 已经绑定过事件');
    }
    if (closeDrawerBtn && !closeDrawerBtn.dataset.mainSharedListenerAdded) {
        closeDrawerBtn.addEventListener('click', closeAdminDrawer);
        closeDrawerBtn.dataset.mainSharedListenerAdded = 'true';
    }
    if (drawerOverlay && !drawerOverlay.dataset.mainSharedListenerAdded) {
        drawerOverlay.addEventListener('click', closeAdminDrawer);
        drawerOverlay.dataset.mainSharedListenerAdded = 'true';
    }
}

// 绑定用户面板事件
function bindUserPanelEvents() {
    const myAccountBtn = document.getElementById('myaccount-btn');
    const closeUserPanelBtn = document.getElementById('close-user-panel-btn');
    if (myAccountBtn && !myAccountBtn.dataset.mainSharedListenerAdded) {
        myAccountBtn.addEventListener('click', toggleUserPanelDrawer);
        myAccountBtn.dataset.mainSharedListenerAdded = 'true';
    }
    if (closeUserPanelBtn && !closeUserPanelBtn.dataset.mainSharedListenerAdded) {
        closeUserPanelBtn.addEventListener('click', closeUserPanelDrawer);
        closeUserPanelBtn.dataset.mainSharedListenerAdded = 'true';
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
    if (previewBtn) {
        previewBtn.addEventListener('click', togglePreview);
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
        buildAllBtn.addEventListener('click', function() {
            buildBook('build');
        });
    }
    
    if (buildEpubBtn) {
        buildEpubBtn.addEventListener('click', function() {
            buildBook('epub');
        });
    }
    
    if (buildPdfBtn) {
        buildPdfBtn.addEventListener('click', function() {
            buildBook('pdf');
        });
    }
}

// 绑定主题切换事件
function bindThemeSelector() {
    const themeSelector = document.getElementById('theme-selector');
    if (themeSelector) {
        themeSelector.addEventListener('change', switchTheme);
    }
}

// 删除文件函数 - 从common.js中移动过来的统一删除逻辑
async function deleteFile() {
    if (!currentFilePath || currentFileArea !== 'src') {
        showMessage('请选择一个src目录下的文件进行删除', 'warning');
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
            showMessage('显示用户角色管理界面失败: ' + error.message, 'error');
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
        showMessage('加载用户角色失败: ' + error.message, 'error');
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
            showMessage('角色移除成功', 'success');
            // 重新加载用户角色
            loadUserRoles(userId);
        } else {
            throw new Error(result.detail || '移除角色失败');
        }
    } catch (error) {
        console.error('移除用户角色失败:', error);
        showMessage('移除用户角色失败: ' + error.message, 'error');
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