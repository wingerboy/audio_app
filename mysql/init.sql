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