#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印彩色信息的函数
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
}

# 停止服务的函数
stop_services() {
    info "正在停止服务..."
    
    # 停止前端服务
    if [ -f .frontend.pid ]; then
        FRONTEND_PID=$(cat .frontend.pid)
        if ps -p $FRONTEND_PID > /dev/null; then
            kill $FRONTEND_PID
            success "前端服务已停止"
        else
            warning "前端服务未运行"
        fi
        rm -f .frontend.pid
    else
        warning "未找到前端服务的PID文件"
    fi
    
    # 停止后端API服务
    if [ -f .api.pid ]; then
        API_PID=$(cat .api.pid)
        if ps -p $API_PID > /dev/null; then
            kill $API_PID
            success "后端API服务已停止"
        else
            warning "后端API服务未运行"
        fi
        rm -f .api.pid
    else
        warning "未找到后端API服务的PID文件"
    fi
    
    # 检查是否有sudo命令
    HAS_SUDO=0
    if command -v sudo &> /dev/null; then
        HAS_SUDO=1
    fi
    
    # 注释掉交互式询问停止MySQL的部分，在自动关停时不要影响MySQL
    # read -p "是否要停止MySQL服务？(y/n) " STOP_MYSQL
    # if [ "$STOP_MYSQL" == "y" ] || [ "$STOP_MYSQL" == "Y" ]; then
    if [ "$1" == "stop_mysql" ]; then
        case $OS in
            ubuntu|debian)
                if [ $HAS_SUDO -eq 1 ]; then
                    sudo systemctl stop mysql
                else
                    systemctl stop mysql 2>/dev/null || warning "停止MySQL服务失败，请手动停止"
                fi
                ;;
            centos|redhat|fedora)
                if [ $HAS_SUDO -eq 1 ]; then
                    sudo systemctl stop mysqld
                else
                    systemctl stop mysqld 2>/dev/null || warning "停止MySQL服务失败，请手动停止"
                fi
                ;;
            alpine)
                if [ $HAS_SUDO -eq 1 ]; then
                    sudo rc-service mariadb stop
                else
                    rc-service mariadb stop 2>/dev/null || warning "停止MySQL服务失败，请手动停止"
                fi
                ;;
            macos)
                brew services stop mysql
                ;;
        esac
        success "MySQL服务已停止"
    fi
    # fi
}

# 自动关停已运行的服务
cleanup_before_start() {
    info "检查并关停已运行的服务实例..."
    
    # 检查前端服务
    if [ -f .frontend.pid ]; then
        FRONTEND_PID=$(cat .frontend.pid)
        if ps -p $FRONTEND_PID > /dev/null; then
            info "发现正在运行的前端服务，准备关停..."
            kill $FRONTEND_PID
            success "前端服务已关停"
        fi
        rm -f .frontend.pid
    fi
    
    # 检查后端API服务
    if [ -f .api.pid ]; then
        API_PID=$(cat .api.pid)
        if ps -p $API_PID > /dev/null; then
            info "发现正在运行的后端API服务，准备关停..."
            kill $API_PID
            success "后端API服务已关停"
        fi
        rm -f .api.pid
    fi
    
    # 额外检查可能存在但PID文件丢失的进程
    info "检查可能存在的残留进程..."
    
    # 检查API进程
    API_PIDS=$(ps aux | grep "python.*api/app.py" | grep -v grep | awk '{print $2}')
    if [ ! -z "$API_PIDS" ]; then
        info "发现残留的API进程，准备关停..."
        for PID in $API_PIDS; do
            kill $PID
            success "关停API进程: $PID"
        done
    fi
    
    # 检查前端进程
    FRONTEND_PIDS=$(ps aux | grep "npm.*start" | grep -v grep | awk '{print $2}')
    if [ ! -z "$FRONTEND_PIDS" ]; then
        info "发现残留的前端进程，准备关停..."
        for PID in $FRONTEND_PIDS; do
            kill $PID
            success "关停前端进程: $PID"
        done
    fi
    
    # 等待进程完全停止
    sleep 2
    success "服务清理完成"
}

