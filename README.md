# MarkEdit Web Editor

一个基于FastAPI的Web图形化编辑器，用于编辑src目录下的所有类型内容。

## 功能特性

- 图形化文件浏览器
- 支持多种文件格式的查看和编辑：
  - 文本文件（.md, .yml, .css, .html, .js, .json等）
  - 图片文件（.png, .jpg, .jpeg, .gif, .svg等）
  - 二进制文件（显示为不可编辑的提示）
- 创建新文件
- 保存文件修改
- 删除文件

## 安装和运行

1. 克隆项目到本地：
   ```
   git clone <repository-url>
   cd MarkEdit
   ```

2. 创建虚拟环境（推荐）：
   ```
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

3. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

4. 运行应用：
   ```
   python app/main.py
   ```

   或者使用uvicorn：
   ```
   python -m uvicorn app.main:app --reload
   ```

5. 在浏览器中访问：
   ```
   http://localhost:8000
   ```

## 项目结构

```
MarkEdit/
├── app/                 # FastAPI应用
│   └── main.py          # 主应用文件
├── src/                 # 要编辑的源文件目录
├── static/              # 静态资源
│   ├── css/             # CSS样式文件
│   └── js/              # JavaScript文件
├── templates/           # HTML模板
├── requirements.txt     # Python依赖
└── README.md            # 项目说明文件
```

## API接口

- `GET /` - 返回主页面
- `GET /api/files` - 获取文件树结构
- `GET /api/file/{file_path}` - 获取文件内容
- `POST /api/file/{file_path}` - 保存文件内容
- `DELETE /api/file/{file_path}` - 删除文件
- `POST /api/create-file/{file_path}` - 创建新文件

## 技术栈

- 后端：FastAPI
- 前端：HTML, CSS, JavaScript
- 模板引擎：Jinja2

## 开发

要进行开发，可以直接修改`app/main.py`中的FastAPI应用，或者修改`static/js/main.js`中的前端JavaScript代码。

## 许可证

MIT
