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

"""Example of using Business Pillar Agents in an organization."""

from google.adk.business_pillars import (
    FinancePillarAgent,
    OperationsPillarAgent,
    MarketingPillarAgent,
    HRPillarAgent,
    ITPillarAgent,
    PillarOrchestrator,
)

# Create individual pillar agents
finance_agent = FinancePillarAgent(
    name="finance_pillar",
    model="gemini-2.0-flash",
    description="Manages financial operations and planning",
)

operations_agent = OperationsPillarAgent(
    name="operations_pillar",
    model="gemini-2.0-flash",
    description="Manages operational excellence and efficiency",
)

marketing_agent = MarketingPillarAgent(
    name="marketing_pillar",
    model="gemini-2.0-flash",
    description="Manages marketing and customer acquisition",
)

hr_agent = HRPillarAgent(
    name="hr_pillar",
    model="gemini-2.0-flash",
    description="Manages human resources and talent",
)

it_agent = ITPillarAgent(
    name="it_pillar",
    model="gemini-2.0-flash",
    description="Manages technology and digital infrastructure",
)

# Create the orchestrator with all pillar agents
orchestrator = PillarOrchestrator(
    name="business_orchestrator",
    model="gemini-2.0-flash",
    description="Orchestrates all business pillars for aligned execution",
    sub_agents=[
        finance_agent,
        operations_agent,
        marketing_agent,
        hr_agent,
        it_agent,
    ],
)

# Example: Configure cross-pillar initiative
# The orchestrator can coordinate complex initiatives that require
# multiple pillars to work together

# Example usage in agent.py:
root_agent = orchestrator

# The orchestrator can now:
# 1. Get enterprise-wide health metrics
# 2. Coordinate cross-functional initiatives
# 3. Resolve conflicts between pillars
# 4. Optimize resource allocation
# 5. Generate executive dashboards
# 6. Analyze dependencies between business functions