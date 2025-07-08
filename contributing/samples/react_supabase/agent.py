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

from google.adk.agents import Agent


# Simple multi-agent hierarchy used by the React + Supabase demo.

greeter = Agent(
    name="greeter",
    model="gemini-2.0-flash",
    instruction="Greet users when asked.",
)

task_executor = Agent(
    name="task_executor",
    model="gemini-2.0-flash",
    instruction="Perform tasks delegated by the coordinator.",
)

root_agent = Agent(
    name="coordinator",
    model="gemini-2.0-flash",
    description="Orchestrates greetings and tasks.",
    sub_agents=[greeter, task_executor],
)
