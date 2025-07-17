import { Filter } from 'lucide-react'

interface TaskFiltersProps {
  filters: {
    status: string
    type: string
    assignee: string
  }
  onChange: (filters: any) => void
}

export default function TaskFilters({ filters, onChange }: TaskFiltersProps) {
  return (
    <div className="flex items-center space-x-3">
      <Filter className="h-4 w-4 text-gray-400" />
      
      {/* Status filter */}
      <select
        value={filters.status}
        onChange={(e) => onChange({ ...filters, status: e.target.value })}
        className="text-sm border border-gray-300 dark:border-gray-600 rounded-md px-3 py-1.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
      >
        <option value="all">All Status</option>
        <option value="PENDING">Pending</option>
        <option value="IN_PROGRESS">In Progress</option>
        <option value="COMPLETED">Completed</option>
        <option value="FAILED">Failed</option>
        <option value="BLOCKED">Blocked</option>
      </select>

      {/* Type filter */}
      <select
        value={filters.type}
        onChange={(e) => onChange({ ...filters, type: e.target.value })}
        className="text-sm border border-gray-300 dark:border-gray-600 rounded-md px-3 py-1.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
      >
        <option value="all">All Types</option>
        <option value="design">Design</option>
        <option value="frontend">Frontend</option>
        <option value="backend">Backend</option>
        <option value="testing">Testing</option>
        <option value="deployment">Deployment</option>
      </select>

      {/* Assignee filter */}
      <select
        value={filters.assignee}
        onChange={(e) => onChange({ ...filters, assignee: e.target.value })}
        className="text-sm border border-gray-300 dark:border-gray-600 rounded-md px-3 py-1.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
      >
        <option value="all">All Agents</option>
        <option value="design-bot">Design Bot</option>
        <option value="frontend-dev">Frontend Dev</option>
        <option value="backend-dev">Backend Dev</option>
        <option value="qa-bot">QA Bot</option>
      </select>
    </div>
  )
}