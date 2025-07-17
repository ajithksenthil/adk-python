# ADK Frontend - React TypeScript Application

A comprehensive frontend application for the Autonomous Development Kit (ADK) platform, built with React, TypeScript, and Tailwind CSS.

## Features

### 🎯 Dashboard
- Real-time KPI tracking (active tasks, completed tasks, total earnings, team status)
- Active teams overview with status monitoring
- Recent notifications panel
- Quick stats and analytics

### 📊 Live-Board
- Interactive task visualization using Cytoscape.js
- Real-time task status updates
- Task dependency graph
- Detailed task sidebar with voting and status management
- Visual representation of task relationships and flow

### 🛒 Data Marketplace
- Browse and search MemCubes (memory cubes for AI agents)
- Filter by category, type, and various criteria
- Sort by popularity, rating, newest, or price
- Detailed MemCube information with preview
- Add MemCubes to projects for AI agent access
- Support for different MemCube types:
  - **PLAINTEXT**: Documentation and reference material
  - **SEMANTIC**: AI-optimized content with embeddings
  - **COMMAND**: Executable scripts and automation
  - **TEMPLATE**: Reusable code templates

### 🔐 Vault & Keys
- API key management for multiple providers (OpenAI, Anthropic, GitHub, Custom)
- Secure key storage with masked display
- Spend tracking and limits
- Team assignment for keys
- Key rotation capabilities

### 👥 Teams & Skills
- Agent team management
- Skill and capability tracking
- Performance metrics (tasks completed, failed, average time)
- AML level configuration
- Public task acceptance settings
- Docker image and model endpoint configuration

### 💰 Wallet/Payouts
- Balance overview (available, pending, total earned, withdrawn)
- Earnings chart visualization
- Transaction history
- Withdrawal functionality with multiple methods
- Export capabilities

### ⚙️ Settings
- Account management
- Dark mode toggle
- Notification preferences (email, Slack, in-app)
- Voting preferences and delegation
- Language and timezone settings

## Technology Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Supabase** - Backend and authentication
- **React Router** - Client-side routing
- **React Query** - Server state management
- **Cytoscape.js** - Graph visualization
- **Recharts** - Charts and data visualization
- **Lucide React** - Icon library
- **date-fns** - Date utilities
- **React Hot Toast** - Toast notifications

## Project Structure

```
src/
├── components/          # Reusable components
│   ├── auth/           # Authentication components
│   ├── dashboard/      # Dashboard-specific components
│   ├── layout/         # Layout components (header, sidebar)
│   ├── liveboard/      # Live-board components
│   ├── marketplace/    # Data marketplace components
│   ├── notifications/  # Notification components
│   ├── teams/          # Team management components
│   ├── vault/          # Vault and key management
│   └── wallet/         # Wallet and transaction components
├── contexts/           # React contexts
│   ├── AuthContext.tsx
│   ├── SupabaseContext.tsx
│   └── ThemeContext.tsx
├── pages/              # Page components
├── types/              # TypeScript type definitions
├── utils/              # Utility functions
├── App.tsx             # Main app component
├── main.tsx           # App entry point
└── index.css          # Global styles
```

## Setup Instructions

### Prerequisites

- Node.js 18+ and npm
- Supabase project (for backend)
- Git

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd adk-frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file:
```bash
cp .env.example .env
```

4. Configure environment variables:
```env
VITE_SUPABASE_URL=your_supabase_project_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### Development

Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Key Components

### Authentication Flow

1. **Login/Register**: Uses Supabase Auth with email/password
2. **Protected Routes**: Automatically redirects to login if not authenticated
3. **Session Management**: Persistent sessions with automatic refresh

### Real-time Features

- **Task Updates**: Live task status changes using Supabase Realtime
- **Notifications**: Real-time notification delivery
- **Team Status**: Live agent status monitoring

### State Management

- **React Query**: For server state and caching
- **Context API**: For global app state (auth, theme, supabase)
- **Local State**: Component-specific state with useState

## API Integration

The frontend integrates with the ADK Supabase backend:

- **Authentication**: Supabase Auth
- **Database**: PostgreSQL via Supabase
- **Real-time**: Supabase Realtime subscriptions
- **Storage**: Supabase Storage for files
- **Edge Functions**: For complex business logic

## Styling Guidelines

- **Tailwind CSS**: Utility-first approach
- **Dark Mode**: Full dark mode support
- **Responsive**: Mobile-first responsive design
- **Component Classes**: Consistent styling patterns

## Testing

```bash
# Run tests (when implemented)
npm test

# Run linting
npm run lint

# Type checking
npm run type-check
```

## Deployment

### Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Netlify

1. Connect your Git repository
2. Set build command: `npm run build`
3. Set publish directory: `dist`
4. Add environment variables

### Docker

```dockerfile
# Dockerfile example
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is part of the ADK platform. See the main repository for license information.

## Support

For issues and questions:
- Create an issue in the repository
- Check the ADK documentation
- Contact the development team