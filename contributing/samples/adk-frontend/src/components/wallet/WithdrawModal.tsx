import { Fragment, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { X, ArrowUpRight, CreditCard, Building2 } from 'lucide-react'

interface WithdrawModalProps {
  open: boolean
  onClose: () => void
  balance: number
  onWithdraw: (data: { amount: number; method: string }) => void
  isLoading?: boolean
}

export default function WithdrawModal({ open, onClose, balance, onWithdraw, isLoading }: WithdrawModalProps) {
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState('bank')
  const [errors, setErrors] = useState<{ amount?: string }>({})

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const newErrors: { amount?: string } = {}
    
    const withdrawAmount = parseFloat(amount)
    
    if (!amount || withdrawAmount <= 0) {
      newErrors.amount = 'Please enter a valid amount'
    } else if (withdrawAmount > balance) {
      newErrors.amount = 'Amount exceeds available balance'
    }
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }
    
    onWithdraw({ amount: withdrawAmount, method })
    setAmount('')
    setErrors({})
  }

  const handleClose = () => {
    setAmount('')
    setMethod('bank')
    setErrors({})
    onClose()
  }

  return (
    <Transition.Root show={open} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={handleClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md sm:p-6">
                <div className="absolute right-0 top-0 pr-4 pt-4">
                  <button
                    type="button"
                    className="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none"
                    onClick={handleClose}
                  >
                    <X className="h-6 w-6" />
                  </button>
                </div>

                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-green-100 dark:bg-green-900 sm:mx-0 sm:h-10 sm:w-10">
                    <ArrowUpRight className="h-6 w-6 text-green-600 dark:text-green-400" />
                  </div>
                  <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left w-full">
                    <Dialog.Title as="h3" className="text-lg font-semibold leading-6 text-gray-900 dark:text-white">
                      Withdraw Funds
                    </Dialog.Title>
                    
                    <form onSubmit={handleSubmit} className="mt-4">
                      {/* Balance Display */}
                      <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                        <p className="text-sm text-gray-500 dark:text-gray-400">Available Balance</p>
                        <p className="text-2xl font-bold text-gray-900 dark:text-white">
                          ${balance.toFixed(2)}
                        </p>
                      </div>

                      {/* Amount */}
                      <div className="mb-4">
                        <label htmlFor="amount" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Amount to Withdraw
                        </label>
                        <div className="mt-1 relative rounded-md shadow-sm">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <span className="text-gray-500 sm:text-sm">$</span>
                          </div>
                          <input
                            type="number"
                            id="amount"
                            step="0.01"
                            min="0"
                            max={balance}
                            value={amount}
                            onChange={(e) => {
                              setAmount(e.target.value)
                              setErrors({})
                            }}
                            className={`block w-full pl-7 pr-3 py-2 sm:text-sm rounded-md ${
                              errors.amount
                                ? 'border-red-300 text-red-900 placeholder-red-300 focus:ring-red-500 focus:border-red-500'
                                : 'border-gray-300 dark:border-gray-600 focus:ring-primary-500 focus:border-primary-500'
                            } dark:bg-gray-700 dark:text-white`}
                            placeholder="0.00"
                          />
                        </div>
                        {errors.amount && (
                          <p className="mt-1 text-sm text-red-600">{errors.amount}</p>
                        )}
                      </div>

                      {/* Withdrawal Method */}
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Withdrawal Method
                        </label>
                        <div className="space-y-2">
                          <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                            method === 'bank' ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' : 'border-gray-300 dark:border-gray-600'
                          }">
                            <input
                              type="radio"
                              value="bank"
                              checked={method === 'bank'}
                              onChange={(e) => setMethod(e.target.value)}
                              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300"
                            />
                            <div className="ml-3 flex items-center">
                              <Building2 className="h-5 w-5 text-gray-400 mr-2" />
                              <div>
                                <p className="text-sm font-medium text-gray-900 dark:text-white">Bank Transfer</p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">2-3 business days</p>
                              </div>
                            </div>
                          </label>
                          
                          <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                            method === 'card' ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' : 'border-gray-300 dark:border-gray-600'
                          }">
                            <input
                              type="radio"
                              value="card"
                              checked={method === 'card'}
                              onChange={(e) => setMethod(e.target.value)}
                              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300"
                            />
                            <div className="ml-3 flex items-center">
                              <CreditCard className="h-5 w-5 text-gray-400 mr-2" />
                              <div>
                                <p className="text-sm font-medium text-gray-900 dark:text-white">Debit Card</p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">Instant</p>
                              </div>
                            </div>
                          </label>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                        <button
                          type="submit"
                          disabled={isLoading || !amount || parseFloat(amount) <= 0}
                          className="inline-flex w-full justify-center rounded-md bg-primary-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 sm:ml-3 sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isLoading ? 'Processing...' : 'Withdraw'}
                        </button>
                        <button
                          type="button"
                          onClick={handleClose}
                          disabled={isLoading}
                          className="mt-3 inline-flex w-full justify-center rounded-md bg-white dark:bg-gray-700 px-3 py-2 text-sm font-semibold text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 sm:mt-0 sm:w-auto disabled:opacity-50"
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}