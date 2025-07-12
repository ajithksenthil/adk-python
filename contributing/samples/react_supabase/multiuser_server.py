# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

"""FastAPI server supporting multiple users' agent teams.

Each user gets their own agents directory under ``users/<user_id>/agents``.
The script mounts a separate ADK FastAPI app for every user specified in the
``USERS`` environment variable. Session data is persisted in Supabase by using
``DatabaseSessionService`` via ``session_service_uri``.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app


def _create_user_app(user_id: str) -> FastAPI:
  """Create a FastAPI app for a given user."""
  agents_dir = (
      Path(__file__).parent / "users" / user_id / "agents"
  ).as_posix()
  return get_fast_api_app(
      agents_dir=agents_dir,
      allow_origins=["http://localhost:3000"],
      web=False,
      session_service_uri=os.getenv(
          "SUPABASE_DB_URL",
          "postgresql+asyncpg://USER:PASSWORD@db.supabase.co/db_name",
      ),
  )


app = FastAPI(title="Multiuser ADK Server")

for user in os.getenv("USERS", "demo").split(","):
  user = user.strip()
  if not user:
    continue
  app.mount(f"/users/{user}", _create_user_app(user), name=f"{user}-app")
