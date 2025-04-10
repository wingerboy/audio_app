#!/bin/bash

# 颜色设置
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# 日志函数
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 杀死现有进程
kill_processes() {
    info "停止现有服务..."
    
    # 查找并终止后端Python进程
    BACKEND_PIDS=$(ps aux | grep "python -m api.app" | grep -v grep | awk '{print $2}')
    if [ -n "$BACKEND_PIDS" ]; then
        for PID in $BACKEND_PIDS; do
            info "终止后端进程: $PID"
            kill -9 $PID 2>/dev/null
        done
    else
        info "未发现运行中的后端进程"
    fi
    
    # 查找并终止前端npm进程
    FRONTEND_PIDS=$(ps aux | grep "npm run dev" | grep -v grep | awk '{print $2}')
    if [ -n "$FRONTEND_PIDS" ]; then
        for PID in $FRONTEND_PIDS; do
            info "终止前端进程: $PID"
            kill -9 $PID 2>/dev/null
        done
    else
        info "未发现运行中的前端进程"
    fi
    
    # 等待进程完全终止
    sleep 2
    success "所有现有服务已停止"
}

# 确保日志目录存在
ensure_dirs() {
    mkdir -p logs
    success "确保日志目录存在"
}

# 启动后端服务
start_backend() {
    info "启动后端服务..."
    
    # 启动后端并将输出重定向到日志文件
    nohup python -m api.app > logs/backend.log 2>&1 &
    BACKEND_PID=$!
    
    # 检查进程是否启动成功
    sleep 2
    if ps -p $BACKEND_PID > /dev/null; then
        echo $BACKEND_PID > .backend.pid
        success "后端服务已启动，PID: $BACKEND_PID，日志位于: logs/backend.log"
        success "后端API地址: http://localhost:5002/api"
    else
        error "后端服务启动失败，请检查日志: logs/backend.log"
        exit 1
    fi
}

# 启动前端服务
start_frontend() {
    info "启动前端服务..."
    
    # 进入前端目录
    cd frontend
    
    # 确保node_modules存在
    if [ ! -d "node_modules" ]; then
        info "安装前端依赖..."
        npm install || {
            cd ..
            error "安装前端依赖失败"
            exit 1
        }
    fi
    
    # 启动前端并将输出重定向到日志文件
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    # 返回项目根目录
    cd ..
    
    # 检查进程是否启动成功
    sleep 5
    if ps -p $FRONTEND_PID > /dev/null; then
        echo $FRONTEND_PID > .frontend.pid
        success "前端服务已启动，PID: $FRONTEND_PID，日志位于: logs/frontend.log"
        success "前端访问地址: http://localhost:3000"
    else
        error "前端服务启动失败，请检查日志: logs/frontend.log"
        exit 1
    fi
}

# 主函数
main() {
    echo "========================================"
    echo "       一键启动音频处理应用"
    echo "========================================"
    
    # 杀死现有进程
    kill_processes
    
    # 确保日志目录存在
    ensure_dirs
    
    # 启动后端服务
    start_backend
    
    # 启动前端服务
    start_frontend
    
    echo ""
    echo "========================================"
    success "所有服务已成功启动"
    echo "后端API地址: http://localhost:5002/api"
    echo "前端访问地址: http://localhost:3000"
    echo "后端日志: logs/backend.log"
    echo "前端日志: logs/frontend.log"
    echo ""
    echo "要查看日志可以使用:"
    echo "  后端: tail -f logs/backend.log"
    echo "  前端: tail -f logs/frontend.log"
    echo ""
    echo "要停止服务可以再次运行此脚本或使用:"
    echo "  kill \$(cat .backend.pid) \$(cat .frontend.pid)"
    echo "========================================"
}

# 执行主函数
main 