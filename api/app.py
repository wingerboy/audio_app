#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import uuid
import json
import time
import traceback
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import logging
from werkzeug.utils import secure_filename
import shutil
from flask_jwt_extended import JWTManager
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__)
CORS(app)

# 配置 JWT
jwt = JWTManager(app)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['UPLOAD_FOLDER'] = os.path.join(project_root, 'data', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 最大500MB
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 60 * 60 * 24 * 7  # 7天

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 初始化余额系统
from src.balance_system import init_app as init_balance_system
init_balance_system(app)

# 注册API路由
from api.routes.balance import bp as balance_bp
from api.routes.usage import bp as usage_bp
from api.auth import login_required, admin_required, get_current_user

app.register_blueprint(balance_bp)
app.register_blueprint(usage_bp)

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
    "whisper": env_manager.ensure_whisper(),
    "gpu": env_manager.check_gpu_status()[0]
}

# 用于跟踪任务状态的字典
tasks = {}

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
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["progress"] = percent
        tasks[task_id]["message"] = message
        logger.info(f"Task {task_id}: {message} ({percent}%)")
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
            is_admin=False,
            balance=0,
            total_charged=0,
            total_consumed=0
        )
        
        db_session.add(new_user)
        db_session.commit()
        db_session.refresh(new_user)
        
        # 生成令牌
        access_token = create_access_token(identity=new_user.id)
        
        return jsonify({
            'status': 'success',
            'message': '注册成功',
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'is_active': new_user.is_active,
                'is_admin': new_user.is_admin,
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
                'is_admin': user.is_admin,
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
@jwt_required()
def get_me():
    """获取当前登录用户信息"""
    try:
        user_id = get_jwt_identity()
        from src.balance_system.models.user import User
        from src.balance_system.db import db_session
        
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({
                'status': 'error',
                'message': '未找到用户信息'
            }), 404
        
        return jsonify({
            'status': 'success',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'is_admin': user.is_admin,
                'balance': float(user.balance),
                'total_charged': float(user.total_charged),
                'total_consumed': float(user.total_consumed)
            }
        })
    except Exception as e:
        logger.exception(f"获取用户信息时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取用户信息失败: {str(e)}'
        }), 500

