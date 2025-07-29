const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// 配置目录
const srcDir = 'src';
const chaptersDir = path.join(srcDir, 'chapters');
const buildDir = 'build';
const metadataFile = path.join(srcDir, 'metadata.yml');
const bookFile = path.join(srcDir, 'book.md');
const cssFile = path.join(srcDir, 'css', 'style.css');

// 创建输出目录（如果不存在）
if (!fs.existsSync(buildDir)) {
    fs.mkdirSync(buildDir, { recursive: true });
}

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

// 构建pandoc命令参数
const inputFiles = [metadataFile, bookFile, ...chapterFiles.map(file => path.join(chaptersDir, file))];
const outputFilePath = path.join(buildDir, 'katakana-dictionary.epub');
const pandocArgs = [
    ...inputFiles,
    '-o', outputFilePath,
    '--toc',
    '--toc-depth=2',
    '--split-level=2',
    `--css=${cssFile}`
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
}