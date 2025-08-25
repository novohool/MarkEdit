// Wooden 主题 JavaScript
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

// 所有主要业务逻辑函数已移至 /static/common/js/main-shared.js
// 包括: loadFile, togglePreview, previewBuildFile, bindEventListeners, deleteFile, highlightCodeInEditor 等

// Wooden主题特有的初始化和自定义函数可以在这里添加
// 其他所有函数都已移至共享模块
