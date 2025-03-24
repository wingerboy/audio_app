# 音频处理应用

这是一个基于React和Python的音频处理应用，支持音频文件上传、分析和分割功能。

## 功能特点

- 音频文件上传和处理
- 使用Whisper模型进行语音识别和转录
- 基于时间段分割音频
- 支持多种音频格式(MP3, WAV, OGG等)
- 前端使用React/Next.js构建，具有响应式界面
- 后端API使用Flask构建

## 技术栈

- **前端**: Next.js, React, TailwindCSS
- **后端**: Python, Flask, Whisper, FFmpeg
- **容器化**: Docker, Docker Compose

## 系统要求

- Python 3.10+
- Node.js 18+
- FFmpeg
- Docker & Docker Compose (可选)

## 快速开始

### 使用Docker部署

1. 克隆仓库:
   ```bash
   git clone https://github.com/yourusername/audio_app.git
   cd audio_app
   ```

2. 使用Docker Compose启动服务:
   ```bash
   docker-compose up -d
   ```

3. 访问应用:
   - 前端: http://localhost:3000
   - API: http://localhost:5002/api/status

### 本地开发

#### 后端

1. 安装Python依赖:
   ```bash
   cd api
   pip install -r requirements.txt
   pip install torch torchvision torchaudio
   pip install git+https://github.com/openai/whisper.git
   pip install pydub ffmpeg-python
   ```

2. 启动API服务:
   ```bash
   python app.py
   ```

#### 前端

1. 安装Node.js依赖:
   ```bash
   cd frontend
   npm install
   ```

2. 设置环境变量:
   创建`.env.local`文件:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:5002/api
   ```

3. 启动开发服务器:
   ```bash
   npm run dev
   ```

## 项目结构

```
audio_app/
├── api/               # Flask API代码
├── src/               # 共享Python源代码
│   ├── audio/         # 音频处理模块
│   ├── temp/          # 临时文件管理
│   └── ...
├── frontend/          # Next.js前端应用
├── data/              # 数据存储目录
├── logs/              # 日志文件
├── Dockerfile         # API Docker构建文件
├── docker-compose.yml # Docker Compose配置
└── README.md          # 项目文档
```

## 许可证

MIT 