'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { ProtectedRoute } from '@/components/ProtectedRoute';

export default function AdminTestPage() {
  const router = useRouter();
  const { auth, setCurrentUserAsAdmin } = useAppStore();
  const [success, setSuccess] = useState<string | null>(null);
  
  const handleSetAdmin = () => {
    setCurrentUserAsAdmin();
    setSuccess('已将当前用户设置为管理员，刷新页面后即可看到"管理员充值"选项');
  };
  
  return (
    <ProtectedRoute>
      <div className="max-w-2xl mx-auto p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold">开发测试</h1>
          <button
            onClick={() => router.push('/')}
            className="text-primary-600 hover:text-primary-700"
          >
            返回首页
          </button>
        </div>
        
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-medium mb-4">用户信息</h2>
          <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700 rounded-md">
            <p><span className="font-medium">ID:</span> {auth.user?.id}</p>
            <p><span className="font-medium">用户名:</span> {auth.user?.username}</p>
            <p><span className="font-medium">邮箱:</span> {auth.user?.email}</p>
            <p><span className="font-medium">余额:</span> {auth.user?.balance} 点</p>
            <p><span className="font-medium">是否管理员:</span> {auth.user?.is_admin ? '是' : '否'}</p>
          </div>
          
          {success && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-600 rounded-md">
              {success}
            </div>
          )}
          
          <button
            onClick={handleSetAdmin}
            className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            将当前用户设置为管理员
          </button>
        </div>
      </div>
    </ProtectedRoute>
  );
} 