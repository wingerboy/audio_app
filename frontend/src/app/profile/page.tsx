'use client';

import { useState } from 'react';
import { FiUser, FiMail, FiSave, FiAlertCircle } from 'react-icons/fi';
import { useAppStore } from '@/lib/store';
import { apiService } from '@/lib/api';
import { ProtectedRoute } from '@/components/ProtectedRoute';

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <ProfileContent />
    </ProtectedRoute>
  );
}

function ProfileContent() {
  const user = useAppStore(state => state.auth.user);
  const updateUserInfo = useAppStore(state => state.updateUserInfo);
  
  const [username, setUsername] = useState(user?.username || '');
  const [email, setEmail] = useState(user?.email || '');
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<{
    type: 'success' | 'error' | null;
    message: string;
  }>({ type: null, message: '' });
  
  // 提交表单
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setStatus({ type: null, message: '' });
    
    try {
      const response = await apiService.updateUser({
        username,
        email
      });
      
      if (response.status === 'success' && response.user) {
        updateUserInfo(response.user);
        setStatus({
          type: 'success',
          message: '个人资料已成功更新'
        });
      } else {
        setStatus({
          type: 'error',
          message: response.message || '更新失败，请稍后重试'
        });
      }
    } catch (error: any) {
      console.error('更新个人资料失败', error);
      setStatus({
        type: 'error',
        message: error.response?.data?.message || '更新失败，请稍后重试'
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  // 如果没有用户信息，显示加载状态
  if (!user) {
    return (
      <div className="text-center py-10">
        <p>加载中...</p>
      </div>
    );
  }
  
  return (
    <div className="max-w-3xl mx-auto">
      <div className="bg-white shadow-sm rounded-lg overflow-hidden">
        <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
          <h1 className="text-xl font-semibold text-gray-900">个人资料</h1>
          <p className="mt-1 text-sm text-gray-500">
            管理您的账户信息
          </p>
        </div>
        
        <div className="px-4 py-5 sm:p-6">
          {status.type && (
            <div 
              className={`mb-4 p-4 rounded-md ${
                status.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
              }`}
            >
              <div className="flex">
                <div className="flex-shrink-0">
                  <FiAlertCircle className="h-5 w-5" />
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium">{status.message}</p>
                </div>
              </div>
            </div>
          )}
          
          <form onSubmit={handleSubmit}>
            <div className="space-y-6">
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                  用户名
                </label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <FiUser className="text-gray-400" />
                  </div>
                  <input
                    type="text"
                    id="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    className="pl-10 block w-full rounded-md border-gray-300 shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  />
                </div>
              </div>
              
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  电子邮箱
                </label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <FiMail className="text-gray-400" />
                  </div>
                  <input
                    type="email"
                    id="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="pl-10 block w-full rounded-md border-gray-300 shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  />
                </div>
              </div>
              
              <div className="text-sm text-gray-500">
                <p>账户创建时间: {new Date(user.created_at * 1000).toLocaleString()}</p>
                {user.last_login && (
                  <p>上次登录时间: {new Date(user.last_login * 1000).toLocaleString()}</p>
                )}
              </div>
              
              <div className="pt-5">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full sm:w-auto flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  {isLoading ? '更新中...' : (
                    <>
                      <FiSave className="mr-2 h-5 w-5" /> 保存更改
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
} 