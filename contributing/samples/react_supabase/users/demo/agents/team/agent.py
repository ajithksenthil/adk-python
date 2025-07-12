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

"""Demo multi-agent team for the multiuser sample."""

from google.adk.agents import Agent

# Simple greeter agent
_greeter = Agent(
    name="greeter",
    model="gemini-2.0-flash",
    instruction="Greet the user warmly when asked.",
)

# Task executor used by the coordinator
_worker = Agent(
    name="task_executor",
    model="gemini-2.0-flash",
    instruction="Carry out delegated tasks with brief responses.",
)

# Root agent that coordinates the team
root_agent = Agent(
    name="coordinator",
    model="gemini-2.0-flash",
    description="Orchestrates the greeter and task executor.",
    sub_agents=[_greeter, _worker],
)
