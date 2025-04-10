#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认环境设置
IS_DOCKER=false
FORCE_DOCKER=false
REBUILD_FRONTEND=false

# 解析命令行参数
parse_args() {
    for arg in "$@"; do
        case $arg in
            --docker)
                IS_DOCKER=true
                FORCE_DOCKER=true
                export IS_DOCKER=true
                export FORCE_DOCKER=true
                export CONTAINER_DEPLOY=true
                echo -e "${GREEN}[INFO]${NC} 通过参数指定为Docker容器环境"
                ;;
            --local)
                IS_DOCKER=false
                FORCE_DOCKER=false
                export IS_DOCKER=false
                export FORCE_DOCKER=false
                export CONTAINER_DEPLOY=false
                echo -e "${GREEN}[INFO]${NC} 通过参数指定为本地环境"
                ;;
            --rebuild-frontend)
                REBUILD_FRONTEND=true
                echo -e "${GREEN}[INFO]${NC} 将重新构建前端"
                ;;
            --api-url=*)
                API_URL="${arg#*=}"
                export API_URL
                echo -e "${GREEN}[INFO]${NC} 通过参数指定API地址: $API_URL"
                ;;
            --api-host=*)
                API_HOST="${arg#*=}"
                export API_HOST
                echo -e "${GREEN}[INFO]${NC} 通过参数指定API主机: $API_HOST"
                ;;
            --api-port=*)
                API_PORT="${arg#*=}"
                export API_PORT
                echo -e "${GREEN}[INFO]${NC} 通过参数指定API端口: $API_PORT"
                ;;
            --help)
                echo "使用方法: $0 [选项]"
                echo "选项:"
                echo "  --docker            指定为Docker容器环境"
                echo "  --local             指定为本地环境（默认）"
                echo "  --rebuild-frontend  强制重新构建前端"
                echo "  --api-url=URL       指定前端请求后端的完整URL (例如: http://api.example.com/api)"
                echo "  --api-host=HOST     指定后端API主机 (例如: localhost, api.example.com)"
                echo "  --api-port=PORT     指定后端API端口 (例如: 5002, 8080)"
                echo "  --help              显示此帮助信息"
                exit 0
                ;;
        esac
    done
}

# 提示函数
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# 检测操作系统类型
detect_os() {
    info "正在检测操作系统..."
    
    if [ -f /etc/os-release ]; then
        # freedesktop.org and systemd
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        # linuxbase.org
        OS=$(lsb_release -si)
        VER=$(lsb_release -sr)
    elif [ -f /etc/lsb-release ]; then
        # For some versions of Debian/Ubuntu without lsb_release command
        . /etc/lsb-release
        OS=$DISTRIB_ID
        VER=$DISTRIB_RELEASE
    elif [ -f /etc/debian_version ]; then
        # Older Debian/Ubuntu/etc.
        OS=Debian
        VER=$(cat /etc/debian_version)
    elif [ -f /etc/Alpine-release ]; then
        # Alpine Linux
        OS=Alpine
        VER=$(cat /etc/Alpine-release)
    elif [ -f /etc/centos-release ]; then
        # Older Red Hat, CentOS, etc.
        OS=CentOS
        VER=$(cat /etc/centos-release | sed 's/.*release \([0-9]\).*/\1/')
    elif [ -f /etc/redhat-release ]; then
        # Older Red Hat, Fedora, etc.
        OS=RedHat
        VER=$(cat /etc/redhat-release | sed 's/.*release \([0-9]\).*/\1/')
    elif [ "$(uname)" == "Darwin" ]; then
        # macOS
        OS=macos
        VER=$(sw_vers -productVersion)
    else
        OS=$(uname -s)
        VER=$(uname -r)
    fi
    
    # 转换为小写
    OS=$(echo "$OS" | tr '[:upper:]' '[:lower:]')
    
    # 简化操作系统名称
    case $OS in
        *ubuntu*)
            OS="ubuntu"
            ;;
        *debian*)
            OS="debian"
            ;;
        *centos*)
            OS="centos"
            ;;
        *redhat*|*"red hat"*)
            OS="redhat"
            ;;
        *fedora*)
            OS="fedora"
            ;;
        *alpine*)
            OS="alpine"
            ;;
        *darwin*)
            OS="macos"
            ;;
    esac
    
    success "检测到操作系统: $OS $VER"
    export OS
    export VER
}

