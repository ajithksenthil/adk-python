import { MemCubeTestHarness } from '../../src/core/MemCubeTestHarness'
import { performance } from 'perf_hooks'
import { writeFileSync } from 'fs'
import { join } from 'path'

interface BenchmarkResult {
  operation: string
  iterations: number
  totalTime: number
  avgTime: number
  minTime: number
  maxTime: number
  throughput: number
  percentiles: {
    p50: number
    p90: number
    p95: number
    p99: number
  }
}

class MemCubeBenchmark {
  private harness: MemCubeTestHarness
  private results: BenchmarkResult[] = []

  constructor() {
    this.harness = new MemCubeTestHarness(
      process.env.SUPABASE_URL || 'http://localhost:54321',
      process.env.SUPABASE_ANON_KEY || 'test-key',
      process.env.OPENAI_API_KEY || 'test-key'
    )
  }

  async runBenchmarks() {
    console.log('🚀 Starting MemCube Performance Benchmarks\n')

    // Benchmark different operations
    await this.benchmarkCreate()
    await this.benchmarkRead()
    await this.benchmarkTextSearch()
    await this.benchmarkSemanticSearch()
    await this.benchmarkConcurrentOperations()
    await this.benchmarkLargePayloads()

    // Generate report
    this.generateReport()
  }

  private async benchmarkCreate() {
    console.log('📝 Benchmarking CREATE operations...')
    const iterations = 100
    const times: number[] = []

    for (let i = 0; i < iterations; i++) {
      const start = performance.now()
      
      await this.harness.createMemCube({
        project_id: 'benchmark-project',
        label: `Benchmark MemCube ${i}`,
        type: 'PLAINTEXT',
        content: 'This is benchmark content for testing performance.',
      })

      const duration = performance.now() - start
      times.push(duration)

      if (i % 10 === 0) {
        process.stdout.write(`\r  Progress: ${i}/${iterations}`)
      }
    }

    console.log(`\r  ✅ Completed ${iterations} iterations\n`)
    this.results.push(this.calculateStats('CREATE', times))
  }

  private async benchmarkRead() {
    console.log('📖 Benchmarking READ operations...')
    
    // First create some MemCubes to read
    const memCubeIds: string[] = []
    for (let i = 0; i < 10; i++) {
      const result = await this.harness.createMemCube({
        project_id: 'benchmark-project',
        label: `Read Test ${i}`,
        type: 'PLAINTEXT',
        content: 'Content for read testing',
      })
      if (result.memCubeId) {
        memCubeIds.push(result.memCubeId)
      }
    }

    const iterations = 100
    const times: number[] = []

    for (let i = 0; i < iterations; i++) {
      const memCubeId = memCubeIds[i % memCubeIds.length]
      const start = performance.now()
      
      await this.harness.readMemCube(memCubeId)

      const duration = performance.now() - start
      times.push(duration)

      if (i % 10 === 0) {
        process.stdout.write(`\r  Progress: ${i}/${iterations}`)
      }
    }

    console.log(`\r  ✅ Completed ${iterations} iterations\n`)
    this.results.push(this.calculateStats('READ', times))
  }

  private async benchmarkTextSearch() {
    console.log('🔍 Benchmarking TEXT SEARCH operations...')
    
    // Create searchable content
    const topics = ['React', 'Python', 'Machine Learning', 'DevOps', 'Blockchain']
    for (const topic of topics) {
      for (let i = 0; i < 20; i++) {
        await this.harness.createMemCube({
          project_id: 'benchmark-project',
          label: `${topic} Guide Part ${i}`,
          type: 'PLAINTEXT',
          content: `Comprehensive guide about ${topic} including best practices and examples.`,
        })
      }
    }

    const iterations = 50
    const times: number[] = []
    const queries = ['React', 'Python', 'Machine', 'Dev', 'Block']

    for (let i = 0; i < iterations; i++) {
      const query = queries[i % queries.length]
      const start = performance.now()
      
      await this.harness.searchMemCubes(query, undefined, 10)

      const duration = performance.now() - start
      times.push(duration)

      if (i % 10 === 0) {
        process.stdout.write(`\r  Progress: ${i}/${iterations}`)
      }
    }

    console.log(`\r  ✅ Completed ${iterations} iterations\n`)
    this.results.push(this.calculateStats('TEXT_SEARCH', times))
  }

  private async benchmarkSemanticSearch() {
    console.log('🧠 Benchmarking SEMANTIC SEARCH operations...')
    
    // Create semantic content
    const semanticContent = [
      'Building user interfaces with React components and hooks',
      'Data analysis using Python pandas and numpy libraries',
      'Implementing neural networks with TensorFlow and Keras',
      'Container orchestration with Kubernetes and Docker',
      'Smart contract development on Ethereum blockchain',
    ]

    for (const content of semanticContent) {
      await this.harness.createMemCube({
        project_id: 'benchmark-project',
        label: content.split(' ').slice(0, 3).join(' '),
        type: 'SEMANTIC',
        content,
      })
    }

    const iterations = 20 // Fewer due to embedding generation cost
    const times: number[] = []
    const queries = [
      'How to create interactive web applications',
      'Processing large datasets efficiently',
      'Building AI models for prediction',
      'Managing cloud infrastructure',
      'Decentralized application development',
    ]

    for (let i = 0; i < iterations; i++) {
      const query = queries[i % queries.length]
      const start = performance.now()
      
      await this.harness.searchMemCubes(query, 'SEMANTIC', 5)

      const duration = performance.now() - start
      times.push(duration)

      if (i % 5 === 0) {
        process.stdout.write(`\r  Progress: ${i}/${iterations}`)
      }
    }

    console.log(`\r  ✅ Completed ${iterations} iterations\n`)
    this.results.push(this.calculateStats('SEMANTIC_SEARCH', times))
  }

