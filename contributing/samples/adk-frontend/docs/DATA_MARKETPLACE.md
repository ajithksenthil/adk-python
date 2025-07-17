# Data Marketplace Documentation

## Overview

The Data Marketplace is a key feature of the ADK platform that enables users to discover, share, and integrate MemCubes (memory cubes) into their AI agent projects. MemCubes are reusable knowledge packages that can enhance AI agent capabilities across different domains.

## Features

### 1. Browse and Search
- **Search Functionality**: Full-text search across MemCube names, descriptions, and tags
- **Category Filtering**: Filter by categories like Frontend, Backend, Data Science, DevOps, etc.
- **Type Filtering**: Filter by MemCube types (PLAINTEXT, SEMANTIC, COMMAND, TEMPLATE)
- **Sorting Options**: Sort by popularity, rating, newest, or price

### 2. MemCube Types

#### PLAINTEXT 📄
- Documentation and reference material
- Plain text content for notes and guides
- No special processing required

#### SEMANTIC 🧠
- AI-optimized content with embeddings
- Semantic search capabilities
- Vector embeddings for similarity matching

#### COMMAND ⚡
- Executable scripts and automation
- Command-line utilities
- Automation workflows

#### TEMPLATE 🎨
- Reusable code templates
- Boilerplate structures
- Project scaffolding

### 3. MemCube Details

Each MemCube displays:
- **Metadata**: Name, type, category, size, and tags
- **Statistics**: Downloads, rating, and last update
- **Creator Info**: Publisher details and credentials
- **Preview**: Code snippets or content preview
- **Pricing**: Free or paid options

### 4. Project Integration

#### Adding to Projects
1. Click "Add to Project" on any MemCube
2. Select target project from your project list
3. Or create a new project directly from the modal
4. MemCube becomes available to all AI agents in that project

#### Access Control
- MemCubes are scoped to projects
- AI agents within a project can access all project MemCubes
- Row Level Security ensures data isolation

## Technical Implementation

### Frontend Components

```typescript
// Main marketplace page
src/pages/DataMarketplace.tsx

// Component structure
src/components/marketplace/
├── MemCubeCard.tsx         // Individual MemCube display card
├── MemCubeDetailModal.tsx  // Detailed view modal
└── AddToProjectModal.tsx   // Project selection/creation modal
```

### Data Flow

1. **Browse**: Users browse available MemCubes with filters
2. **Select**: Click on a MemCube to view details
3. **Add**: Choose "Add to Project" to integrate
4. **Route**: Select or create a project for the MemCube
5. **Access**: AI agents in the project can now use the MemCube

### API Integration

```typescript
// Search MemCubes
const { data: memCubes } = useQuery({
  queryKey: ['marketplace-memcubes', filters],
  queryFn: async () => {
    return await adk.searchMarketplaceMemCubes({
      query: searchQuery,
      category: selectedCategory,
      type: selectedType,
      sortBy: sortBy
    })
  }
})

// Add to Project
const addToProject = useMutation({
  mutationFn: async ({ memCubeId, projectId }) => {
    return await adk.addMemCubeToProject(memCubeId, projectId)
  }
})
```

## Backend Integration

### Database Schema

```sql
-- Marketplace metadata for public MemCubes
CREATE TABLE marketplace_memcubes (
  id UUID PRIMARY KEY REFERENCES memories(id),
  category TEXT NOT NULL,
  tags TEXT[],
  downloads INTEGER DEFAULT 0,
  rating DECIMAL(2,1),
  price DECIMAL(10,2) DEFAULT 0,
  creator_id UUID REFERENCES auth.users(id),
  published_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Project MemCube associations
CREATE TABLE project_memcubes (
  project_id UUID REFERENCES projects(id),
  memcube_id UUID REFERENCES memories(id),
  added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  added_by UUID REFERENCES auth.users(id),
  PRIMARY KEY (project_id, memcube_id)
);
```

### Edge Functions

- `marketplace-search`: Search and filter MemCubes
- `marketplace-details`: Get detailed MemCube information
- `project-add-memcube`: Add MemCube to a project
- `project-list-memcubes`: List MemCubes in a project

## Usage Examples

### For Users

1. **Finding React Components**:
   - Navigate to Data Marketplace
   - Search "react components"
   - Filter by type: TEMPLATE
   - Sort by rating
   - Add to your frontend project

2. **Getting Data Science Tools**:
   - Browse Data Science category
   - Look for COMMAND type MemCubes
   - Check previews and ratings
   - Add to analytics project

### For AI Agents

Once a MemCube is added to a project, AI agents can:

```python
# Access MemCube content
memcube = await adk.get_memory("react-components")
content = memcube.content

# Use in agent workflows
if task.requires("ui-component"):
    template = await adk.search_memories(
        "button component",
        type="TEMPLATE"
    )
    return generate_from_template(template)
```

## Best Practices

### For Publishers

1. **Clear Naming**: Use descriptive names that indicate purpose
2. **Comprehensive Tags**: Add relevant tags for discoverability
3. **Good Documentation**: Include usage examples in descriptions
4. **Version Updates**: Keep MemCubes updated with latest practices
5. **Preview Content**: Provide meaningful preview snippets

### For Consumers

1. **Check Ratings**: Look at ratings and download counts
2. **Review Preview**: Examine preview content before adding
3. **Project Organization**: Group related MemCubes in projects
4. **License Compliance**: Respect usage rights and licenses
5. **Feedback**: Rate and review MemCubes you use

## Security Considerations

1. **Content Validation**: All MemCubes are validated before publishing
2. **Access Control**: RLS ensures project-level isolation
3. **API Keys**: Sensitive data stored securely in Vault
4. **Execution Safety**: COMMAND type MemCubes run in sandboxed environments
5. **User Authentication**: Only authenticated users can add MemCubes

## Future Enhancements

1. **Version Control**: Track MemCube versions and updates
2. **Dependencies**: Define MemCube dependencies
3. **Collaboration**: Share private MemCubes within teams
4. **Analytics**: Usage analytics for publishers
5. **Monetization**: Enhanced payment and licensing options
6. **AI Recommendations**: Suggest MemCubes based on project needs