import { AlertCircle, AlertTriangle, Info, XCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'

interface AlertCardProps {
  type: 'info' | 'warning' | 'error' | 'success'
  title: string
  message: string
  action?: {
    label: string
    href: string
  }
}

const typeConfig = {
  info: {
    icon: Info,
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    borderColor: 'border-blue-200 dark:border-blue-800',
    iconColor: 'text-blue-600 dark:text-blue-400',
    textColor: 'text-blue-800 dark:text-blue-300',
  },
  warning: {
    icon: AlertTriangle,
    bgColor: 'bg-yellow-50 dark:bg-yellow-900/20',
    borderColor: 'border-yellow-200 dark:border-yellow-800',
    iconColor: 'text-yellow-600 dark:text-yellow-400',
    textColor: 'text-yellow-800 dark:text-yellow-300',
  },
  error: {
    icon: XCircle,
    bgColor: 'bg-red-50 dark:bg-red-900/20',
    borderColor: 'border-red-200 dark:border-red-800',
    iconColor: 'text-red-600 dark:text-red-400',
    textColor: 'text-red-800 dark:text-red-300',
  },
  success: {
    icon: AlertCircle,
    bgColor: 'bg-green-50 dark:bg-green-900/20',
    borderColor: 'border-green-200 dark:border-green-800',
    iconColor: 'text-green-600 dark:text-green-400',
    textColor: 'text-green-800 dark:text-green-300',
  },
}

export default function AlertCard({ type, title, message, action }: AlertCardProps) {
  const config = typeConfig[type]
  const Icon = config.icon

  return (
    <div className={clsx(
      'rounded-lg border p-4',
      config.bgColor,
      config.borderColor
    )}>
      <div className="flex">
        <div className="flex-shrink-0">
          <Icon className={clsx('h-5 w-5', config.iconColor)} />
        </div>
        <div className="ml-3 flex-1">
          <h3 className={clsx('text-sm font-medium', config.textColor)}>
            {title}
          </h3>
          <div className={clsx('mt-2 text-sm', config.textColor, 'opacity-90')}>
            <p>{message}</p>
          </div>
          {action && (
            <div className="mt-4">
              <Link
                to={action.href}
                className={clsx(
                  'text-sm font-medium hover:underline',
                  config.iconColor
                )}
              >
                {action.label} →
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}