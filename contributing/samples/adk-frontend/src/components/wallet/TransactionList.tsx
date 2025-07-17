import { ArrowUpRight, ArrowDownLeft, DollarSign } from 'lucide-react'
import { format } from 'date-fns'

interface Transaction {
  id: string
  type: 'earning' | 'withdrawal' | 'fee'
  amount: number
  description: string
  status: 'completed' | 'pending' | 'failed'
  task_id?: string
  created_at: string
}

interface TransactionListProps {
  transactions: Transaction[]
}

export default function TransactionList({ transactions }: TransactionListProps) {
  const getIcon = (type: Transaction['type']) => {
    switch (type) {
      case 'earning':
        return <ArrowDownLeft className="h-5 w-5 text-green-600" />
      case 'withdrawal':
        return <ArrowUpRight className="h-5 w-5 text-blue-600" />
      case 'fee':
        return <DollarSign className="h-5 w-5 text-gray-600" />
    }
  }

  const getStatusBadge = (status: Transaction['status']) => {
    const statusStyles = {
      completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    }

    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusStyles[status]}`}>
        {status}
      </span>
    )
  }

  const formatAmount = (amount: number, type: Transaction['type']) => {
    const isNegative = type === 'withdrawal' || type === 'fee'
    const displayAmount = Math.abs(amount)
    const sign = isNegative ? '-' : '+'
    const colorClass = isNegative ? 'text-red-600' : 'text-green-600'
    
    return (
      <span className={`font-medium ${colorClass}`}>
        {sign}${displayAmount.toFixed(2)}
      </span>
    )
  }

  if (transactions.length === 0) {
    return (
      <div className="px-6 py-12 text-center">
        <DollarSign className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">No transactions</h3>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Your transaction history will appear here.
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-900">
          <tr>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Transaction
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Status
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Date
            </th>
            <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Amount
            </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
          {transactions.map((transaction) => (
            <tr key={transaction.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    {getIcon(transaction.type)}
                  </div>
                  <div className="ml-4">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {transaction.description}
                    </div>
                    {transaction.task_id && (
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        Task: {transaction.task_id}
                      </div>
                    )}
                  </div>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                {getStatusBadge(transaction.status)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                {format(new Date(transaction.created_at), 'MMM d, yyyy')}
                <div className="text-xs">
                  {format(new Date(transaction.created_at), 'h:mm a')}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                {formatAmount(transaction.amount, transaction.type)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}