'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { LoadingSpinner } from './LoadingSpinner';

interface ProtectedRouteProps {
  children: React.ReactNode;
  redirectTo?: string;
}

export function ProtectedRoute({ 
  children, 
  redirectTo = '/auth' 
}: ProtectedRouteProps) {
  const router = useRouter();
  const { isAuthenticated, isAuthInitialized } = useAppStore(state => ({
    isAuthenticated: state.auth.isAuthenticated,
    isAuthInitialized: state.isAuthInitialized
  }));

  useEffect(() => {
    if (isAuthInitialized && !isAuthenticated) {
      router.push(redirectTo);
    }
  }, [isAuthenticated, isAuthInitialized, redirectTo, router]);

  // 如果认证状态还在初始化，显示加载状态
  if (!isAuthInitialized) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="md" />
      </div>
    );
  }

  // 只有在认证完成且已授权的情况下显示内容
  return isAuthenticated ? <>{children}</> : null;
} 