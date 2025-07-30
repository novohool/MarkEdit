# 片假字日语词典项目结构

## 项目目录结构

```
katakana-dictionary/
├── README.md
├── SUMMARY.md
├── package.json
├── build-epub.js              # Node.js构建脚本
├── build-pdf.js               # Node.js PDF构建脚本
├── src/
│   ├── book.md                # 书籍主文件
│   ├── metadata.yml           # 元数据文件
│   ├── chapters/
│   │   ├── 01-introduction.md
│   │   ├── 02-katakana-basics.md
│   │   ├── 03-readings-and-meanings.md
│   │   ├── 04-daily-expressions.md
│   │   ├── 05-classical-stories.md
│   │   ├── 06-poetry-and-rhythm.md
│   │   ├── 07-scenic-spots.md
│   │   ├── 08-cultural-heritage.md
│   │   └── 09-music-and-anime.md
│   ├── assets/
│   │   └── images/
│   │       └── cover-description.txt  # 封面描述文件
│   ├── css/
│   │   ├── common-style.css   # 通用样式文件，支持木质主题和夜间模式
│   │   ├── pdf-style.css      # PDF样式文件
│   │   └── style.css          # EPUB样式文件
│   └── templates/
│       └── chapter-template.md
└── build/
    └── katakana-dictionary.epub      # 生成的EPUB文件
```

## 文件说明

- `README.md`: 项目说明文档
- `SUMMARY.md`: 项目总结文档
- `package.json`: Node.js项目配置文件
- `build-epub.js`: Node.js构建脚本
- `build-epub.go`: Go语言构建脚本
- `src/book.md`: 书籍主文件，包含书籍标题和简介
- `src/metadata.yml`: 元数据文件，包含书籍的元信息
- `src/chapters/`: 各章节内容
- `src/chapters/01-introduction.md`: 片假字基础知识
- `src/chapters/02-katakana-basics.md`: 片假字读音与意思对比
- `src/chapters/03-readings-and-meanings.md`: 日常用语句式
- `src/chapters/04-daily-expressions.md`: 典故与历史
- `src/chapters/05-classical-stories.md`: 音律与诗歌
- `src/chapters/06-poetry-and-rhythm.md`: 风景名胜
- `src/chapters/07-scenic-spots.md`: 风景名胜
- `src/chapters/08-cultural-heritage.md`: 片假字的未来发展与学习建议
- `src/chapters/09-music-and-anime.md`: 音乐与动漫中的片假字
- `src/assets/images/`: 图像资源文件
- `src/css/common-style.css`: 通用样式文件，支持木质主题和夜间模式
- `src/css/pdf-style.css`: PDF样式文件
- `src/css/style.css`: EPUB样式文件
- `src/templates/`: 模板文件
- `build/katakana-dictionary.epub`: 最终生成的EPUB文件

## 构建方式

1. **Node.js方式**: `npm run build` 或 `node build-epub.js`
2. **直接使用pandoc**: 通过命令行直接运行pandoc命令