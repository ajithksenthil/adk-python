import { MemCubeTestHarness, MemCubeType } from '../src/core/MemCubeTestHarness'
import { faker } from '@faker-js/faker'
import { writeFileSync } from 'fs'
import { join } from 'path'

interface TestDataConfig {
  projects: number
  memCubesPerProject: number
  typeDistribution: Record<MemCubeType, number>
  categories: string[]
}

class TestDataGenerator {
  private harness: MemCubeTestHarness
  private generatedData: {
    projects: Array<{ id: string; name: string }>
    memCubes: Array<{ id: string; projectId: string; label: string; type: MemCubeType }>
  } = { projects: [], memCubes: [] }

  constructor() {
    this.harness = new MemCubeTestHarness(
      process.env.SUPABASE_URL || 'http://localhost:54321',
      process.env.SUPABASE_ANON_KEY || 'test-key',
      process.env.OPENAI_API_KEY || 'test-key'
    )
  }

  async generate(config: TestDataConfig) {
    console.log('🏭 Generating test data for MemCube system\n')

    // Generate projects
    console.log(`📁 Creating ${config.projects} projects...`)
    for (let i = 0; i < config.projects; i++) {
      const project = {
        id: `project-${i + 1}`,
        name: faker.company.name() + ' Project',
      }
      this.generatedData.projects.push(project)
      
      // Generate MemCubes for this project
      await this.generateMemCubesForProject(project.id, config)
      
      process.stdout.write(`\r  Progress: ${i + 1}/${config.projects} projects`)
    }
    console.log('\n✅ Projects created\n')

    // Save manifest
    this.saveManifest()
    
    // Generate sample queries
    this.generateSampleQueries()
    
    console.log('\n🎉 Test data generation complete!')
  }

  private async generateMemCubesForProject(
    projectId: string,
    config: TestDataConfig
  ) {
    const types = Object.entries(config.typeDistribution)
    
    for (let i = 0; i < config.memCubesPerProject; i++) {
      // Select type based on distribution
      const typeIndex = Math.floor(Math.random() * types.length)
      const [type, _] = types[typeIndex] as [MemCubeType, number]
      
      // Generate content based on type
      const memCubeData = this.generateMemCubeContent(type, config.categories)
      
      const result = await this.harness.createMemCube({
        project_id: projectId,
        label: memCubeData.label,
        type,
        content: memCubeData.content,
        metadata: memCubeData.metadata,
      })
      
      if (result.success && result.memCubeId) {
        this.generatedData.memCubes.push({
          id: result.memCubeId,
          projectId,
          label: memCubeData.label,
          type,
        })
      }
    }
  }

  private generateMemCubeContent(
    type: MemCubeType,
    categories: string[]
  ): { label: string; content: string; metadata: Record<string, any> } {
    const category = categories[Math.floor(Math.random() * categories.length)]
    
    switch (type) {
      case 'PLAINTEXT':
        return {
          label: faker.lorem.sentence(5),
          content: faker.lorem.paragraphs(3),
          metadata: {
            category,
            tags: faker.lorem.words(5).split(' '),
            author: faker.person.fullName(),
            version: faker.system.semver(),
          },
        }
      
      case 'SEMANTIC':
        const topics = [
          'machine learning algorithms',
          'web development best practices',
          'cloud architecture patterns',
          'data science workflows',
          'mobile app development',
        ]
        const topic = topics[Math.floor(Math.random() * topics.length)]
        return {
          label: `Guide to ${topic}`,
          content: `This is a comprehensive guide about ${topic}. ${faker.lorem.paragraphs(2)}`,
          metadata: {
            category,
            tags: topic.split(' '),
            difficulty: faker.helpers.arrayElement(['beginner', 'intermediate', 'advanced']),
            estimatedReadTime: faker.number.int({ min: 5, max: 30 }),
          },
        }
      
      case 'COMMAND':
        const commands = [
          { lang: 'python', ext: 'py', content: 'def process_data(df):\n    return df.dropna().reset_index()' },
          { lang: 'javascript', ext: 'js', content: 'const filterData = (arr) => arr.filter(x => x > 0);' },
          { lang: 'bash', ext: 'sh', content: '#!/bin/bash\necho "Processing files..."\nfind . -name "*.log"' },
          { lang: 'sql', ext: 'sql', content: 'SELECT * FROM users WHERE created_at > NOW() - INTERVAL "30 days";' },
        ]
        const cmd = commands[Math.floor(Math.random() * commands.length)]
        return {
          label: `${cmd.lang} script - ${faker.word.verb()}_${faker.word.noun()}`,
          content: cmd.content,
          metadata: {
            category,
            language: cmd.lang,
            extension: cmd.ext,
            dependencies: faker.lorem.words(3).split(' '),
          },
        }
      
      case 'TEMPLATE':
        const templates = [
          {
            name: 'React Component',
            content: `import React from 'react';\n\nexport const ${faker.word.noun()} = ({ children }) => {\n  return <div className="container">{children}</div>;\n};`,
          },
          {
            name: 'Python Class',
            content: `class ${faker.word.noun()}:\n    def __init__(self, name):\n        self.name = name\n\n    def process(self):\n        pass`,
          },
          {
            name: 'Docker Compose',
            content: `version: '3.8'\nservices:\n  app:\n    build: .\n    ports:\n      - "3000:3000"`,
          },
        ]
        const template = templates[Math.floor(Math.random() * templates.length)]
        return {
          label: `${template.name} Template`,
          content: template.content,
          metadata: {
            category,
            templateType: template.name,
            customizable: true,
            framework: faker.helpers.arrayElement(['react', 'vue', 'angular', 'python', 'node']),
          },
        }
    }
  }

