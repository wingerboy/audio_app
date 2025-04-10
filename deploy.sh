#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
    esac
    
    success "检测到操作系统: $OS $VER"
    export OS
    export VER
}

# 检测是否在Docker环境中
detect_docker() {
    info "检测是否在Docker环境中..."
    
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
        success "确认运行在Docker容器环境中"
        # 如果确认是Docker环境，设置环境变量
        export MYSQL_HOST=${MYSQL_HOST:-db}
        info "设置默认MySQL主机为: $MYSQL_HOST"
        
        # 如果.env文件存在，更新其中的DB_HOST
        if [ -f ".env" ]; then
            # 创建一个临时文件
            TMP_ENV=$(mktemp)
            
            # 更新DB_HOST
            cat .env | grep -v "^DB_HOST=" > "$TMP_ENV"
            echo "DB_HOST=$MYSQL_HOST" >> "$TMP_ENV"
            
            # 替换原文件
            mv "$TMP_ENV" .env
            
            info "已更新.env文件中的DB_HOST为: $MYSQL_HOST"
        fi
    else
        info "检测到非Docker环境"
    fi
    
    export IS_DOCKER
}

# 安装系统依赖
install_dependencies() {
    info "正在安装系统依赖..."
    
    # 检查是否有sudo命令
    HAS_SUDO=0
    if command -v sudo &> /dev/null; then
        HAS_SUDO=1
    fi
    
    # Python 3.9
    if ! command -v python3 &> /dev/null; then
        case $OS in
            ubuntu|debian)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装Python 3.9..."
                    sudo apt-get update
                    sudo apt-get install -y python3 python3-pip python3-venv
                else
                    warning "无法安装Python，sudo命令不可用，请手动安装Python 3.9"
                fi
                ;;
            centos|redhat|fedora)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装Python 3.9..."
                    sudo yum install -y python3 python3-pip python3-devel
                else
                    warning "无法安装Python，sudo命令不可用，请手动安装Python 3.9"
                fi
                ;;
            alpine)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装Python 3.9..."
                    sudo apk add python3 py3-pip python3-dev
                else
                    apk add python3 py3-pip python3-dev 2>/dev/null || warning "无法安装Python，请手动安装Python 3.9"
                fi
                ;;
            macos)
                info "安装Python 3.9..."
                brew install python@3.9
                ;;
            *)
                warning "未知操作系统，请手动安装Python 3.9"
                ;;
        esac
    else
        PY_VER=$(python3 --version 2>&1)
        success "已安装Python: $PY_VER"
    fi
    
    # FFmpeg
    if ! command -v ffmpeg &> /dev/null; then
        case $OS in
            ubuntu|debian)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装FFmpeg..."
                    sudo apt-get update
                    sudo apt-get install -y ffmpeg
                else
                    warning "无法安装FFmpeg，sudo命令不可用，请手动安装FFmpeg"
                fi
                ;;
            centos|redhat|fedora)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装FFmpeg..."
                    sudo yum install -y epel-release
                    sudo yum install -y ffmpeg ffmpeg-devel
                else
                    warning "无法安装FFmpeg，sudo命令不可用，请手动安装FFmpeg"
                fi
                ;;
            alpine)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装FFmpeg..."
                    sudo apk add ffmpeg
                else
                    apk add ffmpeg 2>/dev/null || warning "无法安装FFmpeg，请手动安装FFmpeg"
                fi
                ;;
            macos)
                info "安装FFmpeg..."
                brew install ffmpeg
                ;;
            *)
                warning "未知操作系统，请手动安装FFmpeg"
                ;;
        esac
    else
        FFMPEG_VER=$(ffmpeg -version | head -n 1)
        success "已安装FFmpeg: $FFMPEG_VER"
    fi
    
    # Node.js
    if ! command -v node &> /dev/null; then
        info "安装Node.js..."
        
        # 使用NVM安装Node.js
        if [ ! -d "$HOME/.nvm" ]; then
            info "安装NVM (Node Version Manager)..."
            
            # 下载NVM安装脚本
            if command -v curl &> /dev/null; then
                info "使用curl下载NVM..."
                curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash || warning "使用curl下载NVM失败"
            elif command -v wget &> /dev/null; then
                info "使用wget下载NVM..."
                wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash || warning "使用wget下载NVM失败"
            else
                warning "未安装curl或wget，无法自动安装NVM"
                warning "将尝试直接下载Node.js二进制文件..."
                
                # 创建本地Node.js目录
                mkdir -p "$HOME/.node"
                
                # 根据系统架构下载Node.js二进制文件
                ARCH=$(uname -m)
                NODE_VER="v18.16.0"
                
                case $ARCH in
                    x86_64)
                        NODE_ARCH="x64"
                        ;;
                    aarch64|arm64)
                        NODE_ARCH="arm64"
                        ;;
                    *)
                        NODE_ARCH="x64"
                        ;;
                esac
                
                NODE_URL="https://nodejs.org/dist/${NODE_VER}/node-${NODE_VER}-linux-${NODE_ARCH}.tar.gz"
                info "尝试从${NODE_URL}下载Node.js..."
                
                if command -v curl &> /dev/null; then
                    curl -L -o "$HOME/.node/node.tar.gz" "$NODE_URL" || warning "无法下载Node.js"
                elif command -v wget &> /dev/null; then
                    wget -O "$HOME/.node/node.tar.gz" "$NODE_URL" || warning "无法下载Node.js"
                else
                    warning "无法下载Node.js，请手动安装Node.js 18"
                fi
                
                if [ -f "$HOME/.node/node.tar.gz" ]; then
                    info "解压Node.js二进制文件..."
                    tar -xzf "$HOME/.node/node.tar.gz" -C "$HOME/.node" || warning "解压Node.js失败"
                    rm -f "$HOME/.node/node.tar.gz"
                    NODE_DIR=$(find "$HOME/.node" -maxdepth 1 -name "node-*" -type d | head -n 1)
                    
                    if [ -n "$NODE_DIR" ]; then
                        info "设置Node.js环境变量..."
                        # 设置PATH
                        echo 'export PATH="'$NODE_DIR'/bin:$PATH"' >> "$HOME/.bashrc"
                        if [ -f "$HOME/.profile" ]; then
                            echo 'export PATH="'$NODE_DIR'/bin:$PATH"' >> "$HOME/.profile"
                        fi
                        if [ -f "$HOME/.zshrc" ]; then
                            echo 'export PATH="'$NODE_DIR'/bin:$PATH"' >> "$HOME/.zshrc"
                        fi
                        
                        # 立即设置PATH
                        export PATH="$NODE_DIR/bin:$PATH"
                        success "Node.js二进制文件安装成功：$(node --version 2>/dev/null || echo '未知版本')"
                    else
                        warning "找不到解压后的Node.js目录"
                    fi
                fi
            fi
        fi
        
        # 加载NVM
        if [ -f "$HOME/.nvm/nvm.sh" ]; then
            info "加载NVM并安装Node.js 18..."
            # shellcheck disable=SC1090
            source "$HOME/.nvm/nvm.sh"
            nvm install 18 || warning "使用NVM安装Node.js 18失败"
            nvm use 18 || warning "使用NVM切换到Node.js 18失败"
            
            # 添加到shell配置文件
            if [ -f "$HOME/.bashrc" ] && ! grep -q "NVM_DIR" "$HOME/.bashrc"; then
                info "将NVM配置添加到.bashrc..."
                echo 'export NVM_DIR="$HOME/.nvm"' >> "$HOME/.bashrc"
                echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"' >> "$HOME/.bashrc"
                echo '[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"' >> "$HOME/.bashrc"
            fi
            
            if [ -f "$HOME/.zshrc" ] && ! grep -q "NVM_DIR" "$HOME/.zshrc"; then
                info "将NVM配置添加到.zshrc..."
                echo 'export NVM_DIR="$HOME/.nvm"' >> "$HOME/.zshrc"
                echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"' >> "$HOME/.zshrc"
                echo '[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"' >> "$HOME/.zshrc"
            fi
            
            if [ -f "$HOME/.profile" ] && ! grep -q "NVM_DIR" "$HOME/.profile"; then
                info "将NVM配置添加到.profile..."
                echo 'export NVM_DIR="$HOME/.nvm"' >> "$HOME/.profile"
                echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"' >> "$HOME/.profile"
            fi
            
            # 确认Node.js安装
            if command -v node &> /dev/null; then
                NODE_VER=$(node --version)
                NPM_VER=$(npm --version)
                success "已安装Node.js: $NODE_VER (npm: $NPM_VER)"
            else
                warning "Node.js安装似乎失败，请手动安装"
            fi
        else
            warning "NVM安装失败或不可用，请尝试手动安装Node.js 18"
        fi
    else
        NODE_VER=$(node --version)
        NPM_VER=$(npm --version)
        success "已安装Node.js: $NODE_VER (npm: $NPM_VER)"
    fi
    
    # MySQL
    if ! command -v mysql &> /dev/null; then
        # 检查是否在Docker环境中
        IS_DOCKER=false
        if [ -f /.dockerenv ] || ([ -f /proc/1/cgroup ] && grep -q "docker\|container" /proc/1/cgroup); then
            IS_DOCKER=true
            info "检测到Docker环境，继续安装MySQL客户端"
        fi
        
        case $OS in
            ubuntu|debian)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装MySQL..."
                    sudo apt-get update
                    # 使用DEBIAN_FRONTEND=noninteractive避免交互式提示
                    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-client
                    if [ "$IS_DOCKER" != true ]; then
                        # 在非Docker环境中安装完整的MySQL服务器
                        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server
                    fi
                else
                    info "在非sudo环境中尝试安装MySQL..."
                    apt-get update 2>/dev/null || warning "apt-get update失败，可能需要root权限"
                    DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-client 2>/dev/null || warning "无法安装MySQL客户端，请手动安装"
                    if [ "$IS_DOCKER" != true ]; then
                        # 在非Docker环境中安装完整的MySQL服务器
                        DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server 2>/dev/null || warning "无法安装MySQL服务器，请手动安装"
                    fi
                fi
                ;;
            centos|redhat|fedora)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装MySQL..."
                    sudo yum install -y mysql
                    if [ "$IS_DOCKER" != true ]; then
                        # 在非Docker环境中安装完整的MySQL服务器
                        sudo yum install -y mysql-server
                    fi
                else
                    info "在非sudo环境中尝试安装MySQL..."
                    yum install -y mysql 2>/dev/null || warning "无法安装MySQL客户端，请手动安装"
                    if [ "$IS_DOCKER" != true ]; then
                        # 在非Docker环境中安装完整的MySQL服务器
                        yum install -y mysql-server 2>/dev/null || warning "无法安装MySQL服务器，请手动安装"
                    fi
                fi
                ;;
            alpine)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装MariaDB (MySQL替代品)..."
                    sudo apk add mysql-client
                    if [ "$IS_DOCKER" != true ]; then
                        # 在非Docker环境中安装完整的MariaDB服务器
                        sudo apk add mariadb mariadb-client
                    fi
                else
                    apk add mysql-client 2>/dev/null || warning "无法安装MySQL客户端，请手动安装"
                    if [ "$IS_DOCKER" != true ]; then
                        # 在非Docker环境中安装完整的MariaDB服务器
                        apk add mariadb mariadb-client 2>/dev/null || warning "无法安装MariaDB，请手动安装"
                    fi
                fi
                ;;
            macos)
                info "安装MySQL..."
                brew install mysql
                ;;
            *)
                warning "未知操作系统，请手动安装MySQL"
                ;;
        esac
    else
        MYSQL_VER=$(mysql --version)
        success "已安装MySQL: $MYSQL_VER"
    fi
    
    success "系统依赖安装完成"
}

