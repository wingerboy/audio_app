'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { apiService, User } from '@/lib/api';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { isAgent, isAdmin } from '@/lib/roleUtils';
import { FiUser, FiMail, FiDollarSign, FiCalendar, FiSearch } from 'react-icons/fi';

// 交易记录接口
interface Transaction {
  id: string;
  amount: number;
  type: string;
  created_at: number;
  description?: string;
  recipient_email?: string;
  recipient_username?: string;
}

// 余额信息接口
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
  const [loadingQuery, setLoadingQuery] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [queryResult, setQueryResult] = useState<User | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
 
  const [agentBalance, setAgentBalance] = useState<number | null>(null);
  const [userBalance, setUserBalance] = useState<number | null>(null);
  const [balanceInfo, setBalanceInfo] = useState<BalanceInfo | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  
  // 非代理用户重定向到首页
  if (auth.user && !isAgent(auth.user) && !isAdmin(auth.user)) {
    router.push('/');
    return null;
  }

  // 获取余额信息和交易历史
  useEffect(() => {
    const fetchBalanceInfo = async () => {
      try {
        setLoadingHistory(true);
        const response = await apiService.getBalanceInfo();
        setBalanceInfo(response);
        setAgentBalance(response.balance);
      } catch (err) {
        console.error('获取账户信息失败:', err);
      } finally {
        setLoadingHistory(false);
      }
    };

    fetchBalanceInfo();
  }, [success]); // 当成功划扣后重新获取余额信息

  // 查找用户
  const handleFindUser = async () => {
    if (!email.trim()) {
      setQueryError('请输入电子邮箱');
      return;
    }
    
    // 验证邮箱格式
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setQueryError('请输入有效的电子邮箱地址');
      return;
    }

    setLoadingQuery(true);
    setQueryError(null);
    setQueryResult(null);
    
    try {
      const result = await apiService.findUserByEmail(email);
      if (result.status === 'success' && result.data && result.data.user) {
        setQueryResult(result.data.user);
      } else {
        setQueryError('未找到该用户');
      }
    } catch (err: any) {
      console.error('查找用户失败:', err);
      setQueryError(err.response?.data?.message || '查找用户失败，请重试');
    } finally {
      setLoadingQuery(false);
    }
  };
  
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
        // 计算实际到账金额
        const actualReceivedAmount = result.data.actual_received !== undefined 
          ? result.data.actual_received 
          : result.data.amount;

        // 显示详细信息
        setSuccess(`成功为邮箱 ${email} 划扣 ${amountValue} 点数`);
        setAgentBalance(result.data.agent_balance);
        setUserBalance(result.data.user_balance);

        // 如果实际到账金额与划扣金额不同，显示差异
        if (actualReceivedAmount !== amountValue) {
          setSuccess(`成功为邮箱 ${email} 划扣 ${amountValue} 点数，实际到账 ${actualReceivedAmount} 点数${
            amountValue > actualReceivedAmount 
              ? `（收取手续费 ${(amountValue - actualReceivedAmount).toFixed(2)} 点）` 
              : ''
          }`);
        }
        
        setAmount('');
        
        // 如果有查询结果，更新查询结果中的余额
        if (queryResult && queryResult.email === email) {
          setQueryResult({
            ...queryResult,
            balance: result.data.user_balance
          });
        }
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

  // 计算实际手续费和费率
  const calculateFeeInfo = (deducted: number, received: number): { fee: number, feeRate: number } => {
    const fee = deducted - received;
    const feeRate = fee > 0 ? (fee / deducted) * 100 : 0;
    return {
      fee: parseFloat(fee.toFixed(2)),
      feeRate: parseFloat(feeRate.toFixed(2))
    };
  };
  
  return (
    <ProtectedRoute>
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold">代理划扣</h1>
          <div className="flex gap-4">
            <button
              onClick={() => router.push('/profile')}
              className="text-primary-600 hover:text-primary-700"
            >
              个人中心
            </button>
            <button
              onClick={() => router.push('/')}
              className="text-primary-600 hover:text-primary-700"
            >
              返回首页
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-6">
            {/* 用户查找区域 */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">用户查找</h2>
              <div className="flex items-end gap-4">
                <div className="flex-grow">
                  <label htmlFor="query-email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    用户电子邮箱
                  </label>
                  <input
                    type="email"
                    id="query-email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                    placeholder="输入普通用户的电子邮箱"
                  />
                </div>
                <button
                  type="button"
                  onClick={handleFindUser}
                  disabled={loadingQuery}
                  className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50 flex items-center"
                >
                  <FiSearch className="mr-2" />
                  {loadingQuery ? '查找中...' : '查找用户'}
                </button>
              </div>
              
              {queryError && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-md">
                  {queryError}
                </div>
              )}
              
              {queryResult && (
                <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-lg flex items-center">
                      <FiUser className="mr-2" /> {queryResult.username}
                    </h3>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                    <div className="flex items-center text-gray-600">
                      <FiMail className="mr-2" /> {queryResult.email}
                    </div>
                    <div className="flex items-center text-gray-600">
                      <FiDollarSign className="mr-2" /> 余额: {queryResult.balance} 点
                    </div>
                    <div className="flex items-center text-gray-600">
                      <FiCalendar className="mr-2" /> 注册时间: {new Date(queryResult.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            {/* 划扣区域 */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">账户划扣</h2>
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
                    <div className="font-medium">{success}</div>
                    {agentBalance !== null && (
                      <div className="text-sm">代理划扣后余额: <span className="font-semibold">{agentBalance}</span> 点</div>
                    )}
                    {userBalance !== null && (
                      <div className="text-sm">用户充值后余额: <span className="font-semibold">{userBalance}</span> 点</div>
                    )}
                    <div className="mt-2 text-xs text-gray-500 bg-gray-50 p-2 rounded">
                      <div className="font-medium mb-1">划扣说明:</div>
                      <ul className="list-disc pl-4 space-y-1">
                        <li>划扣金额为整数点时，系统可能会收取手续费</li>
                        <li>代理账户扣除的是划扣的全部金额</li>
                        <li>用户实际到账金额可能会小于划扣金额</li>
                        <li>划扣手续费由系统自动计算，请以实际到账为准</li>
                      </ul>
                    </div>
                  </div>
                )}
                
                <button
                  type="submit"
                  disabled={loading || !email.trim()}
                  className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                >
                  {loading ? '处理中...' : '确认划扣'}
                </button>
              </form>
            </div>
          </div>

          {/* 账户信息和划扣记录 */}
          <div className="space-y-6">
            {/* 余额信息 */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">账户余额</h2>
                <div className="flex items-center text-2xl font-bold text-primary-600 dark:text-primary-400">
                  <FiDollarSign className="mr-2" />
                  {agentBalance !== null ? agentBalance : (balanceInfo?.balance || 0)} 点数
                </div>
              </div>
            </div>

            {/* 划扣记录 */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">划扣记录</h2>
              </div>
              <div className="overflow-x-auto max-h-96 overflow-y-auto">
                {loadingHistory ? (
                  <div className="flex justify-center items-center p-6">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
                  </div>
                ) : (
                  <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                    <thead className="bg-gray-50 dark:bg-gray-800">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          时间
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          类型
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          金额
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          说明
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                      {!balanceInfo || balanceInfo.transactions.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="px-4 py-3 text-center text-gray-500 dark:text-gray-400">
                            暂无划扣记录
                          </td>
                        </tr>
                      ) : (
                        balanceInfo.transactions
                          .filter(t => t.type === 'agent_charge' || t.type === 'agent_consume')
                          .map((transaction) => (
                            <tr key={transaction.id}>
                              <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500 dark:text-gray-400">
                                {new Date(transaction.created_at * 1000).toLocaleString()}
                              </td>
                              <td className="px-4 py-3 whitespace-nowrap text-xs">
                                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                                  transaction.type === 'agent_charge'
                                    ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                                    : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                                }`}>
                                  {getTransactionTypeLabel(transaction.type)}
                                </span>
                              </td>
                              <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-900 dark:text-white">
                                {transaction.type === 'agent_consume' ? '+' : '-'}{transaction.amount} 点数
                              </td>
                              <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500 dark:text-gray-400">
                                {transaction.recipient_email ? `用户: ${transaction.recipient_email}` : (transaction.description || '-')}
                              </td>
                            </tr>
                          ))
                      )}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
} 