# 配置Docker环境
setup_docker_env() {
    if [ "$IS_DOCKER" = true ] || [ "$CONTAINER_DEPLOY" = "true" ]; then
        IS_DOCKER=true
        export IS_DOCKER=true
        export CONTAINER_DEPLOY=true
        success "配置Docker容器环境..."
        
        # 设置数据库主机 - 直接使用localhost
        export MYSQL_HOST="localhost"
        info "在容器内使用MySQL主机: $MYSQL_HOST"
        
        # 应用级设置
        export FLASK_ENV="production"
    else
        export CONTAINER_DEPLOY=false
    fi
}

# 激活Python虚拟环境
activate_venv() {
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        success "已激活Python虚拟环境"
    else
        warning "未找到Python虚拟环境，将使用系统Python"
    fi
}

# 设置数据库连接环境变量
setup_db_env() {
    # 检查.env文件是否存在
    if [ -f ".env" ]; then
        info "从.env文件加载环境变量"
        
        # 读取数据库配置
        DB_HOST=$(grep -E "^DB_HOST=" .env | cut -d= -f2 || echo "localhost")
        DB_PORT=$(grep -E "^DB_PORT=" .env | cut -d= -f2 || echo "3306")
        DB_NAME=$(grep -E "^(DB_NAME|MYSQL_DATABASE)=" .env | head -1 | cut -d= -f2 || echo "audio_app")
        DB_USER=$(grep -E "^(DB_USER|MYSQL_USER)=" .env | head -1 | cut -d= -f2 || echo "root")
        DB_PASS=$(grep -E "^(DB_PASSWORD|MYSQL_PASSWORD)=" .env | head -1 | cut -d= -f2 || echo "")
        
        # 检查是否在Docker环境中
        CONTAINER_DEPLOY=$(grep -E "^CONTAINER_DEPLOY=" .env | cut -d= -f2 || echo "false")
        if [ "$CONTAINER_DEPLOY" = "true" ] || [ "$IS_DOCKER" = true ]; then
            IS_DOCKER=true
            export IS_DOCKER=true
            export CONTAINER_DEPLOY=true
            info "配置Docker环境变量"
        fi
        
        # 设置Python环境变量
        export DB_HOST=$DB_HOST
        export DB_PORT=$DB_PORT
        export DB_NAME=$DB_NAME
        export DB_USER=$DB_USER
        export DB_PASSWORD=$DB_PASS
        export MYSQL_HOST=$DB_HOST
        export MYSQL_PORT=$DB_PORT
        export MYSQL_DATABASE=$DB_NAME
        export MYSQL_USER=$DB_USER
        export MYSQL_PASSWORD=$DB_PASS
        
        success "数据库环境变量设置完成"
    else
        warning "找不到.env文件，将使用默认环境变量"
    fi
}

# 检查并创建所需目录
check_directories() {
    # 确保logs目录存在
    if [ ! -d "logs" ]; then
        mkdir -p logs
        info "创建logs目录"
    fi
    
    # 确保data目录存在
    if [ ! -d "data" ]; then
        mkdir -p data
        info "创建data目录"
    fi
    
    # 确保temp目录存在
    if [ ! -d "temp" ]; then
        mkdir -p temp
        info "创建temp目录"
    fi
}

# 停止已运行的服务
stop_services() {
    info "正在停止已运行的服务..."
    
    # 停止前端服务
    if [ -f .frontend.pid ]; then
        FRONTEND_PID=$(cat .frontend.pid)
        if ps -p $FRONTEND_PID > /dev/null; then
            kill $FRONTEND_PID 2>/dev/null
            success "前端服务已停止"
        fi
        rm -f .frontend.pid
    fi
    
    # 查找并停止可能存在的前端进程
    FRONTEND_PIDS=$(ps aux | grep "npm.*start" | grep -v grep | awk '{print $2}')
    if [ ! -z "$FRONTEND_PIDS" ]; then
        for PID in $FRONTEND_PIDS; do
            kill $PID 2>/dev/null
            success "停止前端进程: $PID"
        done
    fi
    
    # 停止后端API服务
    if [ -f .api.pid ]; then
        API_PID=$(cat .api.pid)
        if ps -p $API_PID > /dev/null; then
            kill $API_PID 2>/dev/null
            success "后端API服务已停止"
        fi
        rm -f .api.pid
    fi
    
    # 查找并停止可能存在的API进程
    API_PIDS=$(ps aux | grep "python.*app.py" | grep -v grep | awk '{print $2}')
    if [ ! -z "$API_PIDS" ]; then
        for PID in $API_PIDS; do
            kill $PID 2>/dev/null
            success "停止API进程: $PID"
        done
    fi
    
    # 等待进程完全停止
    sleep 2
    success "服务清理完成"
}