# 设置Python虚拟环境
setup_python_env() {
    info "正在设置Python虚拟环境..."
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        python3 -m venv venv || error "无法创建Python虚拟环境，请确保python3-venv已安装"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate || error "无法激活Python虚拟环境"
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装项目依赖
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        warning "未找到requirements.txt文件，跳过Python依赖安装"
    fi
    
    success "Python虚拟环境设置完成"
}

# 设置Node.js环境
setup_nodejs_env() {
    info "正在设置Node.js环境..."
    
    # 检查是否已安装Node.js
    if command -v node &> /dev/null; then
        NODE_VER=$(node -v)
        success "已安装Node.js: $NODE_VER"
    else
        warning "未找到Node.js"
        
        # 尝试使用NVM安装Node.js
        if [ -s "$HOME/.nvm/nvm.sh" ]; then
            info "发现NVM，尝试使用NVM安装Node.js..."
            export NVM_DIR="$HOME/.nvm"
            [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
            nvm install 18 && nvm use 18
        else
            info "尝试安装NVM和Node.js..."
            curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash || warning "NVM安装失败"
            
            # 加载NVM
            export NVM_DIR="$HOME/.nvm"
            [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
            
            # 安装Node.js
            if command -v nvm &> /dev/null; then
                nvm install 18 && nvm use 18 || warning "Node.js安装失败"
            else
                warning "NVM安装失败，无法继续安装Node.js"
            fi
        fi
    fi
    
    # 检查是否已安装npm
    if command -v npm &> /dev/null; then
        NPM_VER=$(npm -v)
        success "已安装npm: $NPM_VER"
        
        # 切换到frontend目录
        if [ -d "frontend" ]; then
            cd frontend
            
            # 检查是否有package.json
            if [ -f "package.json" ]; then
                info "正在安装前端依赖..."
                npm install || warning "前端依赖安装失败"
                
                # 构建前端
                info "正在构建前端..."
                npm run build || warning "前端构建失败"
            else
                warning "frontend目录中未找到package.json文件"
            fi
            
            # 返回到原目录
            cd ..
        else
            warning "未找到frontend目录，跳过前端构建"
        fi
    else
        warning "未找到npm，跳过前端依赖安装和构建"
    fi
    
    success "Node.js环境配置完成"
}

# 配置MySQL
setup_mysql() {
    info "正在配置MySQL..."
    
    # 检查是否在Docker环境中
    IS_DOCKER=false
    if [ -f /.dockerenv ] || ([ -f /proc/1/cgroup ] && grep -q "docker\|container" /proc/1/cgroup); then
        IS_DOCKER=true
        info "检测到Docker环境，将配置MySQL客户端连接"
    fi
    
    # 检查是否有sudo命令
    HAS_SUDO=0
    if command -v sudo &> /dev/null; then
        HAS_SUDO=1
    fi
    
    # 解析.env文件中的数据库信息
    DB_NAME=""
    DB_USER="root"
    DB_PASS=""
    DB_HOST="localhost"
    DB_PORT="3306"
    MYSQL_ROOT_PASSWORD=""
    
    if [ -f ".env" ]; then
        # 从.env文件中提取数据库信息
        DB_NAME=$(grep -E "^(MYSQL_DATABASE|DB_NAME)=" .env | head -1 | cut -d= -f2)
        DB_USER=$(grep -E "^(MYSQL_USER|DB_USER)=" .env | head -1 | cut -d= -f2)
        DB_PASS=$(grep -E "^(MYSQL_PASSWORD|DB_PASSWORD)=" .env | head -1 | cut -d= -f2)
        DB_HOST=$(grep -E "^DB_HOST=" .env | cut -d= -f2 || echo "localhost")
        DB_PORT=$(grep -E "^DB_PORT=" .env | cut -d= -f2 || echo "3306")
        MYSQL_ROOT_PASSWORD=$(grep -E "^MYSQL_ROOT_PASSWORD=" .env | cut -d= -f2 || echo "")
    elif [ -f ".env.example" ]; then
        # 从.env.example文件中提取数据库信息
        DB_NAME=$(grep -E "^(MYSQL_DATABASE|DB_NAME)=" .env.example | head -1 | cut -d= -f2)
        DB_USER=$(grep -E "^(MYSQL_USER|DB_USER)=" .env.example | head -1 | cut -d= -f2)
        DB_PASS=$(grep -E "^(MYSQL_PASSWORD|DB_PASSWORD)=" .env.example | head -1 | cut -d= -f2)
        DB_HOST=$(grep -E "^DB_HOST=" .env.example | cut -d= -f2 || echo "localhost")
        DB_PORT=$(grep -E "^DB_PORT=" .env.example | cut -d= -f2 || echo "3306")
        MYSQL_ROOT_PASSWORD=$(grep -E "^MYSQL_ROOT_PASSWORD=" .env.example | cut -d= -f2 || echo "")
    fi
    
    if [ -z "$DB_NAME" ]; then
        DB_NAME="audio_app"
    fi
    
    # 确保密码非空，用于创建用户
    if [ -z "$DB_PASS" ]; then
        if [ -n "$MYSQL_ROOT_PASSWORD" ]; then
            DB_PASS="$MYSQL_ROOT_PASSWORD"
        else
            # 生成随机密码
            DB_PASS=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 12)
            info "生成随机密码: $DB_PASS"
        fi
    fi
    
    # 设置root密码（如果提供了）
    if [ -n "$MYSQL_ROOT_PASSWORD" ] && [ "$DB_USER" != "root" ]; then
        ROOT_PASS="$MYSQL_ROOT_PASSWORD"
    else
        ROOT_PASS="$DB_PASS"
    fi
    
    # 在Docker环境中，通常使用环境变量中指定的主机名
    if [ "$IS_DOCKER" = true ]; then
        if [ -n "$MYSQL_HOST" ]; then
            DB_HOST="$MYSQL_HOST"
        elif [ -n "$DB_HOST" ]; then
            # 使用.env中指定的主机名
            :
        else
            # Docker环境中默认使用主机网关（通常是host.docker.internal或172.17.0.1）
            if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]]; then
                # macOS或Windows环境下Docker使用特殊的DNS名称访问宿主机
                DB_HOST="host.docker.internal"
            else
                # Linux环境下尝试获取默认网关作为宿主机地址
                DEFAULT_GATEWAY=$(ip route | grep default | awk '{print $3}')
                if [ -n "$DEFAULT_GATEWAY" ]; then
                    DB_HOST="$DEFAULT_GATEWAY"
                else
                    DB_HOST="172.17.0.1"  # Docker默认网桥的网关地址
                fi
            fi
        fi
        
        info "Docker环境中使用MySQL主机: $DB_HOST"
    else
        # 启动MySQL服务（非Docker环境）
        info "在非Docker环境中尝试启动MySQL服务..."
        case $OS in
            ubuntu|debian)
                if [ $HAS_SUDO -eq 1 ]; then
                    sudo systemctl start mysql || info "无法启动MySQL服务，尝试检查MySQL是否已在运行"
                else
                    systemctl start mysql 2>/dev/null || info "无法启动MySQL服务，尝试检查MySQL是否已在运行"
                fi
                ;;
            centos|redhat|fedora)
                if [ $HAS_SUDO -eq 1 ]; then
                    sudo systemctl start mysqld || info "无法启动MySQL服务，尝试检查MySQL是否已在运行"
                else
                    systemctl start mysqld 2>/dev/null || info "无法启动MySQL服务，尝试检查MySQL是否已在运行"
                fi
                ;;
            alpine)
                if [ $HAS_SUDO -eq 1 ]; then
                    # 检查MariaDB数据目录是否需要初始化
                    if [ ! -d "/var/lib/mysql/mysql" ]; then
                        info "初始化MariaDB数据目录..."
                        sudo mysql_install_db --user=mysql --datadir=/var/lib/mysql || warning "MariaDB初始化失败"
                    fi
                    sudo rc-service mariadb start || info "无法启动MariaDB服务，尝试检查MariaDB是否已在运行"
                else
                    if [ ! -d "/var/lib/mysql/mysql" ]; then
                        info "初始化MariaDB数据目录..."
                        mysql_install_db --user=mysql --datadir=/var/lib/mysql 2>/dev/null || warning "MariaDB初始化失败"
                    fi
                    rc-service mariadb start 2>/dev/null || info "无法启动MariaDB服务，尝试检查MariaDB是否已在运行"
                fi
                ;;
            macos)
                brew services start mysql || info "无法启动MySQL服务，尝试检查MySQL是否已在运行"
                
                # macOS MySQL默认设置
                if [ -z "$ROOT_PASS" ]; then
                    info "配置MySQL root用户（macOS）..."
                    mysql -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '$ROOT_PASS';" 2>/dev/null || warning "无法设置root密码"
                fi
                ;;
            *)
                warning "未知操作系统，请手动启动MySQL服务"
                ;;
        esac
        
        # 配置MySQL字符集和时区（参考docker-compose.yml）
        info "配置MySQL字符集和时区..."
        
        if [ $HAS_SUDO -eq 1 ]; then
            MYSQL_CONF_DIR="/etc/mysql/conf.d"
            
            # 检查配置目录是否存在
            if [ ! -d "$MYSQL_CONF_DIR" ]; then
                if sudo mkdir -p "$MYSQL_CONF_DIR" 2>/dev/null; then
                    success "创建MySQL配置目录: $MYSQL_CONF_DIR"
                else
                    warning "无法创建MySQL配置目录，将跳过字符集配置"
                    MYSQL_CONF_DIR=""
                fi
            fi
            
            if [ -n "$MYSQL_CONF_DIR" ]; then
                # 创建自定义配置文件
                MYSQL_CUSTOM_CONF="$MYSQL_CONF_DIR/custom.cnf"
                
                if sudo tee "$MYSQL_CUSTOM_CONF" > /dev/null << EOF
