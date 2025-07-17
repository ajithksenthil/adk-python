import React, { useState, useEffect } from 'react'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts'
import { format } from 'date-fns'

interface TestResult {
  testId: string
  memCubeId: string
  operation: 'create' | 'read' | 'update' | 'delete' | 'search'
  success: boolean
  duration: number
  error?: string
  metadata?: Record<string, any>
  timestamp?: string
}

interface EfficacyMetrics {
  accuracy: number
  recall: number
  precision: number
  f1Score: number
  avgResponseTime: number
  throughput: number
  storageEfficiency: number
}

interface DashboardProps {
  testResults: TestResult[]
  efficacyMetrics: EfficacyMetrics
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']

export const EfficacyDashboard: React.FC<DashboardProps> = ({ testResults, efficacyMetrics }) => {
  const [selectedOperation, setSelectedOperation] = useState<string>('all')
  const [timeRange, setTimeRange] = useState<string>('1h')
  
  // Process data for charts
  const operationStats = testResults.reduce((acc, result) => {
    if (!acc[result.operation]) {
      acc[result.operation] = { count: 0, success: 0, totalTime: 0 }
    }
    acc[result.operation].count++
    if (result.success) acc[result.operation].success++
    acc[result.operation].totalTime += result.duration
    return acc
  }, {} as Record<string, { count: number; success: number; totalTime: number }>)

  const operationData = Object.entries(operationStats).map(([op, stats]) => ({
    operation: op,
    count: stats.count,
    successRate: (stats.success / stats.count * 100).toFixed(1),
    avgTime: (stats.totalTime / stats.count).toFixed(2),
  }))

  // Timeline data
  const timelineData = testResults
    .filter(r => r.timestamp)
    .sort((a, b) => new Date(a.timestamp!).getTime() - new Date(b.timestamp!).getTime())
    .reduce((acc, result) => {
      const hour = format(new Date(result.timestamp!), 'HH:00')
      if (!acc[hour]) {
        acc[hour] = { time: hour, operations: 0, avgDuration: 0, errors: 0 }
      }
      acc[hour].operations++
      acc[hour].avgDuration = (acc[hour].avgDuration + result.duration) / 2
      if (!result.success) acc[hour].errors++
      return acc
    }, {} as Record<string, any>)

  const timelineArray = Object.values(timelineData)

  // Radar chart data for efficacy metrics
  const radarData = [
    { metric: 'Accuracy', value: efficacyMetrics.accuracy * 100 },
    { metric: 'Recall', value: efficacyMetrics.recall * 100 },
    { metric: 'Precision', value: efficacyMetrics.precision * 100 },
    { metric: 'F1 Score', value: efficacyMetrics.f1Score * 100 },
    { metric: 'Storage Eff.', value: efficacyMetrics.storageEfficiency * 100 },
  ]

  // Performance distribution
  const performanceDistribution = testResults.reduce((acc, result) => {
    const bucket = Math.floor(result.duration / 50) * 50
    const key = `${bucket}-${bucket + 50}ms`
    acc[key] = (acc[key] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const distributionData = Object.entries(performanceDistribution)
    .map(([range, count]) => ({ range, count }))
    .sort((a, b) => parseInt(a.range) - parseInt(b.range))

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">MemCube Efficacy Dashboard</h1>
          <p className="text-gray-600 mt-2">Real-time performance and accuracy metrics</p>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Total Operations</h3>
            <p className="text-3xl font-bold text-gray-900">{testResults.length}</p>
            <p className="text-sm text-green-600 mt-2">
              {testResults.filter(r => r.success).length} successful
            </p>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Avg Response Time</h3>
            <p className="text-3xl font-bold text-gray-900">
              {efficacyMetrics.avgResponseTime.toFixed(2)}ms
            </p>
            <p className="text-sm text-gray-600 mt-2">
              Throughput: {efficacyMetrics.throughput.toFixed(1)} ops/sec
            </p>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Accuracy</h3>
            <p className="text-3xl font-bold text-gray-900">
              {(efficacyMetrics.accuracy * 100).toFixed(1)}%
            </p>
            <p className="text-sm text-gray-600 mt-2">
              F1 Score: {(efficacyMetrics.f1Score * 100).toFixed(1)}%
            </p>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500">Storage Efficiency</h3>
            <p className="text-3xl font-bold text-gray-900">
              {(efficacyMetrics.storageEfficiency * 100).toFixed(0)}%
            </p>
            <p className="text-sm text-gray-600 mt-2">
              Compression ratio
            </p>
          </div>
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Operation Performance */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Operation Performance</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={operationData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="operation" />
                <YAxis yAxisId="left" orientation="left" stroke="#8884d8" />
                <YAxis yAxisId="right" orientation="right" stroke="#82ca9d" />
                <Tooltip />
                <Legend />
                <Bar yAxisId="left" dataKey="count" fill="#8884d8" name="Count" />
                <Bar yAxisId="right" dataKey="avgTime" fill="#82ca9d" name="Avg Time (ms)" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Efficacy Radar */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Efficacy Metrics</h3>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="metric" />
                <PolarRadiusAxis angle={90} domain={[0, 100]} />
                <Radar
                  name="Performance"
                  dataKey="value"
                  stroke="#8884d8"
                  fill="#8884d8"
                  fillOpacity={0.6}
                />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* Timeline Chart */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Operations Timeline</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={timelineArray}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="operations" stroke="#8884d8" name="Operations" />
                <Line type="monotone" dataKey="avgDuration" stroke="#82ca9d" name="Avg Duration" />
                <Line type="monotone" dataKey="errors" stroke="#ff7300" name="Errors" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Response Time Distribution */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Response Time Distribution</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={distributionData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Success Rate by Type */}
        <div className="bg-white rounded-lg shadow p-6 mt-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Success Rate by Operation</h3>
          <div className="space-y-4">
            {operationData.map((op, index) => (
              <div key={op.operation} className="flex items-center">
                <div className="w-32 text-sm font-medium text-gray-900">{op.operation}</div>
                <div className="flex-1">
                  <div className="w-full bg-gray-200 rounded-full h-6">
                    <div
                      className="bg-green-500 h-6 rounded-full flex items-center justify-center text-white text-xs font-medium"
                      style={{ width: `${op.successRate}%` }}
                    >
                      {op.successRate}%
                    </div>
                  </div>
                </div>
                <div className="w-24 text-right text-sm text-gray-600 ml-4">
                  {op.count} ops
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}