# 启动MySQL服务
start_mysql() {
    info "正在检查MySQL服务..."
    
    # 如果在Docker环境中，跳过在容器内启动MySQL
    if [ "$IS_DOCKER" = true ]; then
        # 尝试使用ping检查MySQL连接
        mysqladmin ping -h "$MYSQL_HOST" --silent &>/dev/null
        if [ $? -eq 0 ]; then
            success "MySQL服务可用"
            return 0
        fi
        
        # 如果ping失败，尝试使用mysql客户端检查连接
        if command -v mysql &>/dev/null; then
            mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" &>/dev/null
            if [ $? -eq 0 ]; then
                success "MySQL服务可用"
                return 0
            fi
        fi
        
        warning "在Docker环境中无法连接到MySQL服务，请确保MySQL已启动"
        return 1
    fi
    
    # 检查MySQL服务是否已经在运行
    MYSQL_RUNNING=false
    case $OS in
        ubuntu|debian|centos|redhat|fedora)
            if command -v systemctl &>/dev/null; then
                systemctl is-active --quiet mysql || systemctl is-active --quiet mysqld
                if [ $? -eq 0 ]; then
                    MYSQL_RUNNING=true
                    success "MySQL服务已在运行"
                fi
            elif command -v service &>/dev/null; then
                service mysql status &>/dev/null || service mysqld status &>/dev/null
                if [ $? -eq 0 ]; then
                    MYSQL_RUNNING=true
                    success "MySQL服务已在运行"
                fi
            fi
            ;;
        macos)
            if brew services list | grep mysql | grep started &>/dev/null; then
                MYSQL_RUNNING=true
                success "MySQL服务已在运行"
            fi
            ;;
        alpine)
            if rc-service mariadb status &>/dev/null; then
                MYSQL_RUNNING=true
                success "MariaDB服务已在运行"
            fi
            ;;
    esac
    
    # 如果MySQL未运行，尝试启动它
    if [ "$MYSQL_RUNNING" = false ]; then
        info "尝试启动MySQL服务..."
        
        case $OS in
            ubuntu|debian)
                if command -v systemctl &>/dev/null; then
                    sudo systemctl start mysql 2>/dev/null || sudo service mysql start 2>/dev/null
                else
                    service mysql start 2>/dev/null
                fi
                ;;
            centos|redhat|fedora)
                if command -v systemctl &>/dev/null; then
                    sudo systemctl start mysqld 2>/dev/null || sudo service mysqld start 2>/dev/null
                else
                    service mysqld start 2>/dev/null
                fi
                ;;
            alpine)
                sudo rc-service mariadb start 2>/dev/null || rc-service mariadb start 2>/dev/null
                ;;
            macos)
                brew services start mysql 2>/dev/null
                ;;
            *)
                warning "未知操作系统，无法自动启动MySQL服务"
                ;;
        esac
        
        # 等待MySQL启动
        info "等待MySQL服务启动..."
        sleep 5
        
        # 检查MySQL是否已启动
        mysqladmin ping -h "$MYSQL_HOST" --silent &>/dev/null
        if [ $? -eq 0 ]; then
            success "MySQL服务已成功启动"
            return 0
        else
            warning "无法启动MySQL服务，应用可能无法正常工作"
            return 1
        fi
    fi
    
    return 0
}