# 检测是否在Docker容器中运行
detect_docker() {
    info "检测运行环境..."
    
    IS_DOCKER=false
    
    # 检查/.dockerenv文件是否存在（Docker容器中特有的文件）
    if [ -f /.dockerenv ]; then
        IS_DOCKER=true
        info "通过/.dockerenv文件检测到Docker环境"
    fi
    
    # 检查cgroup中是否包含docker字符串
    if [ -f /proc/1/cgroup ] && grep -q "docker\|container" /proc/1/cgroup; then
        IS_DOCKER=true
        info "通过cgroup检测到Docker环境"
    fi
    
    # 检查hostname是否使用了容器ID形式或包含container关键词
    CURRENT_HOSTNAME=$(hostname)
    if [[ "$CURRENT_HOSTNAME" =~ ^[0-9a-f]{12}$ ]] || [[ "$CURRENT_HOSTNAME" == *"container"* ]]; then
        IS_DOCKER=true
        info "通过hostname检测到Docker环境: $CURRENT_HOSTNAME"
    fi
    
    # 检查是否存在Docker相关环境变量
    if [ ! -z "$DOCKER_CONTAINER" ] || [ ! -z "$DOCKER_HOST" ] || [ ! -z "$DOCKER_ENV" ]; then
        IS_DOCKER=true
        info "通过环境变量检测到Docker环境"
    fi
    
    # 允许用户通过环境变量强制设置
    if [ "$FORCE_DOCKER" = "true" ]; then
        IS_DOCKER=true
        info "通过用户设置FORCE_DOCKER=true强制使用Docker环境"
    fi
    
    if [ "$IS_DOCKER" = true ]; then
        info "确认Docker容器环境"
        # 如果确认是Docker环境，设置环境变量和数据库主机
        export FLASK_ENV=docker
        export MYSQL_HOST=gpufree-container
    else
        info "检测到非Docker环境"
        export FLASK_ENV=local
        export MYSQL_HOST=localhost
    fi
    
    export IS_DOCKER
}

# 检测操作系统类型
detect_os() {
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
    elif [ -f /etc/SuSe-release ]; then
        # Older SuSE/etc.
        OS=SuSE
        VER=$(cat /etc/SuSe-release)
    elif [ -f /etc/redhat-release ]; then
        # Older Red Hat, CentOS, etc.
        OS=RedHat
        VER=$(cat /etc/redhat-release)
    else
        # Fall back to uname, e.g. "Linux <version>", also works for BSD, etc.
        OS=$(uname -s)
        VER=$(uname -r)
    fi
    
    # 转换为小写
    OS=$(echo "$OS" | tr '[:upper:]' '[:lower:]')
    
    # 检查是否是macOS
    if [ "$OS" == "darwin" ]; then
        OS="macos"
    fi
    
    info "检测到操作系统: $OS $VER"
}

# 启动MySQL
start_mysql() {
    info "正在启动MySQL服务..."
    
    # 检查是否有sudo命令
    HAS_SUDO=0
    if command -v sudo &> /dev/null; then
        HAS_SUDO=1
    fi
    
    case $OS in
        ubuntu|debian)
            if [ $HAS_SUDO -eq 1 ]; then
                sudo systemctl start mysql
            else
                systemctl start mysql 2>/dev/null || warning "启动MySQL服务失败，请手动启动"
            fi
            ;;
        centos|redhat|fedora)
            if [ $HAS_SUDO -eq 1 ]; then
                sudo systemctl start mysqld
            else
                systemctl start mysqld 2>/dev/null || warning "启动MySQL服务失败，请手动启动"
            fi
            ;;
        alpine)
            if [ $HAS_SUDO -eq 1 ]; then
                sudo rc-service mariadb start
            else
                rc-service mariadb start 2>/dev/null || warning "启动MySQL服务失败，请手动启动"
            fi
            ;;
        macos)
            brew services start mysql
            ;;
        *)
            warning "未知操作系统，请手动启动MySQL服务"
            ;;
    esac
    
    success "MySQL服务已启动"
}

