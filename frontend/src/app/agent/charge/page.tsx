'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { apiService } from '@/lib/api';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { isAgent, isAdmin } from '@/lib/roleUtils';
import { FiUser, FiMail, FiDollarSign, FiCalendar, FiClock } from 'react-icons/fi';

// 添加交易记录接口
interface Transaction {
  id: string;
  amount: number;
  type: string;
  created_at: number;
  description?: string;
}

// 添加余额信息接口
interface BalanceInfo {
  balance: number;
  transactions: Transaction[];
}

export default function AgentChargePage() {
  const router = useRouter();
  const { auth } = useAppStore();
  const [email, setEmail] = useState('');
  const [amount, setAmount] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [agentBalance, setAgentBalance] = useState<number | null>(null);
  const [userBalance, setUserBalance] = useState<number | null>(null);
  const [balanceInfo, setBalanceInfo] = useState<BalanceInfo | null>(null);
  const [foundUser, setFoundUser] = useState<any | null>(null);
  const [loadingBalanceInfo, setLoadingBalanceInfo] = useState(false);
  
  // 非代理用户重定向到首页
  if (auth.user && !isAgent(auth.user) && !isAdmin(auth.user)) {
    router.push('/');
    return null;
  }

  // 获取代理余额信息
  useEffect(() => {
    const fetchBalanceInfo = async () => {
      if (!(auth.user && (isAgent(auth.user) || isAdmin(auth.user)))) return;
      
      setLoadingBalanceInfo(true);
      try {
        const response = await apiService.getBalanceInfo();
        setBalanceInfo(response);
      } catch (err) {
        console.error('获取余额信息失败:', err);
      } finally {
        setLoadingBalanceInfo(false);
      }
    };
    
    fetchBalanceInfo();
  }, [auth.user]);

  // 查找用户
  const handleFindUser = async () => {
    if (!email.trim()) {
      setSearchError('请输入电子邮箱');
      return;
    }
    
    // 验证邮箱格式
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setSearchError('请输入有效的电子邮箱地址');
      return;
    }

    setSearchLoading(true);
    setSearchError(null);
    
    try {
      const result = await apiService.findUserByEmail(email);
      if (result.status === 'success' && result.data && result.data.user) {
        setFoundUser(result.data.user);
        setUserBalance(result.data.user.balance);
      } else {
        setSearchError('未找到该用户');
        setFoundUser(null);
      }
    } catch (err: any) {
      console.error('查找用户失败:', err);
      setSearchError(err.response?.data?.message || '查找用户失败，请重试');
      setFoundUser(null);
    } finally {
      setSearchLoading(false);
    }
  };
  
  // 划扣提交
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!foundUser) {
      setError('请先查找用户');
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
        setSuccess(`成功为用户 ${foundUser.username} 划扣 ${amountValue} 点数`);
        setAgentBalance(result.data.agent_balance);
        setUserBalance(result.data.user_balance);
        setAmount('');
        
        // 更新代理余额信息和交易记录
        const updatedBalanceInfo = await apiService.getBalanceInfo();
        setBalanceInfo(updatedBalanceInfo);
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

  // 获取交易类型标签
  const getTransactionTypeLabel = (type: string): string => {
    switch(type) {
      case 'credit':
        return '充值';
      case 'agent_charge':
        return '代理充值';
      case 'register':
        return '注册赠送';
      case 'agent_consume':
        return '划扣支出';
      case 'consume':
        return '消费';
      default:
        return type;
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
                placeholder="输入普通用户的电子邮箱"
              />
            </div>
            <button
              type="button"
              onClick={handleFindUser}
              disabled={searchLoading}
              className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50"
            >
              {searchLoading ? '查找中...' : '查找用户'}
            </button>
          </div>
          
          {searchError && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-md">
              {searchError}
            </div>
          )}
          
          {foundUser && (
            <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-md">
              <h3 className="font-semibold text-lg mb-2 flex items-center">
                <FiUser className="mr-2" /> 用户信息
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                <div className="flex items-center">
                  <span className="text-gray-500 dark:text-gray-400 mr-2">用户名:</span>
                  <span className="font-medium">{foundUser.username}</span>
                </div>
                <div className="flex items-center">
                  <span className="text-gray-500 dark:text-gray-400 mr-2">余额:</span>
                  <span className="font-medium">{foundUser.balance} 点</span>
                </div>
                <div className="flex items-center">
                  <span className="text-gray-500 dark:text-gray-400 mr-2">邮箱:</span>
                  <span className="font-medium">{foundUser.email}</span>
                </div>
              </div>
            </div>
          )}
        </div>
        
        {/* 划扣区域 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">划扣充值</h2>
          <form onSubmit={handleSubmit}>
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
              disabled={loading || !foundUser}
              className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
            >
              {loading ? '处理中...' : '确认划扣'}
            </button>
          </form>
        </div>
        
        {/* 余额信息 */}
        {balanceInfo && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">账户余额</h2>
              <div className="flex items-center text-2xl font-bold text-primary-600 dark:text-primary-400">
                <FiDollarSign className="mr-2" />
                {balanceInfo.balance} 点数
              </div>
            </div>
          </div>
        )}
        
        {/* 划扣记录 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">划扣记录</h2>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">查看您作为代理的所有划扣记录</p>
          </div>
          
          {loadingBalanceInfo ? (
            <div className="flex justify-center p-6">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      时间
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      类型
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      金额
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      说明
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {!balanceInfo || balanceInfo.transactions.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                        暂无划扣记录
                      </td>
                    </tr>
                  ) : (
                    // 筛选出代理划扣相关的交易记录
                    balanceInfo.transactions
                      .filter(tx => tx.type === 'agent_consume')
                      .map((transaction) => (
                        <tr key={transaction.id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                            {new Date(transaction.created_at * 1000).toLocaleString()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">
                              {getTransactionTypeLabel(transaction.type)}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                            {transaction.amount} 点数
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                            {transaction.description || '-'}
                          </td>
                        </tr>
                      ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
} 