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
        let token = null;
        
        // 使用try-catch包装localStorage操作，防止隐私模式或其他限制导致的错误
        try {
          token = localStorage.getItem('auth_token');
        } catch (e) {
          console.error('访问localStorage失败:', e);
        }
        
        // 同时检查zustand store中是否已有token（可能通过持久化存储恢复）
        const storeAuth = useAppStore.getState().auth;
        
        // 如果store中已有token和用户信息，直接使用，无需再次请求API
        if (storeAuth.token && storeAuth.user && storeAuth.isAuthenticated) {
          // 确保API请求头设置正确
          apiService.setAuthToken(storeAuth.token);
          setAuthInitialized(true);
          return;
        }
        
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
        } else {
          // 没有发现token时，确保logout状态
          logout();
        }
      } catch (error) {
        console.error('认证初始化失败', error);
        logout();
      } finally {
        // 无论认证成功或失败，都标记认证已初始化
        setAuthInitialized(true);
      }
    };

    // 在组件挂载后延迟一小段时间初始化Auth，确保zustand持久化store已加载
    const timer = setTimeout(() => {
      initializeAuth();
    }, 50);
    
    return () => clearTimeout(timer);
  }, [login, logout, setAuthInitialized]);

  // 这个组件不渲染任何内容
  return null;
} 