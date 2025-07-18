import React, { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'
import { useAuth } from '../contexts/AuthContext'
import { useProject } from '../contexts/ProjectContext'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card'
import { Button } from '../components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'
import { Badge } from '../components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import {
  Activity,
  TrendingUp,
  Users,
  Database,
  Download,
  RefreshCw,
  Clock,
  Zap,
  Tag,
  BarChart2,
} from 'lucide-react'

interface DashboardData {
  summary: {
    total_memories: number
    active_memories: number
    total_accesses: number
    unique_users: number
  }
  top_memories: Array<{
    id: string
    label: string
    type: string
    heat: number
    access_count: number
    last_accessed: string
  }>
  tag_cloud: Array<{
    tag: string
    memory_count: number
    total_accesses: number
    popularity_score: number
  }>
  usage_trend: Array<{
    period: string
    access_count: number
    unique_memories: number
  }>
  heat_distribution: {
    hot: number
    warm: number
    cool: number
    cold: number
  }
  recent_activity: Array<{
    id: string
    event_type: string
    interaction_type: string
    created_at: string
    memory_label: string
    user_name: string
  }>
}

const HEAT_COLORS = {
  hot: '#ef4444',
  warm: '#f59e0b',
  cool: '#3b82f6',
  cold: '#6b7280',
}

