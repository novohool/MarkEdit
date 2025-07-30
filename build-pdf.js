const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// 配置目录
const srcDir = 'src';
const chaptersDir = path.join(srcDir, 'chapters');
const buildDir = 'build';
const metadataFile = path.join(srcDir, 'metadata.yml');
const bookFile = path.join(srcDir, 'book.md');
const cssFile = path.join(srcDir, 'css', 'common-style.css');

// wkhtmltopdf路径配置
const wkhtmltopdfPath = process.env.WKHTMLTOPDF_PATH || `"wkhtmltopdf"`;

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

// 构建pandoc命令参数，先生成HTML
const inputFiles = [metadataFile, bookFile, ...chapterFiles.map(file => path.join(chaptersDir, file))];
const htmlOutputPath = path.join(buildDir, 'katakana-dictionary.html');
const pdfOutputPath = path.join(buildDir, 'katakana-dictionary.pdf');

console.log('开始生成PDF文件...');

// 先使用pandoc生成HTML文件
const pandocArgs = [
    ...inputFiles,
    '-o', htmlOutputPath,
    '--toc',
    '--toc-depth=2',
    '--split-level=2',
    `--css=${cssFile}`,
    '--standalone',
    '--embed-resources'
];

// 构建完整的pandoc命令
const pandocCommand = `pandoc ${pandocArgs.join(' ')}`;

console.log('正在执行命令生成HTML:', pandocCommand);

try {
    // 执行pandoc命令生成HTML
    execSync(pandocCommand, { stdio: 'inherit' });
    console.log('HTML文件生成成功:', htmlOutputPath);
    
    // 使用wkhtmltopdf将HTML转换为PDF
    const wkhtmltopdfCommand = `${wkhtmltopdfPath} --enable-local-file-access --print-media-type --margin-top 20mm --margin-bottom 20mm --margin-left 15mm --margin-right 15mm "${htmlOutputPath}" "${pdfOutputPath}"`;
    
    console.log('正在执行命令生成PDF:', wkhtmltopdfCommand);
    
    // 执行wkhtmltopdf命令生成PDF
    execSync(wkhtmltopdfCommand, { stdio: 'inherit' });
    console.log('PDF文件生成成功:', pdfOutputPath);
    
    // 可选：删除临时HTML文件
    // fs.unlinkSync(htmlOutputPath);
    // console.log('临时HTML文件已删除');
} catch (error) {
    console.error('生成PDF文件时出错:', error.message);
    process.exit(1);
}

console.log('PDF生成完成！');