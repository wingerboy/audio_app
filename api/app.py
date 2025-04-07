#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import uuid
import json
import time
import traceback
from flask import Flask, request, jsonify, send_file, g
from flask_cors import CORS
import logging
from werkzeug.utils import secure_filename
import shutil
from flask_jwt_extended import JWTManager
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from dotenv import load_dotenv
from api.auth import setup_jwt, login_required, admin_required, get_current_user, agent_required, admin_or_agent_required
from typing import Optional, Dict
from src.utils.logging_config import LoggingConfig, RequestContext
from src.balance_system.models.user import ROLE_USER, ROLE_ADMIN, ROLE_AGENT, ROLE_SENIOR_AGENT

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 加载环境变量
load_dotenv()

# 设置日志
logger = LoggingConfig.setup_logging(log_level=logging.INFO)

# 创建 Flask 应用
app = Flask(__name__)
# 配置CORS，允许来自所有前端域的请求
CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:3000",  # 本地开发环境
    "http://127.0.0.1:3000",  # 本地开发环境(另一种写法)
    "http://8.155.13.90:3000",  # 生产环境前端服务器
    "http://117.50.172.107:3000",  # 生产环境前端服务器
    "http://www.tarote.tech",  # 域名
    "https://tarote.tech"  # 域名
]}})

# 配置 JWT
jwt = JWTManager(app)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['UPLOAD_FOLDER'] = os.path.join(project_root, 'data', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 最大500MB
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 60 * 60 * 24 * 7  # 7天

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 初始化余额系统
from src.balance_system import init_app as init_balance_system
init_balance_system(app)

# 注册API路由
from api.routes.balance import bp as balance_bp
from api.routes.usage import bp as usage_bp
from api.routes.pricing import bp as pricing_bp
from api.routes.analyze import bp as analyze_bp

app.register_blueprint(balance_bp)
app.register_blueprint(usage_bp)
app.register_blueprint(pricing_bp)
app.register_blueprint(analyze_bp)

# 创建必要的目录结构
DATA_DIR = os.path.join(project_root, "data")
TASKS_DIR = os.path.join(DATA_DIR, "tasks")
USERS_DIR = os.path.join(DATA_DIR, "users")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TASKS_DIR, exist_ok=True)
os.makedirs(USERS_DIR, exist_ok=True)
logger.info(f"创建数据目录: {DATA_DIR}")
logger.info(f"创建任务目录: {TASKS_DIR}")
logger.info(f"创建用户目录: {USERS_DIR}")

# 初始化环境管理器和临时文件管理器
from src.environment_manager import EnvironmentManager
from src.temp import get_global_manager
env_manager = EnvironmentManager()
temp_manager = get_global_manager()

# 检查所需组件
COMPONENTS_READY = {
    "ffmpeg": env_manager.ensure_ffmpeg(),
    # "whisper": env_manager.ensure_whisper(),  # 不再需要检测Whisper
    # "gpu": env_manager.check_gpu_status()[0]  # 不再需要检测GPU
}

# 任务管理器类
class TaskManager:
    def __init__(self):
        self._tasks = {}
        self.logger = LoggingConfig.get_logger(__name__ + '.TaskManager')
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        task = self._tasks.get(task_id)
        if task:
            # 设置上下文
            user_id = task.get("user_id")
            RequestContext.set_context(user_id=user_id, task_id=task_id, operation="get_task")
        return task
    
    def set_task(self, task_id: str, task_data: Dict):
        # 记录任务创建/更新
        is_new = task_id not in self._tasks
        self._tasks[task_id] = task_data
        
        # 设置上下文
        user_id = task_data.get("user_id")
        RequestContext.set_context(user_id=user_id, task_id=task_id, operation="set_task")
        
        if is_new:
            self.logger.info(f"创建新任务: {task_id}, 文件: {task_data.get('filename', 'unknown')}")
        else:
            self.logger.info(f"更新任务: {task_id}, 状态: {task_data.get('status', 'unknown')}")
    
    def delete_task(self, task_id: str):
        if task_id in self._tasks:
            # 设置上下文
            task = self._tasks[task_id]
            user_id = task.get("user_id")
            RequestContext.set_context(user_id=user_id, task_id=task_id, operation="delete_task")
            
            self.logger.info(f"删除任务: {task_id}")
            del self._tasks[task_id]
    
    def get_all_tasks(self) -> Dict[str, Dict]:
        return self._tasks
    
    def get_user_tasks(self, user_id: str) -> Dict[str, Dict]:
        """获取指定用户的所有任务"""
        return {
            task_id: task for task_id, task in self._tasks.items() 
            if task.get("user_id") == user_id
        }

# 创建全局任务管理器实例
task_manager = TaskManager()

# 添加全局错误处理装饰器
@app.errorhandler(Exception)
def handle_exception(e):
    """全局异常处理"""
    # 提取异常详情
    error_msg = str(e)
    error_traceback = traceback.format_exc()
    
    # 记录错误详情
    logger.error(f"未捕获的异常: {error_msg}")
    logger.error(f"错误堆栈: {error_traceback}")
    
    # 返回错误响应
    return jsonify({
        "error": "服务器内部错误",
        "message": error_msg,
        "details": error_traceback if app.debug else None
    }), 500

def get_progress_callback(task_id):
    """创建进度回调函数"""
    def update_progress(message, percent):
        # 设置任务上下文（确保在不同线程中也能正确记录）
        task = task_manager.get_task(task_id)
        if task:
            user_id = task.get("user_id")
            RequestContext.set_context(user_id=user_id, task_id=task_id, operation="progress_update")
            
            task["status"] = "processing"
            task["progress"] = percent
            task["message"] = message
            logger.info(f"任务进度更新: {message} ({percent}%)")
    return update_progress

