// Default主题特有的函数和变量
// 全局变量和通用函数已移至 /static/common/js/common.js
// 用户面板相关函数已移至 /static/common/js/common.js
// 主要业务逻辑函数已移至 /static/common/js/main-shared.js

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化编辑器状态
    initializeEditor();
    
    // 初始化CodeMirror编辑器
    initializeCodeMirror();
    
    // 加载文件树
    loadFileTree();
        
    // 绑定事件监听器（只绑定一次）
    bindEventListeners();
});

// 由于主题切换功能已移至公共库，这里不再重复定义

// findChaptersDirectory, reorderChapters, renderFileTree 函数已移至公共库

// 所有主要业务逻辑函数已移至 /static/common/js/main-shared.js
// 包括: loadFile, saveFile, togglePreview, previewBuildFile, highlightCodeInEditor, bindEventListeners 等

// Default主题特定的初始化和自定义函数可以在这里添加
// 其他所有函数都已移至共享模块
