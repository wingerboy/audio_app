'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { AuthForm } from '@/components/AuthForms';
import { useAppStore } from '@/lib/store';

export default function AuthPage() {
  const router = useRouter();
  const isAuthenticated = useAppStore(state => state.auth.isAuthenticated);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  
  // 如果已登录，重定向到首页
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, router]);
  
  // 切换认证模式
  const toggleAuthMode = () => {
    setAuthMode(authMode === 'login' ? 'register' : 'login');
  };
  
  // 认证成功处理
  const handleAuthSuccess = () => {
    // 可以添加成功提示或其他逻辑
    router.push('/');
  };
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md">
        <h1 className="text-3xl font-bold text-center text-primary-600 mb-8">
          音频分割工具
        </h1>
        
        <AuthForm
          mode={authMode}
          onModeChange={toggleAuthMode}
          onSuccess={handleAuthSuccess}
        />
        
        <p className="text-center text-gray-500 mt-8">
          使用本应用，即表示您同意我们的使用条款和隐私政策
        </p>
      </div>
    </div>
  );
} 