[mysqld]
default-authentication-plugin=mysql_native_password
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
default-time-zone=+08:00

[client]
default-character-set=utf8mb4
EOF
                then
                    success "创建MySQL自定义配置文件: $MYSQL_CUSTOM_CONF"
                    
                    # 重启MySQL服务以应用配置
                    case $OS in
                        ubuntu|debian)
                            sudo systemctl restart mysql || info "无法重启MySQL服务"
                            ;;
                        centos|redhat|fedora)
                            sudo systemctl restart mysqld || info "无法重启MySQL服务"
                            ;;
                        alpine)
                            sudo rc-service mariadb restart || info "无法重启MariaDB服务"
                            ;;
                        macos)
                            brew services restart mysql || info "无法重启MySQL服务"
                            ;;
                    esac
                else
                    warning "无法创建MySQL自定义配置文件，将跳过字符集配置"
                fi
            fi
        else
            # 非sudo环境下的处理
            info "在非sudo环境中配置MySQL..."
            
            # 尝试在用户目录创建配置
            USER_MYSQL_DIR="$HOME/.my.cnf.d"
            mkdir -p "$USER_MYSQL_DIR" 2>/dev/null
            
            if [ -d "$USER_MYSQL_DIR" ]; then
                USER_MYSQL_CONF="$USER_MYSQL_DIR/custom.cnf"
                
                # 创建用户级别的MySQL配置
                cat > "$USER_MYSQL_CONF" << EOF