# 启动后端API服务
start_api() {
    info "正在启动后端API服务..."
    
    # 设置PYTHONPATH确保模块导入正确
    export PYTHONPATH="$(pwd)"
    
    # 检查api目录及app.py是否存在
    if [ -f "api/app.py" ]; then
        info "找到API入口点: api/app.py"
        
        # 确保api目录被识别为Python包
        if [ ! -f "api/__init__.py" ]; then
            info "创建api包的__init__.py文件..."
            touch api/__init__.py
        fi
        
        # 确保api/routes目录被识别为Python包
        if [ -d "api/routes" ] && [ ! -f "api/routes/__init__.py" ]; then
            info "创建api/routes包的__init__.py文件..."
            mkdir -p api/routes
            touch api/routes/__init__.py
        fi
        
        # 确保logs目录存在
        mkdir -p logs
        
        # 启动后端API服务
        if [ "$IS_DOCKER" = true ]; then
            # Docker环境中前台运行
            info "在Docker环境中前台启动API服务..."
            cd api && python3 app.py
        else
            # 非Docker环境中后台运行
            info "在本地环境中后台启动API服务..."
            cd api && nohup python3 app.py > ../logs/api.log 2>&1 &
            API_PID=$!
            cd ..
            
            # 检查进程是否启动成功
            sleep 2
            if ps -p $API_PID > /dev/null; then
                # 保存PID到文件
                echo $API_PID > .api.pid
                success "后端API服务已启动，PID: $API_PID，日志位于: logs/api.log"
            else
                error "后端API服务启动失败，请查看日志: logs/api.log"
                return 1
            fi
        fi
    else
        error "找不到后端API服务入口点: api/app.py"
        return 1
    fi
    
    return 0
}

