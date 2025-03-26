#!/bin/bash
set -e

echo "=========================="
echo "音频处理应用一键部署脚本"
echo "适用于容器环境: gpufree-container"
echo "=========================="

# 确保工作目录正确
cd "$(dirname "$0")"
PROJECT_ROOT=$(pwd)

echo "更新软件源..."
apt-get update || { echo "更新软件源失败，但将继续执行"; }

# 尝试修复可能的依赖问题
echo "尝试修复可能的依赖问题..."
apt-get -f install -y || true

echo "安装系统依赖..."
# 分开安装依赖，以避免全部失败
for pkg in mysql-server libmysqlclient-dev nodejs npm ffmpeg libsndfile1; do
    echo "正在安装 $pkg..."
    apt-get install -y $pkg || echo "安装 $pkg 失败，但将继续执行"
done

echo "检查Python环境..."
# 检查Python3是否已安装
if ! command -v python3 &> /dev/null; then
    echo "尝试安装Python3..."
    apt-get install -y python3 || echo "安装Python3失败，请手动安装"
fi

# 检查pip是否已安装
if ! command -v pip3 &> /dev/null; then
    echo "尝试安装pip3..."
    apt-get install -y python3-pip || echo "安装pip3失败，请手动安装"
fi

# 创建虚拟环境，不依赖于python3-venv包
echo "尝试设置Python虚拟环境..."
if ! [ -d "venv" ]; then
    if command -v python3 &> /dev/null; then
        # 尝试直接使用Python的venv模块
        python3 -m venv venv || {
            # 如果失败，尝试先安装venv模块
            echo "尝试安装venv模块..."
            apt-get install -y python3-venv || {
                # 如果仍然失败，尝试使用pip安装virtualenv
                echo "尝试使用pip安装virtualenv..."
                pip3 install virtualenv && python3 -m virtualenv venv
            }
        }
    else
        echo "错误: Python3未安装，无法创建虚拟环境"
        exit 1
    fi
fi

# 升级npm和node
echo "升级Node.js和npm..."
npm install -g n || echo "升级Node.js失败，但将继续执行"
n stable || echo "安装Node.js稳定版失败，但将继续执行"
PATH="$PATH"  # 刷新PATH以使用新版node

# 启动MySQL服务
echo "配置MySQL服务..."
service mysql start || systemctl start mysql || echo "MySQL可能已经运行"
sleep 2

# 执行MySQL初始化脚本
echo "执行MySQL初始化脚本..."
if [ -f "$PROJECT_ROOT/mysql/init.sql" ]; then
    mysql -u root < "$PROJECT_ROOT/mysql/init.sql" || {
        echo "MySQL初始化脚本执行失败，尝试使用密码认证..."
        # 如果root需要密码，尝试使用默认密码或提示用户输入
        read -sp "请输入MySQL root密码: " MYSQL_ROOT_PASSWORD
        echo
        mysql -u root -p"$MYSQL_ROOT_PASSWORD" < "$PROJECT_ROOT/mysql/init.sql" || {
            echo "MySQL初始化脚本执行失败，将创建基本数据库结构"
            # 创建数据库和用户
            echo "创建数据库和用户..."
            mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS audio_app;"
            mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE USER IF NOT EXISTS 'audio_app_user'@'localhost' IDENTIFIED BY 'yawen_12';"
            mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "GRANT ALL PRIVILEGES ON audio_app.* TO 'audio_app_user'@'localhost';"
            mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "FLUSH PRIVILEGES;"
        }
    }
else
    echo "MySQL初始化脚本不存在，创建基本数据库结构"
    
    # 创建数据库和用户 (仅在没有初始化脚本时执行)
    echo "创建数据库和用户..."
    mysql -e "CREATE DATABASE IF NOT EXISTS audio_app;" || {
        # 如果root需要密码，提示用户输入
        read -sp "请输入MySQL root密码: " MYSQL_ROOT_PASSWORD
        echo
        mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS audio_app;"
        mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "CREATE USER IF NOT EXISTS 'audio_app_user'@'localhost' IDENTIFIED BY 'yawen_12';"
        mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "GRANT ALL PRIVILEGES ON audio_app.* TO 'audio_app_user'@'localhost';"
        mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "FLUSH PRIVILEGES;"
    }
fi

# 设置Python环境
echo "设置Python环境..."
source venv/bin/activate || {
    echo "激活虚拟环境失败，尝试直接使用系统Python"
    # 继续执行，使用系统Python
}

pip install --upgrade pip || echo "升级pip失败，但将继续执行"
pip install -r requirements.txt || {
    echo "安装依赖失败，尝试一个个安装"
    # 逐行读取requirements.txt并尝试安装
    while IFS= read -r package || [[ -n "$package" ]]; do
        # 跳过注释行和空行
        [[ $package =~ ^#.*$ || -z $package ]] && continue
        echo "安装 $package..."
        pip install $package || echo "安装 $package 失败，但将继续执行"
    done < requirements.txt
}

# 设置环境变量
echo "配置环境变量..."
if [ ! -f .env ]; then
  cp .env.example .env || {
    echo "找不到.env.example，创建基本的.env文件"
    cat > .env << EOF
DATABASE_URL=mysql://audio_app_user:yawen_12@localhost:3306/audio_app
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
EOF
  }
  
  # 尝试使用sed更新.env文件
  # 生成随机密钥
  SECRET_KEY=$(openssl rand -hex 32)
  JWT_SECRET_KEY=$(openssl rand -hex 32)
  # 更新环境变量
  sed -i "s/your-secret-key/$SECRET_KEY/g" .env || echo "更新SECRET_KEY失败"
  sed -i "s/your-jwt-secret-key/$JWT_SECRET_KEY/g" .env || echo "更新JWT_SECRET_KEY失败"
  # 根据init.sql中的用户名和密码更新数据库URL
  sed -i "s|DATABASE_URL=.*|DATABASE_URL=mysql://audio_app_user:yawen_12@localhost:3306/audio_app|g" .env || echo "更新DATABASE_URL失败"
  echo "已创建并配置.env文件"
else
  echo ".env文件已存在，跳过配置"
fi

# 确保数据目录存在
echo "创建必要的数据目录..."
mkdir -p data/uploads data/tasks data/users logs

# 初始化数据库 (如果需要)
echo "初始化数据库..."
source venv/bin/activate || echo "激活虚拟环境失败，使用系统Python"
python -c "from src.balance_system.db import init_db; init_db()" || {
    echo "数据库初始化失败，可能需要手动初始化"
}

# 安装前端依赖
echo "设置前端环境..."
cd $PROJECT_ROOT/frontend
npm install || {
    echo "安装前端依赖失败，尝试使用--legacy-peer-deps选项"
    npm install --legacy-peer-deps || echo "安装前端依赖仍然失败，请手动安装"
}

# 确保前端环境变量配置
echo "NEXT_PUBLIC_API_URL=http://localhost:5002/api" > .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:5002/api" > .env.development

# 构建前端
echo "构建前端..."
npm run build || {
    echo "前端构建失败，可能需要手动构建"
}

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
source venv/bin/activate || echo "激活虚拟环境失败，使用系统Python"

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