  private async benchmarkConcurrentOperations() {
    console.log('⚡ Benchmarking CONCURRENT operations...')
    
    const concurrencyLevels = [1, 5, 10, 20]
    const operationsPerLevel = 50

    for (const concurrency of concurrencyLevels) {
      console.log(`  Testing with concurrency: ${concurrency}`)
      const start = performance.now()

      const operations = Array(operationsPerLevel).fill(null).map((_, i) => 
        () => this.harness.createMemCube({
          project_id: 'benchmark-project',
          label: `Concurrent Test ${i}`,
          type: 'PLAINTEXT',
          content: 'Testing concurrent operations',
        })
      )

      await this.harness.runBatchTest(operations, concurrency)
      
      const totalTime = performance.now() - start
      const throughput = (operationsPerLevel / totalTime) * 1000
      
      console.log(`    Total time: ${totalTime.toFixed(2)}ms`)
      console.log(`    Throughput: ${throughput.toFixed(2)} ops/sec\n`)
    }
  }

  private async benchmarkLargePayloads() {
    console.log('📦 Benchmarking LARGE PAYLOAD operations...')
    
    const payloadSizes = [1, 10, 100, 500] // KB
    const iterations = 10

    for (const sizeKB of payloadSizes) {
      console.log(`  Testing ${sizeKB}KB payloads`)
      const times: number[] = []
      const content = 'x'.repeat(sizeKB * 1024)

      for (let i = 0; i < iterations; i++) {
        const start = performance.now()
        
        await this.harness.createMemCube({
          project_id: 'benchmark-project',
          label: `Large Payload ${sizeKB}KB`,
          type: 'PLAINTEXT',
          content,
        })

        const duration = performance.now() - start
        times.push(duration)
      }

      const stats = this.calculateStats(`LARGE_PAYLOAD_${sizeKB}KB`, times)
      console.log(`    Avg time: ${stats.avgTime.toFixed(2)}ms`)
      console.log(`    Throughput: ${stats.throughput.toFixed(2)} ops/sec\n`)
      this.results.push(stats)
    }
  }

  private calculateStats(operation: string, times: number[]): BenchmarkResult {
    times.sort((a, b) => a - b)
    
    const totalTime = times.reduce((sum, t) => sum + t, 0)
    const avgTime = totalTime / times.length
    const minTime = times[0]
    const maxTime = times[times.length - 1]
    const throughput = (times.length / totalTime) * 1000

    const percentiles = {
      p50: times[Math.floor(times.length * 0.5)],
      p90: times[Math.floor(times.length * 0.9)],
      p95: times[Math.floor(times.length * 0.95)],
      p99: times[Math.floor(times.length * 0.99)],
    }

    return {
      operation,
      iterations: times.length,
      totalTime,
      avgTime,
      minTime,
      maxTime,
      throughput,
      percentiles,
    }
  }

  private generateReport() {
    console.log('\n📊 BENCHMARK RESULTS\n')
    console.log('='.repeat(80))
    
    const report = {
      timestamp: new Date().toISOString(),
      environment: {
        node: process.version,
        platform: process.platform,
        arch: process.arch,
      },
      results: this.results,
    }

    // Console output
    for (const result of this.results) {
      console.log(`\n${result.operation}:`)
      console.log(`  Iterations: ${result.iterations}`)
      console.log(`  Avg Time: ${result.avgTime.toFixed(2)}ms`)
      console.log(`  Min Time: ${result.minTime.toFixed(2)}ms`)
      console.log(`  Max Time: ${result.maxTime.toFixed(2)}ms`)
      console.log(`  Throughput: ${result.throughput.toFixed(2)} ops/sec`)
      console.log(`  Percentiles:`)
      console.log(`    P50: ${result.percentiles.p50.toFixed(2)}ms`)
      console.log(`    P90: ${result.percentiles.p90.toFixed(2)}ms`)
      console.log(`    P95: ${result.percentiles.p95.toFixed(2)}ms`)
      console.log(`    P99: ${result.percentiles.p99.toFixed(2)}ms`)
    }

    // Save to file
    const outputPath = join(process.cwd(), 'benchmark-results.json')
    writeFileSync(outputPath, JSON.stringify(report, null, 2))
    console.log(`\n\n💾 Results saved to: ${outputPath}`)
  }
}

// Run benchmarks
if (import.meta.url === `file://${process.argv[1]}`) {
  const benchmark = new MemCubeBenchmark()
  benchmark.runBenchmarks().catch(console.error)
}