# 导入音频处理相关的类
from src.audio_processor_adapter import AudioProcessorAdapter
from src.ai_analyzer_adapter import AIAnalyzerAdapter

#
# 认证API路由
#

@app.route('/api/auth/register', methods=['POST'])
def register():
    """注册新用户"""
    try:
        data = request.json
        
        # 验证必要字段
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'status': 'error',
                    'message': f'缺少必要字段: {field}'
                }), 400
        
        # 密码长度验证
        if len(data['password']) < 6:
            return jsonify({
                'status': 'error',
                'message': '密码至少需要6个字符'
            }), 400
        
        # 创建用户
        from src.balance_system.models.user import User
        from src.balance_system.db import db_session
        from src.balance_system.services.balance_service import BalanceService
        
        # 检查邮箱是否已存在
        existing_user = db_session.query(User).filter(User.email == data['email']).first()
        if existing_user:
            return jsonify({
                'status': 'error',
                'message': '该邮箱已被注册'
            }), 400
        
        # 创建新用户
        new_user = User(
            username=data['username'],
            email=data['email'],
            password_hash=data['password'],  # 实际应用中应该使用加密后的密码
            is_active=True,
            role=ROLE_USER  # 使用角色常量替代is_admin=False
        )
        
        db_session.add(new_user)
        db_session.commit()
        db_session.refresh(new_user)
        
        # 记录注册赠送点数
        BalanceService.record_register_balance(new_user.id)
        
        # 生成令牌
        access_token = create_access_token(identity=new_user.id)
        
        return jsonify({
            'status': 'success',
            'message': '注册成功，已赠送50点数，100点=1元',
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'is_active': new_user.is_active,
                'is_admin': new_user.is_admin(),
                'role': new_user.role,
                'role_name': new_user.get_role_name(),
                'balance': float(new_user.balance),
                'total_charged': float(new_user.total_charged),
                'total_consumed': float(new_user.total_consumed)
            },
            'token': access_token
        })
    except Exception as e:
        logger.exception(f"注册用户时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'注册失败: {str(e)}'
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.json
        
        # 验证必要字段
        if 'email' not in data or 'password' not in data:
            return jsonify({
                'status': 'error',
                'message': '请提供邮箱和密码'
            }), 400
        
        # 认证用户
        from src.balance_system.models.user import User
        from src.balance_system.db import db_session
        
        user = db_session.query(User).filter(User.email == data['email']).first()
        if not user:
            return jsonify({
                'status': 'error',
                'message': '账号未注册'
            }), 401
            
        if user.password_hash != data['password']:  # 实际应用中应该使用加密后的密码比较
            return jsonify({
                'status': 'error',
                'message': '邮箱或密码错误'
            }), 401
        
        # 生成令牌
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'status': 'success',
            'message': '登录成功',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'is_admin': user.is_admin(),
                'role': user.role,
                'role_name': user.get_role_name(),
                'balance': float(user.balance),
                'total_charged': float(user.total_charged),
                'total_consumed': float(user.total_consumed)
            },
            'token': access_token
        })
    except Exception as e:
        logger.exception(f"用户登录时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'登录失败: {str(e)}'
        }), 500

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_me():
    """获取当前用户信息"""
    try:
        # 获取当前用户
        user = get_current_user()
        if not user:
            return jsonify({
                'status': 'error',
                'message': '未找到用户信息'
            }), 404
        
        # 确保user是一个字典
        if not isinstance(user, dict):
            return jsonify({
                'status': 'error',
                'message': '用户数据格式错误'
            }), 500
            
        # 返回用户信息
        return jsonify({
            'status': 'success',
            'data': user
        })
    except Exception as e:
        logger.exception(f"获取用户信息时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取用户信息失败: {str(e)}'
        }), 500

@app.route('/api/auth/update', methods=['PUT'])
@login_required
def update_account():
    """更新用户账户信息"""
    try:
        data = request.json
        
        # 获取当前用户
        from src.balance_system.models.user import User
        from src.balance_system.db import db_session
        
        user = get_current_user()
        if not user:
            return jsonify({
                'status': 'error',
                'message': '未找到用户信息'
            }), 404
        
        user_id = user['id']
        db_user = db_session.query(User).filter(User.id == user_id).first()
        
        if not db_user:
            return jsonify({
                'status': 'error',
                'message': '未找到用户信息'
            }), 404
        
        # 允许更新的字段
        allowed_fields = ['username', 'email', 'password']
        
        # 检查字段是否合法
        for field in data:
            if field not in allowed_fields:
                return jsonify({
                    'status': 'error',
                    'message': f'不允许更新字段: {field}'
                }), 400
        
        # 更新用户信息
        if 'username' in data:
            db_user.username = data['username']
        
        if 'email' in data:
            # 检查邮箱是否已被其他用户使用
            existing_user = db_session.query(User).filter(
                User.email == data['email'], 
                User.id != user_id
            ).first()
            
            if existing_user:
                return jsonify({
                    'status': 'error',
                    'message': '该邮箱已被其他用户使用'
                }), 400
            
            db_user.email = data['email']
        
        if 'password' in data:
            # 密码长度验证
            if len(data['password']) < 6:
                return jsonify({
                    'status': 'error',
                    'message': '密码至少需要6个字符'
                }), 400
            
            db_user.set_password(data['password'])
        
        # 保存更新
        db_session.commit()
        
        # 返回更新后的用户信息
        return jsonify({
            'status': 'success',
            'message': '用户信息更新成功',
            'data': {
                'id': db_user.id,
                'username': db_user.username,
                'email': db_user.email,
                'is_active': db_user.is_active,
                'is_admin': db_user.is_admin(),
                'role': db_user.role,
                'role_name': db_user.get_role_name(),
                'balance': float(db_user.balance),
                'total_charged': float(db_user.total_charged),
                'total_consumed': float(db_user.total_consumed)
            }
        })
    except Exception as e:
        logger.exception(f"更新用户信息时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'更新用户信息失败: {str(e)}'
        }), 500
        
