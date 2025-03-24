#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import uuid
import json
import time
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import logging
from werkzeug.utils import secure_filename
import shutil

# 导入现有的处理组件
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.audio_processor_adapter import AudioProcessorAdapter
from src.ai_analyzer_adapter import AIAnalyzerAdapter
from src.temp import TempFileManager, get_global_manager
from environment_manager import EnvironmentManager
from logging_config import LoggingConfig

# 初始化日志 - 先配置详细的日志级别
LoggingConfig.setup_logging(log_level=logging.DEBUG, app_name="audio_api")
logger = LoggingConfig.get_logger(__name__)
logger.info("======== 音频API服务启动 ========")

# 创建必要的目录结构
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
TASKS_DIR = os.path.join(DATA_DIR, "tasks")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TASKS_DIR, exist_ok=True)
logger.info(f"创建数据目录: {DATA_DIR}")
logger.info(f"创建任务目录: {TASKS_DIR}")

# 初始化Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 设置上传文件大小限制 (500MB)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

# 初始化环境管理器和临时文件管理器
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

def get_progress_callback(task_id):
    """创建进度回调函数"""
    def update_progress(message, percent):
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["progress"] = percent
        tasks[task_id]["message"] = message
        logger.info(f"Task {task_id}: {message} ({percent}%)")
    return update_progress

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取系统状态"""
    return jsonify({
        "status": "ok",
        "components": COMPONENTS_READY,
        "torch_version": env_manager.get_torch_version(),
        "gpu_info": env_manager.get_gpu_info() if COMPONENTS_READY["gpu"] else "不可用"
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """处理文件上传"""
    if 'file' not in request.files:
        return jsonify({"error": "未找到文件"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "未选择文件"}), 400
    
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
        "created_at": time.time()
    }
    
    logger.info(f"文件已上传: {file.filename} ({file_size_mb:.2f} MB), 任务ID: {task_id}")
    
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

if __name__ == '__main__':
    # 启动API服务
    port = int(os.environ.get('PORT', 5002))  # 默认端口改为5002
    app.run(host='0.0.0.0', port=port, debug=True) 