# MarkEdit Web Editor

一个基于FastAPI的Web图形化编辑器，用于编辑src目录下的所有类型内容，用来生成电子书。

## 功能特性

- 图形化文件浏览器
- 支持多种文件格式的查看和编辑：
  - 文本文件（.md, .yml, .css, .html, .js, .json等）
  - 图片文件（.png, .jpg, .jpeg, .gif, .svg等）
  - 二进制文件（显示为不可编辑的提示）
- 创建新文件
- 保存文件修改
- 删除文件
- GitHub认证登录（可选）

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

4. 配置环境变量（如果需要使用GitHub认证功能）：
   ```
   # GitHub OAuth应用配置
   export GITHUB_APP_CLIENT_ID=your_github_app_client_id
   export GITHUB_APP_CLIENT_SECRET=your_github_app_client_secret
   export GITHUB_APP_REDIRECT_URI=http://localhost:8080/callback
   ```

   Windows系统使用以下命令：
   ```
   set GITHUB_APP_CLIENT_ID=your_github_app_client_id
   set GITHUB_APP_CLIENT_SECRET=your_github_app_client_secret
   set GITHUB_APP_REDIRECT_URI=http://localhost:8080/callback
   ```

5. 运行应用：
   ```
   python app/main.py
   ```

   或者使用uvicorn：
   ```
   python -m uvicorn app.main:app --reload
   ```

6. 在浏览器中访问：
   ```
   http://localhost:8080
   ```

## 使用 Docker 运行

1. 构建 Docker 镜像：
   ```
   docker build -t markeditor .
   ```

2. 运行容器（如果需要使用GitHub认证功能，需要设置环境变量）：
   ```
   docker run -p 8080:8080 \
     -e GITHUB_APP_CLIENT_ID=your_github_app_client_id \
     -e GITHUB_APP_CLIENT_SECRET=your_github_app_client_secret \
     -e GITHUB_APP_REDIRECT_URI=http://localhost:8080/callback \
     -v $(pwd)/src:/app/src markeditor
   ```

3. 在浏览器中访问：
   ```
   http://localhost:8080
   ```

注意：使用 `-v` 参数将本地的 src 目录挂载到容器中，以确保文件修改持久化保存在本地。

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

## 管理员密码重置

如果忘记了管理员密码，可以使用以下工具重置默认管理员账户(markedit)的密码：

```
python app/reset_admin_password.py
```

运行此工具将生成一个新的强密码并更新数据库中的管理员账户。工具会显示新生成的明文密码，请妥善保管并立即使用新密码登录系统。

## 许可证

MIT

## GitHub认证

本应用支持使用GitHub账户进行认证登录。要启用此功能，需要先在GitHub上创建一个OAuth应用，然后配置相应的环境变量。

### 创建GitHub OAuth应用

1. 登录GitHub账户，访问 [GitHub Developer Settings](https://github.com/settings/developers)
2. 点击 "OAuth Apps"，然后点击 "New OAuth App"
3. 填写应用信息：
   - Application name: MarkEdit Web Editor
   - Homepage URL: http://localhost:8080
   - Authorization callback URL: http://localhost:8080/callback
4. 点击 "Register application"
5. 创建完成后，点击应用名称进入详情页面，记录下 "Client ID" 和 "Client Secret"

### 配置环境变量

需要设置以下三个环境变量：

- `GITHUB_APP_CLIENT_ID`: GitHub OAuth应用的Client ID
- `GITHUB_APP_CLIENT_SECRET`: GitHub OAuth应用的Client Secret
- `GITHUB_APP_REDIRECT_URI`: 回调URL，必须与GitHub应用配置中的Authorization callback URL一致

### 使用GitHub认证

配置好环境变量后，启动应用时会自动启用GitHub认证功能。用户访问应用时会被重定向到登录页面，点击"使用GitHub登录"按钮即可进行认证。

认证成功后，用户可以正常访问应用的所有功能。点击页面右上角的"退出登录"可以注销当前会话。
