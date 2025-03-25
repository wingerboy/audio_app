'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FiUser, FiLogOut, FiSettings, FiMenu, FiX } from 'react-icons/fi';
import { useAppStore } from '@/lib/store';
import { apiService } from '@/lib/api';

export function Navbar() {
  const router = useRouter();
  const { auth, logout } = useAppStore(state => ({
    auth: state.auth,
    logout: state.logout
  }));
  
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  
  // 检查认证状态
  useEffect(() => {
    const checkAuth = async () => {
      // 如果本地有认证状态但没有用户信息，尝试获取用户信息
      if (auth.isAuthenticated && !auth.user) {
        try {
          const user = await apiService.getCurrentUser();
          if (user) {
            useAppStore.getState().updateUserInfo(user);
          } else {
            // 如果无法获取用户信息，清除认证状态
            logout();
          }
        } catch (error) {
          console.error('获取用户信息失败', error);
          logout();
        }
      }
    };
    
    checkAuth();
  }, [auth.isAuthenticated, auth.user, logout]);
  
  // 处理登出
  const handleLogout = () => {
    logout();
    setIsUserMenuOpen(false);
    router.push('/auth');
  };
  
  return (
    <nav className="bg-white dark:bg-gray-800 shadow-md border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link href="/" className="flex items-center">
              <span className="text-xl font-bold text-primary-600 dark:text-primary-400">音频处理控制台</span>
            </Link>
          </div>
          
          {/* 移动端菜单按钮 */}
          <div className="flex items-center sm:hidden">
            <button
              type="button"
              className="text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white focus:outline-none"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
            >
              {isMenuOpen ? <FiX size={24} /> : <FiMenu size={24} />}
            </button>
          </div>
          
          {/* 桌面端导航 */}
          <div className="hidden sm:flex sm:items-center">
            {auth.isAuthenticated && auth.user ? (
              <div className="relative ml-3">
                <div>
                  <button
                    type="button"
                    className="flex items-center text-sm rounded-full focus:outline-none"
                    onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  >
                    <div className="h-8 w-8 rounded-full bg-primary-100 dark:bg-primary-800 flex items-center justify-center text-primary-600 dark:text-primary-200 font-medium">
                      {auth.user.username.charAt(0).toUpperCase()}
                    </div>
                    <span className="ml-2 text-gray-800 dark:text-gray-200 font-medium">{auth.user.username}</span>
                  </button>
                </div>
                
                {isUserMenuOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg py-1 z-10 border border-gray-200 dark:border-gray-700">
                    <Link
                      href="/profile"
                      className="block px-4 py-2 text-sm text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center"
                      onClick={() => setIsUserMenuOpen(false)}
                    >
                      <FiUser className="mr-2" /> 个人资料
                    </Link>
                    <Link
                      href="/settings"
                      className="block px-4 py-2 text-sm text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center"
                      onClick={() => setIsUserMenuOpen(false)}
                    >
                      <FiSettings className="mr-2" /> 设置
                    </Link>
                    <button
                      onClick={handleLogout}
                      className="block w-full text-left px-4 py-2 text-sm text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center"
                    >
                      <FiLogOut className="mr-2" /> 退出登录
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Link
                href="/auth"
                className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                登录 / 注册
              </Link>
            )}
          </div>
        </div>
      </div>
      
      {/* 移动端菜单 */}
      {isMenuOpen && (
        <div className="sm:hidden">
          <div className="pt-2 pb-3 space-y-1 border-t border-gray-200 dark:border-gray-700">
            {auth.isAuthenticated && auth.user ? (
              <>
                <div className="px-4 py-2 text-sm text-gray-800 dark:text-gray-200 flex items-center">
                  <div className="h-8 w-8 rounded-full bg-primary-100 dark:bg-primary-800 flex items-center justify-center text-primary-600 dark:text-primary-200 font-medium mr-2">
                    {auth.user.username.charAt(0).toUpperCase()}
                  </div>
                  <span className="font-medium">{auth.user.username}</span>
                </div>
                <Link
                  href="/profile"
                  className="block px-4 py-2 text-sm text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <FiUser className="mr-2" /> 个人资料
                </Link>
                <Link
                  href="/settings"
                  className="block px-4 py-2 text-sm text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <FiSettings className="mr-2" /> 设置
                </Link>
                <button
                  onClick={handleLogout}
                  className="block w-full text-left px-4 py-2 text-sm text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center"
                >
                  <FiLogOut className="mr-2" /> 退出登录
                </button>
              </>
            ) : (
              <Link
                href="/auth"
                className="block px-4 py-2 text-sm text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                onClick={() => setIsMenuOpen(false)}
              >
                登录 / 注册
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  );
} 