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
                success "通过参数指定为Docker容器环境"
                ;;
            --local)
                IS_DOCKER=false
                FORCE_DOCKER=false
                export IS_DOCKER=false
                export FORCE_DOCKER=false
                export CONTAINER_DEPLOY=false
                success "通过参数指定为本地环境"
                ;;
            --help)
                echo "使用方法: $0 [选项]"
                echo "选项:"
                echo "  --docker    指定为Docker容器环境"
                echo "  --local     指定为本地环境（默认）"
                echo "  --help      显示此帮助信息"
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
    esac
    
    success "检测到操作系统: $OS $VER"
    export OS
    export VER
}

# 配置Docker环境
setup_docker_env() {
    if [ "$IS_DOCKER" = true ]; then
        success "配置Docker容器环境..."
        
        # 设置容器内默认值
        export CONTAINER_DEPLOY=true
        
        # 设置数据库主机 - 直接使用localhost
        export MYSQL_HOST="localhost"
        info "在容器内使用MySQL主机: $MYSQL_HOST"
        
        # 更新数据库端口
        export MYSQL_PORT=${MYSQL_PORT:-"3306"}
        
        # 应用级设置
        export FLASK_ENV="production"
        
        # 如果.env文件存在，更新其中的DB_HOST
        if [ -f ".env" ]; then
            # 创建一个临时文件
            TMP_ENV=$(mktemp)
            
            # 更新DB_HOST
            cat .env | grep -v "^DB_HOST=" > "$TMP_ENV"
            echo "DB_HOST=$MYSQL_HOST" >> "$TMP_ENV"
            echo "CONTAINER_DEPLOY=true" >> "$TMP_ENV"
            
            # 替换原文件
            mv "$TMP_ENV" .env
            
            info "已更新.env文件中的DB_HOST为: $MYSQL_HOST"
        fi
    else
        info "配置本地环境模式"
        export CONTAINER_DEPLOY=false
    fi
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
                    info "在非sudo环境中尝试安装Python..."
                    apt-get update 2>/dev/null || warning "apt-get update失败，可能需要root权限"
                    apt-get install -y python3 python3-pip python3-venv 2>/dev/null || warning "无法安装Python，请手动安装Python 3.9"
                fi
                ;;
            centos|redhat|fedora)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装Python 3.9..."
                    sudo yum install -y python3 python3-pip python3-devel
                else
                    info "在非sudo环境中尝试安装Python..."
                    yum install -y python3 python3-pip python3-devel 2>/dev/null || warning "无法安装Python，请手动安装Python 3.9"
                fi
                ;;
            alpine)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装Python 3.9..."
                    sudo apk add python3 py3-pip python3-dev
                else
                    info "在非sudo环境中尝试安装Python..."
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
    
    # 确保Python venv包已安装（特别是对于Python 3.10版本）
    info "检查Python venv包是否已安装..."
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    NEED_VENV=0
    
    # 检查是否已安装venv模块
    if ! python3 -m venv --help &>/dev/null; then
        NEED_VENV=1
    fi
    
    if [ $NEED_VENV -eq 1 ]; then
        case $OS in
            ubuntu|debian)
                PYTHON_MAJOR_MINOR=${PYTHON_VERSION//.}  # 移除点号，例如3.10变为310
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装Python venv包..."
                    sudo apt-get update
                    # 尝试安装特定版本的venv
                    sudo apt-get install -y python${PYTHON_VERSION}-venv || sudo apt-get install -y python3-venv
                else
                    info "在非sudo环境中尝试安装Python venv包..."
                    apt-get update 2>/dev/null || warning "apt-get update失败，可能需要root权限"
                    apt-get install -y python${PYTHON_VERSION}-venv 2>/dev/null || apt-get install -y python3-venv 2>/dev/null || warning "无法安装Python venv包，请手动安装"
                fi
                ;;
            centos|redhat|fedora)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装Python venv包..."
                    sudo yum install -y python3-virtualenv || sudo yum install -y python-virtualenv
                else
                    info "在非sudo环境中尝试安装Python venv包..."
                    yum install -y python3-virtualenv 2>/dev/null || yum install -y python-virtualenv 2>/dev/null || warning "无法安装Python venv包，请手动安装"
                fi
                ;;
            alpine)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装Python venv包..."
                    sudo apk add py3-virtualenv
                else
                    info "在非sudo环境中尝试安装Python venv包..."
                    apk add py3-virtualenv 2>/dev/null || warning "无法安装Python venv包，请手动安装"
                fi
                ;;
            macos)
                # macOS通常不需要单独安装venv
                ;;
            *)
                warning "未知操作系统，请手动安装Python venv包"
                ;;
        esac
    else
        success "Python venv包已安装"
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
                    info "在非sudo环境中尝试安装FFmpeg..."
                    apt-get update 2>/dev/null || warning "apt-get update失败，可能需要root权限"
                    apt-get install -y ffmpeg 2>/dev/null || warning "无法安装FFmpeg，请手动安装FFmpeg"
                fi
                ;;
            centos|redhat|fedora)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装FFmpeg..."
                    sudo yum install -y epel-release
                    sudo yum install -y ffmpeg ffmpeg-devel
                else
                    info "在非sudo环境中尝试安装FFmpeg..."
                    yum install -y epel-release 2>/dev/null || warning "无法安装epel-release，可能需要root权限"
                    yum install -y ffmpeg ffmpeg-devel 2>/dev/null || warning "无法安装FFmpeg，请手动安装FFmpeg"
                fi
                ;;
            alpine)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装FFmpeg..."
                    sudo apk add ffmpeg
                else
                    info "在非sudo环境中尝试安装FFmpeg..."
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
                
                # 尝试多个源，首先是国内源
                info "尝试从国内镜像下载NVM..."
                curl --connect-timeout 10 --retry 3 -o- https://gitee.com/mirrors/nvm/raw/master/install.sh | bash && {
                    success "从Gitee镜像成功下载NVM"
                } || {
                    info "国内镜像下载失败，尝试GitHub源..."
                    curl --connect-timeout 20 --retry 3 -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash || {
                        warning "NVM安装失败"
                        # 下载失败时直接下载到本地然后执行
                        info "尝试先下载安装脚本到本地再执行..."
                        mkdir -p "/tmp/nvm-install"
                        if curl --connect-timeout 20 --retry 3 -o "/tmp/nvm-install/nvm-install.sh" https://gitee.com/mirrors/nvm/raw/master/install.sh; then
                            chmod +x "/tmp/nvm-install/nvm-install.sh"
                            bash "/tmp/nvm-install/nvm-install.sh" || warning "安装脚本执行失败"
                        else
                            warning "无法下载NVM安装脚本"
                        fi
                    }
                }
            elif command -v wget &> /dev/null; then
                info "使用wget下载NVM..."
                
                # 尝试多个源，首先是国内源
                info "尝试从国内镜像下载NVM..."
                wget --timeout=10 --tries=3 -qO- https://gitee.com/mirrors/nvm/raw/master/install.sh | bash && {
                    success "从Gitee镜像成功下载NVM"
                } || {
                    info "国内镜像下载失败，尝试GitHub源..."
                    wget --timeout=20 --tries=3 -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash || {
                        warning "使用wget下载NVM失败"
                        
                        # 下载失败时直接下载到本地然后执行
                        info "尝试先下载安装脚本到本地再执行..."
                        mkdir -p "/tmp/nvm-install"
                        if wget --timeout=20 --tries=3 -O "/tmp/nvm-install/nvm-install.sh" https://gitee.com/mirrors/nvm/raw/master/install.sh; then
                            chmod +x "/tmp/nvm-install/nvm-install.sh"
                            bash "/tmp/nvm-install/nvm-install.sh" || warning "安装脚本执行失败"
                        else
                            warning "无法下载NVM安装脚本"
                        fi
                    }
                }
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
                warning "Node.js安装似乎失败，尝试使用备选方案"
                install_node_binary
            fi
        else
            warning "NVM安装失败或不可用，尝试使用备选方案安装Node.js"
            install_node_binary
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
                    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-client || {
                        warning "安装MySQL客户端失败，尝试修复包管理器..."
                        sudo apt-get --fix-broken install -y
                        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-client || warning "无法安装MySQL客户端，请手动安装"
                    }
                    
                    if [ "$IS_DOCKER" != true ]; then
                        # 在非Docker环境中安装完整的MySQL服务器
                        info "安装MySQL服务器..."
                        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server || {
                            warning "安装MySQL服务器失败，尝试替代方法..."
                            # 尝试安装mariadb-server作为替代
                            sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mariadb-server || {
                                # 尝试修复可能的依赖问题
                                sudo apt-get --fix-broken install -y
                                sudo apt-get update
                                sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server || warning "无法安装MySQL服务器，请手动安装"
                            }
                        }
                    fi
                else
                    info "在非sudo环境中尝试安装MySQL..."
                    apt-get update 2>/dev/null || warning "apt-get update失败，可能需要root权限"
                    DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-client 2>/dev/null || warning "无法安装MySQL客户端，请手动安装"
                    if [ "$IS_DOCKER" != true ]; then
                        # 在非Docker环境中安装完整的MySQL服务器
                        DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server 2>/dev/null || {
                            warning "安装MySQL服务器失败，尝试使用mariadb..."
                            DEBIAN_FRONTEND=noninteractive apt-get install -y mariadb-server 2>/dev/null || warning "无法安装MySQL/MariaDB服务器，请手动安装"
                        }
                    fi
                fi
                ;;
            centos|redhat|fedora)
                if [ $HAS_SUDO -eq 1 ]; then
                    info "安装MySQL..."
                    # 尝试安装MariaDB作为首选（CentOS/RHEL 8+默认）
                    sudo yum install -y mariadb mariadb-client &>/dev/null || {
                        # 回退到MySQL
                        sudo yum install -y mysql || warning "无法安装MySQL客户端，请手动安装"
                    }
                    
                    if [ "$IS_DOCKER" != true ]; then
                        # 在非Docker环境中安装完整的MySQL服务器
                        info "安装数据库服务器..."
                        sudo yum install -y mariadb-server &>/dev/null || {
                            # 回退到MySQL服务器
                            sudo yum install -y mysql-server || {
                                # 对于较新的CentOS/RHEL，可能需要从特定的repo安装
                                info "尝试使用额外的仓库安装MySQL..."
                                sudo yum install -y https://repo.mysql.com/mysql80-community-release-el$(rpm -E '%{rhel}').rpm &>/dev/null
                                sudo yum install -y mysql-community-server || warning "无法安装MySQL/MariaDB服务器，请手动安装"
                            }
                        }
                    fi
                else
                    info "在非sudo环境中尝试安装MySQL..."
                    yum install -y mariadb mariadb-client &>/dev/null || 
                    yum install -y mysql 2>/dev/null || warning "无法安装MySQL客户端，请手动安装"
                    
                    if [ "$IS_DOCKER" != true ]; then
                        # 在非Docker环境中安装完整的MySQL服务器
                        yum install -y mariadb-server &>/dev/null || 
                        yum install -y mysql-server 2>/dev/null || warning "无法安装MySQL/MariaDB服务器，请手动安装"
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
        # 尝试使用Python venv模块创建虚拟环境
        python3 -m venv venv
        
        # 检查venv创建是否成功
        if [ ! -d "venv" ] || [ ! -f "venv/bin/python" ]; then
            warning "venv创建失败，尝试使用替代方法..."
            
            # 尝试使用virtualenv工具
            if command -v virtualenv &> /dev/null; then
                info "使用virtualenv创建虚拟环境..."
                virtualenv venv || {
                    warning "virtualenv创建失败，尝试手动创建目录结构..."
                    
                    # 手动创建最小venv结构
                    mkdir -p venv/bin venv/lib venv/include
                    if command -v python3 &> /dev/null; then
                        # 创建python链接
                        ln -sf $(which python3) venv/bin/python
                        ln -sf $(which python3) venv/bin/python3
                        
                        # 创建pip链接
                        if command -v pip3 &> /dev/null; then
                            ln -sf $(which pip3) venv/bin/pip
                            ln -sf $(which pip3) venv/bin/pip3
                        fi
                        
                        success "手动创建基本虚拟环境结构成功"
                    else
                        error "无法找到Python3，无法创建虚拟环境"
                    fi
                }
            else
                error "无法创建Python虚拟环境，请确保python3-venv已安装或手动安装virtualenv"
            fi
        else
            success "虚拟环境创建成功"
        fi
    fi
    
    # 激活虚拟环境
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        PY_VER=$(python --version 2>&1)
        success "虚拟环境激活成功：$PY_VER"
    else
        warning "找不到虚拟环境激活脚本，尝试使用系统Python"
        # 确保系统Python可用
        if ! command -v python3 &> /dev/null; then
            error "找不到Python3，请确保Python已正确安装"
        fi
    fi
    
    # 升级pip
    info "升级pip..."
    python3 -m pip install --upgrade pip || warning "pip升级失败，继续使用当前版本"
    
    # 安装项目依赖
    if [ -f "requirements.txt" ]; then
        info "安装项目依赖..."
        python3 -m pip install -r requirements.txt || warning "依赖安装失败，请检查requirements.txt"
    else
        warning "未找到requirements.txt文件，跳过Python依赖安装"
    fi
    
    success "Python环境设置完成"
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
            # 尝试多个源，首先是国内源
            info "尝试从国内镜像下载NVM..."
            curl --connect-timeout 10 --retry 3 -o- https://gitee.com/mirrors/nvm/raw/master/install.sh | bash && {
                success "从Gitee镜像成功下载NVM"
            } || {
                info "国内镜像下载失败，尝试GitHub源..."
                curl --connect-timeout 20 --retry 3 -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash || {
                    warning "NVM安装失败"
                    # 下载失败时直接下载到本地然后执行
                    info "尝试先下载安装脚本到本地再执行..."
                    mkdir -p "/tmp/nvm-install"
                    if curl --connect-timeout 20 --retry 3 -o "/tmp/nvm-install/nvm-install.sh" https://gitee.com/mirrors/nvm/raw/master/install.sh; then
                        chmod +x "/tmp/nvm-install/nvm-install.sh"
                        bash "/tmp/nvm-install/nvm-install.sh" || warning "安装脚本执行失败"
                    else
                        warning "无法下载NVM安装脚本"
                    fi
                }
            }
            
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
    
    # 在Docker环境中，使用localhost作为MySQL主机
    if [ "$IS_DOCKER" = true ]; then
        # 直接设置为localhost，忽略其他设置
        DB_HOST="localhost"
        info "Docker环境中使用MySQL主机: $DB_HOST"
        info "在容器中运行，假设MySQL服务由宿主机或其他容器提供"
    else
        # 启动MySQL服务（非Docker环境）
        info "在本地环境中尝试启动MySQL服务..."
        case $OS in
            ubuntu|debian)
                if [ $HAS_SUDO -eq 1 ]; then
                    sudo systemctl start mysql || sudo service mysql start || info "无法启动MySQL服务，尝试检查MySQL是否已在运行"
                else
                    systemctl start mysql 2>/dev/null || service mysql start 2>/dev/null || info "无法启动MySQL服务，尝试检查MySQL是否已在运行"
                fi
                ;;
            centos|redhat|fedora)
                if [ $HAS_SUDO -eq 1 ]; then
                    sudo systemctl start mysqld || sudo service mysqld start || info "无法启动MySQL服务，尝试检查MySQL是否已在运行"
                else
                    systemctl start mysqld 2>/dev/null || service mysqld start 2>/dev/null || info "无法启动MySQL服务，尝试检查MySQL是否已在运行"
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
                            sudo systemctl restart mysql || sudo service mysql restart || info "无法重启MySQL服务"
                            ;;
                        centos|redhat|fedora)
                            sudo systemctl restart mysqld || sudo service mysqld restart || info "无法重启MySQL服务"
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
                        systemctl restart mysql 2>/dev/null || service mysql restart 2>/dev/null || info "无法重启MySQL服务，请完成部署后手动配置MySQL"
                        ;;
                    centos|redhat|fedora)
                        systemctl restart mysqld 2>/dev/null || service mysqld restart 2>/dev/null || info "无法重启MySQL服务，请完成部署后手动配置MySQL"
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
    
    info "将尝试连接到数据库: $DB_NAME (主机: $DB_HOST, 用户: $DB_USER, 密码: $DB_PASS)"
    
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
            if [ "$IS_DOCKER" = true ]; then
                warning "无法连接到MySQL服务器 $DB_HOST"
                info "在Docker环境中，MySQL服务可能需要稍后启动，将继续后续步骤"
                # 在Docker环境中，设置外部数据库连接而不报错退出
                export MYSQL_HOST=$DB_HOST
                export MYSQL_PORT=$DB_PORT
                export MYSQL_DATABASE=$DB_NAME
                export MYSQL_USER=$DB_USER
                export MYSQL_PASSWORD=$DB_PASS
            else
                warning "无法连接到MySQL服务器 $DB_HOST"
                # 尝试设置本地默认值
                if [ "$DB_HOST" != "localhost" ]; then
                    info "尝试使用localhost作为替代连接点..."
                    DB_HOST="localhost"
                    
                    # 重新尝试连接
                    if mysqladmin ping -h "$DB_HOST" --silent &> /dev/null; then
                        MYSQL_RUNNING=1
                        success "MySQL服务在localhost正在运行（无需密码）"
                    elif [ -n "$DB_PASS" ] && mysqladmin ping -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" --silent &> /dev/null; then
                        MYSQL_RUNNING=1
                        success "MySQL服务在localhost正在运行（需要密码）"
                    fi
                fi
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
        
        # 在Docker环境中添加标记
        if [ "$IS_DOCKER" = true ]; then
            echo "CONTAINER_DEPLOY=true" >> "$TMP_ENV"
        fi
        
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
            if [ "$IS_DOCKER" = true ]; then
                info "在容器环境中使用外部数据库，确保数据库已创建并配置了适当权限"
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
        fi
    else
        if [ "$IS_DOCKER" = true ]; then
            info "在Docker环境中，数据库将由宿主机或外部服务提供"
            info "已配置连接信息: 主机=$DB_HOST, 端口=$DB_PORT, 数据库=$DB_NAME, 用户=$DB_USER"
        else
            warning "跳过数据库创建，服务可能还未启动"
        fi
    fi
    
    success "MySQL配置完成"
}

