#!/bin/bash
set -e

echo "=========================="
echo "音频处理应用一键部署脚本"
echo "适用于容器环境: gpufree-container"
echo "=========================="

# 确保工作目录正确
cd "$(dirname "$0")"
PROJECT_ROOT=$(pwd)

echo "安装系统依赖..."
apt-get update || { echo "请使用 sudo 运行此脚本"; exit 1; }
apt-get install -y python3 python3-pip python3-venv mysql-server libmysqlclient-dev \
    nodejs npm curl wget git ffmpeg libsndfile1 build-essential

# 升级npm和node
echo "升级Node.js和npm..."
npm install -g n
n stable
PATH="$PATH"  # 刷新PATH以使用新版node

# 启动MySQL服务
echo "配置MySQL服务..."
service mysql start || systemctl start mysql || echo "MySQL可能已经运行"
sleep 2

# 执行MySQL初始化脚本
echo "执行MySQL初始化脚本..."
if [ -f "$PROJECT_ROOT/mysql/init.sql" ]; then
    mysql -u root < "$PROJECT_ROOT/mysql/init.sql"
    echo "MySQL初始化脚本执行完成"
else
    echo "MySQL初始化脚本不存在，跳过执行"
    
    # 创建数据库和用户 (仅在没有初始化脚本时执行)
    echo "创建数据库和用户..."
    mysql -e "CREATE DATABASE IF NOT EXISTS audio_app;"
    mysql -e "CREATE USER IF NOT EXISTS 'audio_app'@'localhost' IDENTIFIED BY 'password';"
    mysql -e "GRANT ALL PRIVILEGES ON audio_app.* TO 'audio_app'@'localhost';"
    mysql -e "FLUSH PRIVILEGES;"
fi

# 设置Python环境
echo "设置Python环境..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 设置环境变量
echo "配置环境变量..."
if [ ! -f .env ]; then
  cp .env.example .env
  # 生成随机密钥
  SECRET_KEY=$(openssl rand -hex 32)
  JWT_SECRET_KEY=$(openssl rand -hex 32)
  # 更新环境变量
  sed -i "s/your-secret-key/$SECRET_KEY/g" .env
  sed -i "s/your-jwt-secret-key/$JWT_SECRET_KEY/g" .env
  # 根据init.sql中的用户名和密码更新数据库URL
  sed -i "s|DATABASE_URL=.*|DATABASE_URL=mysql://audio_app_user:yawen_12@localhost:3306/audio_app|g" .env
  echo "已创建并配置.env文件"
else
  echo ".env文件已存在，跳过配置"
fi

# 确保数据目录存在
echo "创建必要的数据目录..."
mkdir -p data/uploads data/tasks data/users logs

# 初始化数据库 (如果需要)
# 根据具体项目结构可能需要调整
echo "初始化数据库..."
source venv/bin/activate
python -c "from src.balance_system.db import init_db; init_db()"

# 安装前端依赖
echo "设置前端环境..."
cd $PROJECT_ROOT/frontend
npm install

# 确保前端环境变量配置
echo "NEXT_PUBLIC_API_URL=http://localhost:5002/api" > .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:5002/api" > .env.development

# 构建前端
echo "构建前端..."
npm run build

# 创建启动脚本
echo "创建启动脚本..."
cd $PROJECT_ROOT
cat > start.sh << 'EOF'
#!/bin/bash
set -e

# 启动MySQL (如果需要)
service mysql start || systemctl start mysql || echo "MySQL可能已经运行"

# 启动API服务
cd "$(dirname "$0")"
source venv/bin/activate

# 确保日志目录存在
mkdir -p logs

# 启动API服务
nohup python api/app.py > logs/api.log 2>&1 &
API_PID=$!
echo "API服务已启动 (PID: $API_PID)"
echo "API服务地址: http://localhost:5002/api"

# 等待API服务启动
echo "等待API服务启动..."
sleep 5

# 启动前端服务
cd frontend
nohup npm start > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "前端服务已启动 (PID: $FRONTEND_PID)"
echo "前端访问地址: http://localhost:3000"

echo "所有服务已启动"
echo "API日志: $(dirname "$0")/logs/api.log"
echo "前端日志: $(dirname "$0")/logs/frontend.log"
EOF

chmod +x start.sh

# 创建停止脚本
cat > stop.sh << 'EOF'
#!/bin/bash
pkill -f "python api/app.py" || echo "API服务未运行"
pkill -f "npm start" || echo "前端服务未运行"
echo "所有服务已停止"
EOF

chmod +x stop.sh

echo "=========================="
echo "部署完成!"
echo "运行 ./start.sh 启动所有服务"
echo "运行 ./stop.sh 停止所有服务"
echo "=========================="

# 询问是否立即启动服务
read -p "是否立即启动服务? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ./start.sh
fi 