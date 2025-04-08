import datetime

from sqlalchemy import Column, String, Numeric, Boolean, Text, DateTime, Integer, func, TIMESTAMP, text, ForeignKey, \
    Float
from ..db import Base
import json

class UserTask(Base):
    __tablename__ = 'user_tasks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_no = Column(String(255), default='', nullable=False)
    source_file_name = Column(String(100), unique=True, nullable=False)
    source_file_path = Column(String(100), unique=True, nullable=False)
    user_id = Column(String(36), nullable=False)
    status = Column(Integer, default=0, nullable=False)
    source_file_size = Column(Float, default='', nullable=False)
    source_file_duration_minutes = Column(Float, default=0, nullable=False)
    source_file_duration_seconds = Column(Float, default=0, nullable=False)
    transaction_id = Column(Integer, ForeignKey('transaction_records.id'))
    audio_path = Column(String(255), default='', nullable=True)
    segments = Column(Text, default='', nullable=True)
    output_files = Column(Text, default='', nullable=True)
    output_dir = Column(String(255), default='', nullable=True)
    create_time = Column(TIMESTAMP, server_default=func.now())
    update_time = Column(TIMESTAMP, server_default=func.now())

    def __repr__(self):
        return f"<User {self.user_id} task_no {self.task_no}>"

    
    def to_dict(self):
        """转换为字典表示"""
        # return {
        #     'id': int(self.id),
        #     'task_no': self.task_no,
        #     'source_file_name': self.source_file_name,
        #     'source_file_path': self.source_file_path,
        #     'user_id': self.user_id,
        #     'status': int(self.status),
        #     'source_file_size': self.source_file_size,
        #     'source_file_duration_minutes': self.source_file_duration_minutes,
        #     'source_file_duration_seconds': self.source_file_duration_seconds,
        #     'transaction_id': int(self.transaction_id),
        #     'create_time': self.create_time if self.create_time else None,
        #     'update_time': self.update_time if self.update_time else None,
        # }
        print("self.create_time.timestamp() is ", self.create_time.timestamp())

        result = {
            'id': self.task_no,
            'filename': self.source_file_name,
            'path': self.source_file_path,
            'user_id': self.user_id,
            'status': self.getTaskStatus(int(self.status)),
            'size_mb': self.source_file_size,
            'audio_duration_minutes': self.source_file_duration_minutes,
            'audio_duration_seconds': self.source_file_duration_seconds,
            'transaction_id': int(self.transaction_id),
            'audio_path': self.audio_path,
            'segments': json.loads(self.segments) if self.segments else None,
            'output_files': json.loads(self.output_files) if self.output_files else None,
            'output_dir': self.output_dir,
            'create_time': self.create_time if self.create_time else None,
            'created_at': self.create_time.timestamp() if self.create_time else None,
            'update_time': self.update_time.timestamp() if self.update_time else None,
        }

        result['transcription'] = {'segments': result['segments']}
        return result

    def getTaskStatus(self, status: int):
        if (status == 0):
            return 'uploaded'
        elif (status == 1):
            return 'processing'
        elif (status == 2):
            return 'analyzed'
        elif (status == 3):
            return 'splitting'
        elif (status == 4):
            return 'completed'
        else:
            return 'failed'

# task_info = {
#     "id": task_id,
#     "filename": file.filename,
#     "path": file_path,
#     "original_file": file_path,  # 保存原始文件路径
#     "audio_path": audio_path,    # 保存提取的音频路径
#     "size_mb": file_size_mb,
#     "audio_duration_seconds": audio_duration_seconds,  # 添加音频时长信息
#     "audio_duration_minutes": audio_duration_minutes,  # 添加音频时长（分钟）
#     "status": "uploaded",
#     "progress": 0,
#     "message": "文件已上传",
#     "created_at": time.time(),
#     "user_id": user_id,  # 记录用户ID
#     "estimated_cost": estimated_cost  # 记录预估费用
# }