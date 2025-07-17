import { createContext, useContext, ReactNode } from 'react'
import { createClient, SupabaseClient } from '@supabase/supabase-js'

// Mock ADK client for development
const createADKClient = (_config: any): any => {
  return {
    querySlice: async (_sliceId: string, _pattern: string, _limit?: number) => {
      // Mock implementation
      return { slice: {} };
    },
    applyDelta: async (_sliceId: string, _deltas: any[], _source: string) => {
      // Mock implementation
      return true;
    },
    subscribeToState: (_sliceId: string, _callback: () => void) => {
      // Mock implementation
      return () => {};
    },
    setProject: (_projectId: string) => {
      // Mock implementation
      console.log('Setting project:', _projectId);
    },
    createProject: async (_name: string, _description: string) => {
      // Mock implementation
      return 'mock-project-id';
    },
    // Add other required methods as needed
    getState: async () => ({}),
    updateState: async () => true,
    createTask: async () => 'mock-task-id',
    getTask: async () => ({}),
  };
};

interface SupabaseContextType {
  supabase: SupabaseClient
  adk: any
}

const SupabaseContext = createContext<SupabaseContextType | undefined>(undefined)

export function SupabaseProvider({ children }: { children: ReactNode }) {
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
  const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error('Missing Supabase environment variables')
  }

  const supabase = createClient(supabaseUrl, supabaseAnonKey)
  const adk = createADKClient({
    supabaseUrl,
    supabaseKey: supabaseAnonKey,
  })

  return (
    <SupabaseContext.Provider value={{ supabase, adk }}>
      {children}
    </SupabaseContext.Provider>
  )
}

export function useSupabase() {
  const context = useContext(SupabaseContext)
  if (!context) {
    throw new Error('useSupabase must be used within a SupabaseProvider')
  }
  return context
}