import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useSupabase } from '../contexts/SupabaseContext'
import { useAuth } from '../contexts/AuthContext'
import { Wallet as WalletIcon, ArrowUpRight, ArrowDownLeft, DollarSign, TrendingUp, Download } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import WithdrawModal from '../components/wallet/WithdrawModal'
import TransactionList from '../components/wallet/TransactionList'

interface WalletData {
  balance: number
  pending_earnings: number
  total_earned: number
  total_withdrawn: number
  currency: string
}

interface Transaction {
  id: string
  type: 'earning' | 'withdrawal' | 'fee'
  amount: number
  description: string
  status: 'completed' | 'pending' | 'failed'
  task_id?: string
  created_at: string
}

export default function Wallet() {
  const { } = useSupabase()
  const { projectId } = useAuth()
  const [showWithdrawModal, setShowWithdrawModal] = useState(false)
  const [selectedPeriod, setSelectedPeriod] = useState('7d')

  // Fetch wallet data
  const { data: wallet, isLoading: walletLoading } = useQuery({
    queryKey: ['wallet', projectId],
    queryFn: async () => {
      if (!projectId) return null
      
      // Mock data - replace with real API call
      const mockWallet: WalletData = {
        balance: 1234.56,
        pending_earnings: 98.50,
        total_earned: 5678.90,
        total_withdrawn: 4444.34,
        currency: 'USD',
      }
      
      return mockWallet
    },
    enabled: !!projectId,
  })

  // Fetch transactions
  const { data: transactions, isLoading: transactionsLoading } = useQuery({
    queryKey: ['transactions', projectId, selectedPeriod],
    queryFn: async () => {
      if (!projectId) return []
      
      // Mock data - replace with real API call
      const mockTransactions: Transaction[] = [
        {
          id: '1',
          type: 'earning',
          amount: 12.30,
          description: 'Task AD_VARIANTS completed',
          status: 'completed',
          task_id: 'AD_VARIANTS',
          created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: '2',
          type: 'earning',
          amount: 45.00,
          description: 'Template royalty - React Component',
          status: 'completed',
          created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: '3',
          type: 'withdrawal',
          amount: -500.00,
          description: 'Withdrawal to bank account',
          status: 'completed',
          created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: '4',
          type: 'fee',
          amount: -5.00,
          description: 'Processing fee',
          status: 'completed',
          created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
        },
      ]
      
      return mockTransactions
    },
    enabled: !!projectId,
  })

  // Earnings chart data
  const chartData = [
    { date: '2024-01-01', earnings: 120 },
    { date: '2024-01-02', earnings: 150 },
    { date: '2024-01-03', earnings: 180 },
    { date: '2024-01-04', earnings: 140 },
    { date: '2024-01-05', earnings: 200 },
    { date: '2024-01-06', earnings: 220 },
    { date: '2024-01-07', earnings: 190 },
  ]

  // Withdraw mutation
  const withdrawMutation = useMutation({
    mutationFn: async (data: { amount: number; method: string }) => {
      // Implement withdrawal logic
      console.log('Processing withdrawal:', data)
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 2000))
    },
    onSuccess: () => {
      toast.success('Withdrawal initiated')
      setShowWithdrawModal(false)
      // Refetch wallet data
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to process withdrawal')
    },
  })

  const loading = walletLoading || transactionsLoading

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Wallet</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage your earnings and payouts
          </p>
        </div>
        <button
          onClick={() => setShowWithdrawModal(true)}
          disabled={!wallet || wallet.balance === 0}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ArrowUpRight className="h-4 w-4 mr-2" />
          Withdraw
        </button>
      </div>

      {/* Balance Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Available Balance</p>
              <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
                ${wallet?.balance.toFixed(2) || '0.00'}
              </p>
            </div>
            <div className="p-3 bg-green-100 dark:bg-green-900 rounded-lg">
              <WalletIcon className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Pending Earnings</p>
              <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
                ${wallet?.pending_earnings.toFixed(2) || '0.00'}
              </p>
            </div>
            <div className="p-3 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
              <DollarSign className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Earned</p>
              <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
                ${wallet?.total_earned.toFixed(2) || '0.00'}
              </p>
            </div>
            <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-lg">
              <TrendingUp className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Withdrawn</p>
              <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
                ${wallet?.total_withdrawn.toFixed(2) || '0.00'}
              </p>
            </div>
            <div className="p-3 bg-purple-100 dark:bg-purple-900 rounded-lg">
              <ArrowDownLeft className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Earnings Chart */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">Earnings Overview</h2>
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="text-sm border border-gray-300 dark:border-gray-600 rounded-md px-3 py-1.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorEarnings" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis 
              dataKey="date" 
              tickFormatter={(value) => format(new Date(value), 'MMM d')}
              className="text-xs"
            />
            <YAxis className="text-xs" />
            <Tooltip 
              formatter={(value) => `$${value}`}
              labelFormatter={(label) => format(new Date(label), 'MMM d, yyyy')}
            />
            <Area 
              type="monotone" 
              dataKey="earnings" 
              stroke="#3b82f6" 
              fillOpacity={1} 
              fill="url(#colorEarnings)" 
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Transactions */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white">Recent Transactions</h2>
            <button className="text-sm text-primary-600 hover:text-primary-500 font-medium inline-flex items-center">
              <Download className="h-4 w-4 mr-1" />
              Export
            </button>
          </div>
        </div>
        <TransactionList transactions={transactions || []} />
      </div>

      {/* Withdraw Modal */}
      <WithdrawModal
        open={showWithdrawModal}
        onClose={() => setShowWithdrawModal(false)}
        balance={wallet?.balance || 0}
        onWithdraw={(data) => withdrawMutation.mutate(data)}
        isLoading={withdrawMutation.isPending}
      />
    </div>
  )
}