-- 切换到MySQL数据库
USE mysql;

-- 删除可能存在的用户
DROP USER IF EXISTS 'audio_app_user'@'%';
DROP USER IF EXISTS 'audio_app_user'@'localhost';

-- 创建数据库
CREATE DATABASE IF NOT EXISTS audio_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户并设置密码（使用mysql_native_password认证）
CREATE USER 'audio_app_user'@'%' IDENTIFIED WITH mysql_native_password BY 'yawen_12';
CREATE USER 'audio_app_user'@'localhost' IDENTIFIED WITH mysql_native_password BY 'yawen_12';

-- 授予权限
GRANT ALL PRIVILEGES ON audio_app.* TO 'audio_app_user'@'%';
GRANT ALL PRIVILEGES ON audio_app.* TO 'audio_app_user'@'localhost';

-- 刷新权限
FLUSH PRIVILEGES;

-- 切换到新创建的数据库
USE audio_app;

-- 设置连接字符集
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 设置字符集
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET character_set_client = utf8mb4;
SET character_set_connection = utf8mb4;
SET character_set_results = utf8mb4;

-- 设置时区
SET time_zone = '+08:00';

-- 显示配置验证
SHOW VARIABLES LIKE 'character%';
SHOW VARIABLES LIKE '%time_zone%'; 