# 设置环境变量
setup_env() {
    info "正在设置环境变量..."
    
    # 从环境变量获取数据库连接信息
    DB_HOST_ENV=${MYSQL_HOST:-"localhost"}
    DB_PORT_ENV=${MYSQL_PORT:-"3306"}
    DB_NAME_ENV=${MYSQL_DATABASE:-"audio_app"}
    DB_USER_ENV=${MYSQL_USER:-"root"}
    DB_PASSWORD_ENV=${MYSQL_PASSWORD:-""}
    
    # 检查是否存在.env文件
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        cp .env.example .env
        success "已从.env.example创建.env文件"
    elif [ ! -f ".env" ] && [ -f ".env.production" ]; then
        cp .env.production .env
        success "已从.env.production创建.env文件"
    elif [ ! -f ".env" ]; then
        warning "未找到.env文件模板，将创建基本.env文件"
        
        # 创建基本的.env文件
        cat > .env << EOF
# 数据库配置
DB_HOST=${DB_HOST_ENV}
DB_PORT=${DB_PORT_ENV}
DB_NAME=${DB_NAME_ENV}
DB_USER=${DB_USER_ENV}
DB_PASSWORD=${DB_PASSWORD_ENV}

# API配置
API_PORT=5002

# 容器配置
CONTAINER_DEPLOY=${CONTAINER_DEPLOY:-false}
EOF
        
        success "已创建基本.env文件，使用环境变量填充数据库连接信息"
    else
        success "已存在.env文件，更新数据库连接信息..."
        
        # 临时文件
        TMP_ENV=$(mktemp)
        
        # 更新数据库配置
        cat .env | grep -v "^DB_HOST=" | grep -v "^DB_PORT=" | grep -v "^DB_NAME=" | grep -v "^DB_USER=" | grep -v "^DB_PASSWORD=" | grep -v "^CONTAINER_DEPLOY=" > "$TMP_ENV"
        echo "DB_HOST=${DB_HOST_ENV}" >> "$TMP_ENV"
        echo "DB_PORT=${DB_PORT_ENV}" >> "$TMP_ENV"
        echo "DB_NAME=${DB_NAME_ENV}" >> "$TMP_ENV"
        echo "DB_USER=${DB_USER_ENV}" >> "$TMP_ENV"
        echo "DB_PASSWORD=${DB_PASSWORD_ENV}" >> "$TMP_ENV"
        echo "CONTAINER_DEPLOY=${CONTAINER_DEPLOY:-false}" >> "$TMP_ENV"
        
        # 替换原文件
        mv "$TMP_ENV" .env
    fi
    
    # 在Docker环境中，导出可见的环境变量
    if [ "$IS_DOCKER" = true ]; then
        # 在当前会话中设置环境变量
        export DB_HOST=${DB_HOST_ENV}
        export DB_PORT=${DB_PORT_ENV}
        export DB_NAME=${DB_NAME_ENV}
        export DB_USER=${DB_USER_ENV}
        export DB_PASSWORD=${DB_PASSWORD_ENV}
        
        # 将环境变量添加到shell配置文件
        ENV_CONFIG_FILE=""
        if [ -f "$HOME/.bashrc" ]; then
            ENV_CONFIG_FILE="$HOME/.bashrc"
        elif [ -f "$HOME/.bash_profile" ]; then
            ENV_CONFIG_FILE="$HOME/.bash_profile"
        elif [ -f "$HOME/.profile" ]; then
            ENV_CONFIG_FILE="$HOME/.profile"
        fi
        
        if [ ! -z "$ENV_CONFIG_FILE" ]; then
            info "更新Shell环境变量配置: $ENV_CONFIG_FILE"
            
            # 添加环境变量到配置文件
            echo "# Audio App环境变量 - 由deploy.sh添加" >> "$ENV_CONFIG_FILE"
            echo "export DB_HOST=${DB_HOST_ENV}" >> "$ENV_CONFIG_FILE"
            echo "export DB_PORT=${DB_PORT_ENV}" >> "$ENV_CONFIG_FILE"
            echo "export DB_NAME=${DB_NAME_ENV}" >> "$ENV_CONFIG_FILE"
            echo "export DB_USER=${DB_USER_ENV}" >> "$ENV_CONFIG_FILE"
            echo "export DB_PASSWORD=${DB_PASSWORD_ENV}" >> "$ENV_CONFIG_FILE"
            echo "export CONTAINER_DEPLOY=true" >> "$ENV_CONFIG_FILE"
            
            success "已更新shell环境变量配置"
        fi
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

# 定义安装Node.js二进制包的函数
install_node_binary() {
    info "尝试直接安装Node.js二进制包..."
    
    # 创建本地Node.js目录
    mkdir -p "$HOME/.node"
    
    # 根据系统架构确定下载地址
    ARCH=$(uname -m)
    NODE_VER="v18.18.2"
    NODE_DIST="node-${NODE_VER}"
    
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
    
    # 根据操作系统确定下载文件
    case $OS in
        macos)
            NODE_OS="darwin"
            NODE_EXT="tar.gz"
            ;;
        *)
            NODE_OS="linux"
            NODE_EXT="tar.gz"
            ;;
    esac
    
    # 构建下载URL (优先使用国内镜像)
    NODE_MIRROR="https://npmmirror.com/mirrors/node"
    NODE_URL="${NODE_MIRROR}/${NODE_VER}/${NODE_DIST}-${NODE_OS}-${NODE_ARCH}.${NODE_EXT}"
    GITHUB_URL="https://nodejs.org/dist/${NODE_VER}/${NODE_DIST}-${NODE_OS}-${NODE_ARCH}.${NODE_EXT}"
    
    info "尝试从国内镜像下载Node.js: ${NODE_URL}..."
    
    # 下载Node.js二进制包
    DOWNLOAD_SUCCESS=0
    
    if command -v curl &> /dev/null; then
        curl --connect-timeout 10 --retry 3 -L -o "$HOME/.node/node.tar.gz" "$NODE_URL" && DOWNLOAD_SUCCESS=1 || {
            info "国内镜像下载失败，尝试从官方网站下载: ${GITHUB_URL}..."
            curl --connect-timeout 20 --retry 3 -L -o "$HOME/.node/node.tar.gz" "$GITHUB_URL" && DOWNLOAD_SUCCESS=1 || warning "无法下载Node.js"
        }
    elif command -v wget &> /dev/null; then
        wget --timeout=10 --tries=3 -O "$HOME/.node/node.tar.gz" "$NODE_URL" && DOWNLOAD_SUCCESS=1 || {
            info "国内镜像下载失败，尝试从官方网站下载: ${GITHUB_URL}..."
            wget --timeout=20 --tries=3 -O "$HOME/.node/node.tar.gz" "$GITHUB_URL" && DOWNLOAD_SUCCESS=1 || warning "无法下载Node.js"
        }
    else
        warning "未安装curl或wget，无法下载Node.js"
        return 1
    fi
    
    if [ $DOWNLOAD_SUCCESS -eq 1 ]; then
        info "解压Node.js二进制文件..."
        tar -xzf "$HOME/.node/node.tar.gz" -C "$HOME/.node" || {
            warning "解压Node.js失败"
            return 1
        }
        rm -f "$HOME/.node/node.tar.gz"
        
        # 找到解压出的目录
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
            
            # 验证安装
            if command -v node &> /dev/null; then
                NODE_VER=$(node --version)
                NPM_VER=$(npm --version 2>/dev/null || echo "未知")
                success "Node.js二进制文件安装成功：Node.js ${NODE_VER} (npm: ${NPM_VER})"
                return 0
            else
                warning "Node.js路径设置失败，请手动将 ${NODE_DIR}/bin 添加到PATH环境变量"
                return 1
            fi
        else
            warning "找不到解压后的Node.js目录"
            return 1
        fi
    fi
    
    return 1
}

