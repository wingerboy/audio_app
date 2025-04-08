'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { apiService } from '@/lib/api';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { isAgent, isAdmin } from '@/lib/roleUtils';

export default function AgentChargePage() {
  const router = useRouter();
  const { auth } = useAppStore();
  const [email, setEmail] = useState('');
  const [amount, setAmount] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [agentBalance, setAgentBalance] = useState<number | null>(null);
  const [userBalance, setUserBalance] = useState<number | null>(null);
  
  // 非代理用户重定向到首页
  if (auth.user && !isAgent(auth.user) && !isAdmin(auth.user)) {
    router.push('/');
    return null;
  }
  
  // 划扣提交
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
      setError('请输入划扣点数');
      return;
    }

    const amountValue = parseFloat(amount);
    if (isNaN(amountValue) || amountValue <= 0) {
      setError('请输入有效的划扣点数');
      return;
    }
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    setAgentBalance(null);
    setUserBalance(null);
    
    try {
      const result = await apiService.agentCharge(email, amountValue);
      if (result.status === 'success' && result.data) {
        setSuccess(`成功为邮箱 ${email} 划扣 ${amountValue} 点数`);
        setAgentBalance(result.data.agent_balance);
        setUserBalance(result.data.user_balance);
        setAmount('');
      } else {
        setError(result.message || '划扣失败，请重试');
      }
    } catch (err: any) {
      console.error('划扣失败:', err);
      setError(err.response?.data?.message || '划扣失败，请重试');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <ProtectedRoute>
      <div className="max-w-2xl mx-auto p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold">代理划扣</h1>
          <button
            onClick={() => router.push('/')}
            className="text-primary-600 hover:text-primary-700"
          >
            返回首页
          </button>
        </div>
        
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                用户电子邮箱
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                placeholder="输入普通用户的电子邮箱"
              />
            </div>
            
            <div className="mb-6">
              <label htmlFor="amount" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                划扣点数
              </label>
              <input
                type="number"
                id="amount"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                placeholder="输入划扣点数"
                min="1"
                step="1"
              />
            </div>
            
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-md">
                {error}
              </div>
            )}
            
            {success && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-600 rounded-md flex flex-col gap-1">
                <div>{success}</div>
                {agentBalance !== null && (
                  <div className="text-sm">代理划扣后余额: <span className="font-semibold">{agentBalance}</span> 点</div>
                )}
                {userBalance !== null && (
                  <div className="text-sm">用户充值后余额: <span className="font-semibold">{userBalance}</span> 点</div>
                )}
              </div>
            )}
            
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
            >
              {loading ? '处理中...' : '确认划扣'}
            </button>
          </form>
        </div>
      </div>
    </ProtectedRoute>
  );
} 