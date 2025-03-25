# 音频处理应用

一个基于 Flask 和 Next.js 的音频处理应用，支持音频转写、分割等功能。

## 功能特点

- 音频文件上传和处理
- 音频转写（使用 Whisper）
- 音频分割
- 用户认证和授权
- 余额管理和计费系统
- 响应式前端界面

## 技术栈

### 后端
- Python 3.9
- Flask
- SQLAlchemy
- MySQL
- Whisper
- FFmpeg

### 前端
- Next.js
- TypeScript
- Tailwind CSS
- React Query

## 系统要求

- Docker
- Docker Compose
- 至少 4GB RAM
- 支持 CUDA 的 GPU（可选，用于加速转写）

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/audio_app.git
cd audio_app
```

### 2. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑环境变量文件
vim .env
```

### 3. 启动服务

```bash
# 构建并启动所有服务
docker-compose up --build
```

服务将在以下地址运行：
- 前端: http://localhost:3000
- API: http://localhost:5002

## 数据管理

### Docker Volume 说明

应用使用 Docker volume 来持久化数据：
- `mysql_data`: 存储 MySQL 数据库数据
- `audio_data`: 存储上传的音频文件

### 数据备份和恢复

#### 备份数据

```bash
# 备份 MySQL 数据
docker run --rm -v audio_app_mysql_data:/source -v $(pwd):/backup alpine tar czf /backup/mysql_backup.tar.gz -C /source .

# 备份音频数据
docker run --rm -v audio_app_audio_data:/source -v $(pwd):/backup alpine tar czf /backup/audio_backup.tar.gz -C /source .
```

#### 恢复数据

```bash
# 恢复 MySQL 数据
docker volume create audio_app_mysql_data
docker run --rm -v audio_app_mysql_data:/target -v $(pwd):/backup alpine sh -c "cd /target && tar xzf /backup/mysql_backup.tar.gz"

# 恢复音频数据
docker volume create audio_app_audio_data
docker run --rm -v audio_app_audio_data:/target -v $(pwd):/backup alpine sh -c "cd /target && tar xzf /backup/audio_backup.tar.gz"
```

### 服务迁移

1. 在原服务器上备份数据：
```bash
# 备份所有数据
docker run --rm -v audio_app_mysql_data:/source -v $(pwd):/backup alpine tar czf /backup/mysql_backup.tar.gz -C /source .
docker run --rm -v audio_app_audio_data:/source -v $(pwd):/backup alpine tar czf /backup/audio_backup.tar.gz -C /source .
```

2. 将备份文件传输到新服务器：
```bash
scp mysql_backup.tar.gz audio_backup.tar.gz user@new-server:/path/to/backup/
```

3. 在新服务器上恢复数据：
```bash
# 恢复所有数据
docker volume create audio_app_mysql_data
docker volume create audio_app_audio_data
docker run --rm -v audio_app_mysql_data:/target -v $(pwd):/backup alpine sh -c "cd /target && tar xzf /backup/mysql_backup.tar.gz"
docker run --rm -v audio_app_audio_data:/target -v $(pwd):/backup alpine sh -c "cd /target && tar xzf /backup/audio_backup.tar.gz"
```

4. 启动服务：
```bash
docker-compose up -d
```

### 数据清理

```bash
# 停止所有服务
docker-compose down

# 删除所有数据（谨慎使用！）
docker volume rm audio_app_mysql_data audio_app_audio_data
```

## 开发指南

### 目录结构

```
.
├── api/                    # API 服务
│   ├── routes/            # API 路由
│   └── app.py             # 主应用文件
├── frontend/              # 前端应用
│   ├── src/              # 源代码
│   └── public/           # 静态资源
├── src/                   # 后端源代码
│   ├── balance_system/   # 余额系统
│   ├── user_system/      # 用户系统
│   └── audio_processor/  # 音频处理
├── data/                  # 数据目录
├── logs/                  # 日志目录
├── docker-compose.yml     # Docker 编排配置
├── Dockerfile            # API 服务 Dockerfile
└── requirements.txt      # Python 依赖
```

### 本地开发

1. 启动开发环境：
```bash
docker-compose -f docker-compose.dev.yml up --build
```

2. 访问开发服务器：
- 前端: http://localhost:3000
- API: http://localhost:5002

### 调试

```bash
# 查看日志
docker-compose logs -f

# 进入容器
docker-compose exec api bash
docker-compose exec frontend sh

# 检查数据库
docker-compose exec db mysql -u audioapp -p
```

## 部署指南

### 生产环境部署

1. 准备服务器：
```bash
# 安装 Docker 和 Docker Compose
curl -fsSL https://get.docker.com | sh
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2. 克隆代码：
```bash
git clone https://github.com/yourusername/audio_app.git
cd audio_app
```

3. 配置环境：
```bash
cp .env.example .env
vim .env  # 编辑环境变量
```

4. 启动服务：
```bash
docker-compose up -d
```

### 监控和维护

```bash
# 查看服务状态
docker-compose ps

# 查看资源使用情况
docker stats

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart
```

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件 