FROM ubuntu:latest
ENV PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]

WORKDIR /app
COPY . .

RUN apt-get update && \
    apt-get install -y python3.12 python3.12-venv python3-pip python3-dev pandoc wkhtmltopdf build-essential libssl-dev libffi-dev && \
    python3.12 -m venv workspace  && \
    source workspace/bin/activate && \
    pip3 install --upgrade pip setuptools  && \
    pip3 install --no-cache-dir -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

# 暴露端口
EXPOSE 8080

# 运行应用
CMD ["python", "app/main.py"]