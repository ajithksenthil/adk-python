import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useSupabase } from '../contexts/SupabaseContext'
import { useAuth } from '../contexts/AuthContext'
import cytoscape from 'cytoscape'
import cola from 'cytoscape-cola'
import TaskSidebar from '../components/liveboard/TaskSidebar'
import TaskFilters from '../components/liveboard/TaskFilters'
import { Task as BaseTask } from '@adk/supabase-sdk'

interface ExtendedTask extends BaseTask {
  task_id: string;
  type: string;
  assigned_to?: string;
  depends_on?: string[];
}
import toast from 'react-hot-toast'

// Register cola layout
cytoscape.use(cola)

// Node colors based on status
const nodeColors = {
  PENDING: '#9ca3af', // gray
  IN_PROGRESS: '#3b82f6', // blue
  COMPLETED: '#10b981', // green
  FAILED: '#ef4444', // red
  BLOCKED: '#f59e0b', // yellow
}

export default function LiveBoard() {
  const { adk } = useSupabase()
  const { projectId } = useAuth()
  const cyRef = useRef<HTMLDivElement>(null)
  const cyInstance = useRef<cytoscape.Core | null>(null)
  const [selectedTask, setSelectedTask] = useState<ExtendedTask | null>(null)
  const [filters, setFilters] = useState({
    status: 'all',
    type: 'all',
    assignee: 'all',
  })

  // Fetch tasks
  const { data: tasks, isLoading, refetch } = useQuery({
    queryKey: ['live-board-tasks', projectId, filters],
    queryFn: async () => {
      if (!projectId) return []
      
      const state = await adk.querySlice(`project-${projectId}`, 'tasks:*')
      const allTasks = Object.values(state.slice || {}) as ExtendedTask[]
      
      // Apply filters
      return allTasks.filter((task) => {
        if (filters.status !== 'all' && task.status !== filters.status) return false
        if (filters.type !== 'all' && task.type !== filters.type) return false
        if (filters.assignee !== 'all' && task.assigned_to !== filters.assignee) return false
        return true
      })
    },
    enabled: !!projectId,
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  // Approve task mutation
  const approveMutation = useMutation({
    mutationFn: async (taskId: string) => {
      const task = tasks?.find(t => t.id === taskId)
      if (!task) throw new Error('Task not found')
      
      // Update task status
      await adk.applyDelta(
        `project-${projectId}`,
        [{
          op: 'set',
          path: ['tasks', task.task_id, 'status'],
          value: 'IN_PROGRESS'
        }],
        'user'
      )
    },
    onSuccess: () => {
      toast.success('Task approved')
      refetch()
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to approve task')
    },
  })

  // Reject task mutation
  const rejectMutation = useMutation({
    mutationFn: async (taskId: string) => {
      const task = tasks?.find(t => t.id === taskId)
      if (!task) throw new Error('Task not found')
      
      await adk.applyDelta(
        `project-${projectId}`,
        [{
          op: 'set',
          path: ['tasks', task.task_id, 'status'],
          value: 'BLOCKED'
        }],
        'user'
      )
    },
    onSuccess: () => {
      toast.success('Task rejected')
      refetch()
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to reject task')
    },
  })

  // Initialize Cytoscape
  useEffect(() => {
    if (!cyRef.current || !tasks) return

    // Create Cytoscape instance
    const cy = cytoscape({
      container: cyRef.current,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (ele: any) => nodeColors[ele.data('status') as keyof typeof nodeColors],
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '12px',
            'color': '#fff',
            'text-outline-width': 2,
            'text-outline-color': (ele: any) => nodeColors[ele.data('status') as keyof typeof nodeColors],
            'width': 60,
            'height': 60,
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#ccc',
            'target-arrow-color': '#ccc',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier'
          }
        },
        {
          selector: ':selected',
          style: {
            'border-width': 3,
            'border-color': '#333'
          }
        }
      ],
      layout: {
        name: 'cola',
        animate: true,
        randomize: false,
        avoidOverlap: true,
        nodeSpacing: 100,
        edgeLength: 200,
      } as any,
      minZoom: 0.1,
      maxZoom: 2,
      wheelSensitivity: 0.1,
    })

    cyInstance.current = cy

    // Add nodes
    const nodes = tasks.map((task) => ({
      data: {
        id: task.id,
        label: task.task_id,
        status: task.status,
        task,
      }
    }))

    // Add edges based on dependencies
    const edges: any[] = []
    tasks.forEach((task) => {
      if (task.depends_on) {
        task.depends_on.forEach((depTaskId: string) => {
          const depTask = tasks.find(t => t.task_id === depTaskId)
          if (depTask) {
            edges.push({
              data: {
                id: `${depTask.id}-${task.id}`,
                source: depTask.id,
                target: task.id,
              }
            })
          }
        })
      }
    })

    cy.add([...nodes, ...edges])
    cy.layout({ name: 'cola' } as any).run()

    // Handle node click
    cy.on('tap', 'node', (evt) => {
      const task = evt.target.data('task')
      setSelectedTask(task)
    })

    // Handle background click
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedTask(null)
      }
    })

    return () => {
      cy.destroy()
    }
  }, [tasks])

  // Subscribe to real-time updates
  useEffect(() => {
    if (!projectId) return

    const unsubscribe = adk.subscribeToState(`project-${projectId}`, () => {
      refetch()
    })

    return unsubscribe
  }, [projectId, adk, refetch])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex">
      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Live Task Board</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {tasks?.length || 0} tasks • Real-time updates enabled
              </p>
            </div>
            <TaskFilters filters={filters} onChange={setFilters} />
          </div>
        </div>

        {/* Cytoscape container */}
        <div className="flex-1 relative">
          <div ref={cyRef} className="absolute inset-0 cy-container" />
          
          {/* Legend */}
          <div className="absolute bottom-4 left-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 space-y-2">
            <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">Task Status</p>
            {Object.entries(nodeColors).map(([status, color]) => (
              <div key={status} className="flex items-center space-x-2">
                <div 
                  className="w-4 h-4 rounded-full" 
                  style={{ backgroundColor: color }}
                />
                <span className="text-xs text-gray-600 dark:text-gray-400">
                  {status.replace('_', ' ')}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Task sidebar */}
      <TaskSidebar
        task={selectedTask}
        onClose={() => setSelectedTask(null)}
        onApprove={(taskId) => approveMutation.mutate(taskId)}
        onReject={(taskId) => rejectMutation.mutate(taskId)}
      />
    </div>
  )
}