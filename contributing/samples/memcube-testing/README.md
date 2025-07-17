# MemCube Testing Framework

A comprehensive testing framework for evaluating the efficacy and performance of the MemCube persistent memory system.

## Features

### 🧪 Unit Testing
- CRUD operations (Create, Read, Update, Delete)
- Search functionality (text and semantic)
- Error handling and edge cases
- Type-specific operations

### 🔄 Integration Testing
- Marketplace publishing and discovery
- Project integration and access control
- Multi-tenant isolation
- Real-world workflows

### ⚡ Performance Benchmarking
- Operation latency measurement
- Throughput analysis
- Concurrent operation testing
- Large payload handling
- Response time distribution

### 📊 Efficacy Metrics
- **Accuracy**: Overall correctness of operations
- **Recall**: Percentage of relevant results retrieved
- **Precision**: Percentage of retrieved results that are relevant
- **F1 Score**: Harmonic mean of precision and recall
- **Response Time**: Average operation duration
- **Throughput**: Operations per second
- **Storage Efficiency**: Compression and optimization metrics

### 📈 Real-time Dashboard
- Live performance monitoring
- Visual metrics representation
- Historical data analysis
- Export capabilities

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd memcube-testing

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your Supabase and OpenAI credentials
```

## Environment Setup

Create a `.env` file with:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# OpenAI Configuration (for embeddings)
OPENAI_API_KEY=your_openai_api_key

# Dashboard Configuration
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_OPENAI_API_KEY=your_openai_api_key
```

## Usage

### Running Unit Tests

```bash
# Run all unit tests
npm test

# Run with coverage
npm run test:coverage

# Run with UI
npm run test:ui
```

### Running Integration Tests

```bash
# Run integration tests
npm run test:integration
```

### Running Performance Benchmarks

```bash
# Run full benchmark suite
npm run test:performance

# Results saved to benchmark-results.json
```

### Generating Test Data

```bash
# Generate default test data (5 projects, 20 MemCubes each)
npm run generate:data

# Custom configuration
npm run generate:data -- --projects 10 --memcubes 50
```

### Analyzing Efficacy

```bash
# Run efficacy analysis
npm run analyze:efficacy
```

### Running the Dashboard

```bash
# Start the dashboard
npm run dashboard

# Open http://localhost:5173 in your browser
```

## Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── memcube-crud.test.ts
│   ├── search.test.ts
│   └── error-handling.test.ts
├── integration/             # Integration tests
│   ├── marketplace.test.ts
│   ├── project-flow.test.ts
│   └── access-control.test.ts
├── performance/             # Performance tests
│   ├── benchmark.ts
│   └── stress-test.ts
└── setup.ts                # Test utilities
```

## Core Classes

### MemCubeTestHarness

The main testing harness for MemCube operations:

```typescript
const harness = new MemCubeTestHarness(
  supabaseUrl,
  supabaseKey,
  openaiKey
)

// Create a MemCube
const result = await harness.createMemCube({
  project_id: 'test-project',
  label: 'Test MemCube',
  type: 'PLAINTEXT',
  content: 'Test content'
})

// Search MemCubes
const searchResult = await harness.searchMemCubes(
  'query',
  'SEMANTIC',
  10
)

// Calculate metrics
const metrics = harness.calculateEfficacyMetrics(
  relevantSet,
  retrievedArray
)
```

### MarketplaceTestSuite

Testing suite for marketplace operations:

```typescript
const marketplace = new MarketplaceTestSuite(harness)

// Publish to marketplace
await marketplace.publishMemCube(memCubeId, {
  description: 'Description',
  category: 'Frontend',
  tags: ['react', 'components'],
  price: 0
})

// Search marketplace
const results = await marketplace.searchMarketplace('React', {
  category: 'Frontend',
  sortBy: 'downloads'
})
```

## Metrics Explained

### Accuracy Metrics

- **Precision**: Of all MemCubes retrieved, how many were relevant?
  ```
  Precision = Relevant Retrieved / Total Retrieved
  ```

- **Recall**: Of all relevant MemCubes, how many were retrieved?
  ```
  Recall = Relevant Retrieved / Total Relevant
  ```

- **F1 Score**: Balanced measure of precision and recall
  ```
  F1 = 2 * (Precision * Recall) / (Precision + Recall)
  ```

### Performance Metrics

- **Response Time**: Time from request to response
- **Throughput**: Number of operations completed per second
- **Concurrency**: Performance under parallel operations
- **Scalability**: Performance with increasing data size

## Dashboard Features

### Real-time Monitoring
- Live operation tracking
- Success/failure rates
- Performance trends

### Visual Analytics
- Operation distribution charts
- Performance radar charts
- Timeline analysis
- Response time histograms

### Export Options
- JSON export for raw data
- CSV export for analysis
- PDF reports (coming soon)

## Best Practices

1. **Test Data Isolation**: Use separate projects for testing
2. **Cleanup**: Always clean up test data after integration tests
3. **Benchmarking**: Run benchmarks in consistent environments
4. **Monitoring**: Use the dashboard for continuous monitoring

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## Troubleshooting

### Common Issues

1. **Connection Errors**: Check Supabase credentials
2. **Embedding Errors**: Verify OpenAI API key
3. **Performance Issues**: Check network latency
4. **Test Failures**: Ensure database migrations are up to date

### Debug Mode

Enable debug logging:

```bash
DEBUG=memcube:* npm test
```

## License

MIT License - See LICENSE file for details