#
# 系统状态API
#

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取系统状态"""
    try:
        return jsonify({
            "status": "ok",
            "components": {
                "ffmpeg": COMPONENTS_READY["ffmpeg"]
                # "whisper": COMPONENTS_READY["whisper"],  # 不再需要检测Whisper
                # "gpu": COMPONENTS_READY["gpu"]           # 不再需要检测GPU
            },
            # "torch_version": env_manager.get_torch_version(),  # 不再需要Torch版本
            # "gpu_info": env_manager.get_gpu_info() if COMPONENTS_READY["gpu"] else "不可用"  # 不再需要GPU信息
        })
    except Exception as e:
        logger.exception(f"获取系统状态时出错: {str(e)}")
        return jsonify({"error": str(e), "status": "error"}), 500

#
# 受保护的音频处理API路由
#

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_file():
    """处理文件上传 - 优化版本：使用流式处理和PyAV"""
    if 'file' not in request.files:
        return jsonify({"error": "未找到文件"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "未选择文件"}), 400
    
    # 获取当前用户
    user = get_current_user()
    if not user:
        return jsonify({"error": "未找到用户信息"}), 404
    
    user_id = user['id']
    username = user['username']
    
    # 记录开始时间（用于性能分析）
    start_time = time.time()

    # 生成唯一任务ID
    task_id = str(uuid.uuid4())
    
    # 创建任务目录
    task_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tasks", task_id)
    os.makedirs(task_dir, exist_ok=True)
    
    # 流式保存文件，直接写入任务目录
    filename, file_extension = os.path.splitext(secure_filename(file.filename))
    file_path = os.path.join(task_dir, f"original{file_extension}")
    
    logger.info(f"开始流式保存文件: {file.filename} -> {file_path}")
    
    # 使用流式处理保存文件，避免内存溢出
    chunk_size = 4 * 1024 * 1024  # 4MB 块大小
    file_size = 0
    with open(file_path, 'wb') as f:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            file_size += len(chunk)
    
    file_size_mb = file_size / (1024 * 1024)
    logger.info(f"文件保存完成: {file_path}, 大小: {file_size_mb:.2f} MB")
    
    # 音频提取和处理
    audio_path = None
    audio_duration_seconds = 0
    
    try:
        # 检查是否可以使用PyAV
        import av
        use_pyav = True
        logger.info("使用PyAV处理音频")
    except ImportError:
        use_pyav = False
        logger.info("PyAV不可用，回退到FFmpeg命令行")
    
    try:
        # 音频处理逻辑
        if file_extension.lower() in ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac']:
            # 如果已经是音频文件，直接使用
            audio_path = file_path
            logger.info(f"上传的文件已经是音频: {file.filename}")
        else:
            # 提取音频
            logger.info(f"从上传的文件中提取音频: {file.filename}")
            audio_path = os.path.join(task_dir, f"audio.wav")
            
            if use_pyav:
                # 使用PyAV提取音频
                try:
                    input_container = av.open(file_path)
                    output_container = av.open(audio_path, 'w')
                    
                    # 找到第一个音频流
                    input_stream = next(s for s in input_container.streams if s.type == 'audio')
                    
                    # 创建输出流
                    output_stream = output_container.add_stream(template=input_stream)
                    
                    # 处理帧
                    for frame in input_container.decode(input_stream):
                        for packet in output_stream.encode(frame):
                            output_container.mux(packet)
                    
                    # 刷新所有剩余帧
                    for packet in output_stream.encode(None):
                        output_container.mux(packet)
                    
                    # 关闭容器
                    output_container.close()
                    input_container.close()
                    
                    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                        logger.info(f"PyAV 音频提取成功: {audio_path}")
                    else:
                        raise RuntimeError("PyAV提取的音频文件为空")
                        
                except Exception as e:
                    logger.warning(f"PyAV提取音频失败，回退到FFmpeg: {str(e)}")
                    use_pyav = False
            
            if not use_pyav:
                # 回退到使用FFmpeg命令行
                audio_processor = AudioProcessorAdapter()
                extracted_path = audio_processor.extract_audio(file_path)
                if extracted_path:
                    # 复制到任务目录
                    shutil.copy2(extracted_path, audio_path)
                    logger.info(f"FFmpeg音频提取成功: {audio_path}")
                else:
                    logger.warning(f"无法从文件中提取音频: {file.filename}")
                    audio_path = None
    except Exception as e:
        logger.warning(f"音频提取过程中出错: {str(e)}")
        # 如果提取失败，尝试继续使用原始文件
        if not audio_path or not os.path.exists(audio_path):
            audio_path = file_path
    
    # 获取音频时长 - 优先使用PyAV以提高性能
    if audio_path and os.path.exists(audio_path):
        try:
            if use_pyav:
                # 使用PyAV获取音频时长
                with av.open(audio_path) as container:
                    # 获取音频流
                    stream = next(s for s in container.streams if s.type == 'audio')
                    # 计算时长（秒）
                    if stream.duration and stream.time_base:
                        audio_duration_seconds = stream.duration * float(stream.time_base)
                    else:
                        # 回退：使用总时长除以音频流数量
                        audio_duration_seconds = container.duration / 1000000.0  # 微秒转秒
                    
                    logger.info(f"使用PyAV获取音频时长: {audio_duration_seconds:.2f} 秒")
            else:
                # 回退到AudioUtils
                from src.audio.utils import AudioUtils
                audio_duration_seconds = AudioUtils.get_audio_duration(audio_path)
                logger.info(f"使用AudioUtils获取音频时长: {audio_duration_seconds:.2f} 秒")
                
            if audio_duration_seconds <= 0:
                # 如果获取失败，使用基于文件大小的估算
                logger.warning(f"无法获取准确音频时长，使用基于文件大小的估算")
                file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
                audio_duration_seconds = file_size_mb * 2  # 假设每MB约2秒音频
        except Exception as e:
            logger.warning(f"获取音频时长失败: {str(e)}")
            # 使用基于文件大小的估算
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            audio_duration_seconds = file_size_mb * 2
    else:
        # 如果提取失败，尝试直接从原始文件获取时长
        try:
            from src.audio.utils import AudioUtils
            audio_duration_seconds = AudioUtils.get_audio_duration(file_path)
        except Exception:
            # 最终回退：基于文件大小估算
            audio_duration_seconds = file_size_mb * 2
    
    # 计算音频时长（分钟）和预估费用
    audio_duration_minutes = audio_duration_seconds / 60
    estimated_cost = 0
    
    try:
        from src.balance_system.services.pricing_service import PricingService
        
        analyze_cost = PricingService.estimate_cost(
            file_size_mb=file_size_mb, 
            audio_duration_minutes=audio_duration_minutes
        )
        estimated_cost = analyze_cost["estimated_cost"]
        logger.info(f"已计算预估费用: {estimated_cost}")
    except Exception as e:
        logger.warning(f"计算预估费用失败: {str(e)}")
    
    # 记录任务信息
    task_info = {
        "id": task_id,
        "filename": file.filename,
        "path": file_path,
        "original_file": file_path,
        "audio_path": audio_path,
        "size_mb": file_size_mb,
        "audio_duration_seconds": audio_duration_seconds,
        "audio_duration_minutes": audio_duration_minutes,
        "status": "uploaded",
        "progress": 0,
        "message": "文件已上传",
        "created_at": int(time.time()),
        "user_id": user_id,
        "estimated_cost": estimated_cost
    }
    
    # 保存任务信息
    task_manager.set_task(task_id, task_info)
    
    # 计算总处理时间
    processing_time = time.time() - start_time
    logger.info(f"文件上传处理完成: {file.filename} ({file_size_mb:.2f} MB, {audio_duration_seconds:.2f} 秒), 任务ID: {task_id}, 用户: {username}, 处理时间: {processing_time:.2f}秒")
    
    # 返回响应，包含预估费用
    return jsonify({
        "task_id": task_id,
        "filename": file.filename,
        "size_mb": file_size_mb,
        "audio_duration_seconds": audio_duration_seconds,
        "audio_duration_minutes": audio_duration_minutes,
        "estimated_cost": estimated_cost,
        "processing_time": processing_time
    })

@app.route('/api/analyze', methods=['POST'])
@login_required
def analyze_audio():
    """分析音频内容"""
    data = request.json
    task_id = data.get('task_id')
    model_size = data.get('model_size', 'base')  # 默认使用base模型
    
    if not task_id or task_id not in task_manager.get_all_tasks():
        return jsonify({"error": "无效的任务ID"}), 400

    # 手动执行余额检查
    from src.balance_system.services.user_service import UserService
    
    # 获取用户余额
    user = get_current_user()
    if not user:
        return jsonify({"error": "未找到用户信息"}), 404
    
    user_id = user['id']
    user_service = UserService()
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        return jsonify({"error": "用户不存在"}), 404
        
    current_balance = float(user.balance)    
    task = task_manager.get_task(task_id)
    estimated_cost = task.get('estimated_cost', 0)
    
    # 检查余额是否足够
    if current_balance < estimated_cost:
        error_msg = f"余额不足，当前余额 {current_balance} 点，需要 {estimated_cost} 点"
        logger.warning(f"用户 {user_id} {error_msg}")
        return jsonify({
            "error": "余额不足",
            "current_balance": current_balance,
            "estimated_cost": estimated_cost
        }), 402
    file_path = task["path"]
    
    # 设置任务上下文
    user_id = task.get("user_id")
    RequestContext.set_context(user_id=user_id, task_id=task_id, operation="analyze_audio")
    logger.info(f"开始分析音频任务: {task_id}, 文件: {os.path.basename(file_path)}")
    
    # 更新任务状态
    task["status"] = "processing"
    task["progress"] = 0
    task["message"] = "开始处理..."
    task["model_size"] = model_size  # 记录使用的模型大小
    
    try:
        # 创建进度回调
        progress_callback = get_progress_callback(task_id)
        
        # 检查是否已经在上传阶段提取了音频
        audio_path = task.get("audio_path")
        if not audio_path or not os.path.exists(audio_path):
            # 只有在上传阶段没有提取音频时才提取
            progress_callback("提取音频中...", 5)
            audio_processor = AudioProcessorAdapter()
            audio_path = audio_processor.extract_audio(file_path, progress_callback=progress_callback)
            
            if not audio_path:
                task["status"] = "failed"
                task["message"] = "音频提取失败"
                return jsonify({"error": "音频提取失败"}), 500
            
            # 创建任务专用的持久化目录
            task_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tasks", task_id)
            os.makedirs(task_dir, exist_ok=True)
            
            # 复制提取的音频文件到持久化目录
            filename, ext = os.path.splitext(os.path.basename(audio_path))
            persistent_audio_path = os.path.join(task_dir, f"{filename}{ext}")
            try:
                logger.info(f"复制音频文件到持久化路径: {audio_path} -> {persistent_audio_path}")
                shutil.copy2(audio_path, persistent_audio_path)
                # 更新音频路径为持久化路径
                audio_path = persistent_audio_path
            except Exception as e:
                logger.warning(f"复制音频文件失败: {str(e)}，将继续使用临时路径")
        else:
            progress_callback("使用已提取的音频...", 15)
            logger.info(f"使用上传时已提取的音频: {audio_path}")
        
        # 分析音频
        progress_callback(f"使用云API分析音频内容...", 20)  # 修改提示信息
        audio_analyzer = AIAnalyzerAdapter()
        transcription = audio_analyzer.transcribe_audio(
            audio_path, 
            progress_callback=progress_callback
        )
        
        if not transcription or not transcription.get("segments"):
            task["status"] = "failed"
            task["message"] = "音频分析失败，未能识别出任何内容"
            return jsonify({"error": "音频分析失败，未能识别出任何内容"}), 500
        
        # 保存转录结果
        task["transcription"] = transcription
        task["audio_path"] = audio_path
        task["persistent_audio"] = audio_path  # 添加持久化音频路径的标记
        task["status"] = "analyzed"
        task["progress"] = 100
        task["message"] = "分析完成"
        
        # 扣除用户余额
        try:
            from src.balance_system.services.api_usage_service import ApiUsageService
            
            # 获取音频时长（分钟）和文件大小
            audio_duration_minutes = task.get("audio_duration_minutes", 0)
            file_size_mb = task.get("size_mb", 0)
            estimated_cost = task.get("estimated_cost", 0)
            model_size = task.get("model_size", "base")
            original_file = task.get("original_file", "")
            
            # 记录API使用并扣除余额
            usage_result = ApiUsageService.record_api_usage(
                user_id=user_id,
                api_type="analyze_audio",
                task_id=task_id,
                cost=estimated_cost,
                input_size=file_size_mb,
                duration=audio_duration_minutes * 60,  # 转换为秒
                details=f"analyze file {original_file}"
            )
            
            logger.info(f"成功扣除用户 {user_id} 余额: {estimated_cost} 点")
        except Exception as e:
            logger.error(f"扣除用户余额失败: {str(e)}")
        
        # 返回结果
        return jsonify({
            "task_id": task_id,
            "status": "success",
            "message": "分析完成",
            "segments": transcription.get("segments", []),
            "text": transcription.get("text", "")
        })
        
    except Exception as e:
        logger.exception(f"处理音频时出错: {str(e)}")
        task["status"] = "failed"
        task["message"] = f"处理失败: {str(e)}"
        return jsonify({"error": str(e)}), 500

@app.route('/api/split', methods=['POST'])
@login_required
def split_audio():
    """分割音频"""    
    data = request.json
    task_id = data.get('task_id')
    segments = data.get('segments', [])
    output_format = data.get('output_format', 'mp3')
    output_quality = data.get('output_quality', 'medium')
    
    if not task_id or task_id not in task_manager.get_all_tasks():
        return jsonify({"error": "无效的任务ID"}), 400
    
    task = task_manager.get_task(task_id)
    if "audio_path" not in task:
        return jsonify({"error": "尚未完成音频分析"}), 400
    
    audio_path = task["audio_path"]
    
    # 设置任务上下文
    user_id = task.get("user_id")
    RequestContext.set_context(user_id=user_id, task_id=task_id, operation="split_audio")
    logger.info(f"开始分割音频任务: {task_id}, 分段数: {len(segments)}")
    
    # 余额检查已由装饰器处理
    
    # 更新任务状态
    task["status"] = "splitting"
    task["progress"] = 0
    task["message"] = "开始分割音频..."
    
    try:
        # 创建进度回调
        progress_callback = get_progress_callback(task_id)
        
        # 创建任务专用的输出目录
        task_dir = os.path.join(TASKS_DIR, task_id)
        output_dir = os.path.join(task_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"创建输出目录: {output_dir}")
        
        # 检查音频文件是否存在
        if not os.path.exists(audio_path):
            logger.error(f"音频文件不存在: {audio_path}")
            
            # 如果使用的是持久化音频但文件被删除，尝试从原始文件重新提取
            if "original_file" in task and os.path.exists(task["original_file"]):
                original_file = task["original_file"]
                logger.info(f"重新从原始文件提取音频: {original_file}")
                
                # 创建音频处理器
                audio_processor = AudioProcessorAdapter(auto_cleanup=False)
                
                # 提取音频
                temp_audio_path = audio_processor.extract_audio(
                    original_file, 
                    progress_callback=lambda msg, progress: progress_callback(f"重新提取音频: {msg}", progress)
                )
                
                if not temp_audio_path:
                    error_msg = "重新提取音频失败"
                    logger.error(error_msg)
                    task["status"] = "failed"
                    task["message"] = error_msg
                    return jsonify({"error": error_msg}), 500
                
                # 复制到持久化目录
                filename, ext = os.path.splitext(os.path.basename(temp_audio_path))
                audio_path = os.path.join(task_dir, f"{filename}{ext}")
                
                try:
                    shutil.copy2(temp_audio_path, audio_path)
                    logger.info(f"复制音频到持久化路径: {temp_audio_path} -> {audio_path}")
                    
                    # 更新任务中的音频路径
                    task["audio_path"] = audio_path
                    task["persistent_audio"] = audio_path
                except Exception as e:
                    logger.error(f"复制音频文件失败: {str(e)}")
                    # 如果复制失败，使用临时文件路径
                    audio_path = temp_audio_path
                    task["audio_path"] = audio_path
            else:
                error_msg = "音频文件不存在且无法重新提取"
                logger.error(error_msg)
                task["status"] = "failed"
                task["message"] = error_msg
                return jsonify({"error": error_msg}), 500
        
        # 分割音频
        logger.info(f"开始分割音频: {audio_path} -> {output_dir}, 分段数: {len(segments)}")
        audio_processor = AudioProcessorAdapter(use_disk_processing=True, auto_cleanup=False)
        
        # 执行分割
        output_files = audio_processor.split_audio(
            audio_path,
            segments,
            output_dir,
            output_format=output_format,
            quality=output_quality,
            progress_callback=progress_callback
        )
        
        # 检查结果
        if not output_files:
            error_msg = "音频分割失败，未生成输出文件"
            logger.error(error_msg)
            task["status"] = "failed"
            task["message"] = error_msg
            return jsonify({"error": error_msg}), 500
        
        # 保存输出文件路径
        task["output_files"] = output_files
        task["output_dir"] = output_dir
        task["status"] = "completed"
        task["progress"] = 100
        task["message"] = "分割完成"
        
        # 准备文件信息
        files_info = []
        for i, file_path in enumerate(output_files):
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            files_info.append({
                "id": i,
                "name": file_name,
                "path": file_path,
                "size": file_size,
                "size_formatted": f"{file_size/1024/1024:.2f} MB",
                "download_url": f"/api/download/{task_id}/{i}"
            })
        
        task["files_info"] = files_info
        
        # 返回结果
        return jsonify({
            "task_id": task_id,
            "status": "success",
            "message": "分割完成",
            "files": files_info
        })
        
    except Exception as e:
        error_details = f"分割音频时出错: {str(e)}"
        logger.exception(error_details)
        task["status"] = "failed"
        task["message"] = "音频分割失败"
        task["error_details"] = error_details
        return jsonify({
            "error": "音频分割失败", 
            "details": str(e)
        }), 500

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    
    # 清理敏感或过大的字段
    task_info = {k: v for k, v in task.items() if k not in ["path", "audio_path", "transcription"]}
    
    # 如果有转录结果，添加段落数量
    if "transcription" in task and "segments" in task["transcription"]:
        task_info["segments_count"] = len(task["transcription"]["segments"])
    
    return jsonify(task_info)

@app.route('/api/download/<task_id>/<int:file_index>', methods=['GET'])
def download_file(task_id, file_index):
    """下载分割后的文件"""
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    
    if "output_files" not in task or not task["output_files"]:
        return jsonify({"error": "没有可下载的文件"}), 404
    
    if file_index < 0 or file_index >= len(task["output_files"]):
        return jsonify({"error": "文件索引无效"}), 404
    
    file_path = task["output_files"][file_index]
    return send_file(file_path, as_attachment=True)

@app.route('/api/download/<task_id>/zip', methods=['GET'])
def download_zip(task_id):
    """下载所有分割文件的ZIP压缩包"""
    import zipfile
    import io
    import os
    
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    
    if "output_files" not in task or not task["output_files"]:
        return jsonify({"error": "没有可下载的文件"}), 404
    
    # 创建内存中的ZIP文件
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in task["output_files"]:
            # 获取文件名，去除路径
            file_name = os.path.basename(file_path)
            # 添加文件到ZIP
            zf.write(file_path, file_name)
    
    # 重置文件指针位置
    memory_file.seek(0)
    
    # 返回ZIP文件
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'audio_segments_{task_id}.zip'
    )

@app.route('/api/cleanup/<task_id>', methods=['DELETE'])
def cleanup_task(task_id):
    """清理任务资源"""
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    
    try:
        # 清理文件
        if "path" in task and os.path.exists(task["path"]):
            os.remove(task["path"])
        
        if "audio_path" in task and os.path.exists(task["audio_path"]):
            os.remove(task["audio_path"])
        
        if "output_dir" in task and os.path.exists(task["output_dir"]):
            import shutil
            shutil.rmtree(task["output_dir"])
        
        # 从任务列表中移除
        task_manager.delete_task(task_id)
        
        return jsonify({"status": "success", "message": "任务已清理"})
    
    except Exception as e:
        logger.exception(f"清理任务资源时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 应用启动前的初始化
def init_app():
    logger.info("Initializing application...")
    from src.environment_manager import EnvironmentManager
    EnvironmentManager.ensure_ffmpeg()
    EnvironmentManager.ensure_whisper()
    EnvironmentManager.check_gpu_status()
    logger.info("Application initialized.")

# 在应用上下文中执行初始化
with app.app_context():
    init_app()

# 健康检查端点
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "success",
        "message": "API is running"
    })

# 用户信息端点
@app.route('/api/user/me', methods=['GET'])
@login_required
def get_user_info():
    """获取当前用户信息 (与/api/auth/me功能相同，保留此路由是为了兼容性)"""
    # 获取当前用户
    from api.auth import get_current_user
    user = get_current_user()
    if not user:
        return jsonify({
            'status': 'error',
            'message': '未找到用户信息'
        }), 404
    
    # 返回用户信息
    return jsonify({
        'status': 'success',
        'data': user
    })

@app.route('/api/user/last-task', methods=['GET'])
@login_required
def get_user_last_task():
    """获取当前用户的最后一个任务"""
    # 获取当前用户ID
    user_id = get_jwt_identity()
    if not user_id:
        return jsonify({
            'status': 'error',
            'message': '未找到用户信息'
        }), 401
    
    # 获取用户的所有任务
    user_tasks = task_manager.get_user_tasks(user_id)
    if not user_tasks:
        return jsonify({
            'status': 'error',
            'message': '未找到任务'
        }), 404
    
    # 按创建时间排序，获取最新任务
    last_task = None
    newest_time = 0
    
    for task_id, task in user_tasks.items():
        created_at = task.get('created_at', 0)
        if created_at > newest_time:
            newest_time = created_at
            last_task = task
    
    if not last_task:
        return jsonify({
            'status': 'error',
            'message': '未找到任务'
        }), 404
    
    # 清理敏感或过大的字段
    task_info = {k: v for k, v in last_task.items() if k not in ["path", "audio_path", "transcription"]}
    
    # 如果有转录结果，添加段落数量
    if "transcription" in last_task and "segments" in last_task["transcription"]:
        task_info["segments_count"] = len(last_task["transcription"]["segments"])
    
    return jsonify(task_info)

# 添加请求前钩子，自动设置日志上下文
@app.before_request
def setup_request_context():
    """在每个请求开始时设置日志上下文"""
    # 清除上一个请求的上下文
    RequestContext.clear_context()
    
    # 设置请求ID
    request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
    g.request_id = request_id
    
    # 尝试从JWT获取用户ID
    user_id = None
    try:
        user_id = get_jwt_identity()
    except Exception:
        # 未认证的请求
        pass
    
    # 尝试从URL获取任务ID
    task_id = None
    # 从请求参数中获取任务ID
    if request.method == 'GET':
        task_id = request.args.get('task_id')
    elif request.is_json and request.get_json():
        task_id = request.json.get('task_id')
    
    # 设置上下文
    context = {
        'request_id': request_id,
        'remote_addr': request.remote_addr,
        'method': request.method,
        'path': request.path
    }
    
    if user_id:
        context['user_id'] = user_id
    if task_id:
        context['task_id'] = task_id
    
    RequestContext.set_context(**context)
    
    # 记录请求开始日志
    logger.info(f"请求开始: {request.method} {request.path}")

# 添加请求后钩子，记录请求处理时间
@app.after_request
def log_request_info(response):
    """在每个请求结束后记录处理信息"""
    # 计算请求处理时间
    if hasattr(g, 'request_start_time'):
        elapsed = time.time() - g.request_start_time
        logger.info(f"请求结束: {response.status_code} - 耗时 {elapsed:.4f}s")
    
    return response

# 记录每个请求的开始时间
@app.before_request
def start_timer():
    """记录请求开始时间"""
    g.request_start_time = time.time()

@app.route('/api/admin/update-role', methods=['POST'])
@admin_required
def update_user_role():
    """更新用户角色 - 仅限管理员操作"""
    try:
        data = request.json
        
        # 验证必要字段
        if 'user_id' not in data or 'role' not in data:
            return jsonify({
                'status': 'error',
                'message': '请提供用户ID和角色值'
            }), 400
        
        user_id = data['user_id']
        try:
            role = int(data['role'])
        except (ValueError, TypeError):
            return jsonify({
                'status': 'error',
                'message': '角色值必须是整数'
            }), 400
        
        # 验证角色值
        from src.balance_system.models.user import ROLE_USER, ROLE_ADMIN, ROLE_AGENT, ROLE_SENIOR_AGENT
        valid_roles = [ROLE_USER, ROLE_ADMIN, ROLE_AGENT, ROLE_SENIOR_AGENT]
        
        if role not in valid_roles:
            return jsonify({
                'status': 'error',
                'message': f'无效的角色值: {role}'
            }), 400
        
        # 获取当前管理员信息
        admin = get_current_user()
        if not admin:
            return jsonify({
                'status': 'error',
                'message': '未找到管理员信息'
            }), 404
        
        from src.balance_system.db import get_db_session
        from src.balance_system.models.user import User
        
        # 检查要修改的用户是否存在
        with get_db_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return jsonify({
                    'status': 'error',
                    'message': f'用户 {user_id} 不存在'
                }), 404
            
            # 更新用户角色
            old_role = user.role
            user.role = role
            session.commit()
            
            logger.info(f"管理员 {admin['username']} 将用户 {user.username} 的角色从 {old_role} 更新为 {role}")
            
            return jsonify({
                'status': 'success',
                'message': f'已将用户 {user.username} 的角色更新为 {user.get_role_name()}',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'role_name': user.get_role_name(),
                    'is_admin': user.is_admin()
                }
            })
    except Exception as e:
        logger.exception(f"更新用户角色时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'更新用户角色失败: {str(e)}'
        }), 500

@app.route('/api/admin/find-user', methods=['POST'])
@admin_or_agent_required
def find_user():
    """通过邮箱查找用户 - 仅限管理员或代理操作"""
    try:
        data = request.json
        
        # 验证必要字段
        if 'email' not in data:
            return jsonify({
                'status': 'error',
                'message': '请提供用户邮箱'
            }), 400
        
        email = data['email'].strip()
        
        # 获取当前管理员/代理信息
        admin = get_current_user()
        if not admin:
            return jsonify({
                'status': 'error',
                'message': '未找到管理员/代理信息'
            }), 404
        
        from src.balance_system.db import get_db_session
        from src.balance_system.models.user import User
        
        # 查找用户
        with get_db_session() as session:
            user = session.query(User).filter_by(email=email).first()
            
            if not user:
                return jsonify({
                    'status': 'error',
                    'message': f'未找到邮箱为 {email} 的用户'
                }), 404
            
            logger.info(f"{admin['username']} 查询了用户 {user.username} 的信息")
            
            return jsonify({
                'status': 'success',
                'message': f'已找到用户',
                'data': {
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'role': user.role,
                        'role_name': user.get_role_name(),
                        'is_admin': user.is_admin(),
                        'balance': float(user.balance) if user.balance else 0.0
                    }
                }
            })
    except Exception as e:
        logger.exception(f"查找用户时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'查找用户失败: {str(e)}'
        }), 500

@app.route('/api/balance/agent/charge', methods=['POST'])
@agent_required
def agent_charge():
    """代理为普通用户充值（划扣）- 仅限代理操作"""
    try:
        data = request.json
        
        # 验证必要字段
        if 'email' not in data or 'amount' not in data:
            return jsonify({
                'status': 'error',
                'message': '请提供用户邮箱和充值金额'
            }), 400
        
        email = data['email'].strip()
        
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({
                    'status': 'error',
                    'message': '充值金额必须大于0'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'status': 'error',
                'message': '无效的充值金额'
            }), 400
        
        # 获取当前代理信息
        agent = get_current_user()
        if not agent:
            return jsonify({
                'status': 'error',
                'message': '未找到代理信息'
            }), 404
        
        agent_id = agent['id']
        
        from src.balance_system.db import get_db_session
        from src.balance_system.models.user import User
        from src.balance_system.services.balance_service import BalanceService
        
        # 检查代理余额是否足够
        with get_db_session() as session:
            agent_user = session.query(User).filter_by(id=agent_id).first()
            
            if not agent_user:
                return jsonify({
                    'status': 'error',
                    'message': '代理账户不存在'
                }), 404
            
            if float(agent_user.balance) < amount:
                return jsonify({
                    'status': 'error',
                    'message': f'代理余额不足，当前余额: {float(agent_user.balance)} 点'
                }), 400
            
            # 查找目标用户
            target_user = session.query(User).filter_by(email=email).first()
            
            if not target_user:
                return jsonify({
                    'status': 'error',
                    'message': f'未找到邮箱为 {email} 的用户'
                }), 404
            
            # 检查目标用户不是代理或管理员
            if target_user.role > 0:  # 非普通用户
                return jsonify({
                    'status': 'error',
                    'message': f'不能给其他代理或管理员充值'
                }), 400
            
            # 执行划扣操作：从代理账户扣除，加到用户账户
            # 1. 从代理账户扣除
            agent_user.balance = float(agent_user.balance) - amount
            agent_user.total_consumed = float(agent_user.total_consumed) + amount
            
            # 2. 给用户账户充值
            target_user.balance = float(target_user.balance) + amount
            target_user.total_charged = float(target_user.total_charged) + amount
            
            # 保存更改
            session.commit()
            
            # 记录交易历史
            BalanceService.record_agent_charge(agent_id, target_user.id, amount)
            
            logger.info(f"代理 {agent['username']} 为用户 {target_user.username} 充值 {amount} 点")
            
            return jsonify({
                'status': 'success',
                'message': f'成功为用户 {target_user.username} 充值 {amount} 点',
                'data': {
                    'agent_balance': float(agent_user.balance),
                    'user_balance': float(target_user.balance),
                    'amount': amount
                }
            })
    except Exception as e:
        logger.exception(f"代理充值时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'充值失败: {str(e)}'
        }), 500

@app.route('/api/admin/special-users', methods=['GET'])
@admin_required
def get_special_users():
    """获取所有特殊用户（非普通用户）- 仅限管理员访问"""
    try:
        # 获取当前管理员信息
        admin = get_current_user()
        if not admin:
            return jsonify({
                'status': 'error',
                'message': '未找到管理员信息'
            }), 404
        
        from src.balance_system.db import get_db_session
        from src.balance_system.models.user import User, ROLE_USER
        
        # 查询所有特殊用户
        with get_db_session() as session:
            # 查询除了当前用户外的所有非普通用户
            special_users = session.query(User).filter(
                User.role > ROLE_USER
            ).order_by(User.role.desc()).all()
            
            users_data = []
            for user in special_users:
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'role_name': user.get_role_name(),
                    'balance': float(user.balance) if user.balance else 0.0,
                    'total_charged': float(user.total_charged) if user.total_charged else 0.0,
                    'total_consumed': float(user.total_consumed) if user.total_consumed else 0.0,
                    'created_at': user.created_at.isoformat() if user.created_at else None
                })
            
            logger.info(f"管理员 {admin['username']} 查询了特殊用户列表，共 {len(users_data)} 人")
            
            return jsonify({
                'status': 'success',
                'message': '获取特殊用户列表成功',
                'data': {
                    'users': users_data
                }
            })
    except Exception as e:
        logger.exception(f"获取特殊用户列表失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取特殊用户列表失败: {str(e)}'
        }), 500

if __name__ == '__main__':
    # 启动API服务
    port = int(os.getenv('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True) 