import { useEffect, useState } from 'react';
import { FiClock, FiDollarSign, FiArrowLeft } from 'react-icons/fi';
import apiService from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { useRouter } from 'next/navigation';

interface BalanceInfo {
  balance: number;
  transactions: {
    id: string;
    amount: number;
    type: string;
    created_at: number;
    description?: string;
  }[];
}

export function UserProfile() {
  const [balanceInfo, setBalanceInfo] = useState<BalanceInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const user = useAppStore(state => state.auth.user);
  const router = useRouter();

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

  useEffect(() => {
    const fetchBalanceInfo = async () => {
      try {
        setLoading(true);
        const response = await apiService.getBalanceInfo();
        setBalanceInfo(response);
      } catch (err) {
        setError('获取账户信息失败');
        console.error('获取账户信息失败:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchBalanceInfo();
  }, []);

  const handleGoBack = () => {
    router.back();
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 text-red-700 rounded-md">
        {error}
      </div>
    );
  }

  if (!balanceInfo) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* 返回按钮 */}
      <button 
        onClick={handleGoBack}
        className="flex items-center text-primary-600 hover:text-primary-700 mb-4"
      >
        <FiArrowLeft className="mr-1" /> 返回
      </button>
      
      {/* 用户基本信息 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">账号信息</h2>
        <div className="space-y-3">
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">用户名</span>
            <span className="font-medium">{user?.username || '未设置'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">邮箱</span>
            <span className="font-medium">{user?.email || '未设置'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">注册时间</span>
            <span className="font-medium">
              {user?.created_at ? new Date(user.created_at).toLocaleString() : '未知'}
            </span>
          </div>
        </div>
      </div>

      {/* 余额信息 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">账户余额</h2>
          <div className="flex items-center text-2xl font-bold text-primary-600 dark:text-primary-400">
            <FiDollarSign className="mr-2" />
            {balanceInfo.balance} 点数
          </div>
        </div>
      </div>

      {/* 充值记录 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">充值记录</h2>
        </div>
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
              {balanceInfo.transactions.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                    暂无充值记录
                  </td>
                </tr>
              ) : (
                balanceInfo.transactions.map((transaction) => (
                  <tr key={transaction.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {new Date(transaction.created_at * 1000).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        transaction.type === 'credit' || transaction.type === 'agent_charge' || transaction.type === 'register'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' 
                          : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                      }`}>
                        {getTransactionTypeLabel(transaction.type)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {(transaction.type === 'credit' || transaction.type === 'agent_charge' || transaction.type === 'register') ? '+' : ''}{transaction.amount} 点数
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
      </div>
    </div>
  );
} 