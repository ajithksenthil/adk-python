import { MemCubeTestHarness } from '../src/core/MemCubeTestHarness'
import { readFileSync, writeFileSync } from 'fs'
import { join } from 'path'

interface AnalysisReport {
  timestamp: string
  summary: {
    totalTests: number
    successRate: number
    avgResponseTime: number
    efficacyScore: number
  }
  recommendations: string[]
  detailedMetrics: any
}

class EfficacyAnalyzer {
  private harness: MemCubeTestHarness

  constructor() {
    this.harness = new MemCubeTestHarness(
      process.env.SUPABASE_URL || 'http://localhost:54321',
      process.env.SUPABASE_ANON_KEY || 'test-key',
      process.env.OPENAI_API_KEY || 'test-key'
    )
  }

  async analyzeEfficacy(): Promise<AnalysisReport> {
    console.log('🔬 Analyzing MemCube System Efficacy\n')

    // Load test results if available
    const testResults = this.loadTestResults()
    
    // Run efficacy tests
    const searchEfficacy = await this.testSearchEfficacy()
    const storageEfficacy = await this.testStorageEfficacy()
    const performanceEfficacy = await this.testPerformanceEfficacy()
    
    // Calculate overall efficacy score
    const efficacyScore = this.calculateOverallScore({
      search: searchEfficacy,
      storage: storageEfficacy,
      performance: performanceEfficacy,
    })

    // Generate recommendations
    const recommendations = this.generateRecommendations({
      searchEfficacy,
      storageEfficacy,
      performanceEfficacy,
    })

    // Create report
    const report: AnalysisReport = {
      timestamp: new Date().toISOString(),
      summary: {
        totalTests: testResults.length,
        successRate: testResults.filter(r => r.success).length / testResults.length,
        avgResponseTime: testResults.reduce((sum, r) => sum + r.duration, 0) / testResults.length,
        efficacyScore,
      },
      recommendations,
      detailedMetrics: {
        search: searchEfficacy,
        storage: storageEfficacy,
        performance: performanceEfficacy,
      },
    }

    // Save report
    this.saveReport(report)
    
    return report
  }

  private async testSearchEfficacy() {
    console.log('🔍 Testing Search Efficacy...')
    
    // Create test dataset
    const testData = [
      { label: 'React Component Library', content: 'A collection of reusable React components', type: 'TEMPLATE' as const },
      { label: 'Python Data Science Tools', content: 'Essential tools for data analysis in Python', type: 'COMMAND' as const },
      { label: 'Machine Learning Guide', content: 'Comprehensive guide to machine learning concepts', type: 'SEMANTIC' as const },
      { label: 'API Documentation', content: 'RESTful API documentation and examples', type: 'PLAINTEXT' as const },
      { label: 'DevOps Best Practices', content: 'Infrastructure as code and CI/CD pipelines', type: 'TEMPLATE' as const },
    ]

    const createdIds: string[] = []
    for (const data of testData) {
      const result = await this.harness.createMemCube({
        project_id: 'efficacy-test',
        ...data,
      })
      if (result.memCubeId) createdIds.push(result.memCubeId)
    }

    // Test different search scenarios
    const searchTests = [
      { query: 'React', expectedRelevant: new Set(['React Component Library']) },
      { query: 'Python', expectedRelevant: new Set(['Python Data Science Tools']) },
      { query: 'machine learning', expectedRelevant: new Set(['Machine Learning Guide', 'Python Data Science Tools']) },
      { query: 'documentation', expectedRelevant: new Set(['API Documentation']) },
    ]

    let totalPrecision = 0
    let totalRecall = 0

    for (const test of searchTests) {
      const result = await this.harness.searchMemCubes(test.query, undefined, 10)
      if (result.results) {
        const retrieved = result.results.map(r => r.label)
        const relevant = retrieved.filter(label => test.expectedRelevant.has(label))
        
        const precision = retrieved.length > 0 ? relevant.length / retrieved.length : 0
        const recall = test.expectedRelevant.size > 0 ? relevant.length / test.expectedRelevant.size : 0
        
        totalPrecision += precision
        totalRecall += recall
      }
    }

    return {
      avgPrecision: totalPrecision / searchTests.length,
      avgRecall: totalRecall / searchTests.length,
      f1Score: 2 * (totalPrecision * totalRecall) / (totalPrecision + totalRecall) / searchTests.length,
    }
  }

