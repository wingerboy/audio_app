"""
余额系统模块，负责用户充值、消费和余额管理
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from src.balance_system.db import init_db
from flask import Blueprint

# 初始化日志
logger = logging.getLogger(__name__)

# 创建蓝图
bp = Blueprint('balance', __name__)

def init_app(app):
    """初始化余额系统"""
    try:
        # 初始化数据库
        init_db()
        # 注册蓝图
        app.register_blueprint(bp, url_prefix='/api/balance')
        print("余额系统初始化完成")
    except Exception as e:
        print(f"余额系统初始化失败: {str(e)}")
        raise 