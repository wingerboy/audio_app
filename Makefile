.PHONY: build run stop clean logs dev dev-backend dev-frontend

# 构建Docker镜像
build:
	docker-compose build

# 启动应用
run:
	docker-compose up -d
	@echo "应用已启动:"
	@echo "前端界面: http://localhost:3000"
	@echo "API服务: http://localhost:5000/api/status"

# 停止应用
stop:
	docker-compose down

# 清理构建缓存
clean:
	docker-compose down --rmi all --volumes --remove-orphans

# 查看日志
logs:
	docker-compose logs -f

# 开发模式 - 同时启动前端和后端开发服务
dev: dev-backend dev-frontend

# 仅启动后端开发服务
dev-backend:
	cd api && python app.py &

# 仅启动前端开发服务
dev-frontend:
	cd frontend && npm run dev

# 显示帮助信息
help:
	@echo "使用说明:"
	@echo "  make build      - 构建Docker镜像"
	@echo "  make run        - 启动应用"
	@echo "  make stop       - 停止应用"
	@echo "  make clean      - 清理构建缓存"
	@echo "  make logs       - 查看应用日志"
	@echo "  make dev        - 开发模式"
	@echo "  make dev-backend  - 仅启动后端开发服务"
	@echo "  make dev-frontend - 仅启动前端开发服务"

# 默认目标
default: help 