[mysqld]
default-authentication-plugin=mysql_native_password
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
default-time-zone=+08:00

[client]
default-character-set=utf8mb4
EOF
                success "在用户目录创建MySQL配置: $USER_MYSQL_CONF"
                
                # 在非sudo环境中尝试重启MySQL（不太可能成功，但尝试一下）
                case $OS in
                    ubuntu|debian)
                        systemctl restart mysql 2>/dev/null || info "无法重启MySQL服务，请完成部署后手动配置MySQL"
                        ;;
                    centos|redhat|fedora)
                        systemctl restart mysqld 2>/dev/null || info "无法重启MySQL服务，请完成部署后手动配置MySQL"
                        ;;
                    alpine)
                        rc-service mariadb restart 2>/dev/null || info "无法重启MariaDB服务，请完成部署后手动配置MySQL"
                        ;;
                    macos)
                        brew services restart mysql 2>/dev/null || info "无法重启MySQL服务，请完成部署后手动配置MySQL"
                        ;;
                esac
            else
                warning "无法创建用户级MySQL配置目录"
            fi
            
            # 向用户提供手动配置MySQL的说明
            info "由于您没有sudo权限，可能需要手动配置MySQL字符集和时区"
            info "建议的MySQL配置如下："
            echo "----------------------------------------"
            echo "[mysqld]"
            echo "default-authentication-plugin=mysql_native_password"
            echo "character-set-server=utf8mb4"
            echo "collation-server=utf8mb4_unicode_ci"
            echo "default-time-zone=+08:00"
            echo ""
            echo "[client]"
            echo "default-character-set=utf8mb4"
            echo "----------------------------------------"
            info "如果MySQL是由其他服务（如Docker Compose）管理的，您可以忽略此提示"
        fi
    fi
    
    info "将尝试连接到数据库: $DB_NAME (主机: $DB_HOST, 用户: $DB_USER)"
    
    # 检查MySQL服务是否正在运行
    MYSQL_RUNNING=0
    if command -v mysqladmin &> /dev/null; then
        # 尝试连接MySQL
        if mysqladmin ping -h "$DB_HOST" --silent &> /dev/null; then
            MYSQL_RUNNING=1
            success "MySQL服务正在运行（无需密码）"
        elif [ -n "$DB_PASS" ] && mysqladmin ping -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" --silent &> /dev/null; then
            MYSQL_RUNNING=1
            success "MySQL服务正在运行（需要密码）"
        else
            warning "无法连接到MySQL服务器 $DB_HOST"
            info "在Docker环境中，MySQL服务可能需要稍后启动，将继续后续步骤"
            if [ "$IS_DOCKER" = true ]; then
                # 在Docker环境中，我们通常只确保连接信息正确，而不尝试创建数据库
                MYSQL_RUNNING=0
            fi
        fi
    else
        warning "找不到mysqladmin命令，无法检查MySQL状态"
    fi
    
    # 更新.env文件中的数据库配置（无论是否连接成功）
    if [ -f ".env" ]; then
        info "更新.env文件中的数据库配置..."
        
        # 临时文件
        TMP_ENV=$(mktemp)
        
        # 创建或更新数据库配置
        cat .env | grep -v "^DB_NAME=" | grep -v "^DB_USER=" | grep -v "^DB_PASSWORD=" | grep -v "^DB_HOST=" | grep -v "^DB_PORT=" > "$TMP_ENV"
        echo "DB_NAME=$DB_NAME" >> "$TMP_ENV"
        echo "DB_USER=$DB_USER" >> "$TMP_ENV"
        echo "DB_PASSWORD=$DB_PASS" >> "$TMP_ENV"
        echo "DB_HOST=$DB_HOST" >> "$TMP_ENV"
        echo "DB_PORT=$DB_PORT" >> "$TMP_ENV"
        
        # 替换原文件
        mv "$TMP_ENV" .env
        
        success "已更新.env文件中的数据库配置"
    fi
    
    # 创建数据库和用户（如果MySQL正在运行且不在Docker环境中）
    if [ $MYSQL_RUNNING -eq 1 ] && [ -n "$DB_NAME" ]; then
        info "尝试创建数据库和配置用户..."
        
        # 尝试使用无密码root登录
        if mysql -h "$DB_HOST" -u root -e "SELECT 1" &>/dev/null; then
            # 创建数据库
            info "使用root无密码创建数据库..."
            mysql -h "$DB_HOST" -u root -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            
            # 如果用户不是root，创建用户并授予权限
            if [ "$DB_USER" != "root" ]; then
                info "创建MySQL用户: $DB_USER"
                mysql -h "$DB_HOST" -u root -e "CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';"
                mysql -h "$DB_HOST" -u root -e "GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'%';"
                mysql -h "$DB_HOST" -u root -e "FLUSH PRIVILEGES;"
            fi
            
            # 导入初始化SQL（如果存在）
            if [ -f "./mysql/init.sql" ]; then
                info "导入初始化SQL..."
                mysql -h "$DB_HOST" -u root "$DB_NAME" < ./mysql/init.sql && success "初始化SQL导入成功" || warning "初始化SQL导入失败"
            fi
            
            success "数据库 $DB_NAME 创建成功"
        # 尝试使用有密码root登录
        elif [ -n "$ROOT_PASS" ] && mysql -h "$DB_HOST" -u root -p"$ROOT_PASS" -e "SELECT 1" &>/dev/null; then
            # 创建数据库
            info "使用root有密码创建数据库..."
            mysql -h "$DB_HOST" -u root -p"$ROOT_PASS" -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            
            # 如果用户不是root，创建用户并授予权限
            if [ "$DB_USER" != "root" ]; then
                info "创建MySQL用户: $DB_USER"
                mysql -h "$DB_HOST" -u root -p"$ROOT_PASS" -e "CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';"
                mysql -h "$DB_HOST" -u root -p"$ROOT_PASS" -e "GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'%';"
                mysql -h "$DB_HOST" -u root -p"$ROOT_PASS" -e "FLUSH PRIVILEGES;"
            fi
            
            # 导入初始化SQL（如果存在）
            if [ -f "./mysql/init.sql" ]; then
                info "导入初始化SQL..."
                mysql -h "$DB_HOST" -u root -p"$ROOT_PASS" "$DB_NAME" < ./mysql/init.sql && success "初始化SQL导入成功" || warning "初始化SQL导入失败"
            fi
            
            success "数据库 $DB_NAME 创建成功"
        else
            warning "无法连接到MySQL服务器，可能需要手动创建数据库和用户"
            echo "请手动执行以下命令："
            echo "  mysql -h $DB_HOST -u root -p"
            echo "  CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            if [ "$DB_USER" != "root" ]; then
                echo "  CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';"
                echo "  GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'%';"
                echo "  FLUSH PRIVILEGES;"
            fi
            echo "  exit"
        fi
    else
        if [ "$IS_DOCKER" = true ]; then
            info "在Docker环境中，数据库将由Docker Compose或外部服务提供"
            info "已配置连接信息: 主机=$DB_HOST, 端口=$DB_PORT, 数据库=$DB_NAME, 用户=$DB_USER"
        else
            warning "跳过数据库创建"
        fi
    fi
    
    success "MySQL配置完成"
}

