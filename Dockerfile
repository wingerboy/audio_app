FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 创建 sources.list 文件并配置阿里云镜像
RUN echo "deb http://mirrors.aliyun.com/debian/ bullseye main non-free contrib" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security/ bullseye-security main" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bullseye-updates main non-free contrib" >> /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsndfile1 \
    default-libmysqlclient-dev \
    pkg-config \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install torch torchvision torchaudio --index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip install git+https://github.com/openai/whisper.git -i https://mirrors.aliyun.com/pypi/simple/ \
    && pip install pydub ffmpeg-python -i https://mirrors.aliyun.com/pypi/simple/

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p logs data/tasks

# 设置环境变量
ENV PORT=5002 \
    PYTHONPATH=/app:$PYTHONPATH

# 暴露端口
EXPOSE 5002

# 启动命令
CMD ["python", "api/app.py"] 