import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { EfficacyDashboard } from './EfficacyDashboard'
import { MemCubeTestHarness } from '../core/MemCubeTestHarness'
import './index.css'

// Create query client
const queryClient = new QueryClient()

// Initialize test harness
const harness = new MemCubeTestHarness(
  import.meta.env.VITE_SUPABASE_URL || 'http://localhost:54321',
  import.meta.env.VITE_SUPABASE_ANON_KEY || 'test-key',
  import.meta.env.VITE_OPENAI_API_KEY || 'test-key'
)

function App() {
  const [testResults, setTestResults] = React.useState([])
  const [efficacyMetrics, setEfficacyMetrics] = React.useState({
    accuracy: 0,
    recall: 0,
    precision: 0,
    f1Score: 0,
    avgResponseTime: 0,
    throughput: 0,
    storageEfficiency: 0,
  })
  const [isRunning, setIsRunning] = React.useState(false)

  // Load existing results
  React.useEffect(() => {
    const savedResults = localStorage.getItem('memcube-test-results')
    if (savedResults) {
      const parsed = JSON.parse(savedResults)
      setTestResults(parsed.results || [])
      setEfficacyMetrics(parsed.metrics || efficacyMetrics)
    }
  }, [])

  // Run live tests
  const runLiveTests = async () => {
    setIsRunning(true)
    harness.clearTestResults()

    try {
      // Run various test scenarios
      console.log('Running create tests...')
      for (let i = 0; i < 10; i++) {
        await harness.createMemCube({
          project_id: 'live-test',
          label: `Live Test ${i}`,
          type: ['PLAINTEXT', 'SEMANTIC', 'COMMAND', 'TEMPLATE'][i % 4] as any,
          content: `Test content ${i}`,
        })
      }

      // Run search tests
      console.log('Running search tests...')
      await harness.searchMemCubes('Live Test', undefined, 5)
      await harness.searchMemCubes('Test content', 'SEMANTIC', 5)

      // Get results
      const results = harness.getTestResults().map(r => ({
        ...r,
        timestamp: new Date().toISOString(),
      }))

      // Calculate metrics (mock for demo)
      const metrics = harness.calculateEfficacyMetrics(
        new Set(['id1', 'id2', 'id3']),
        ['id1', 'id2', 'id4']
      )

      // Update state
      setTestResults(prev => [...prev, ...results])
      setEfficacyMetrics(metrics)

      // Save to localStorage
      localStorage.setItem('memcube-test-results', JSON.stringify({
        results: [...testResults, ...results],
        metrics,
      }))
    } catch (error) {
      console.error('Test error:', error)
    } finally {
      setIsRunning(false)
    }
  }

  const clearResults = () => {
    setTestResults([])
    setEfficacyMetrics({
      accuracy: 0,
      recall: 0,
      precision: 0,
      f1Score: 0,
      avgResponseTime: 0,
      throughput: 0,
      storageEfficiency: 0,
    })
    localStorage.removeItem('memcube-test-results')
  }

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-100">
        {/* Control Panel */}
        <div className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4">
              <h1 className="text-xl font-semibold text-gray-900">
                MemCube Testing Dashboard
              </h1>
              <div className="flex space-x-4">
                <button
                  onClick={runLiveTests}
                  disabled={isRunning}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {isRunning ? 'Running Tests...' : 'Run Live Tests'}
                </button>
                <button
                  onClick={clearResults}
                  className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                >
                  Clear Results
                </button>
              </div>
            </div>
          </div>
        </div>
        
        {/* Dashboard */}
        <EfficacyDashboard
          testResults={testResults}
          efficacyMetrics={efficacyMetrics}
        />
      </div>
    </QueryClientProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)