# 启动后端API服务
start_api() {
    info "正在启动后端API服务..."
    
    # 检查Python虚拟环境是否存在
    if [ ! -d "venv" ]; then
        warning "Python虚拟环境不存在，尝试创建..."
        python3 -m venv venv || error "无法创建Python虚拟环境，请确保python3-venv已安装"
    fi
    
    # 激活Python虚拟环境
    source venv/bin/activate || {
        error "无法激活Python虚拟环境"
        return 1
    }
    
    # 检查是否存在logs目录
    mkdir -p logs
    
    # 检查requirements.txt是否已安装
    if [ ! -f ".requirements_installed" ]; then
        info "安装Python依赖..."
        pip install -r requirements.txt && touch .requirements_installed
    fi
    
    # 确保api目录被识别为Python包
    if [ ! -f "api/__init__.py" ]; then
        info "创建api包的__init__.py文件..."
        touch api/__init__.py
    fi
    
    # 确保api/routes目录被识别为Python包
    mkdir -p api/routes
    if [ ! -f "api/routes/__init__.py" ]; then
        info "创建api/routes包的__init__.py文件..."
        touch api/routes/__init__.py
    fi
    
    # 检查数据库连接
    info "检查数据库连接..."
    
    # 使用全局设置的环境变量，不再重复设置
    DB_HOST=${MYSQL_HOST:-"localhost"}
    
    info "使用数据库主机: $DB_HOST, 环境: $FLASK_ENV"
    
    # 检查MySQL连接
    python3 - <<EOF
import pymysql
import os
import sys
import time

DB_HOST = "$DB_HOST"
DB_PORT = int(os.environ.get('MYSQL_PORT', 3306))
DB_USER = os.environ.get('MYSQL_USER', 'audio_app_user')
DB_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
DB_NAME = os.environ.get('MYSQL_DATABASE', 'audio_app')

print(f'尝试连接到MySQL: {DB_HOST}:{DB_PORT}, 用户: {DB_USER}, 数据库: {DB_NAME}')

max_retries = 3
retry_count = 0

while retry_count < max_retries:
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            connect_timeout=10
        )
        
        print('MySQL连接成功！')
        cursor = conn.cursor()
        cursor.execute('SELECT VERSION()')
        version = cursor.fetchone()
        print(f'MySQL版本: {version[0]}')
        cursor.close()
        conn.close()
        sys.exit(0)
    except Exception as e:
        print(f'MySQL连接失败: {e}')
        retry_count += 1
        if retry_count < max_retries:
            wait_time = retry_count * 2
            print(f'等待 {wait_time} 秒后重试...')
            time.sleep(wait_time)
        else:
            print('已达到最大重试次数，请检查MySQL服务是否正在运行。')
            print('确保MySQL服务已启动，并且用户名和密码正确。')
            print('API将继续启动，但数据库相关功能可能无法使用。')
            sys.exit(1)
EOF
    
    # 即使数据库连接失败也继续启动API
    
    # 获取项目根目录的绝对路径
    PROJECT_ROOT="$(pwd)"
    
    # 使用项目根目录作为PYTHONPATH
    export PROJECT_ROOT
    PYTHONPATH="$PROJECT_ROOT" nohup python -m api.app > logs/api.log 2>&1 &
    API_PID=$!
    
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
}

# 启动前端服务
start_frontend() {
    info "正在启动前端服务..."
    
    # 确保Node.js可用
    if ! command -v node &> /dev/null; then
        # 尝试从~/.node目录加载Node.js
        NODE_DIR=$(find ~/.node -maxdepth 1 -name "node-*" -type d 2>/dev/null | head -n 1)
        if [ -n "$NODE_DIR" ] && [ -f "$NODE_DIR/bin/node" ]; then
            info "找到Node.js安装: $NODE_DIR"
            export PATH="$NODE_DIR/bin:$PATH"
        else
            # 尝试从~/.nvm加载
            if [ -f "$HOME/.nvm/nvm.sh" ]; then
                source "$HOME/.nvm/nvm.sh"
                nvm use 18 2>/dev/null || nvm use default 2>/dev/null
            fi
        fi
    fi
    
    # 再次检查Node.js
    if ! command -v node &> /dev/null; then
        error "Node.js未安装或未添加到PATH，无法启动前端服务"
        return 1
    fi
    
    # 进入前端目录
    cd frontend
    
    # 检查node_modules是否存在
    if [ ! -d "node_modules" ]; then
        info "安装前端依赖..."
        npm install || {
            error "安装前端依赖失败"
            cd ..
            return 1
        }
    fi
    
    # 以后台方式启动前端服务
    nohup npm start > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    # 检查进程是否启动成功
    sleep 5
    if ps -p $FRONTEND_PID > /dev/null; then
        # 返回根目录并保存PID到文件
        cd ..
        echo $FRONTEND_PID > .frontend.pid
        success "前端服务已启动，PID: $FRONTEND_PID，日志位于: logs/frontend.log"
    else
        cd ..
        error "前端服务启动失败，请查看日志: logs/frontend.log"
        return 1
    fi
}