@app.route('/api/auth/update', methods=['PUT'])
@jwt_required()
def update_account():
    """更新用户信息"""
    try:
        user_id = get_jwt_identity()
        from src.balance_system.models.user import User
        from src.balance_system.db import db_session
        
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({
                'status': 'error',
                'message': '未找到用户信息'
            }), 404
        
        data = request.json
        
        # 允许更新的字段
        allowed_fields = ['username', 'email', 'password']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        # 更新用户
        for field, value in update_data.items():
            if field == 'password':
                user.password_hash = value  # 实际应用中应该使用加密后的密码
            else:
                setattr(user, field, value)
        
        db_session.commit()
        db_session.refresh(user)
        
        return jsonify({
            'status': 'success',
            'message': '用户信息已更新',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'is_admin': user.is_admin,
                'balance': float(user.balance),
                'total_charged': float(user.total_charged),
                'total_consumed': float(user.total_consumed)
            }
        })
    except Exception as e:
        logger.exception(f"更新用户信息时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'更新失败: {str(e)}'
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
            "components": COMPONENTS_READY,
            "torch_version": env_manager.get_torch_version(),
            "gpu_info": env_manager.get_gpu_info() if COMPONENTS_READY["gpu"] else "不可用"
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
    """处理文件上传"""
    if 'file' not in request.files:
        return jsonify({"error": "未找到文件"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "未选择文件"}), 400
    
    # 获取当前用户
    user_id = get_jwt_identity()
    from src.balance_system.models.user import User
    from src.balance_system.db import db_session
    
    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        return jsonify({"error": "未找到用户信息"}), 404
    
    # 生成唯一任务ID
    task_id = str(uuid.uuid4())
    
    # 保存文件到临时目录
    filename, file_extension = os.path.splitext(secure_filename(file.filename))
    file_path = temp_manager.create_named_file(filename, suffix=file_extension)
    file.save(file_path)
    
    # 记录任务信息
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    tasks[task_id] = {
        "id": task_id,
        "filename": file.filename,
        "path": file_path,
        "original_file": file_path,  # 保存原始文件路径
        "size_mb": file_size_mb,
        "status": "uploaded",
        "progress": 0,
        "message": "文件已上传",
        "created_at": time.time(),
        "user_id": user.id  # 记录用户ID
    }
    
    logger.info(f"文件已上传: {file.filename} ({file_size_mb:.2f} MB), 任务ID: {task_id}, 用户: {user.username}")
    
    return jsonify({
        "task_id": task_id,
        "filename": file.filename,
        "size_mb": file_size_mb
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_audio():
    """分析音频内容"""
    data = request.json
    task_id = data.get('task_id')
    model_size = data.get('model_size', 'base')
    
    if not task_id or task_id not in tasks:
        return jsonify({"error": "无效的任务ID"}), 400
    
    task = tasks[task_id]
    file_path = task["path"]
    
    # 更新任务状态
    task["status"] = "processing"
    task["progress"] = 0
    task["message"] = "开始处理..."
    
    try:
        # 创建进度回调
        progress_callback = get_progress_callback(task_id)
        
        # 提取音频
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
        
        # 分析音频
        progress_callback(f"使用Whisper {model_size}模型分析音频内容...", 20)
        audio_analyzer = AIAnalyzerAdapter(model_size=model_size)
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
def split_audio():
    """分割音频"""
    data = request.json
    task_id = data.get('task_id')
    segments = data.get('segments', [])
    output_format = data.get('output_format', 'mp3')
    output_quality = data.get('output_quality', 'medium')
    
    if not task_id or task_id not in tasks:
        return jsonify({"error": "无效的任务ID"}), 400
    
    task = tasks[task_id]
    if "audio_path" not in task:
        return jsonify({"error": "尚未完成音频分析"}), 400
    
    audio_path = task["audio_path"]
    
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
    if task_id not in tasks:
        return jsonify({"error": "任务不存在"}), 404
    
    task = tasks[task_id]
    
    # 清理敏感或过大的字段
    task_info = {k: v for k, v in task.items() if k not in ["path", "audio_path", "transcription"]}
    
    # 如果有转录结果，添加段落数量
    if "transcription" in task and "segments" in task["transcription"]:
        task_info["segments_count"] = len(task["transcription"]["segments"])
    
    return jsonify(task_info)

@app.route('/api/download/<task_id>/<int:file_index>', methods=['GET'])
def download_file(task_id, file_index):
    """下载分割后的文件"""
    if task_id not in tasks:
        return jsonify({"error": "任务不存在"}), 404
    
    task = tasks[task_id]
    
    if "output_files" not in task or not task["output_files"]:
        return jsonify({"error": "没有可下载的文件"}), 404
    
    if file_index < 0 or file_index >= len(task["output_files"]):
        return jsonify({"error": "文件索引无效"}), 404
    
    file_path = task["output_files"][file_index]
    return send_file(file_path, as_attachment=True)

@app.route('/api/cleanup/<task_id>', methods=['DELETE'])
def cleanup_task(task_id):
    """清理任务资源"""
    if task_id not in tasks:
        return jsonify({"error": "任务不存在"}), 404
    
    task = tasks[task_id]
    
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
        del tasks[task_id]
        
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
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    from src.balance_system.models.user import User
    from src.balance_system.db import db_session
    
    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        return jsonify({
            "status": "error",
            "message": "未找到用户信息"
        }), 404
        
    return jsonify({
        "status": "success",
        "data": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "balance": float(user.balance),
            "total_charged": float(user.total_charged),
            "total_consumed": float(user.total_consumed)
        }
    })

if __name__ == '__main__':
    # 启动API服务
    port = int(os.getenv('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True) 