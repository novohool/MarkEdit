// epub-viewer.html页面的JavaScript代码

var params = URLSearchParams && new URLSearchParams(document.location.search.substring(1));
var originalUrl = params && params.get("url") && decodeURIComponent(params.get("url"));
var currentSectionIndex = (params && params.get("loc")) ? params.get("loc") : undefined;

// 转换API URL为代理URL
var url = originalUrl;
if (url && url.includes('/api/file/build/')) {
    // 提取文件路径部分
    var filePath = url.split('/api/file/build/')[1];
    if (filePath) {
        // 移除查询参数
        filePath = filePath.split('?')[0];
        // 使用代理端点
        url = '/epub-proxy/' + filePath;
    }
}

// 如果URL是相对路径，转换为绝对路径
if (url && !url.startsWith('http') && !url.startsWith('/')) {
    url = '/' + url;
}

console.log("EPUB Viewer - Original URL:", originalUrl);
console.log("EPUB Viewer - Proxy URL:", url);
console.log("EPUB Viewer - Current section:", currentSectionIndex);
console.log("EPUB Viewer - Base URL:", window.location.origin);

// 全局变量
var book, rendition;

if (!url) {
    console.error("No EPUB URL provided");
    document.addEventListener("DOMContentLoaded", function() {
        document.getElementById("viewer").innerHTML = "<div style='text-align: center; padding: 50px; color: #666;'><h3>请提供EPUB文件URL</h3><p>在URL中添加 ?url=your-epub-file-url 参数</p></div>";
    });
} else {
    // 显示加载指示器
    document.addEventListener("DOMContentLoaded", function() {
        document.getElementById("viewer").innerHTML = "<div style='text-align: center; padding: 50px; color: #666;'><h3>正在加载EPUB文件...</h3><p>请稍候</p></div>";
    });
    try {
        // 测试URL是否可访问
        console.log("Testing EPUB URL accessibility...");
        fetch(url, { 
            method: 'HEAD',
            credentials: 'include'
        })
            .then(response => {
                console.log("URL test response:", response.status, response.statusText);
                console.log("Response headers:", Object.fromEntries(response.headers.entries()));
                if (!response.ok) {
                    console.warn(`HTTP ${response.status}: ${response.statusText}`);
                } else {
                    console.log("URL is accessible, Content-Length:", response.headers.get('content-length'));
                }
            })
            .catch(error => {
                console.warn("URL accessibility test failed:", error);
            });
        
        // Load the opf
        book = ePub(url);
        rendition = book.renderTo("viewer", {
            width: "100%",
            height: "100%",
            spread: "always",
            method: "write"
        });

        console.log("Attempting to display EPUB...");
        rendition.display(currentSectionIndex);
        
        // 添加渲染事件监听
        rendition.on("rendered", function(section) {
            console.log("EPUB section rendered:", section);
        });
        
        rendition.on("displayError", function(error) {
            console.error("EPUB display error:", error);
            document.getElementById("viewer").innerHTML = "<div style='text-align: center; padding: 50px; color: red;'><h3>显示EPUB内容失败</h3><p>" + error.message + "</p></div>";
        });
        
        // 设置加载超时
        var loadingTimeout = setTimeout(function() {
            console.warn("EPUB loading timeout");
            document.getElementById("viewer").innerHTML = "<div style='text-align: center; padding: 50px; color: orange;'><h3>加载EPUB文件超时</h3><p>文件可能较大或网络较慢，请稍候...</p><p>URL: " + url + "</p><div style='margin-top: 20px;'><button onclick='location.reload()' style='padding: 10px 20px; background: #3b82f6; color: white; border: none; border-radius: 5px; cursor: pointer;'>重新加载</button></div></div>";
        }, 30000); // 30秒超时
        
        // 添加错误处理
        book.ready.then(function() {
            clearTimeout(loadingTimeout);
            console.log("Book is ready, metadata:", book.package.metadata);
            
            // 清除加载提示
            var viewer = document.getElementById("viewer");
            if (viewer && viewer.innerHTML.includes("正在加载EPUB文件")) {
                viewer.innerHTML = "";
            }
            
            initializeControls();
        }).catch(function(error) {
            clearTimeout(loadingTimeout);
            console.error("Error loading book:", error);
            document.getElementById("viewer").innerHTML = "<div style='text-align: center; padding: 50px; color: red;'><h3>加载EPUB文件失败</h3><p>" + error.message + "</p><p>URL: " + url + "</p><div style='margin-top: 20px; font-size: 14px; color: #666;'><p>可能的原因：</p><ul style='text-align: left; display: inline-block;'><li>文件不存在或无法访问</li><li>文件格式不正确</li><li>网络连接问题</li><li>服务器权限问题</li></ul></div></div>";
        });
        
    } catch (error) {
        console.error("Error initializing EPUB:", error);
        document.addEventListener("DOMContentLoaded", function() {
            document.getElementById("viewer").innerHTML = "<div style='text-align: center; padding: 50px; color: red;'><h3>初始化EPUB阅读器失败</h3><p>" + error.message + "</p></div>";
        });
    }
}

