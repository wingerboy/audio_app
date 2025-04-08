'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { apiService, User } from '@/lib/api';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { hasSpecialRole, ROLE_USER, ROLE_ADMIN, ROLE_AGENT, ROLE_SENIOR_AGENT, getRoleName, isAdmin } from '@/lib/roleUtils';
import { FiUser, FiMail, FiDollarSign, FiCalendar } from 'react-icons/fi';

export default function AdminChargePage() {
  const router = useRouter();
  const { auth } = useAppStore();
  const [email, setEmail] = useState('');
  const [amount, setAmount] = useState('');
  const [role, setRole] = useState(ROLE_USER.toString());
  const [loading, setLoading] = useState(false);
  const [loadingRole, setLoadingRole] = useState(false);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorRole, setErrorRole] = useState<string | null>(null);
  const [errorUsers, setErrorUsers] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [successRole, setSuccessRole] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [specialUsers, setSpecialUsers] = useState<User[]>([]);
  
  // 非管理员用户重定向到首页
  if (auth.user && !isAdmin(auth.user)) {
    router.push('/');
    return null;
  }

  // 获取特殊用户列表
  useEffect(() => {
    const fetchSpecialUsers = async () => {
      if (!isAdmin(auth.user)) return;
      
      setLoadingUsers(true);
      setErrorUsers(null);
      
      try {
        const result = await apiService.getSpecialUsers();
        if (result.status === 'success' && result.data?.users) {
          setSpecialUsers(result.data.users);
        } else {
          setErrorUsers('获取用户列表失败');
        }
      } catch (err: any) {
        console.error('获取特殊用户列表失败:', err);
        setErrorUsers(err.response?.data?.message || '获取特殊用户列表失败');
      } finally {
        setLoadingUsers(false);
      }
    };
    
    fetchSpecialUsers();
  }, [auth.user]);

  // 查找用户
  const handleFindUser = async () => {
    if (!email.trim()) {
      setError('请输入电子邮箱');
      return;
    }
    
    // 验证邮箱格式
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('请输入有效的电子邮箱地址');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      // 这里应该添加一个查找用户的API调用
      // 假设这个API返回userId和当前角色
      const result = await apiService.findUserByEmail(email);
      if (result.status === 'success' && result.data && result.data.user) {
        setUserId(result.data.user.id);
        setRole(result.data.user.role.toString());
        setSuccess(`找到用户: ${result.data.user.username}`);
      } else {
        setError('未找到该用户');
      }
    } catch (err: any) {
      console.error('查找用户失败:', err);
      setError(err.response?.data?.message || '查找用户失败，请重试');
    } finally {
      setLoading(false);
    }
  };
  
  // 充值提交
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email.trim()) {
      setError('请输入电子邮箱');
      return;
    }
    
    // 验证邮箱格式
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('请输入有效的电子邮箱地址');
      return;
    }
    
    if (!amount || amount.trim() === '') {
      setError('请输入充值点数');
      return;
    }

    const amountValue = parseFloat(amount);
    if (isNaN(amountValue) || amountValue <= 0) {
      setError('请输入有效的充值点数');
      return;
    }
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      const result = await apiService.adminCharge(email, amountValue);
      setSuccess(`成功为邮箱 ${email} 充值 ${amountValue} 点数`);
      setAmount('');
    } catch (err: any) {
      console.error('充值失败:', err);
      setError(err.response?.data?.message || '充值失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 角色分配提交
  const handleRoleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!userId) {
      setErrorRole('请先查找用户');
      return;
    }
    
    setLoadingRole(true);
    setErrorRole(null);
    setSuccessRole(null);
    
    try {
      const roleValue = parseInt(role);
      const result = await apiService.updateUserRole(userId, roleValue);
      setSuccessRole(`成功将用户角色更新为: ${getRoleName(roleValue)}`);
    } catch (err: any) {
      console.error('更新角色失败:', err);
      setErrorRole(err.response?.data?.message || '更新角色失败，请重试');
    } finally {
      setLoadingRole(false);
    }
  };
  
  return (
    <ProtectedRoute>
      <div className="max-w-2xl mx-auto p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold">管理员控制面板</h1>
          <button
            onClick={() => router.push('/')}
            className="text-primary-600 hover:text-primary-700"
          >
            返回首页
          </button>
        </div>
        
        {/* 用户查找区域 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">用户查找</h2>
          <div className="flex items-end gap-4">
            <div className="flex-grow">
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                电子邮箱
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                placeholder="输入电子邮箱"
              />
            </div>
            <button
              type="button"
              onClick={handleFindUser}
              disabled={loading}
              className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50"
            >
              {loading ? '查找中...' : '查找用户'}
            </button>
          </div>
          
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-md">
              {error}
            </div>
          )}
          
          {success && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 text-green-600 rounded-md">
              {success}
            </div>
          )}
        </div>
        
        {/* 充值区域 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">账户充值</h2>
          <form onSubmit={handleSubmit}>
            <div className="mb-6">
              <label htmlFor="amount" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                充值点数
              </label>
              <input
                type="number"
                id="amount"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                placeholder="输入充值点数"
                min="1"
                step="1"
              />
            </div>
            
            <button
              type="submit"
              disabled={loading || !email.trim()}
              className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
            >
              {loading ? '处理中...' : '确认充值'}
            </button>
          </form>
        </div>
        
        {/* 角色分配区域 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">角色分配</h2>
          {userId ? (
            <form onSubmit={handleRoleSubmit}>
              <div className="mb-6">
                <label htmlFor="role" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  用户角色
                </label>
                <select
                  id="role"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value={ROLE_USER.toString()}>普通用户</option>
                  <option value={ROLE_ADMIN.toString()}>管理员</option>
                  <option value={ROLE_AGENT.toString()}>一级代理</option>
                  <option value={ROLE_SENIOR_AGENT.toString()}>高级代理</option>
                </select>
              </div>
              
              {errorRole && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-md">
                  {errorRole}
                </div>
              )}
              
              {successRole && (
                <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-600 rounded-md">
                  {successRole}
                </div>
              )}
              
              <button
                type="submit"
                disabled={loadingRole}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {loadingRole ? '处理中...' : '更新角色'}
              </button>
            </form>
          ) : (
            <div className="text-center text-gray-500 dark:text-gray-400 py-4">
              请先查找用户来分配角色
            </div>
          )}
        </div>
        
        {/* 特殊用户列表区域 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mt-6">
          <h2 className="text-xl font-semibold mb-4">特殊用户列表</h2>
          
          {loadingUsers ? (
            <div className="flex justify-center py-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : errorUsers ? (
            <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded-md">
              {errorUsers}
            </div>
          ) : specialUsers.length === 0 ? (
            <div className="text-center py-4 text-gray-500">
              暂无特殊用户
            </div>
          ) : (
            <div className="space-y-4">
              {specialUsers.map(user => (
                <div key={user.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-lg flex items-center">
                      <FiUser className="mr-2" /> {user.username}
                    </h3>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      user.role === ROLE_ADMIN 
                        ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300'
                        : user.role === ROLE_SENIOR_AGENT
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                        : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                    }`}>
                      {user.role_name}
                    </span>
                  </div>
                  
                  <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                    <div className="flex items-center text-gray-600 dark:text-gray-400">
                      <FiMail className="mr-2" /> {user.email}
                    </div>
                    <div className="flex items-center text-gray-600 dark:text-gray-400">
                      <FiDollarSign className="mr-2" /> 余额: {user.balance} 点
                    </div>
                    <div className="flex items-center text-gray-600 dark:text-gray-400">
                      <FiCalendar className="mr-2" /> 注册: {new Date(user.created_at).toLocaleDateString()}
                    </div>
                    <div className="flex items-center text-gray-600 dark:text-gray-400">
                      消费/充值: {user.total_consumed}/{user.total_charged}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
} 