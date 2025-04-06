'use client';

import { useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { apiService } from '@/lib/api';

export function AuthInitializer() {
  const { login, logout, setAuthInitialized } = useAppStore((state) => ({
    login: state.login,
    logout: state.logout,
    setAuthInitialized: state.setAuthInitialized
  }));

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        // 检查本地存储中是否有token
        const token = localStorage.getItem('auth_token');
        
        if (token) {
          // 设置API服务的token
          apiService.setAuthToken(token);
          
          // 尝试获取当前用户信息
          const user = await apiService.getCurrentUser();
          
          if (user) {
            // 如果成功获取用户信息，更新认证状态
            login(token, user);
          } else {
            // 如果无法获取用户信息，清除认证状态
            logout();
          }
        }
      } catch (error) {
        console.error('认证初始化失败', error);
        logout();
      } finally {
        // 无论认证成功或失败，都标记认证已初始化
        setAuthInitialized(true);
      }
    };

    initializeAuth();
  }, [login, logout, setAuthInitialized]);

  // 这个组件不渲染任何内容
  return null;
} 