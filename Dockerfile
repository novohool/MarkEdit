# 使用官方 Python 运行时作为基础镜像
FROM python:slim

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 8000

# 运行应用
CMD ["python", "app/main.py"]