# 检查服务状态
check_services() {
    info "正在检查服务状态..."
    
    # 检查是否有sudo命令
    HAS_SUDO=0
    if command -v sudo &> /dev/null; then
        HAS_SUDO=1
    fi
    
    # 检查MySQL服务
    case $OS in
        ubuntu|debian|centos|redhat|fedora)
            if [ $HAS_SUDO -eq 1 ]; then
                if systemctl is-active --quiet mysql || systemctl is-active --quiet mysqld; then
                    success "MySQL服务正在运行"
                else
                    warning "MySQL服务未运行，尝试启动..."
                    start_mysql
                fi
            else
                # 尝试通过其他方式检查MySQL状态
                if netstat -tlpn 2>/dev/null | grep -q 3306 || ps aux | grep -v grep | grep -q mysqld; then
                    success "MySQL服务似乎正在运行"
                else
                    warning "MySQL服务可能未运行，尝试启动..."
                    start_mysql
                fi
            fi
            ;;
        macos)
            if brew services list | grep mysql | grep started > /dev/null; then
                success "MySQL服务正在运行"
            else
                warning "MySQL服务未运行，尝试启动..."
                start_mysql
            fi
            ;;
        alpine)
            if [ $HAS_SUDO -eq 1 ]; then
                if rc-service mariadb status >/dev/null 2>&1; then
                    success "MySQL服务正在运行"
                else
                    warning "MySQL服务未运行，尝试启动..."
                    start_mysql
                fi
            else
                # 尝试通过其他方式检查MySQL状态
                if netstat -tlpn 2>/dev/null | grep -q 3306 || ps aux | grep -v grep | grep -q mysqld; then
                    success "MySQL服务似乎正在运行"
                else
                    warning "MySQL服务可能未运行，尝试启动..."
                    start_mysql
                fi
            fi
            ;;
        *)
            warning "未知操作系统，无法自动检查MySQL状态"
            ;;
    esac
    
    # 检查API服务
    if [ -f .api.pid ]; then
        API_PID=$(cat .api.pid)
        if ps -p $API_PID > /dev/null; then
            success "后端API服务正在运行，PID: $API_PID"
        else
            warning "后端API服务未运行，PID文件可能过期，尝试启动..."
            start_api
        fi
    else
        warning "未找到后端API服务的PID文件，尝试启动..."
        start_api
    fi
    
    # 检查前端服务
    if [ -f .frontend.pid ]; then
        FRONTEND_PID=$(cat .frontend.pid)
        if ps -p $FRONTEND_PID > /dev/null; then
            success "前端服务正在运行，PID: $FRONTEND_PID"
        else
            warning "前端服务未运行，PID文件可能过期，尝试启动..."
            start_frontend
        fi
    else
        warning "未找到前端服务的PID文件，尝试启动..."
        start_frontend
    fi
}

# 查看日志
view_logs() {
    LOG_TYPE=$1
    
    case $LOG_TYPE in
        api)
            if [ -f logs/api.log ]; then
                tail -f logs/api.log
            else
                error "API日志文件不存在"
            fi
            ;;
        frontend)
            if [ -f logs/frontend.log ]; then
                tail -f logs/frontend.log
            else
                error "前端日志文件不存在"
            fi
            ;;
        *)
            error "未知的日志类型: $LOG_TYPE"
            echo "可用的日志类型: api, frontend"
            ;;
    esac
}

# 显示帮助信息
show_help() {
    echo "使用方法: $0 [选项]"
    echo
    echo "选项:"
    echo "  start       启动所有服务"
    echo "  stop        停止所有服务"
    echo "  restart     重启所有服务"
    echo "  status      查看服务状态"
    echo "  logs [type] 查看日志 (类型: api, frontend)"
    echo "  help        显示此帮助信息"
    echo
}

# 主函数
main() {
    # 检测是否在Docker容器中运行
    detect_docker
    
    # 检测操作系统
    detect_os
    
    # 处理命令行参数
    COMMAND=${1:-"start"}
    
    case $COMMAND in
        start)
            echo "========================================"
            echo "      启动音频处理应用"
            echo "========================================"
            echo
            
            # 自动关停已运行的服务
            cleanup_before_start
            
            # 启动服务
            start_mysql
            start_api
            start_frontend
            
            echo
            echo "========================================"
            success "所有服务已启动"
            echo "后端API访问地址: http://localhost:5002/api"
            echo "前端访问地址: http://localhost:3000"
            echo "========================================"
            ;;
        stop)
            echo "========================================"
            echo "      停止音频处理应用"
            echo "========================================"
            echo
            
            # 停止服务
            # stop_services
            cleanup_before_start

            # 询问是否停止MySQL
            read -p "是否要停止MySQL服务？(y/n) " STOP_MYSQL
            if [ "$STOP_MYSQL" == "y" ] || [ "$STOP_MYSQL" == "Y" ]; then
                stop_services "stop_mysql"
            fi
            
            echo
            echo "========================================"
            success "所有服务已停止"
            echo "========================================"
            ;;
        restart)
            echo "========================================"
            echo "      重启音频处理应用"
            echo "========================================"
            echo
            
            # 停止然后启动服务
            cleanup_before_start
            sleep 2
            start_mysql
            start_api
            start_frontend
            
            echo
            echo "========================================"
            success "所有服务已重启"
            echo "后端API访问地址: http://localhost:5002/api"
            echo "前端访问地址: http://localhost:3000"
            echo "========================================"
            ;;
        status)
            echo "========================================"
            echo "      查看服务状态"
            echo "========================================"
            echo
            
            # 检查服务状态
            check_services
            
            echo
            echo "========================================"
            ;;
        logs)
            LOG_TYPE=${2:-"api"}
            view_logs $LOG_TYPE
            ;;
        help|*)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@"
