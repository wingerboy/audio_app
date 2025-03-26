#!/bin/bash

show_help() {
  echo "使用方法: $0 [选项]"
  echo "实时查看音频处理应用的日志"
  echo ""
  echo "选项:"
  echo "  -a, --api       查看API日志"
  echo "  -f, --frontend  查看前端日志"
  echo "  -b, --both      同时查看API和前端日志（默认）"
  echo "  -h, --help      显示此帮助"
  echo ""
  echo "示例:"
  echo "  $0 -a           # 仅查看API日志"
  echo "  $0 -f           # 仅查看前端日志"
  echo "  $0              # 同时查看所有日志"
}

check_log_files() {
  if [ ! -f "logs/api.log" ]; then
    mkdir -p logs
    touch logs/api.log
    echo "$(date): 创建API日志文件" > logs/api.log
  fi
  
  if [ ! -f "logs/frontend.log" ]; then
    mkdir -p logs
    touch logs/frontend.log
    echo "$(date): 创建前端日志文件" > logs/frontend.log
  fi
}

# 默认查看两种日志
VIEW_API=true
VIEW_FRONTEND=true

# 解析命令行参数
while [ "$1" != "" ]; do
  case $1 in
    -a | --api )
      VIEW_API=true
      VIEW_FRONTEND=false
      ;;
    -f | --frontend )
      VIEW_API=false
      VIEW_FRONTEND=true
      ;;
    -b | --both )
      VIEW_API=true
      VIEW_FRONTEND=true
      ;;
    -h | --help )
      show_help
      exit 0
      ;;
    * )
      echo "未知选项: $1"
      show_help
      exit 1
      ;;
  esac
  shift
done

# 确保日志文件存在
check_log_files

# 查看日志
if $VIEW_API && $VIEW_FRONTEND; then
  echo "同时查看API和前端日志。按Ctrl+C退出。"
  tail -f logs/api.log logs/frontend.log
elif $VIEW_API; then
  echo "查看API日志。按Ctrl+C退出。"
  tail -f logs/api.log
elif $VIEW_FRONTEND; then
  echo "查看前端日志。按Ctrl+C退出。"
  tail -f logs/frontend.log
fi 