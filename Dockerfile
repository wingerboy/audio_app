FROM python:3.10-slim-buster

# 设置工作目录
WORKDIR /app

# 替换为阿里云镜像源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.aliyun.com\/debian-security/g' /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY api/requirements.txt .
COPY api/app.py .
COPY environment_manager.py .

# 创建和设置Python环境
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install torch torchvision torchaudio --index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip install git+https://github.com/openai/whisper.git -i https://mirrors.aliyun.com/pypi/simple/ \
    && pip install pydub ffmpeg-python -i https://mirrors.aliyun.com/pypi/simple/

# 添加应用代码
COPY src/ ./src/
COPY logging_config.py .

# 创建必要的目录
RUN mkdir -p logs data/tasks

# 设置环境变量
ENV PORT=5002 \
    PYTHONPATH=/app:$PYTHONPATH \
    PYTHONUNBUFFERED=1

# 暴露API端口
EXPOSE 5002

# 运行应用
CMD ["python", "app.py"] 