# 设置Node.js环境
setup_nodejs_env() {
    info "正在设置Node.js环境..."
    
    # 检查Node.js是否可用
    if ! command -v node &> /dev/null; then
        warning "未找到Node.js，尝试寻找..."
        
        # 尝试从~/.node目录加载Node.js
        NODE_DIR=$(find ~/.node -maxdepth 1 -name "node-*" -type d 2>/dev/null | head -n 1)
        if [ -n "$NODE_DIR" ] && [ -f "$NODE_DIR/bin/node" ]; then
            info "找到Node.js安装: $NODE_DIR"
            export PATH="$NODE_DIR/bin:$PATH"
        fi
        
        # 尝试从~/.nvm加载
        if [ ! -f "$NODE_DIR/bin/node" ] && [ -f "$HOME/.nvm/nvm.sh" ]; then
            info "找到NVM安装，尝试加载Node.js..."
            export NVM_DIR="$HOME/.nvm"
            [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
            nvm use 18 2>/dev/null || nvm use default 2>/dev/null
        fi
        
        # 再次检查Node.js是否可用
        if ! command -v node &> /dev/null; then
            warning "无法找到Node.js，跳过前端构建和启动"
            return 1
        fi
    fi
    
    # 检查npm是否可用
    if ! command -v npm &> /dev/null; then
        warning "无法找到npm，跳过前端构建和启动"
        return 1
    fi
    
    # 显示Node.js和npm版本
    NODE_VER=$(node --version 2>/dev/null || echo "未知")
    NPM_VER=$(npm --version 2>/dev/null || echo "未知")
    success "使用Node.js: $NODE_VER (npm: $NPM_VER)"
    
    return 0
}

# 检查并构建前端
check_and_build_frontend() {
    if [ ! -d "frontend" ]; then
        warning "未找到前端目录: frontend"
        return 1
    fi
    
    # 确保Node.js环境可用
    setup_nodejs_env || {
        warning "Node.js环境不可用，跳过前端构建"
        return 1
    }
    
    info "检查前端代码..."
    
    cd frontend || {
        warning "无法进入frontend目录"
        return 1
    }
    
    # 检查是否需要安装依赖
    if [ ! -d "node_modules" ] || [ "$REBUILD_FRONTEND" = true ]; then
        info "安装前端依赖..."
        npm install || {
            cd ..
            error "安装前端依赖失败"
            return 1
        }
    fi
    
    # 配置API地址逻辑
    NEED_UPDATE=false
    FRONTEND_API_URL=$(grep -E "^REACT_APP_API_URL=" .env 2>/dev/null | cut -d= -f2 || echo "")
    
    # 确定API地址 - 优先级: 命令行参数 > 环境变量 > .env文件 > 默认值
    if [ -n "$API_URL" ]; then
        # 1. 使用命令行参数提供的完整URL
        EXPECTED_API_URL="$API_URL"
        info "使用命令行参数指定的API地址: $EXPECTED_API_URL"
        NEED_UPDATE=true
    elif [ -n "$API_HOST" ] || [ -n "$API_PORT" ]; then
        # 2. 使用命令行参数提供的主机和/或端口
        HOST="${API_HOST:-localhost}"
        PORT="${API_PORT:-5002}"
        EXPECTED_API_URL="http://${HOST}:${PORT}/api"
        info "使用命令行参数指定的API主机/端口: $EXPECTED_API_URL"
        NEED_UPDATE=true
    elif [ -f "../.env" ]; then
        # 3. 从后端.env中提取API地址
        BACKEND_HOST=$(grep -E "^API_HOST=" ../.env | cut -d= -f2 || echo "")
        BACKEND_PORT=$(grep -E "^API_PORT=" ../.env | cut -d= -f2 || echo "")
        BACKEND_URL=$(grep -E "^API_URL=" ../.env | cut -d= -f2 || echo "")
        
        if [ -n "$BACKEND_URL" ]; then
            # 3.1 使用后端.env中指定的完整URL
            EXPECTED_API_URL="$BACKEND_URL"
            info "使用后端.env中配置的API URL: $EXPECTED_API_URL"
        elif [ -n "$BACKEND_HOST" ] || [ -n "$BACKEND_PORT" ]; then
            # 3.2 使用后端.env中的主机和/或端口
            HOST="${BACKEND_HOST:-localhost}"
            PORT="${BACKEND_PORT:-5002}"
            EXPECTED_API_URL="http://${HOST}:${PORT}/api"
            info "使用后端.env中配置的API主机/端口: $EXPECTED_API_URL"
        elif [ "$IS_DOCKER" != true ]; then
            # 如果不是Docker环境，设置为当前服务器IP地址
            # 尝试获取主机IP地址
            SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || hostname)
            if [ -n "$SERVER_IP" ] && [ "$SERVER_IP" != "localhost" ]; then
                EXPECTED_API_URL="http://${SERVER_IP}:5002/api"
                info "使用服务器IP地址作为API地址: $EXPECTED_API_URL"
            else
                # 3.3 使用默认值
                EXPECTED_API_URL="http://localhost:5002/api"
                info "使用默认API地址: $EXPECTED_API_URL"
            fi
        else
            # 3.3 使用默认值
            EXPECTED_API_URL="http://localhost:5002/api"
            info "使用默认API地址: $EXPECTED_API_URL"
        fi
        
        # 检查是否需要更新
        if [ "$FRONTEND_API_URL" != "$EXPECTED_API_URL" ] || [ "$REBUILD_FRONTEND" = true ]; then
            NEED_UPDATE=true
        fi
    else
        # 尝试获取主机IP地址
        SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || hostname)
        if [ -n "$SERVER_IP" ] && [ "$SERVER_IP" != "localhost" ] && [ "$IS_DOCKER" != true ]; then
            EXPECTED_API_URL="http://${SERVER_IP}:5002/api"
            info "使用服务器IP地址作为API地址: $EXPECTED_API_URL"
        else
            # 4. 使用默认值
            EXPECTED_API_URL="http://localhost:5002/api"
            info "使用默认API地址: $EXPECTED_API_URL"
        fi
        
        # 检查是否需要更新
        if [ "$FRONTEND_API_URL" != "$EXPECTED_API_URL" ] || [ "$REBUILD_FRONTEND" = true ]; then
            NEED_UPDATE=true
        fi
    fi
    
    # 更新前端.env文件中的API URL
    if [ "$NEED_UPDATE" = true ]; then
        info "更新前端API地址为: $EXPECTED_API_URL"
        
        # 创建或更新.env文件
        if [ ! -f ".env" ]; then
            echo "REACT_APP_API_URL=$EXPECTED_API_URL" > .env
        else
            # 更新.env文件
            TMP_ENV=$(mktemp)
            cat .env | grep -v "^REACT_APP_API_URL=" > "$TMP_ENV"
            echo "REACT_APP_API_URL=$EXPECTED_API_URL" >> "$TMP_ENV"
            mv "$TMP_ENV" .env
        fi
        
        # 显示当前的环境设置
        info "前端环境变量配置:"
        cat .env
        
        # 标记需要重新构建
        REBUILD_FRONTEND=true
        
        # 导出环境变量，确保构建过程能够正确使用
        export REACT_APP_API_URL="$EXPECTED_API_URL"
    fi
    
    # 如果需要重新构建
    if [ "$REBUILD_FRONTEND" = true ]; then
        info "重新构建前端..."
        # 确保环境变量能被npm构建过程使用
        REACT_APP_API_URL="$EXPECTED_API_URL" npm run build || {
            cd ..
            error "前端构建失败"
            return 1
        }
        success "前端构建成功，API地址: $EXPECTED_API_URL"
    fi
    
    # 返回上级目录
    cd ..
    return 0
}