# 主函数
main() {
    echo "========================================"
    echo "       音频处理应用部署脚本"
    echo "========================================"
    
    # 解析命令行参数
    parse_args "$@"
    
    # 检测操作系统环境
    detect_os
    
    # 配置Docker环境（不再自动检测）
    setup_docker_env
    
    # 如果在Docker中，提示用户
    if [ "$IS_DOCKER" = true ]; then
        info "在Docker容器内进行部署，将自动选择适当的配置"
    fi
    
    # 安装依赖
    install_dependencies
    
    # 设置环境
    setup_python_env
    setup_nodejs_env
    
    # 配置MySQL（在Docker中可能连接到外部MySQL）
    setup_mysql
    
    # 设置环境变量
    setup_env
    
    # 创建目录
    create_directories
    
    # 创建启动脚本的启动命令
    if [ "$IS_DOCKER" = true ]; then
        echo ""
        echo "在容器内，您可以使用以下命令启动应用："
        echo "  ./start.sh"
        echo ""
        echo "如需在后台运行，可以使用："
        echo "  nohup ./start.sh &> /dev/null &"
        echo ""
    fi
    
    echo ""
    echo "========================================"
    success "部署完成！"
    echo "========================================"
    echo ""
    echo "要启动服务，请运行 ./start.sh"
    echo "Docker环境下请使用: ./start.sh --docker"
    echo "本地环境下请使用: ./start.sh --local"
    echo ""
}

# 执行主函数，传递命令行参数
main "$@"
