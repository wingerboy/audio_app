import os
from typing import Dict, Any

class BaseDBConfig:
    """数据库基础配置"""
    # 数据库连接池配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    POOL_SIZE = 5
    MAX_OVERFLOW = 10
    POOL_TIMEOUT = 30
    POOL_RECYCLE = 3600
    
    def __init__(self):
        """初始化配置"""
        self.DB_USER = os.environ.get('MYSQL_USER', 'audio_app_user')
        self.DB_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
        self.DB_PORT = os.environ.get('MYSQL_PORT', '3306')
        self.DB_NAME = os.environ.get('MYSQL_DATABASE', 'audio_app')
        self.DB_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """数据库连接URI"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换配置为字典"""
        return {key: getattr(self, key) for key in dir(self) 
                if key.isupper() and not key.startswith('_')}

class LocalDBConfig(BaseDBConfig):
    """本地开发数据库配置"""
    ENV = 'local'

class DockerDBConfig(BaseDBConfig):
    """Docker环境数据库配置"""
    ENV = 'docker'

class ProductionDBConfig(BaseDBConfig):
    """生产环境数据库配置"""
    ENV = 'production'
    
    def __init__(self):
        """生产环境必须通过环境变量设置所有配置"""
        super().__init__()
        required_vars = ['MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_HOST', 'MYSQL_DATABASE']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            raise ValueError(f"生产环境缺少必要的环境变量: {', '.join(missing_vars)}")

# 配置映射
db_config_by_name = {
    'local': LocalDBConfig(),
    'docker': DockerDBConfig(),
    'production': ProductionDBConfig()
}

def get_db_config():
    """获取当前环境的数据库配置"""
    env = os.environ.get('FLASK_ENV', 'local')
    return db_config_by_name[env] 