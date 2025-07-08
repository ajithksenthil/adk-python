# React + Supabase Integration Sample

This sample demonstrates how to run ADK agents with a Supabase-backed
session store and interact with them from a React frontend.

## Files

- `agent.py` – defines a simple multi-agent team.
- `server.py` – FastAPI app exposing the agents with Supabase persistence.
- `frontend/src/App.jsx` – React component streaming agent replies.

## Running the Backend

1. Install dependencies:
   ```bash
   pip install google-adk uvicorn asyncpg
   ```
2. Start the server:
   ```bash
   uvicorn contributing.samples.react_supabase.server:app --reload
   ```

Update `server.py` with your Supabase connection string.

## Running the Frontend

Use your preferred React tooling to bundle `App.jsx`.
The component connects to `/run_sse` and streams responses
from the agents as they arrive.
