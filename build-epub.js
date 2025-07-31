const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// 配置目录
const srcDir = 'src';
const chaptersDir = path.join(srcDir, 'chapters');
const illustrationsDir = path.join(srcDir, 'illustrations');
const buildDir = 'build';
const metadataFile = path.join(srcDir, 'metadata.yml');
const bookFile = path.join(srcDir, 'book.md');
const cssFile = path.join(srcDir, 'css', 'common-style.css');

// 创建输出目录（如果不存在）
if (!fs.existsSync(buildDir)) {
    fs.mkdirSync(buildDir, { recursive: true });
}

// 复制插图目录到构建目录
const buildIllustrationsDir = path.join(buildDir, 'illustrations');
if (!fs.existsSync(buildIllustrationsDir)) {
    fs.mkdirSync(buildIllustrationsDir, { recursive: true });
}

// 复制所有SVG插图到构建目录
const illustrationFiles = fs.readdirSync(illustrationsDir);
illustrationFiles.forEach(file => {
    if (path.extname(file) === '.svg') {
        const srcPath = path.join(illustrationsDir, file);
        const destPath = path.join(buildIllustrationsDir, file);
        fs.copyFileSync(srcPath, destPath);
        console.log(`已复制插图文件: ${file}`);
    }
});

// 优化SVG文件以提高epub兼容性
const optimizeSvgForEpub = (svgContent) => {
    // 移除可能引起问题的特性
    let optimizedContent = svgContent;
    
    // 确保xmlns属性正确
    if (!optimizedContent.includes('xmlns="http://www.w3.org/2000/svg"')) {
        optimizedContent = optimizedContent.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"');
    }
    
    // 移除可能不被epub支持的特性
    optimizedContent = optimizedContent.replace(/<\?xml.*?\?>/g, '');
    
    // 确保SVG有明确的宽度和高度
    if (!optimizedContent.match(/width="\d+"/) || !optimizedContent.match(/height="\d+"/)) {
        // 如果没有明确的宽度和高度，添加默认值
        optimizedContent = optimizedContent.replace(/<svg([^>]*?)(?<!width="[^"]*")>/, '<svg$1 width="400" height="300">');
    }
    
    // 移除元素上的opacity属性，因为可能不被epub支持
    console.log('优化前的SVG内容:', optimizedContent.substring(0, 300) + '...');
    // 检查是否包含opacity属性
    if (optimizedContent.includes('opacity')) {
        console.log('发现opacity属性，正在移除...');
        // 使用更精确的正则表达式移除opacity属性
        // 匹配所有形式的opacity属性，包括opacity="0.3"和opacity="0.7"
        optimizedContent = optimizedContent.replace(/\s+opacity\s*=\s*"[^"]*"/g, '');
        // 也匹配没有前导空格的opacity属性
        optimizedContent = optimizedContent.replace(/opacity\s*=\s*"[^"]*"/g, '');
        console.log('移除opacity属性后的SVG内容:', optimizedContent.substring(0, 300) + '...');
    }
    
    // 移除style标签中的opacity属性
    optimizedContent = optimizedContent.replace(/<style[^>]*>[\s\S]*?<\/style>/g, (match) => {
        // 移除opacity样式
        return match.replace(/opacity\s*:\s*[^;]+;?/g, '');
    });
    
    return optimizedContent;
};

// 优化所有SVG文件
illustrationFiles.forEach(file => {
    if (path.extname(file) === '.svg') {
        const svgPath = path.join(buildIllustrationsDir, file);
        const svgContent = fs.readFileSync(svgPath, 'utf8');
        const optimizedSvgContent = optimizeSvgForEpub(svgContent);
        fs.writeFileSync(svgPath, optimizedSvgContent, 'utf8');
        console.log(`已优化SVG文件: ${file}`);
    }
});


// 按照优化顺序排列章节
const chapterFiles = [
    '01-introduction.md',
    '02-katakana-basics.md',
    '03-readings-and-meanings.md',
    '04-daily-expressions.md',
    '05-classical-stories.md',
    '07-scenic-spots.md',
    '06-poetry-and-rhythm.md',
    '08-cultural-heritage.md',
    '09-music-and-anime.md'
];

// 为EPUB创建临时章节目录
const tempChaptersDir = path.join(buildDir, 'temp-chapters');
if (!fs.existsSync(tempChaptersDir)) {
    fs.mkdirSync(tempChaptersDir, { recursive: true });
}

// 复制并修改章节文件，调整图片路径
chapterFiles.forEach(file => {
    const srcPath = path.join(chaptersDir, file);
    const destPath = path.join(tempChaptersDir, file);
    
    // 读取原始章节文件
    let content = fs.readFileSync(srcPath, 'utf8');
    
    // 修改图片路径，将 "../illustrations/" 替换为 "illustrations/"
    content = content.replace(/\.\.\/illustrations\//g, 'illustrations/');
    
    // 写入修改后的章节文件到临时目录
    fs.writeFileSync(destPath, content, 'utf8');
    console.log(`已处理章节文件: ${file}`);
});

// 构建pandoc命令参数
const inputFiles = [metadataFile, bookFile, ...chapterFiles.map(file => path.join(tempChaptersDir, file))];
const outputFilePath = path.join(buildDir, 'katakana-dictionary.epub');
const pandocArgs = [
    ...inputFiles,
    '-o', outputFilePath,
    '--toc',
    '--toc-depth=2',
    '--split-level=2',
    `--css=${cssFile}`,
    '--from', 'markdown',
    '--html-q-tags',
    '--embed-resources',
    `--resource-path=${buildDir}`
];

// 构建完整的pandoc命令
const command = `pandoc ${pandocArgs.join(' ')}`;

console.log('正在执行命令:', command);

try {
    // 执行pandoc命令
    execSync(command, { stdio: 'inherit' });
    console.log('EPUB文件生成成功:', outputFilePath);
} catch (error) {
    console.error('生成EPUB文件时出错:', error.message);
    process.exit(1);
} finally {
    // 清理临时目录
    if (fs.existsSync(tempChaptersDir)) {
        fs.rmSync(tempChaptersDir, { recursive: true });
        console.log('已清理临时目录');
    }
}