export default function Analytics() {
  const { user } = useAuth()
  const { selectedProject } = useProject()
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const [recommendations, setRecommendations] = useState<any[]>([])
  const [timeRange, setTimeRange] = useState('7d')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    if (selectedProject) {
      fetchAnalytics()
    }
  }, [selectedProject, timeRange])

  const fetchAnalytics = async () => {
    if (!selectedProject) return

    try {
      setLoading(true)
      setError(null)

      const { data, error } = await supabase.functions.invoke('memory-analytics', {
        body: {
          action: 'dashboard',
          project_id: selectedProject.id,
          time_range: timeRange,
        },
      })

      if (error) throw error

      setDashboardData(data.dashboard)
      setRecommendations(data.recommendations || [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const exportAnalytics = async (format: 'json' | 'csv') => {
    if (!selectedProject) return

    try {
      const { data, error } = await supabase.functions.invoke('memory-analytics', {
        body: {
          action: 'export',
          project_id: selectedProject.id,
          time_range: timeRange,
          export_format: format,
        },
      })

      if (error) throw error

      // Create download link
      const blob = new Blob([format === 'csv' ? data : JSON.stringify(data, null, 2)], {
        type: format === 'csv' ? 'text/csv' : 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `analytics_${selectedProject.id}_${timeRange}.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err: any) {
      setError(err.message)
    }
  }

  if (!selectedProject) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Please select a project</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-destructive mb-4">{error}</p>
          <Button onClick={fetchAnalytics}>Retry</Button>
        </div>
      </div>
    )
  }

  if (!dashboardData) return null

  const heatData = Object.entries(dashboardData.heat_distribution).map(([key, value]) => ({
    name: key.charAt(0).toUpperCase() + key.slice(1),
    value,
    fill: HEAT_COLORS[key as keyof typeof HEAT_COLORS],
  }))

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Memory Analytics</h1>
          <p className="text-muted-foreground">
            Insights into memory usage and performance
          </p>
        </div>
        <div className="flex gap-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">Last Hour</SelectItem>
              <SelectItem value="24h">Last 24h</SelectItem>
              <SelectItem value="7d">Last 7 Days</SelectItem>
              <SelectItem value="30d">Last 30 Days</SelectItem>
              <SelectItem value="90d">Last 90 Days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={fetchAnalytics}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button variant="outline" onClick={() => exportAnalytics('json')}>
            <Download className="h-4 w-4 mr-2" />
            Export JSON
          </Button>
          <Button variant="outline" onClick={() => exportAnalytics('csv')}>
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Memories</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboardData.summary.total_memories}
            </div>
            <p className="text-xs text-muted-foreground">
              {dashboardData.summary.active_memories} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Accesses</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboardData.summary.total_accesses}
            </div>
            <p className="text-xs text-muted-foreground">In selected period</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Unique Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboardData.summary.unique_users}
            </div>
            <p className="text-xs text-muted-foreground">Agents and users</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Heat Level</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Math.round(
                (dashboardData.heat_distribution.hot * 90 +
                  dashboardData.heat_distribution.warm * 65 +
                  dashboardData.heat_distribution.cool * 35 +
                  dashboardData.heat_distribution.cold * 10) /
                  Object.values(dashboardData.heat_distribution).reduce(
                    (a, b) => a + b,
                    0
                  )
              )}
            </div>
            <p className="text-xs text-muted-foreground">Memory temperature</p>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="memories">Top Memories</TabsTrigger>
          <TabsTrigger value="tags">Tag Analysis</TabsTrigger>
          <TabsTrigger value="activity">Recent Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Usage Trend Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Usage Trend</CardTitle>
                <CardDescription>Memory accesses over time</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={dashboardData.usage_trend}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="period"
                      tickFormatter={(value) =>
                        new Date(value).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                        })
                      }
                    />
                    <YAxis />
                    <Tooltip
                      labelFormatter={(value) =>
                        new Date(value).toLocaleString()
                      }
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="access_count"
                      stroke="#8884d8"
                      name="Total Accesses"
                    />
                    <Line
                      type="monotone"
                      dataKey="unique_memories"
                      stroke="#82ca9d"
                      name="Unique Memories"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Heat Distribution Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Heat Distribution</CardTitle>
                <CardDescription>Memory temperature breakdown</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={heatData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) =>
                        `${name} ${(percent * 100).toFixed(0)}%`
                      }
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {heatData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Recommended Memories</CardTitle>
                <CardDescription>
                  Based on collaborative filtering
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {recommendations.map((rec) => (
                    <div
                      key={rec.memory_id}
                      className="flex items-center justify-between p-2 rounded-lg border"
                    >
                      <div>
                        <p className="font-medium">{rec.memory_id}</p>
                        <p className="text-sm text-muted-foreground">
                          {rec.reason}
                        </p>
                      </div>
                      <Badge variant="secondary">
                        Score: {(rec.score * 100).toFixed(0)}%
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="memories" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Top Memories</CardTitle>
              <CardDescription>Most accessed memories in this period</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {dashboardData.top_memories.map((memory) => (
                  <div
                    key={memory.id}
                    className="flex items-center justify-between p-3 rounded-lg border"
                  >
                    <div className="flex-1">
                      <p className="font-medium">{memory.label}</p>
                      <div className="flex gap-2 mt-1">
                        <Badge variant="outline">{memory.type}</Badge>
                        <span className="text-sm text-muted-foreground">
                          {memory.access_count} accesses
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div
                        className="w-2 h-8 rounded"
                        style={{
                          backgroundColor:
                            memory.heat > 80
                              ? HEAT_COLORS.hot
                              : memory.heat > 50
                              ? HEAT_COLORS.warm
                              : memory.heat > 20
                              ? HEAT_COLORS.cool
                              : HEAT_COLORS.cold,
                        }}
                      />
                      <span className="text-sm font-medium">{memory.heat}</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tags" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Tag Cloud</CardTitle>
              <CardDescription>Popular tags by usage</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {dashboardData.tag_cloud.map((tag) => {
                  const size = Math.min(
                    Math.max(12 + tag.popularity_score * 2, 12),
                    32
                  )
                  return (
                    <Badge
                      key={tag.tag}
                      variant="secondary"
                      style={{ fontSize: `${size}px` }}
                      className="cursor-pointer hover:bg-secondary/80"
                    >
                      {tag.tag} ({tag.total_accesses})
                    </Badge>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Tag Performance</CardTitle>
              <CardDescription>Tag usage statistics</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={dashboardData.tag_cloud.slice(0, 10)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="tag" angle={-45} textAnchor="end" height={80} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="total_accesses" fill="#8884d8" />
                  <Bar dataKey="memory_count" fill="#82ca9d" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Latest memory interactions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {dashboardData.recent_activity.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-center justify-between p-2 rounded-lg border"
                  >
                    <div className="flex-1">
                      <p className="font-medium">{activity.memory_label}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {activity.event_type}
                        </Badge>
                        {activity.interaction_type && (
                          <Badge variant="outline" className="text-xs">
                            {activity.interaction_type}
                          </Badge>
                        )}
                        <span className="text-xs text-muted-foreground">
                          by {activity.user_name || 'Agent'}
                        </span>
                      </div>
                    </div>
                    <span className="text-sm text-muted-foreground">
                      {new Date(activity.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}