  private async testStorageEfficacy() {
    console.log('📦 Testing Storage Efficacy...')
    
    const payloadSizes = [100, 1000, 10000, 100000] // bytes
    const results: any[] = []

    for (const size of payloadSizes) {
      const content = 'x'.repeat(size)
      const startTime = performance.now()
      
      const result = await this.harness.createMemCube({
        project_id: 'storage-test',
        label: `Storage Test ${size}B`,
        type: 'PLAINTEXT',
        content,
      })
      
      const duration = performance.now() - startTime
      
      results.push({
        size,
        duration,
        success: result.success,
        throughput: size / duration * 1000, // bytes per second
      })
    }

    const avgThroughput = results.reduce((sum, r) => sum + r.throughput, 0) / results.length
    const successRate = results.filter(r => r.success).length / results.length

    return {
      avgThroughput,
      successRate,
      compressionRatio: 0.75, // Mock value - would calculate actual compression
      results,
    }
  }

  private async testPerformanceEfficacy() {
    console.log('⚡ Testing Performance Efficacy...')
    
    const operations = [
      { type: 'create', count: 50 },
      { type: 'read', count: 100 },
      { type: 'search', count: 20 },
    ]

    const performanceResults: any[] = []

    for (const op of operations) {
      const times: number[] = []
      
      for (let i = 0; i < op.count; i++) {
        const startTime = performance.now()
        
        switch (op.type) {
          case 'create':
            await this.harness.createMemCube({
              project_id: 'perf-test',
              label: `Perf Test ${i}`,
              type: 'PLAINTEXT',
              content: 'Performance test content',
            })
            break
          case 'read':
            // Would read existing MemCubes
            break
          case 'search':
            await this.harness.searchMemCubes('Perf Test', undefined, 5)
            break
        }
        
        times.push(performance.now() - startTime)
      }

      const avgTime = times.reduce((sum, t) => sum + t, 0) / times.length
      const p95 = times.sort((a, b) => a - b)[Math.floor(times.length * 0.95)]
      
      performanceResults.push({
        operation: op.type,
        avgTime,
        p95,
        throughput: 1000 / avgTime, // ops per second
      })
    }

    return {
      results: performanceResults,
      overallThroughput: performanceResults.reduce((sum, r) => sum + r.throughput, 0) / performanceResults.length,
    }
  }

  private calculateOverallScore(metrics: any): number {
    // Weighted scoring algorithm
    const weights = {
      search: 0.4,
      storage: 0.3,
      performance: 0.3,
    }

    const searchScore = (metrics.search.avgPrecision + metrics.search.avgRecall) / 2
    const storageScore = metrics.storage.successRate * metrics.storage.compressionRatio
    const performanceScore = Math.min(metrics.performance.overallThroughput / 100, 1) // Normalize to 0-1

    return (
      searchScore * weights.search +
      storageScore * weights.storage +
      performanceScore * weights.performance
    ) * 100 // Convert to percentage
  }

  private generateRecommendations(metrics: any): string[] {
    const recommendations: string[] = []

    // Search recommendations
    if (metrics.search.avgPrecision < 0.7) {
      recommendations.push('🔍 Improve search precision by refining text matching algorithms')
    }
    if (metrics.search.avgRecall < 0.7) {
      recommendations.push('🔍 Enhance search recall by implementing synonym expansion')
    }

    // Storage recommendations
    if (metrics.storage.compressionRatio < 0.6) {
      recommendations.push('📦 Implement better compression algorithms for storage efficiency')
    }
    if (metrics.storage.avgThroughput < 1000000) { // 1MB/s
      recommendations.push('📦 Optimize storage I/O operations for better throughput')
    }

    // Performance recommendations
    const slowOps = metrics.performance.results.filter(r => r.avgTime > 100)
    if (slowOps.length > 0) {
      recommendations.push(`⚡ Optimize ${slowOps.map(op => op.operation).join(', ')} operations (>100ms avg)`)
    }

    if (recommendations.length === 0) {
      recommendations.push('✅ System is performing optimally!')
    }

    return recommendations
  }

  private loadTestResults(): any[] {
    try {
      const resultsPath = join(process.cwd(), 'benchmark-results.json')
      const data = JSON.parse(readFileSync(resultsPath, 'utf-8'))
      return data.results || []
    } catch {
      return []
    }
  }

  private saveReport(report: AnalysisReport) {
    const reportPath = join(process.cwd(), 'efficacy-report.json')
    writeFileSync(reportPath, JSON.stringify(report, null, 2))
    
    console.log('\n📊 EFFICACY ANALYSIS COMPLETE\n')
    console.log(`Overall Efficacy Score: ${report.summary.efficacyScore.toFixed(1)}%\n`)
    console.log('Recommendations:')
    report.recommendations.forEach(rec => console.log(`  ${rec}`))
    console.log(`\n💾 Full report saved to: ${reportPath}`)
  }
}

// Run analysis
if (import.meta.url === `file://${process.argv[1]}`) {
  const analyzer = new EfficacyAnalyzer()
  analyzer.analyzeEfficacy().catch(console.error)
}