  private generateSampleQueries() {
    console.log('🔍 Generating sample search queries...\n')
    
    const queries = {
      text: [
        'React components',
        'Python data analysis',
        'Machine learning',
        'Docker configuration',
        'API documentation',
      ],
      semantic: [
        'How to build scalable web applications',
        'Best practices for data preprocessing',
        'Implementing authentication in mobile apps',
        'Optimizing database performance',
        'Cloud deployment strategies',
      ],
      byType: {
        PLAINTEXT: ['documentation', 'guide', 'tutorial'],
        SEMANTIC: ['how to', 'best practices', 'explain'],
        COMMAND: ['script', 'function', 'automation'],
        TEMPLATE: ['template', 'boilerplate', 'starter'],
      },
    }
    
    const queriesPath = join(process.cwd(), 'test-queries.json')
    writeFileSync(queriesPath, JSON.stringify(queries, null, 2))
    console.log(`💾 Sample queries saved to: ${queriesPath}`)
  }

  private saveManifest() {
    const manifest = {
      generatedAt: new Date().toISOString(),
      summary: {
        totalProjects: this.generatedData.projects.length,
        totalMemCubes: this.generatedData.memCubes.length,
        typeDistribution: this.generatedData.memCubes.reduce((acc, mc) => {
          acc[mc.type] = (acc[mc.type] || 0) + 1
          return acc
        }, {} as Record<MemCubeType, number>),
      },
      data: this.generatedData,
    }
    
    const manifestPath = join(process.cwd(), 'test-data-manifest.json')
    writeFileSync(manifestPath, JSON.stringify(manifest, null, 2))
    console.log(`💾 Test data manifest saved to: ${manifestPath}`)
  }
}

// Default configuration
const defaultConfig: TestDataConfig = {
  projects: 5,
  memCubesPerProject: 20,
  typeDistribution: {
    PLAINTEXT: 0.3,
    SEMANTIC: 0.3,
    COMMAND: 0.2,
    TEMPLATE: 0.2,
  },
  categories: [
    'Frontend',
    'Backend',
    'Data Science',
    'DevOps',
    'Mobile',
    'Security',
    'Documentation',
  ],
}

// Run generator
if (import.meta.url === `file://${process.argv[1]}`) {
  const generator = new TestDataGenerator()
  
  // Parse command line arguments
  const args = process.argv.slice(2)
  const customConfig = { ...defaultConfig }
  
  if (args.includes('--projects')) {
    const idx = args.indexOf('--projects')
    customConfig.projects = parseInt(args[idx + 1]) || defaultConfig.projects
  }
  
  if (args.includes('--memcubes')) {
    const idx = args.indexOf('--memcubes')
    customConfig.memCubesPerProject = parseInt(args[idx + 1]) || defaultConfig.memCubesPerProject
  }
  
  generator.generate(customConfig).catch(console.error)
}