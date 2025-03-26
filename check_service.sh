#!/bin/bash
set -e

echo "=========================="
echo "音频处理应用服务检查脚本"
echo "=========================="

# 检查MySQL服务
echo -n "检查MySQL服务... "
if mysqladmin ping -h localhost --silent; then
    echo "运行中 ✅"
else
    echo "未运行 ❌"
    echo "请运行 ./start.sh 启动服务"
    exit 1
fi

# 检查API服务
echo -n "检查API服务... "
if pgrep -f "python api/app.py" > /dev/null; then
    echo "运行中 ✅"
    API_PID=$(pgrep -f "python api/app.py")
    echo "  • API PID: $API_PID"
    
    # 检查API是否可访问
    echo -n "  • API可访问性: "
    if curl -s http://localhost:5002/api/health | grep -q "ok"; then
        echo "正常 ✅"
    else
        echo "异常 ❌"
        echo "    API服务可能未正确启动，请检查日志: logs/api.log"
    fi
else
    echo "未运行 ❌"
    echo "请运行 ./start.sh 启动服务"
fi

# 检查前端服务
echo -n "检查前端服务... "
if pgrep -f "npm start" > /dev/null; then
    echo "运行中 ✅"
    FRONTEND_PID=$(pgrep -f "npm start")
    echo "  • 前端 PID: $FRONTEND_PID"
    
    # 检查前端是否可访问
    echo -n "  • 前端可访问性: "
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
        echo "正常 ✅"
    else
        echo "异常 ❌"
        echo "    前端服务可能未正确启动，请检查日志: logs/frontend.log"
    fi
else
    echo "未运行 ❌"
    echo "请运行 ./start.sh 启动服务"
fi

# 检查磁盘空间
echo -n "检查磁盘空间... "
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 90 ]; then
    echo "正常 ($DISK_USAGE%) ✅"
else
    echo "警告 ($DISK_USAGE%) ⚠️"
    echo "  • 磁盘空间不足，可能影响服务性能"
fi

# 检查内存使用
echo -n "检查内存使用... "
MEM_AVAILABLE=$(free -m | grep "Mem:" | awk '{print $7}')
if [ "$MEM_AVAILABLE" -gt 1000 ]; then
    echo "正常 (${MEM_AVAILABLE}MB可用) ✅"
else
    echo "警告 (仅${MEM_AVAILABLE}MB可用) ⚠️"
    echo "  • 可用内存较少，可能影响服务性能"
fi

# 检查CPU负载
echo -n "检查CPU负载... "
LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}' | sed 's/ //g')
LOAD_INT=${LOAD%.*}
if [ "$LOAD_INT" -lt 4 ]; then
    echo "正常 ($LOAD) ✅"
else
    echo "警告 ($LOAD) ⚠️"
    echo "  • CPU负载较高，可能影响服务性能"
fi

# 如果一切正常，显示服务访问信息
if pgrep -f "python api/app.py" > /dev/null && pgrep -f "npm start" > /dev/null; then
    echo ""
    echo "所有服务运行正常! 您可以通过以下地址访问应用:"
    echo "  • 前端: http://localhost:3000"
    echo "  • API: http://localhost:5002/api"
    echo ""
    exit 0
else
    echo ""
    echo "有服务未正常运行，请检查问题后重新启动服务"
    echo ""
    exit 1
fi 