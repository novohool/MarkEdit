# 片假字日语词典

这是一个包含中文和日语片假字读音意思对比的词典，内容涵盖日常用语句式、典故、音律、诗歌、风景名胜、文化古迹、音乐与动漫等丰富信息，并制作成EPUB电子书格式。

## 项目结构

请查看 [project_structure.md](project_structure.md) 了解完整的项目目录结构。

## 内容章节

1. 片假字基础知识
2. 片假字读音与意思对比
3. 日常用语句式
4. 典故与历史
5. 文化古迹
6. 风景名胜
7. 音律与诗歌
8. 音乐与动漫中的片假字
9. 片假字的未来发展与学习建议

## 构建EPUB电子书

### 使用Node.js脚本构建（推荐）

```bash
npm run build
```
### 直接使用pandoc命令构建

```bash
pandoc src/metadata.yml src/book.md src/chapters/01-introduction.md src/chapters/02-katakana-basics.md src/chapters/03-readings-and-meanings.md src/chapters/04-daily-expressions.md src/chapters/05-classical-stories.md src/chapters/07-scenic-spots.md src/chapters/06-poetry-and-rhythm.md src/chapters/08-cultural-heritage.md src/chapters/09-music-and-anime.md -o build/katakana-dictionary.epub --toc --toc-depth=2 --split-level=2 --css=src/css/style.css
```

## 许可证

MIT