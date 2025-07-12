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

from google.adk.cli.fast_api import get_fast_api_app

"""FastAPI app exposing the demo agents with Supabase persistence."""
app = get_fast_api_app(
    agents_dir="contributing/samples/react_supabase",
    allow_origins=["http://localhost:3000"],
    web=False,
    session_service_uri=(
        "postgresql+asyncpg://USER:PASSWORD@db.supabase.co/db_name"
    ),
)