function initializeControls() {
    if (!book || !rendition) return;

    // 导航按钮事件
    var next = document.getElementById("next");
    if (next) {
        next.addEventListener("click", function(e){
            book.package.metadata.direction === "rtl" ? rendition.prev() : rendition.next();
            e.preventDefault();
        }, false);
    }

    var prev = document.getElementById("prev");
    if (prev) {
        prev.addEventListener("click", function(e){
            book.package.metadata.direction === "rtl" ? rendition.next() : rendition.prev();
            e.preventDefault();
        }, false);
    }

    // 键盘事件
    var keyListener = function(e){
        // Left Key
        if ((e.keyCode || e.which) == 37) {
            book.package.metadata.direction === "rtl" ? rendition.next() : rendition.prev();
        }
        // Right Key
        if ((e.keyCode || e.which) == 39) {
            book.package.metadata.direction === "rtl" ? rendition.prev() : rendition.next();
        }
    };

    rendition.on("keyup", keyListener);
    document.addEventListener("keyup", keyListener, false);

    // 渲染事件
    rendition.on("rendered", function(section){
        var current = book.navigation && book.navigation.get(section.href);

        if (current) {
            var $select = document.getElementById("toc");
            if ($select) {
                var $selected = $select.querySelector("option[selected]");
                if ($selected) {
                    $selected.removeAttribute("selected");
                }

                var $options = $select.querySelectorAll("option");
                for (var i = 0; i < $options.length; ++i) {
                    let selected = $options[i].getAttribute("ref") === current.href;
                    if (selected) {
                        $options[i].setAttribute("selected", "");
                    }
                }
            }
        }
    });

    // 位置变化事件
    rendition.on("relocated", function(location){
        console.log("Relocated:", location);

        var nextBtn = book.package.metadata.direction === "rtl" ? document.getElementById("prev") : document.getElementById("next");
        var prevBtn = book.package.metadata.direction === "rtl" ? document.getElementById("next") : document.getElementById("prev");

        if (nextBtn) {
            if (location.atEnd) {
                nextBtn.style.visibility = "hidden";
            } else {
                nextBtn.style.visibility = "visible";
            }
        }

        if (prevBtn) {
            if (location.atStart) {
                prevBtn.style.visibility = "hidden";
            } else {
                prevBtn.style.visibility = "visible";
            }
        }

        // 更新阅读进度
        updateReadingProgress(location);
    });

    // 布局事件
    rendition.on("layout", function(layout) {
        let viewer = document.getElementById("viewer");
        if (viewer) {
            if (layout.spread) {
                viewer.classList.remove('single');
            } else {
                viewer.classList.add('single');
            }
        }
    });

    // 加载目录
    book.loaded.navigation.then(function(toc){
        var $select = document.getElementById("toc");
        if ($select) {
            var docfrag = document.createDocumentFragment();

            toc.forEach(function(chapter) {
                var option = document.createElement("option");
                option.textContent = chapter.label;
                option.setAttribute("ref", chapter.href);
                docfrag.appendChild(option);
            });

            $select.appendChild(docfrag);

            $select.onchange = function(){
                var index = $select.selectedIndex;
                var selectedUrl = $select.options[index].getAttribute("ref");
                if (selectedUrl) {
                    rendition.display(selectedUrl);
                }
                return false;
            };
        }
    }).catch(function(error) {
        console.error("Error loading navigation:", error);
    });

    // 生成位置信息用于精确的进度计算
    setTimeout(function() {
        generateLocations();
    }, 1000); // 延迟1秒生成，确保书籍已完全加载

    // 添加进度条交互功能（点击和拖拽）
    var progressBar = document.querySelector(".progress-bar");
    var progressSlider = document.getElementById("progress-slider");
    
    if (progressBar && progressSlider) {
        var isDragging = false;
        var dragStartX = 0;
        var dragStartProgress = 0;
        
        // 跳转到指定进度的函数
        function jumpToProgress(progressPercent) {
            if (!book || !book.locations || !book.locations.total) {
                console.warn("Locations not ready for progress bar navigation");
                return false;
            }
            
            // 确保百分比在0-1之间
            progressPercent = Math.max(0, Math.min(1, progressPercent));
            
            // 计算目标位置
            var targetLocation = Math.floor(progressPercent * book.locations.total);
            
            // 跳转到目标位置
            var targetCfi = book.locations.cfiFromLocation(targetLocation);
            if (targetCfi) {
                rendition.display(targetCfi);
                console.log("Jumped to progress:", Math.round(progressPercent * 100) + "%");
                return true;
            }
            return false;
        }
        
        // 更新滑块位置
        function updateSliderPosition(progressPercent) {
            progressPercent = Math.max(0, Math.min(1, progressPercent));
            progressSlider.style.left = (progressPercent * 100) + "%";
        }
        
        // 进度条点击事件
        progressBar.addEventListener("click", function(e) {
            if (isDragging) return; // 如果正在拖拽，忽略点击事件
            
            var rect = progressBar.getBoundingClientRect();
            var clickX = e.clientX - rect.left;
            var progressPercent = clickX / rect.width;
            
            if (jumpToProgress(progressPercent)) {
                updateSliderPosition(progressPercent);
            }
        });
        
        // 滑块拖拽开始
        progressSlider.addEventListener("mousedown", function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            isDragging = true;
            dragStartX = e.clientX;
            
            var rect = progressBar.getBoundingClientRect();
            var currentLeft = progressSlider.offsetLeft;
            dragStartProgress = currentLeft / rect.width;
            
            progressBar.classList.add("dragging");
            progressSlider.classList.add("dragging");
            document.body.style.userSelect = "none";
            
            console.log("Started dragging at progress:", Math.round(dragStartProgress * 100) + "%");
        });
        
        // 全局鼠标移动事件（拖拽中）
        document.addEventListener("mousemove", function(e) {
            if (!isDragging) return;
            
            var rect = progressBar.getBoundingClientRect();
            var deltaX = e.clientX - dragStartX;
            var deltaProgress = deltaX / rect.width;
            var newProgress = dragStartProgress + deltaProgress;
            
            // 限制在0-1范围内
            newProgress = Math.max(0, Math.min(1, newProgress));
            
            // 更新滑块位置
            updateSliderPosition(newProgress);
            
            // 实时更新进度显示
            var progressText = document.getElementById("progress-text");
            if (progressText) {
                progressText.textContent = Math.round(newProgress * 100) + "%";
            }
            
            // 实时更新进度条填充
            var progressFill = document.getElementById("reading-progress");
            if (progressFill) {
                progressFill.style.width = (newProgress * 100) + "%";
            }
        });
        
        // 全局鼠标释放事件（拖拽结束）
        document.addEventListener("mouseup", function(e) {
            if (!isDragging) return;
            
            isDragging = false;
            progressBar.classList.remove("dragging");
            progressSlider.classList.remove("dragging");
            document.body.style.userSelect = "";
            
            // 计算最终进度
            var rect = progressBar.getBoundingClientRect();
            var deltaX = e.clientX - dragStartX;
            var deltaProgress = deltaX / rect.width;
            var finalProgress = dragStartProgress + deltaProgress;
            
            // 限制在0-1范围内
            finalProgress = Math.max(0, Math.min(1, finalProgress));
            
            // 跳转到最终位置
            jumpToProgress(finalProgress);
            
            console.log("Finished dragging at progress:", Math.round(finalProgress * 100) + "%");
        });
        
        // 触摸设备支持
        progressSlider.addEventListener("touchstart", function(e) {
            e.preventDefault();
            var touch = e.touches[0];
            var mouseEvent = new MouseEvent("mousedown", {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            progressSlider.dispatchEvent(mouseEvent);
        });
        
        document.addEventListener("touchmove", function(e) {
            if (!isDragging) return;
            e.preventDefault();
            var touch = e.touches[0];
            var mouseEvent = new MouseEvent("mousemove", {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            document.dispatchEvent(mouseEvent);
        });
        
        document.addEventListener("touchend", function(e) {
            if (!isDragging) return;
            e.preventDefault();
            var mouseEvent = new MouseEvent("mouseup", {
                clientX: e.changedTouches[0].clientX,
                clientY: e.changedTouches[0].clientY
            });
            document.dispatchEvent(mouseEvent);
        });
    }

    // 添加字体大小控制功能
    var currentFontSize = 100; // 默认字体大小百分比
    
    var fontIncreaseBtn = document.getElementById("font-size-increase");
    var fontDecreaseBtn = document.getElementById("font-size-decrease");
    
    if (fontIncreaseBtn) {
        fontIncreaseBtn.addEventListener("click", function() {
            currentFontSize = Math.min(200, currentFontSize + 10); // 最大200%
            updateFontSize();
        });
    }
    
    if (fontDecreaseBtn) {
        fontDecreaseBtn.addEventListener("click", function() {
            currentFontSize = Math.max(50, currentFontSize - 10); // 最小50%
            updateFontSize();
        });
    }
    
    function updateFontSize() {
        if (rendition) {
            rendition.themes.fontSize(currentFontSize + "%");
            console.log("Font size updated to:", currentFontSize + "%");
            
            // 更新按钮状态
            if (fontIncreaseBtn) {
                fontIncreaseBtn.disabled = currentFontSize >= 200;
                fontIncreaseBtn.style.opacity = currentFontSize >= 200 ? "0.5" : "1";
                fontIncreaseBtn.title = currentFontSize >= 200 ? "已达到最大字体" : "增大字体 (" + currentFontSize + "%)";
            }
            if (fontDecreaseBtn) {
                fontDecreaseBtn.disabled = currentFontSize <= 50;
                fontDecreaseBtn.style.opacity = currentFontSize <= 50 ? "0.5" : "1";
                fontDecreaseBtn.title = currentFontSize <= 50 ? "已达到最小字体" : "减小字体 (" + currentFontSize + "%)";
            }
        }
    }
    
    // 初始化字体大小按钮状态
    updateFontSize();
}

// 更新阅读进度的函数
function updateReadingProgress(location) {
    if (!location || !book) return;
    
    try {
        // 计算进度百分比
        var progress = 0;
        
        if (location.start && location.end && book.locations && book.locations.total) {
            // 使用位置信息计算进度
            var currentLocation = location.start.location || location.start.cfi;
            if (currentLocation && book.locations.locationFromCfi) {
                var locationNumber = book.locations.locationFromCfi(currentLocation);
                progress = (locationNumber / book.locations.total) * 100;
            }
        } else if (location.start && location.end) {
            // 使用CFI计算大概进度
            var startCfi = location.start.cfi;
            var endCfi = location.end.cfi;
            
            // 简单的进度估算（基于章节）
            if (book.spine && book.spine.items) {
                var currentSpineIndex = -1;
                for (var i = 0; i < book.spine.items.length; i++) {
                    if (startCfi.includes(book.spine.items[i].idref)) {
                        currentSpineIndex = i;
                        break;
                    }
                }
                
                if (currentSpineIndex >= 0) {
                    progress = ((currentSpineIndex + 1) / book.spine.items.length) * 100;
                }
            }
        }
        
        // 确保进度在0-100之间
        progress = Math.max(0, Math.min(100, progress));
        
        // 更新进度条
        var progressFill = document.getElementById("reading-progress");
        var progressText = document.getElementById("progress-text");
        var progressSlider = document.getElementById("progress-slider");
        
        if (progressFill) {
            progressFill.style.width = progress + "%";
        }
        
        if (progressText) {
            progressText.textContent = Math.round(progress) + "%";
        }
        
        // 更新滑块位置（只在非拖拽状态下更新）
        if (progressSlider && !progressSlider.classList.contains("dragging")) {
            progressSlider.style.left = progress + "%";
        }
        
        console.log("Reading progress updated:", Math.round(progress) + "%");
        
    } catch (error) {
        console.warn("Error updating reading progress:", error);
    }
}

// 初始化位置生成（用于更精确的进度计算）
function generateLocations() {
    if (!book) return;
    
    book.locations.generate(1024).then(function() {
        console.log("Locations generated, total:", book.locations.total);
        // 重新计算当前进度
        if (rendition && rendition.location) {
            updateReadingProgress(rendition.location);
        }
    }).catch(function(error) {
        console.warn("Error generating locations:", error);
    });
}

// 使用pagehide事件替代unload事件，避免权限策略违规
window.addEventListener("pagehide", function () {
    console.log("page hiding");
    if (window.book) {
        window.book.destroy();
    }
});