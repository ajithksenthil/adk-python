import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react'
import clsx from 'clsx'

interface KPICardProps {
  title: string
  value: string | number
  icon: LucideIcon
  trend?: number
  subtitle?: string
  color?: 'green' | 'blue' | 'purple' | 'yellow' | 'red'
}

const colorClasses = {
  green: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  blue: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  purple: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  yellow: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  red: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
}

export default function KPICard({ 
  title, 
  value, 
  icon: Icon, 
  trend, 
  subtitle,
  color = 'blue' 
}: KPICardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
          <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">{value}</p>
          {subtitle && (
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>
          )}
          {trend !== undefined && (
            <div className="mt-2 flex items-center text-sm">
              {trend > 0 ? (
                <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
              ) : (
                <TrendingDown className="h-4 w-4 text-red-500 mr-1" />
              )}
              <span className={clsx(
                'font-medium',
                trend > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
              )}>
                {Math.abs(trend)}%
              </span>
              <span className="ml-2 text-gray-500 dark:text-gray-400">vs last week</span>
            </div>
          )}
        </div>
        <div className={clsx(
          'p-3 rounded-lg',
          colorClasses[color]
        )}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  )
}