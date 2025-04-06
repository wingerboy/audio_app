'use client';

import { useState } from 'react';
import { FiUser, FiMail, FiLock, FiAlertCircle, FiEye, FiEyeOff } from 'react-icons/fi';
import { useAppStore } from '@/lib/store';
import { apiService } from '@/lib/api';

interface AuthFormProps {
  mode: 'login' | 'register';
  onModeChange: () => void;
  onSuccess: () => void;
}

export function AuthForm({ mode, onModeChange, onSuccess }: AuthFormProps) {
  // 表单状态
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  
  // 获取登录方法
  const login = useAppStore(state => state.login);
  
  // 处理表单提交
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    
    try {
      if (mode === 'register') {
        // 注册流程
        const response = await apiService.register(username, email, password);
        
        if (response.status === 'success' && response.token && response.user) {
          // 注册成功后自动登录
          login(response.token, response.user);
          onSuccess();
        } else {
          setError(response.message || '注册失败，请稍后重试');
        }
      } else {
        // 登录流程
        const response = await apiService.login(email, password);
        
        if (response.status === 'success' && response.token && response.user) {
          login(response.token, response.user);
          onSuccess();
        } else {
          setError(response.message || '登录失败，请稍后重试');
        }
      }
    } catch (error: any) {
      console.error(`${mode === 'login' ? '登录' : '注册'}失败`, error);
      setError(error.response?.data?.message || `${mode === 'login' ? '登录' : '注册'}失败，请稍后重试`);
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="bg-white py-8 px-6 shadow rounded-lg sm:px-10">
      <form className="space-y-6" onSubmit={handleSubmit}>
        <h2 className="text-2xl font-bold text-center text-gray-900">
          {mode === 'login' ? '账号登录' : '创建账号'}
        </h2>
        
        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <FiAlertCircle className="h-5 w-5 text-red-400" />
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}
        
        {/* 仅注册时显示用户名字段 */}
        {mode === 'register' && (
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700">
              用户名
            </label>
            <div className="mt-1 relative rounded-md shadow-sm">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <FiUser className="text-gray-400" />
              </div>
              <input
                id="username"
                name="username"
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="pl-10 block w-full rounded-md border border-gray-400 bg-white text-gray-900 shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                placeholder="请输入用户名"
              />
            </div>
          </div>
        )}
        
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700">
            电子邮箱
          </label>
          <div className="mt-1 relative rounded-md shadow-sm">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <FiMail className="text-gray-400" />
            </div>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="pl-10 block w-full rounded-md border border-gray-400 bg-white text-gray-900 shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              placeholder="请输入电子邮箱"
            />
          </div>
        </div>
        
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700">
            密码
          </label>
          <div className="mt-1 relative rounded-md shadow-sm">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <FiLock className="text-gray-400" />
            </div>
            <input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="pl-10 pr-10 block w-full rounded-md border border-gray-400 bg-white text-gray-900 shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              placeholder={mode === 'login' ? '请输入密码' : '请设置密码（至少6位）'}
              minLength={6}
            />
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="text-gray-400 hover:text-gray-500 focus:outline-none"
                tabIndex={-1}
              >
                {showPassword ? (
                  <FiEyeOff className="h-5 w-5" aria-hidden="true" />
                ) : (
                  <FiEye className="h-5 w-5" aria-hidden="true" />
                )}
              </button>
            </div>
          </div>
        </div>
        
        <div>
          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            {isLoading 
              ? (mode === 'login' ? '登录中...' : '注册中...') 
              : (mode === 'login' ? '登录' : '注册')}
          </button>
        </div>
      </form>
      
      <div className="mt-6">
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">
              {mode === 'login' ? '还没有账号？' : '已经有账号？'}
            </span>
          </div>
        </div>
        
        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={onModeChange}
            className="text-primary-600 hover:text-primary-700 font-medium focus:outline-none"
          >
            {mode === 'login' ? '创建新账号' : '使用已有账号登录'}
          </button>
        </div>
      </div>
    </div>
  );
} 