"""
数据库连接和会话管理模块
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from .config import get_db_config
from contextlib import contextmanager

# 初始化日志
logger = logging.getLogger(__name__)

# 获取配置
db_config = get_db_config()

# 创建引擎
engine = create_engine(
    db_config.SQLALCHEMY_DATABASE_URI,
    pool_size=db_config.POOL_SIZE,
    max_overflow=db_config.MAX_OVERFLOW,
    pool_timeout=db_config.POOL_TIMEOUT,
    pool_recycle=db_config.POOL_RECYCLE
)

# 创建会话工厂
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建线程安全的会话
db_session = scoped_session(Session)

# 创建基类
Base = declarative_base()
Base.query = db_session.query_property()

@contextmanager
def get_db_session():
    """
    获取数据库会话的上下文管理器
    
    用法:
    with get_db_session() as session:
        # 使用session进行数据库操作
        user = session.query(User).filter_by(id=1).first()
    
    Returns:
        SQLAlchemy会话对象
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"数据库会话操作失败: {str(e)}")
        raise
    finally:
        session.close()

def init_db():
    """初始化数据库"""
    try:
        # 导入所有模型以确保它们被注册
        # 注意：导入顺序很重要，被引用的表需要先导入
        from src.balance_system.models.user import User  # 先导入 User 模型
        from src.balance_system.models.user_balance import UserBalance
        from src.balance_system.models.transaction_record import TransactionRecord
        from src.balance_system.models.api_usage import ApiUsage
        from src.balance_system.models.pricing_rule import PricingRule
        from src.balance_system.models.charge_package import ChargePackage
        from src.balance_system.models.user_task import UserTask
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise

def shutdown_session(exception=None):
    """关闭会话"""
    db_session.remove() 