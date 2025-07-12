# React + Supabase Integration Sample

This sample demonstrates how to run ADK agents with a Supabase-backed
session store and interact with them from a React frontend. It also
includes a multiuser server so each user can host their own agent team.

## Files

- `agent.py` – defines a simple multi-agent team.
- `server.py` – FastAPI app exposing a single team's agents.
- `multiuser_server.py` – mounts multiple user apps under `/users/<id>`.
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

   The `multiuser_server.py` script can be started in the same way to
   serve all users listed in the `USERS` environment variable:

   ```bash
   USERS=demo uvicorn contributing.samples.react_supabase.multiuser_server:app --reload
   ```

Update `server.py` with your Supabase connection string.

## Running the Frontend

Use your preferred React tooling to bundle `App.jsx`.
The component connects to `/run_sse` and streams responses
from the agents as they arrive.

### Multiuser Layout

Each user's agents live under `users/<user_id>/agents`. The sample ships
with a `demo` user whose team definition can be found at
`users/demo/agents/team/agent.py`.