# 设置环境变量
setup_env() {
    info "正在设置环境变量..."
    
    # 检查是否存在.env文件
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        cp .env.example .env
        success "已从.env.example创建.env文件"
        
        # 提示用户编辑.env文件
        echo "请根据需要编辑.env文件中的配置："
        echo "  vim .env"
    elif [ ! -f ".env" ] && [ -f ".env.production" ]; then
        cp .env.production .env
        success "已从.env.production创建.env文件"
        
        # 提示用户编辑.env文件
        echo "请根据需要编辑.env文件中的配置："
        echo "  vim .env"
    elif [ ! -f ".env" ]; then
        warning "未找到.env文件模板，将创建基本.env文件"
        
        # 创建基本的.env文件
        cat > .env << EOF
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_NAME=audio_app
DB_USER=root
DB_PASSWORD=

# API配置
API_PORT=5002
EOF
        
        success "已创建基本.env文件，请根据需要进行编辑"
    else
        success "已存在.env文件，跳过创建"
    fi
}

# 创建必要目录
create_directories() {
    info "正在创建必要目录..."
    
    # 创建logs目录
    mkdir -p logs
    
    # 创建data目录
    mkdir -p data
    
    success "必要目录创建完成"
}

# 主函数
main() {
    echo "========================================"
    echo "       音频处理应用部署脚本"
    echo "========================================"
    
    detect_os
    detect_docker
    install_dependencies
    setup_python_env
    setup_nodejs_env
    setup_mysql
    setup_env
    create_directories
    
    echo ""
    echo "========================================"
    success "部署完成！"
    echo "========================================"
    echo ""
    echo "要启动服务，请运行 ./start.sh"
    echo ""
}

# 执行主函数
main