# 启动前端服务
start_frontend() {
    info "正在启动前端服务..."
    
    # 确保Node.js环境可用
    setup_nodejs_env || {
        warning "Node.js环境不可用，跳过前端启动"
        return 1
    }
    
    if [ ! -d "frontend" ]; then
        warning "未找到前端目录: frontend"
        return 1
    fi
    
    cd frontend || {
        warning "无法进入frontend目录"
        return 1
    }
    
    # 读取当前API URL
    FRONTEND_API_URL=$(grep -E "^REACT_APP_API_URL=" .env 2>/dev/null | cut -d= -f2 || echo "http://localhost:5002/api")
    info "前端将使用API地址: $FRONTEND_API_URL"
    
    # 确保node_modules存在
    if [ ! -d "node_modules" ]; then
        info "前端依赖不存在，尝试安装..."
        npm install || {
            cd ..
            error "安装前端依赖失败"
            return 1
        }
    fi
    
    # 在Docker环境中判断是否需要前台启动
    if [ "$IS_DOCKER" = true ]; then
        # Docker环境中通常不需要启动前端服务，只需要构建
        if [ -d "build" ]; then
            info "在Docker环境中使用构建好的前端静态文件"
            cd ..
            return 0
        else
            info "构建前端静态文件..."
            # 使用环境变量构建
            REACT_APP_API_URL="$FRONTEND_API_URL" npm run build || {
                cd ..
                error "前端构建失败"
                return 1
            }
            cd ..
            return 0
        fi
    else
        # 本地环境中启动开发服务器
        info "在本地环境中启动前端开发服务器..."
        mkdir -p ../logs
        # 使用环境变量启动
        export REACT_APP_API_URL="$FRONTEND_API_URL"
        nohup npm start > ../logs/frontend.log 2>&1 &
        FRONTEND_PID=$!
        
        # 检查进程是否启动成功
        sleep 5
        if ps -p $FRONTEND_PID > /dev/null; then
            cd ..
            echo $FRONTEND_PID > .frontend.pid
            success "前端服务已启动，PID: $FRONTEND_PID，日志位于: logs/frontend.log"
            success "前端使用API地址: $FRONTEND_API_URL"
            return 0
        else
            cd ..
            error "前端服务启动失败，请查看日志: logs/frontend.log"
            return 1
        fi
    fi
}

# 启动所有服务
start_all_services() {
    info "正在启动所有服务..."
    
    # 首先停止已运行的服务
    stop_services
    
    # 启动MySQL服务
    start_mysql
    
    # 检查并构建前端
    check_and_build_frontend
    
    # 在Docker环境中前台启动后端API服务
    if [ "$IS_DOCKER" = true ]; then
        # 直接启动API服务（前台运行）
        start_api
    else
        # 启动前端和后端服务（后台运行）
        start_api
        start_frontend
        
        # 显示服务访问地址
        echo ""
        echo "========================================"
        success "所有服务已启动"
        echo "后端API访问地址: http://localhost:5002/api"
        echo "前端访问地址: http://localhost:3000"
        echo "========================================"
    fi
}

# 主函数
main() {
    echo "========================================"
    echo "       音频处理应用启动脚本"
    echo "========================================"
    
    # 解析命令行参数
    parse_args "$@"
    
    # 检测操作系统
    detect_os
    
    # 配置Docker环境
    setup_docker_env
    
    # 设置数据库连接环境变量
    setup_db_env
    
    # 激活Python虚拟环境
    activate_venv
    
    # 配置Node.js环境
    setup_nodejs_env
    
    # 检查目录
    check_directories
    
    # 启动所有服务
    start_all_services
}

# 执行主函数，传递命令行参数
main "$@"
