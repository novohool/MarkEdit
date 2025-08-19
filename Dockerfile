FROM ubuntu:latest
ENV PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]

WORKDIR /app
COPY . .

RUN apt-get update && \
    apt-get install -y python3.12 python3.12-venv python3-pip python3-dev pandoc wkhtmltopdf build-essential \
    libssl-dev libffi-dev  fonts-wqy-zenhei fonts-wqy-microhei xfonts-wqy  && \
    fc-cache -f -v && \
    python3.12 -m venv workspace  && \
    echo ". workspace/bin/activate" >> ~/.bashrc && \
    source workspace/bin/activate && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    pip3 install --upgrade pip setuptools  && \
    pip3 install --no-cache-dir -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

# 暴露端口
EXPOSE 8080

# 运行应用
CMD ["/app/workspace/bin/python", "app/main.py"]